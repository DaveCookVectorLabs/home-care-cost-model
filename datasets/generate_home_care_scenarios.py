#!/usr/bin/env python3
"""
Generate home_care_scenarios.csv — 5,000 synthetic household scenarios.

Each scenario samples a recipient and household profile, then runs the
Python reference engine to compute the full cost stack.

Deterministic with random.seed(42).

Sampling calibration:
  - province weighted by StatsCan 17-10-0005-01 65+ population share
  - joint (diagnosis, cognitive, mobility) distribution approximated from
    CIHI Home Care Reporting System indicator patterns
  - ADL/IADL scores derived from the functional state triple
  - net_family_income sampled from a log-normal calibrated to 65+ CCB

Author: Dave Cook
License: MIT (code), CC BY 4.0 (data)
"""

import csv
import os
import random
import sys
from pathlib import Path

# Import the engine
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engines" / "python"))
from engine import calculate_home_care_costs, VALID_PROVINCES  # noqa: E402

OUTPUT_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = OUTPUT_DIR / "home_care_scenarios.csv"
NUM_SCENARIOS = 5000
SEED = 42

random.seed(SEED)

# ──────────────────────────────────────────────────────────────────────────
# Sampling distributions
# ──────────────────────────────────────────────────────────────────────────

# Province weights — StatsCan 17-10-0005-01 July 2024, 65+ share (approx)
PROVINCE_WEIGHTS = [
    ("ON", 0.395),
    ("QC", 0.234),
    ("BC", 0.145),
    ("AB", 0.104),
    ("SK", 0.029),
    ("MB", 0.032),
    ("NS", 0.031),
    ("NB", 0.024),
    ("NL", 0.015),
    ("PE", 0.005),
    ("YT", 0.0014),
    ("NT", 0.0008),
    ("NU", 0.0008),
]

RURALITY_WEIGHTS = [("urban", 0.65), ("suburban", 0.18), ("rural", 0.14), ("remote", 0.03)]

HOUSEHOLD_WEIGHTS = [
    ("alone", 0.38),
    ("with_spouse", 0.41),
    ("with_adult_child", 0.15),
    ("multigen", 0.06),
]

# Joint diagnosis distribution for home-care 65+ population
DIAGNOSIS_WEIGHTS = [
    ("dementia", 0.22),
    ("frailty", 0.28),
    ("mobility_only", 0.14),
    ("chronic_mixed", 0.18),
    ("stroke", 0.08),
    ("parkinson", 0.05),
    ("post_surgical", 0.05),
]

# Age distribution (truncated normal)
AGE_MIN = 55
AGE_MAX = 98
AGE_MEAN = 78
AGE_SD = 8


def weighted_choice(pairs):
    total = sum(w for _, w in pairs)
    r = random.uniform(0, total)
    cum = 0
    for item, w in pairs:
        cum += w
        if r <= cum:
            return item
    return pairs[-1][0]


def sample_age():
    while True:
        a = int(round(random.gauss(AGE_MEAN, AGE_SD)))
        if AGE_MIN <= a <= AGE_MAX:
            return a


def sample_cognition_given_diagnosis(diagnosis: str) -> str:
    if diagnosis == "dementia":
        return weighted_choice([("mild", 0.25), ("moderate", 0.45), ("severe", 0.30)])
    if diagnosis == "stroke":
        return weighted_choice([("intact", 0.35), ("mild", 0.35), ("moderate", 0.25), ("severe", 0.05)])
    if diagnosis == "parkinson":
        return weighted_choice([("intact", 0.45), ("mild", 0.35), ("moderate", 0.15), ("severe", 0.05)])
    if diagnosis == "post_surgical":
        return weighted_choice([("intact", 0.70), ("mild", 0.20), ("moderate", 0.10)])
    if diagnosis == "frailty":
        return weighted_choice([("intact", 0.55), ("mild", 0.30), ("moderate", 0.13), ("severe", 0.02)])
    if diagnosis == "mobility_only":
        return weighted_choice([("intact", 0.85), ("mild", 0.13), ("moderate", 0.02)])
    return weighted_choice([("intact", 0.50), ("mild", 0.30), ("moderate", 0.15), ("severe", 0.05)])


