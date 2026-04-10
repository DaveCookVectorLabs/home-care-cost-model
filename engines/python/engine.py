#!/usr/bin/env python3
"""
Home Care Cost Model — Python reference engine

Reference implementation of the home care cost model described in the
accompanying working paper. Takes a recipient's Katz ADL and Lawton IADL
scores, their Canadian province, household composition, cognitive and
mobility status, and primary diagnosis category, and returns a recommended
service mix, private-pay cost, subsidised hours allocation, federal and
provincial tax credit stack, and out-of-pocket cost after credits.

Exposes `POST /calculate` and `GET /health` REST endpoints via FastAPI.
Also runs in CLI mode with a sample calculation.

Reference instruments:
  - Katz S, Ford AB, Moskowitz RW, Jackson BA, Jaffe MW. Studies of Illness
    in the Aged. The Index of ADL. JAMA. 1963;185(12):914-919.
  - Lawton MP, Brody EM. Assessment of older people: self-maintaining and
    instrumental activities of daily living. The Gerontologist. 1969;9(3):
    179-186.

Working paper: https://www.binx.ca/guides/home-care-cost-model-guide.pdf
Maintainer: Dave Cook, Binx Professional Cleaning. This reference model is
not clinical or financial advice; consult a regulated health professional
or registered tax practitioner for individual decisions.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel, Field
    import uvicorn
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

# ──────────────────────────────────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────────────────────────────────

DATASETS_DIR = Path(__file__).resolve().parent.parent.parent / "datasets"
SERVICES_CSV = DATASETS_DIR / "home_care_services_canada.csv"
TAX_CSV = DATASETS_DIR / "home_care_tax_parameters_2026.csv"
SUBSIDY_CSV = DATASETS_DIR / "home_care_subsidy_programs.csv"

# ──────────────────────────────────────────────────────────────────────────
# Enumerations
# ──────────────────────────────────────────────────────────────────────────

VALID_PROVINCES = {
    "ON", "QC", "BC", "AB", "SK", "MB",
    "NS", "NB", "NL", "PE", "YT", "NT", "NU",
}

VALID_HOUSEHOLD = {
    "alone", "with_spouse", "with_adult_child", "multigen",
}

VALID_COGNITIVE = {"intact", "mild", "moderate", "severe"}
VALID_MOBILITY = {"independent", "cane", "walker", "wheelchair", "bedbound"}
VALID_DIAGNOSIS = {
    "dementia", "stroke", "frailty", "parkinson",
    "post_surgical", "mobility_only", "chronic_mixed",
}

VALID_AGENCY_VS_PRIVATE = {"private", "agency"}

# Personal-care category used per province (title varies)
def personal_care_category_for(province: str) -> str:
    if province in ("ON", "QC"):
        return "PSW"
    if province in ("BC", "AB", "SK", "MB"):
        return "HCA"
    return "HSW"

# ──────────────────────────────────────────────────────────────────────────
# Reference data loaders — lazy-initialised singletons
# ──────────────────────────────────────────────────────────────────────────

_SERVICES: Optional[dict] = None
_TAX: Optional[dict] = None
_SUBSIDY: Optional[dict] = None


def load_services() -> dict:
    """Load the services reference table keyed by (province, category)."""
    services = {}
    if not SERVICES_CSV.exists():
        return services
    with open(SERVICES_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row["jurisdiction_code"], row["service_category"])
            services[key] = row
    return services


def load_tax_parameters() -> dict:
    """Load tax parameters keyed by (jurisdiction_code, parameter_category, parameter_name)."""
    params = {}
    if not TAX_CSV.exists():
        return params
    with open(TAX_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row["jurisdiction_code"], row["parameter_category"], row["parameter_name"])
            params[key] = row
    return params


def load_subsidy_programs() -> dict:
    """Load subsidy programs keyed by jurisdiction_code (one primary program each)."""
    programs = {}
    if not SUBSIDY_CSV.exists():
        return programs
    with open(SUBSIDY_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row["jurisdiction_code"]
            if code not in programs:  # take the first program per jurisdiction
                programs[code] = row
    return programs


def get_services():
    global _SERVICES
    if _SERVICES is None:
        _SERVICES = load_services()
    return _SERVICES


def get_tax_parameters():
    global _TAX
    if _TAX is None:
        _TAX = load_tax_parameters()
    return _TAX


def get_subsidy_programs():
    global _SUBSIDY
    if _SUBSIDY is None:
        _SUBSIDY = load_subsidy_programs()
    return _SUBSIDY


def tax_value(jurisdiction: str, category: str, name: str, *, is_rate: bool = False) -> float:
    params = get_tax_parameters()
    row = params.get((jurisdiction, category, name))
    if row is None:
        return 0.0
    return float(row["rate"] if is_rate else row["value_cad"])


def service_rate(province: str, category: str) -> float:
    """Median CAD/hour private-pay rate for (province, service category)."""
    services = get_services()
    row = services.get((province, category))
    if row is None:
        return 0.0
    return float(row["private_pay_rate_cad_median"])


def agency_markup(province: str) -> float:
    services = get_services()
    # Any row for the province will have the same markup column
    for key, row in services.items():
        if key[0] == province:
            return float(row["agency_markup_typical"])
    return 1.35  # reasonable default


# ──────────────────────────────────────────────────────────────────────────
# Assessment-to-hours derivation
# ──────────────────────────────────────────────────────────────────────────

def cognitive_bump_hours(cognitive_status: str) -> float:
    return {
        "intact": 0.0,
        "mild": 3.0,
        "moderate": 8.0,
        "severe": 14.0,
    }.get(cognitive_status, 0.0)


def mobility_bump_hours(mobility_status: str) -> float:
    return {
        "independent": 0.0,
        "cane": 0.5,
        "walker": 2.0,
        "wheelchair": 5.0,
        "bedbound": 12.0,
    }.get(mobility_status, 0.0)


def household_housekeeping_modifier(household_composition: str) -> float:
    return {
        "alone": 3.0,
        "with_spouse": 1.5,
        "with_adult_child": 1.0,
        "multigen": 0.5,
    }.get(household_composition, 2.0)


def diagnosis_nursing_hours(diagnosis: str) -> float:
    """Baseline weekly nursing hours by diagnosis category."""
    return {
        "dementia": 0.0,
        "stroke": 4.0,
        "frailty": 0.0,
        "parkinson": 1.0,
        "post_surgical": 6.0,
        "mobility_only": 0.0,
        "chronic_mixed": 2.0,
    }.get(diagnosis, 0.0)


def derive_psw_hours(
    adl_katz_score: int,
    cognitive_status: str,
    mobility_status: str,
    informal_caregiver_hours_per_week: float,
) -> float:
    """
    Recommended weekly PSW/HCA hours.

    Formula:
        base = 7 * (6 - ADL) + cognitive_bump + mobility_bump
        credited_informal = min(informal_hours * 0.5, base * 0.6)
        hours = max(0, base - credited_informal)

    The informal-caregiver credit is capped at 60% of base to reflect the
    practical reality that family caregivers cannot reliably substitute for
    all formal hours (respite need, employment constraints, burnout risk).
    """
    base = 7.0 * max(0, 6 - adl_katz_score)
    base += cognitive_bump_hours(cognitive_status)
    base += mobility_bump_hours(mobility_status)
    credited = min(informal_caregiver_hours_per_week * 0.5, base * 0.6)
    return round(max(0.0, base - credited), 1)


def derive_housekeeping_hours(
    iadl_lawton_score: int,
    household_composition: str,
) -> float:
    base = 2.0 * max(0, 8 - iadl_lawton_score)
    base += household_housekeeping_modifier(household_composition)
    return round(max(0.0, base), 1)


def derive_nursing_hours(
    primary_diagnosis_category: str,
    cognitive_status: str,
) -> float:
    base = diagnosis_nursing_hours(primary_diagnosis_category)
    if cognitive_status == "severe":
        base += 1.0
    return round(max(0.0, base), 1)


# ──────────────────────────────────────────────────────────────────────────
# Scope gate and nursing gate (hard rules)
# ──────────────────────────────────────────────────────────────────────────

def scope_gate_warnings(
    adl_katz_score: int,
    cognitive_status: str,
    primary_diagnosis_category: str,
    mobility_status: str,
) -> list:
    warnings = []
    if adl_katz_score <= 4 or cognitive_status in ("moderate", "severe"):
        warnings.append(
            "Personal care required: the recipient's ADL score or cognitive "
            "status indicates that personal care tasks (bathing, toileting, "
            "transfers) are needed. A housekeeper or cleaning service cannot "
            "legally substitute for a PSW/HCA in this scope. If a cleaning "
            "service is part of the plan, it must be in addition to, not "
            "instead of, personal support."
        )
    if mobility_status in ("wheelchair", "bedbound") and adl_katz_score >= 5:
        warnings.append(
            "Mobility status suggests transfer assistance despite a high ADL "
            "score. Verify ADL independence in transfers before excluding "
            "personal support hours."
        )
    if primary_diagnosis_category == "dementia" and cognitive_status == "intact":
        warnings.append(
            "Dementia diagnosis is inconsistent with intact cognition. "
            "Verify the cognitive assessment before applying the model."
        )
    return warnings


def nursing_gate_warnings(
    primary_diagnosis_category: str,
    nursing_hours: float,
) -> list:
    warnings = []
    if primary_diagnosis_category in ("stroke", "post_surgical") and nursing_hours == 0:
        warnings.append(
            "Nursing gate: a stroke or post-surgical diagnosis typically "
            "requires LPN/RN hours for medication management, wound care, "
            "and vitals monitoring. Confirm whether a nursing plan exists."
        )
    return warnings


def employment_law_warnings(
    total_private_hours: float,
    agency_vs_private: str,
    province: str,
) -> list:
    warnings = []
    if agency_vs_private == "private" and total_private_hours >= 20:
        warnings.append(
            f"At {total_private_hours:.0f} hours per week of privately-hired "
            f"care in {province}, the CRA employer-determination test is "
            f"likely to classify the family as an employer. Obligations may "
            f"include CPP contributions, EI premiums, provincial WSIB or "
            f"WorkSafe coverage, and T4 reporting. Agency arrangements "
            f"transfer these obligations to the agency as employer of record."
        )
    return warnings


# ──────────────────────────────────────────────────────────────────────────
# Cost calculation
# ──────────────────────────────────────────────────────────────────────────

def subsidised_hours_awarded(province: str, adl_katz_score: int) -> float:
    """
    Estimate weekly PSW/HCA hours allocated by the province's subsidised
    home care program for a recipient with the given ADL score.

    Uses the `typical_psw_hours_per_week_moderate` and `_high` fields from
    home_care_subsidy_programs.csv with a linear interpolation across the
    ADL spectrum.
    """
    programs = get_subsidy_programs()
    row = programs.get(province)
    if row is None:
        return 0.0
    moderate = float(row.get("typical_psw_hours_per_week_moderate", 0) or 0)
    high = float(row.get("typical_psw_hours_per_week_high", 0) or 0)
    # Moderate need roughly corresponds to ADL 4; high to ADL 0
    # Linear interpolation; clamp to [0, high]
    if adl_katz_score >= 5:
        return 0.0
    if adl_katz_score <= 1:
        return round(high, 1)
    # ADL in [2, 4] → interpolate
    alpha = (4 - adl_katz_score) / 3.0
    return round(moderate + alpha * (high - moderate), 1)


def calculate_tax_credits(
    out_of_pocket_annual_cad: float,
    province: str,
    net_family_income_cad: float,
    has_dtc: bool,
    cognitive_status: str,
    household_composition: str,
    is_veteran: bool,
    psw_hours_per_week: float,
) -> dict:
    """Return the full federal + provincial tax relief stack for 2026."""
    # METC — federal
    metc_fed_rate = tax_value("CA-FED", "METC", "federal_rate", is_rate=True)
    metc_floor_frac = tax_value("CA-FED", "METC", "net_income_floor_fraction", is_rate=True)
    metc_abs_floor = tax_value("CA-FED", "METC", "absolute_floor")
    metc_threshold = min(net_family_income_cad * metc_floor_frac, metc_abs_floor)
    metc_qualifying = max(0.0, out_of_pocket_annual_cad - metc_threshold)
    metc_federal_value = metc_qualifying * metc_fed_rate

    # METC — provincial
    metc_prov_rate = tax_value(province, "METC", "provincial_rate", is_rate=True)
    metc_prov_floor = tax_value(province, "METC", "provincial_absolute_floor")
    prov_threshold = min(net_family_income_cad * metc_floor_frac, metc_prov_floor)
    metc_prov_qualifying = max(0.0, out_of_pocket_annual_cad - prov_threshold)
    metc_provincial_value = metc_prov_qualifying * metc_prov_rate

    # DTC
    dtc_value = 0.0
    if has_dtc or cognitive_status == "severe":
        dtc_fed_base = tax_value("CA-FED", "DTC", "base_amount")
        dtc_prov_base = tax_value(province, "DTC", "provincial_base_amount")
        dtc_value = (dtc_fed_base * metc_fed_rate) + (dtc_prov_base * metc_prov_rate)

    # CCC — eligibility heuristic: caregiver living with recipient
    ccc_value = 0.0
    if household_composition in ("with_spouse", "with_adult_child", "multigen"):
        if psw_hours_per_week >= 10:  # indicates meaningful care dependency
            ccc_fed_base = tax_value("CA-FED", "CCC", "caregiver_base")
            ccc_prov_base = tax_value(province, "CCC", "provincial_base_amount")
            phase_start = tax_value("CA-FED", "CCC", "phaseout_start_income")
            phase_end = tax_value("CA-FED", "CCC", "phaseout_end_income")
            if phase_end > phase_start:
                if net_family_income_cad <= phase_start:
                    phase_factor = 1.0
                elif net_family_income_cad >= phase_end:
                    phase_factor = 0.0
                else:
                    phase_factor = 1.0 - (net_family_income_cad - phase_start) / (phase_end - phase_start)
            else:
                phase_factor = 1.0
            ccc_value = ((ccc_fed_base * metc_fed_rate) + (ccc_prov_base * metc_prov_rate)) * phase_factor

    # VAC VIP
    vac_vip_value = 0.0
    if is_veteran:
        housekeeping_ceiling = tax_value("CA-FED", "VIP", "housekeeping_annual_ceiling")
        personal_care_ceiling = tax_value("CA-FED", "VIP", "personal_care_annual_ceiling")
        vac_vip_value = housekeeping_ceiling + personal_care_ceiling

    total = metc_federal_value + metc_provincial_value + dtc_value + ccc_value + vac_vip_value
    return {
        "metc_qualifying_amount_cad": round(metc_qualifying, 2),
        "metc_federal_value_cad": round(metc_federal_value, 2),
        "metc_provincial_value_cad": round(metc_provincial_value, 2),
        "metc_credit_value_cad": round(metc_federal_value + metc_provincial_value, 2),
        "dtc_credit_value_cad": round(dtc_value, 2),
        "ccc_credit_value_cad": round(ccc_value, 2),
        "vac_vip_credit_value_cad": round(vac_vip_value, 2),
        "total_credits_value_cad": round(total, 2),
    }


# ──────────────────────────────────────────────────────────────────────────
# Top-level calculation
# ──────────────────────────────────────────────────────────────────────────

DISCLAIMER = (
    "Reference model only. Not clinical or financial advice; consult a "
    "regulated health professional or registered tax practitioner for "
    "individual decisions."
)


@dataclass
class HomeCareCostCalculation:
    # Inputs echo
    province: str
    adl_katz_score: int
    iadl_lawton_score: int
    household_composition: str
    cognitive_status: str
    mobility_status: str
    primary_diagnosis_category: str
    tax_year: int
    # Recommended service mix
    recommended_psw_hours_per_week: float
    recommended_housekeeping_hours_per_week: float
    recommended_nursing_hours_per_week: float
    recommended_service_mix: str
    rationale: list
    # Cost stack
    psw_hourly_rate_cad: float
    housekeeping_hourly_rate_cad: float
    nursing_hourly_rate_cad: float
    private_pay_monthly_cad: float
    private_pay_annual_cad: float
    subsidy_hours_per_week_allocated: float
    subsidy_value_monthly_cad: float
    out_of_pocket_before_credits_monthly_cad: float
    out_of_pocket_before_credits_annual_cad: float
    # Tax relief
    metc_qualifying_amount_cad: float
    metc_federal_value_cad: float
    metc_provincial_value_cad: float
    metc_credit_value_cad: float
    dtc_credit_value_cad: float
    ccc_credit_value_cad: float
    vac_vip_credit_value_cad: float
    total_credits_value_cad: float
    out_of_pocket_after_credits_monthly_cad: float
    out_of_pocket_after_credits_annual_cad: float
    # Comparison
    all_psw_cost_comparison_monthly_cad: float
    hybrid_savings_vs_all_psw_monthly_cad: float
    # Warnings and provenance
    scope_warnings: list
    nursing_warnings: list
    employment_law_warnings: list
    data_source_citations: list
    currency: str
    disclaimer: str


def calculate_home_care_costs(
    adl_katz_score: int,
    iadl_lawton_score: int,
    province: str,
    household_composition: str,
    cognitive_status: str,
    mobility_status: str,
    primary_diagnosis_category: str,
    informal_caregiver_hours_per_week: float = 0.0,
    net_family_income_cad: float = 60000.0,
    is_veteran: bool = False,
    has_dtc: bool = False,
    agency_vs_private: str = "private",
    include_subsidy: bool = True,
    tax_year: int = 2026,
) -> HomeCareCostCalculation:
    """
    Compute the full home care cost model for a single scenario.

    See the module docstring for input semantics and the working paper
    for the formal derivation of each equation.
    """
    # Input validation
    if province not in VALID_PROVINCES:
        raise ValueError(f"province must be one of {sorted(VALID_PROVINCES)}")
    if household_composition not in VALID_HOUSEHOLD:
        raise ValueError(f"household_composition must be one of {sorted(VALID_HOUSEHOLD)}")
    if cognitive_status not in VALID_COGNITIVE:
        raise ValueError(f"cognitive_status must be one of {sorted(VALID_COGNITIVE)}")
    if mobility_status not in VALID_MOBILITY:
        raise ValueError(f"mobility_status must be one of {sorted(VALID_MOBILITY)}")
    if primary_diagnosis_category not in VALID_DIAGNOSIS:
        raise ValueError(f"primary_diagnosis_category must be one of {sorted(VALID_DIAGNOSIS)}")
    if agency_vs_private not in VALID_AGENCY_VS_PRIVATE:
        raise ValueError(f"agency_vs_private must be one of {sorted(VALID_AGENCY_VS_PRIVATE)}")
    if not (0 <= adl_katz_score <= 6):
        raise ValueError("adl_katz_score must be in [0, 6]")
    if not (0 <= iadl_lawton_score <= 8):
        raise ValueError("iadl_lawton_score must be in [0, 8]")
    if net_family_income_cad < 0:
        raise ValueError("net_family_income_cad must be non-negative")

    # Service mix hours
    psw_hours = derive_psw_hours(
        adl_katz_score, cognitive_status, mobility_status,
        informal_caregiver_hours_per_week,
    )
    housekeeping_hours = derive_housekeeping_hours(iadl_lawton_score, household_composition)
    nursing_hours = derive_nursing_hours(primary_diagnosis_category, cognitive_status)

    # Service mix label
    if nursing_hours > 0 and psw_hours > 0:
        mix = "nursing+psw+housekeeping" if housekeeping_hours > 0 else "nursing+psw"
    elif psw_hours > 0 and housekeeping_hours > 0:
        mix = "psw+housekeeping"
    elif psw_hours > 0:
        mix = "psw_only"
    elif housekeeping_hours > 0:
        mix = "housekeeping_only"
    else:
        mix = "no_formal_services"

    rationale = [
        f"ADL={adl_katz_score} (Katz), IADL={iadl_lawton_score} (Lawton)",
        f"Cognitive={cognitive_status}, mobility={mobility_status}",
        f"Diagnosis={primary_diagnosis_category}, household={household_composition}",
        f"Informal caregiving credited: {min(informal_caregiver_hours_per_week * 0.5, 999):.1f} hrs/wk (capped at 60% of base)",
        f"PSW hours = 7*(6-ADL) + cognitive_bump + mobility_bump - informal credit",
        f"Housekeeping hours = 2*(8-IADL) + household_modifier",
        f"Nursing hours = diagnosis_baseline + cognitive_bump",
    ]

    # Rate lookups
    personal_care_cat = personal_care_category_for(province)
    psw_rate = service_rate(province, personal_care_cat)
    housekeeping_rate = service_rate(province, "Cleaning_Service_Agency") if agency_vs_private == "agency" \
        else service_rate(province, "Housekeeper_Private")
    nursing_rate = service_rate(province, "LPN_RPN")

    if agency_vs_private == "agency":
        markup = agency_markup(province)
        psw_rate = round(psw_rate * markup, 2)
        nursing_rate = round(nursing_rate * markup, 2)

    # Private-pay cost (monthly assumes 4.345 weeks/month)
    WEEKS_PER_MONTH = 4.345
    private_pay_monthly = (
        psw_hours * psw_rate +
        housekeeping_hours * housekeeping_rate +
        nursing_hours * nursing_rate
    ) * WEEKS_PER_MONTH
    private_pay_annual = private_pay_monthly * 12.0

    # Subsidy allocation (applied to PSW hours only)
    if include_subsidy:
        subsidy_hours = subsidised_hours_awarded(province, adl_katz_score)
        subsidy_hours = min(subsidy_hours, psw_hours)
    else:
        subsidy_hours = 0.0
    subsidy_value_monthly = subsidy_hours * psw_rate * WEEKS_PER_MONTH

    out_of_pocket_monthly = max(0.0, private_pay_monthly - subsidy_value_monthly)
    out_of_pocket_annual = out_of_pocket_monthly * 12.0

    # Tax credits
    credits = calculate_tax_credits(
        out_of_pocket_annual_cad=out_of_pocket_annual,
        province=province,
        net_family_income_cad=net_family_income_cad,
        has_dtc=has_dtc,
        cognitive_status=cognitive_status,
        household_composition=household_composition,
        is_veteran=is_veteran,
        psw_hours_per_week=psw_hours,
    )

    out_of_pocket_after_credits_annual = max(0.0, out_of_pocket_annual - credits["total_credits_value_cad"])
    out_of_pocket_after_credits_monthly = out_of_pocket_after_credits_annual / 12.0

    # All-PSW comparison (counterfactual)
    total_hours = psw_hours + housekeeping_hours + nursing_hours
    all_psw_monthly = total_hours * psw_rate * WEEKS_PER_MONTH
    hybrid_savings_monthly = all_psw_monthly - private_pay_monthly

    # Warnings
    scope_w = scope_gate_warnings(adl_katz_score, cognitive_status, primary_diagnosis_category, mobility_status)
    nursing_w = nursing_gate_warnings(primary_diagnosis_category, nursing_hours)
    employment_w = employment_law_warnings(total_hours - subsidy_hours, agency_vs_private, province)

    # Data source citations
    services = get_services()
    citations = set()
    for cat in (personal_care_cat, "Housekeeper_Private", "Cleaning_Service_Agency", "LPN_RPN"):
        row = services.get((province, cat))
        if row and row.get("source_ids"):
            for sid in row["source_ids"].split(";"):
                citations.add(sid.strip())
    citations.add("cra-s1-f1-c1-metc")
    citations.add("cra-s1-f1-c2-dtc")
    citations.add("cra-canada-caregiver-credit")
    if is_veteran:
        citations.add("vac-vip-2026")

    return HomeCareCostCalculation(
        province=province,
        adl_katz_score=adl_katz_score,
        iadl_lawton_score=iadl_lawton_score,
        household_composition=household_composition,
        cognitive_status=cognitive_status,
        mobility_status=mobility_status,
        primary_diagnosis_category=primary_diagnosis_category,
        tax_year=tax_year,
        recommended_psw_hours_per_week=psw_hours,
        recommended_housekeeping_hours_per_week=housekeeping_hours,
        recommended_nursing_hours_per_week=nursing_hours,
        recommended_service_mix=mix,
        rationale=rationale,
        psw_hourly_rate_cad=round(psw_rate, 2),
        housekeeping_hourly_rate_cad=round(housekeeping_rate, 2),
        nursing_hourly_rate_cad=round(nursing_rate, 2),
        private_pay_monthly_cad=round(private_pay_monthly, 2),
        private_pay_annual_cad=round(private_pay_annual, 2),
        subsidy_hours_per_week_allocated=round(subsidy_hours, 1),
        subsidy_value_monthly_cad=round(subsidy_value_monthly, 2),
        out_of_pocket_before_credits_monthly_cad=round(out_of_pocket_monthly, 2),
        out_of_pocket_before_credits_annual_cad=round(out_of_pocket_annual, 2),
        metc_qualifying_amount_cad=credits["metc_qualifying_amount_cad"],
        metc_federal_value_cad=credits["metc_federal_value_cad"],
        metc_provincial_value_cad=credits["metc_provincial_value_cad"],
        metc_credit_value_cad=credits["metc_credit_value_cad"],
        dtc_credit_value_cad=credits["dtc_credit_value_cad"],
        ccc_credit_value_cad=credits["ccc_credit_value_cad"],
        vac_vip_credit_value_cad=credits["vac_vip_credit_value_cad"],
        total_credits_value_cad=credits["total_credits_value_cad"],
        out_of_pocket_after_credits_monthly_cad=round(out_of_pocket_after_credits_monthly, 2),
        out_of_pocket_after_credits_annual_cad=round(out_of_pocket_after_credits_annual, 2),
        all_psw_cost_comparison_monthly_cad=round(all_psw_monthly, 2),
        hybrid_savings_vs_all_psw_monthly_cad=round(hybrid_savings_monthly, 2),
        scope_warnings=scope_w,
        nursing_warnings=nursing_w,
        employment_law_warnings=employment_w,
        data_source_citations=sorted(citations),
        currency="CAD",
        disclaimer=DISCLAIMER,
    )


# ──────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────

def run_sample() -> HomeCareCostCalculation:
    """Worked example: Mr. B., Vancouver BC, moderate dementia post-stroke."""
    return calculate_home_care_costs(
        adl_katz_score=2,
        iadl_lawton_score=1,
        province="BC",
        household_composition="with_spouse",
        cognitive_status="moderate",
        mobility_status="walker",
        primary_diagnosis_category="dementia",
        informal_caregiver_hours_per_week=20.0,
        net_family_income_cad=72000.0,
        is_veteran=False,
        has_dtc=True,
        agency_vs_private="private",
        include_subsidy=True,
        tax_year=2026,
    )


def print_result(result: HomeCareCostCalculation):
    print("Home Care Cost Model — Result")
    print("=" * 70)
    print(f"Jurisdiction: {result.province}   Tax year: {result.tax_year}")
    print(f"ADL (Katz): {result.adl_katz_score}/6   IADL (Lawton): {result.iadl_lawton_score}/8")
    print(f"Cognitive: {result.cognitive_status}   Mobility: {result.mobility_status}")
    print(f"Diagnosis: {result.primary_diagnosis_category}")
    print()
    print("Recommended service mix")
    print(f"  PSW/HCA hours per week:        {result.recommended_psw_hours_per_week}")
    print(f"  Housekeeping hours per week:   {result.recommended_housekeeping_hours_per_week}")
    print(f"  Nursing hours per week:        {result.recommended_nursing_hours_per_week}")
    print(f"  Mix label:                     {result.recommended_service_mix}")
    print()
    print("Cost (CAD, 2026)")
    print(f"  Private pay monthly:           ${result.private_pay_monthly_cad:,.2f}")
    print(f"  Subsidy allocated monthly:     ${result.subsidy_value_monthly_cad:,.2f}")
    print(f"  OoP before credits monthly:    ${result.out_of_pocket_before_credits_monthly_cad:,.2f}")
    print(f"  Tax credits annual:            ${result.total_credits_value_cad:,.2f}")
    print(f"  OoP after credits monthly:     ${result.out_of_pocket_after_credits_monthly_cad:,.2f}")
    print(f"  OoP after credits annual:      ${result.out_of_pocket_after_credits_annual_cad:,.2f}")
    print()
    print("Hybrid vs all-PSW comparison")
    print(f"  All-PSW monthly cost:          ${result.all_psw_cost_comparison_monthly_cad:,.2f}")
    print(f"  Hybrid savings monthly:        ${result.hybrid_savings_vs_all_psw_monthly_cad:,.2f}")
    print()
    if result.scope_warnings:
        print("Scope warnings:")
        for w in result.scope_warnings:
            print(f"  ! {w}")
        print()
    if result.nursing_warnings:
        print("Nursing warnings:")
        for w in result.nursing_warnings:
            print(f"  ! {w}")
        print()
    if result.employment_law_warnings:
        print("Employment law warnings:")
        for w in result.employment_law_warnings:
            print(f"  ! {w}")
        print()
    print("Data source citations:")
    for cite in result.data_source_citations:
        print(f"  - {cite}")
    print()
    print(f"Disclaimer: {result.disclaimer}")


# ──────────────────────────────────────────────────────────────────────────
# FastAPI
# ──────────────────────────────────────────────────────────────────────────

if HAS_FASTAPI:
    app = FastAPI(
        title="Home Care Cost Model",
        description="Reference cost model for Canadian home care service-mix decisions.",
        version="0.1.0",
    )

    class CalculateRequest(BaseModel):
        adl_katz_score: int = Field(..., ge=0, le=6)
        iadl_lawton_score: int = Field(..., ge=0, le=8)
        province: str
        household_composition: str = "alone"
        cognitive_status: str = "intact"
        mobility_status: str = "independent"
        primary_diagnosis_category: str = "frailty"
        informal_caregiver_hours_per_week: float = Field(default=0.0, ge=0)
        net_family_income_cad: float = Field(default=60000.0, ge=0)
        is_veteran: bool = False
        has_dtc: bool = False
        agency_vs_private: str = "private"
        include_subsidy: bool = True
        tax_year: int = 2026

    @app.post("/calculate")
    def api_calculate(req: CalculateRequest):
        try:
            result = calculate_home_care_costs(
                adl_katz_score=req.adl_katz_score,
                iadl_lawton_score=req.iadl_lawton_score,
                province=req.province,
                household_composition=req.household_composition,
                cognitive_status=req.cognitive_status,
                mobility_status=req.mobility_status,
                primary_diagnosis_category=req.primary_diagnosis_category,
                informal_caregiver_hours_per_week=req.informal_caregiver_hours_per_week,
                net_family_income_cad=req.net_family_income_cad,
                is_veteran=req.is_veteran,
                has_dtc=req.has_dtc,
                agency_vs_private=req.agency_vs_private,
                include_subsidy=req.include_subsidy,
                tax_year=req.tax_year,
            )
            return asdict(result)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.get("/health")
    def health():
        services = get_services()
        tax = get_tax_parameters()
        subsidies = get_subsidy_programs()
        return {
            "status": "ok",
            "engine": "python",
            "version": "0.1.0",
            "port": 8003,
            "reference_tables_loaded": {
                "home_care_services_canada": len(services),
                "home_care_tax_parameters_2026": len(tax),
                "home_care_subsidy_programs": len(subsidies),
            },
            "disclaimer": DISCLAIMER,
        }


# ──────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Home Care Cost Model engine")
    parser.add_argument("--serve", action="store_true", help="Run HTTP server")
    parser.add_argument("--port", type=int, default=8003, help="HTTP server port")
    parser.add_argument("--sample", action="store_true", help="Run sample calculation and print result")
    parser.add_argument("--json", action="store_true", help="Emit sample as JSON")
    args = parser.parse_args()

    if args.serve:
        if not HAS_FASTAPI:
            print("FastAPI not installed. Run: pip install fastapi uvicorn pydantic", file=sys.stderr)
            sys.exit(1)
        uvicorn.run(app, host="0.0.0.0", port=args.port)
    else:
        result = run_sample()
        if args.json:
            print(json.dumps(asdict(result), indent=2, default=str))
        else:
            print_result(result)


if __name__ == "__main__":
    main()