def sample_mobility_given_diagnosis(diagnosis: str) -> str:
    if diagnosis == "stroke":
        return weighted_choice([("walker", 0.35), ("wheelchair", 0.35), ("bedbound", 0.15), ("cane", 0.15)])
    if diagnosis == "parkinson":
        return weighted_choice([("cane", 0.25), ("walker", 0.45), ("wheelchair", 0.25), ("bedbound", 0.05)])
    if diagnosis == "mobility_only":
        return weighted_choice([("cane", 0.35), ("walker", 0.40), ("wheelchair", 0.20), ("bedbound", 0.05)])
    if diagnosis == "post_surgical":
        return weighted_choice([("walker", 0.55), ("cane", 0.25), ("wheelchair", 0.15), ("independent", 0.05)])
    if diagnosis == "dementia":
        return weighted_choice([("independent", 0.25), ("cane", 0.35), ("walker", 0.25), ("wheelchair", 0.10), ("bedbound", 0.05)])
    return weighted_choice([("independent", 0.30), ("cane", 0.35), ("walker", 0.20), ("wheelchair", 0.10), ("bedbound", 0.05)])


def derive_adl_from_state(cognitive: str, mobility: str, diagnosis: str) -> int:
    """Derive Katz ADL (0=total dependence, 6=independent) from the state triple."""
    base = 6
    base -= {"intact": 0, "mild": 0, "moderate": 1, "severe": 2}[cognitive]
    base -= {"independent": 0, "cane": 0, "walker": 1, "wheelchair": 3, "bedbound": 5}[mobility]
    if diagnosis in ("stroke", "post_surgical"):
        base -= 1
    base += random.choice([-1, 0, 0, 0, 1])  # small noise
    return max(0, min(6, base))


def derive_iadl_from_state(cognitive: str, mobility: str, adl: int) -> int:
    """Derive Lawton IADL (0=total dependence, 8=independent) from state."""
    base = 8
    base -= {"intact": 0, "mild": 1, "moderate": 3, "severe": 5}[cognitive]
    base -= {"independent": 0, "cane": 0, "walker": 1, "wheelchair": 2, "bedbound": 4}[mobility]
    # IADL is highly correlated with ADL but independently attenuated by cognition
    if adl <= 2:
        base = min(base, adl + 1)
    base += random.choice([-1, 0, 0, 0, 1])
    return max(0, min(8, base))


def sample_informal_hours(household: str) -> float:
    if household == "alone":
        return round(max(0, random.gauss(5, 4)), 1)
    if household == "with_spouse":
        return round(max(0, random.gauss(25, 12)), 1)
    if household == "with_adult_child":
        return round(max(0, random.gauss(15, 10)), 1)
    return round(max(0, random.gauss(30, 15)), 1)


def sample_net_family_income() -> float:
    # Log-normal; median around $52k for 65+ households
    return round(max(15000, random.lognormvariate(10.85, 0.45)), 0)


def sample_is_veteran() -> bool:
    return random.random() < 0.04


def sample_has_dtc(cognitive: str, adl: int) -> bool:
    if cognitive == "severe":
        return True
    if adl <= 2:
        return random.random() < 0.60
    if adl <= 4:
        return random.random() < 0.25
    return random.random() < 0.05


def sample_nihb_eligible(province: str) -> bool:
    # Rough weighting by Indigenous population share; NU highest
    base = {
        "NU": 0.85, "NT": 0.50, "YT": 0.25, "MB": 0.18, "SK": 0.17,
        "AB": 0.07, "BC": 0.06, "ON": 0.03, "NB": 0.04, "NL": 0.10,
        "NS": 0.06, "PE": 0.02, "QC": 0.02,
    }
    return random.random() < base.get(province, 0.03)


def generate_dataset():
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "scenario_id", "province", "rurality", "recipient_age", "recipient_sex",
            "household_composition", "primary_diagnosis_category",
            "cognitive_status", "mobility_status",
            "adl_katz_score", "iadl_lawton_score",
            "informal_caregiver_hours_per_week", "net_family_income_cad",
            "is_veteran", "has_dtc", "nihb_eligible",
            "recommended_psw_hours_per_week", "recommended_housekeeping_hours_per_week",
            "recommended_nursing_hours_per_week", "recommended_service_mix",
            "psw_hourly_rate_cad", "housekeeping_hourly_rate_cad", "nursing_hourly_rate_cad",
            "private_pay_monthly_cad", "private_pay_annual_cad",
            "subsidy_hours_per_week_allocated", "subsidy_value_monthly_cad",
            "out_of_pocket_before_credits_monthly_cad",
            "metc_qualifying_amount_cad", "metc_credit_value_cad",
            "dtc_credit_value_cad", "ccc_credit_value_cad", "vac_vip_credit_value_cad",
            "total_credits_value_cad",
            "out_of_pocket_after_credits_monthly_cad",
            "out_of_pocket_after_credits_annual_cad",
            "all_psw_cost_comparison_monthly_cad",
            "hybrid_savings_vs_all_psw_monthly_cad",
            "scope_warning_triggered", "nursing_warning_triggered",
            "employment_law_warning_triggered",
            "data_source_citations",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        # Header comment
        f.flush()

        for i in range(1, NUM_SCENARIOS + 1):
            province = weighted_choice(PROVINCE_WEIGHTS)
            rurality = weighted_choice(RURALITY_WEIGHTS)
            age = sample_age()
            sex = random.choice(["F", "F", "F", "M"])  # women disproportionate 65+
            household = weighted_choice(HOUSEHOLD_WEIGHTS)
            diagnosis = weighted_choice(DIAGNOSIS_WEIGHTS)
            cognitive = sample_cognition_given_diagnosis(diagnosis)
            mobility = sample_mobility_given_diagnosis(diagnosis)
            adl = derive_adl_from_state(cognitive, mobility, diagnosis)
            iadl = derive_iadl_from_state(cognitive, mobility, adl)
            informal = sample_informal_hours(household)
            income = sample_net_family_income()
            veteran = sample_is_veteran()
            dtc = sample_has_dtc(cognitive, adl)
            nihb = sample_nihb_eligible(province)

            try:
                result = calculate_home_care_costs(
                    adl_katz_score=adl,
                    iadl_lawton_score=iadl,
                    province=province,
                    household_composition=household,
                    cognitive_status=cognitive,
                    mobility_status=mobility,
                    primary_diagnosis_category=diagnosis,
                    informal_caregiver_hours_per_week=informal,
                    net_family_income_cad=income,
                    is_veteran=veteran,
                    has_dtc=dtc,
                    agency_vs_private="private",
                    include_subsidy=True,
                    tax_year=2026,
                )
            except ValueError as e:
                print(f"Scenario {i} failed: {e}", file=sys.stderr)
                continue

            writer.writerow({
                "scenario_id": f"HCM-{i:05d}",
                "province": province,
                "rurality": rurality,
                "recipient_age": age,
                "recipient_sex": sex,
                "household_composition": household,
                "primary_diagnosis_category": diagnosis,
                "cognitive_status": cognitive,
                "mobility_status": mobility,
                "adl_katz_score": adl,
                "iadl_lawton_score": iadl,
                "informal_caregiver_hours_per_week": informal,
                "net_family_income_cad": income,
                "is_veteran": veteran,
                "has_dtc": dtc,
                "nihb_eligible": nihb,
                "recommended_psw_hours_per_week": result.recommended_psw_hours_per_week,
                "recommended_housekeeping_hours_per_week": result.recommended_housekeeping_hours_per_week,
                "recommended_nursing_hours_per_week": result.recommended_nursing_hours_per_week,
                "recommended_service_mix": result.recommended_service_mix,
                "psw_hourly_rate_cad": result.psw_hourly_rate_cad,
                "housekeeping_hourly_rate_cad": result.housekeeping_hourly_rate_cad,
                "nursing_hourly_rate_cad": result.nursing_hourly_rate_cad,
                "private_pay_monthly_cad": result.private_pay_monthly_cad,
                "private_pay_annual_cad": result.private_pay_annual_cad,
                "subsidy_hours_per_week_allocated": result.subsidy_hours_per_week_allocated,
                "subsidy_value_monthly_cad": result.subsidy_value_monthly_cad,
                "out_of_pocket_before_credits_monthly_cad": result.out_of_pocket_before_credits_monthly_cad,
                "metc_qualifying_amount_cad": result.metc_qualifying_amount_cad,
                "metc_credit_value_cad": result.metc_credit_value_cad,
                "dtc_credit_value_cad": result.dtc_credit_value_cad,
                "ccc_credit_value_cad": result.ccc_credit_value_cad,
                "vac_vip_credit_value_cad": result.vac_vip_credit_value_cad,
                "total_credits_value_cad": result.total_credits_value_cad,
                "out_of_pocket_after_credits_monthly_cad": result.out_of_pocket_after_credits_monthly_cad,
                "out_of_pocket_after_credits_annual_cad": result.out_of_pocket_after_credits_annual_cad,
                "all_psw_cost_comparison_monthly_cad": result.all_psw_cost_comparison_monthly_cad,
                "hybrid_savings_vs_all_psw_monthly_cad": result.hybrid_savings_vs_all_psw_monthly_cad,
                "scope_warning_triggered": len(result.scope_warnings) > 0,
                "nursing_warning_triggered": len(result.nursing_warnings) > 0,
                "employment_law_warning_triggered": len(result.employment_law_warnings) > 0,
                "data_source_citations": ";".join(result.data_source_citations),
            })

    print(f"Generated {NUM_SCENARIOS} scenarios -> {OUTPUT_FILE}")
    print("Note: Synthetic. Generated from seed 42. Not survey data.")


if __name__ == "__main__":
    generate_dataset()
