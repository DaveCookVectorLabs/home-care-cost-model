#!/usr/bin/env python3
"""
Generate home_care_subsidy_gap.csv — 13 jurisdictions × 30 representative
scenarios showing subsidised hours awarded vs model-recommended hours vs
monthly dollar gap. Exposes the cross-province inequity in home care
program generosity.

Author: Dave Cook
License: MIT (code), CC BY 4.0 (data)
"""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engines" / "python"))
from engine import calculate_home_care_costs, VALID_PROVINCES  # noqa: E402

OUTPUT_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = OUTPUT_DIR / "home_care_subsidy_gap.csv"

# 30 representative scenario profiles, designed to span the assessment space
SCENARIOS = [
    # (profile_id, adl, iadl, cognitive, mobility, diagnosis, household)
    ("A01-MildFrailty-Alone",        5, 5, "intact", "cane",        "frailty",       "alone"),
    ("A02-MildFrailty-Spouse",       5, 5, "intact", "cane",        "frailty",       "with_spouse"),
    ("A03-MildCognitive-Alone",      5, 4, "mild", "cane",          "dementia",      "alone"),
    ("A04-MildCognitive-Spouse",     5, 4, "mild", "cane",          "dementia",      "with_spouse"),
    ("A05-ParkinsonsEarly-Spouse",   4, 4, "intact", "cane",        "parkinson",     "with_spouse"),

    ("B06-ModerateFrailty-Alone",    4, 3, "mild", "walker",        "frailty",       "alone"),
    ("B07-ModerateFrailty-Spouse",   4, 3, "mild", "walker",        "frailty",       "with_spouse"),
    ("B08-PostSurgical-Spouse",      4, 4, "intact", "walker",      "post_surgical", "with_spouse"),
    ("B09-ChronicMixed-Spouse",      4, 3, "mild", "walker",        "chronic_mixed", "with_spouse"),
    ("B10-EarlyStroke-Spouse",       4, 2, "mild", "walker",        "stroke",        "with_spouse"),

    ("C11-ModerateDementia-Spouse",  3, 2, "moderate", "walker",    "dementia",      "with_spouse"),
    ("C12-ModerateDementia-Child",   3, 2, "moderate", "walker",    "dementia",      "with_adult_child"),
    ("C13-ParkinsonsAdvancing",      3, 2, "mild", "wheelchair",    "parkinson",     "with_spouse"),
    ("C14-StrokeRecovery",           3, 2, "moderate", "wheelchair","stroke",        "with_spouse"),
    ("C15-ModerateMultiDx-Alone",    3, 2, "moderate", "walker",    "chronic_mixed", "alone"),

    ("D16-SevereDementia-Spouse",    2, 1, "severe", "wheelchair",  "dementia",      "with_spouse"),
    ("D17-SevereDementia-Multigen",  2, 1, "severe", "wheelchair",  "dementia",      "multigen"),
    ("D18-DenseStroke",              2, 1, "severe", "bedbound",    "stroke",        "with_spouse"),
    ("D19-EndStageParkinsons",       2, 1, "severe", "wheelchair",  "parkinson",     "with_adult_child"),
    ("D20-CompoundComplex",          2, 1, "moderate", "bedbound",  "chronic_mixed", "with_adult_child"),

    ("E21-BedboundSevere-Spouse",    1, 0, "severe", "bedbound",    "dementia",      "with_spouse"),
    ("E22-BedboundSevere-Alone",     1, 0, "severe", "bedbound",    "chronic_mixed", "alone"),
    ("E23-TerminalCare",             0, 0, "severe", "bedbound",    "chronic_mixed", "with_spouse"),
    ("E24-FullSupport-Multigen",     0, 0, "severe", "bedbound",    "stroke",        "multigen"),

    ("F25-VeteranFrailty-Alone",     4, 3, "mild", "walker",        "frailty",       "alone"),
    ("F26-VeteranDementia-Spouse",   3, 2, "moderate", "walker",    "dementia",      "with_spouse"),
    ("F27-VeteranStroke",            2, 1, "moderate", "wheelchair","stroke",        "with_spouse"),

    ("G28-DiabetesHypertension",     4, 4, "intact", "cane",        "chronic_mixed", "with_spouse"),
    ("G29-MSProgressive",            3, 2, "mild", "wheelchair",    "mobility_only", "with_spouse"),
    ("G30-PostFallRecovery",         4, 3, "intact", "walker",      "post_surgical", "alone"),
]

IS_VETERAN_FOR = lambda pid: pid.startswith("F")


def generate_dataset():
    rows = []
    row_id = 1
    for province in sorted(VALID_PROVINCES):
        for pid, adl, iadl, cognitive, mobility, diagnosis, household in SCENARIOS:
            result = calculate_home_care_costs(
                adl_katz_score=adl,
                iadl_lawton_score=iadl,
                province=province,
                household_composition=household,
                cognitive_status=cognitive,
                mobility_status=mobility,
                primary_diagnosis_category=diagnosis,
                informal_caregiver_hours_per_week=0.0,
                net_family_income_cad=55000.0,
                is_veteran=IS_VETERAN_FOR(pid),
            )
            model_recommended_hours = (
                result.recommended_psw_hours_per_week +
                result.recommended_nursing_hours_per_week
            )
            subsidised_hours = result.subsidy_hours_per_week_allocated
            hours_gap = max(0.0, model_recommended_hours - subsidised_hours)
            dollar_gap_monthly = hours_gap * result.psw_hourly_rate_cad * 4.345

            rows.append({
                "id": row_id,
                "jurisdiction_code": province,
                "scenario_id": pid,
                "adl_katz_score": adl,
                "iadl_lawton_score": iadl,
                "cognitive_status": cognitive,
                "mobility_status": mobility,
                "diagnosis": diagnosis,
                "household_composition": household,
                "is_veteran": IS_VETERAN_FOR(pid),
                "model_recommended_personal_care_hours_per_week": round(model_recommended_hours, 1),
                "subsidised_hours_per_week_allocated": subsidised_hours,
                "hours_gap_per_week": round(hours_gap, 1),
                "psw_hourly_rate_cad": result.psw_hourly_rate_cad,
                "dollar_gap_monthly_cad": round(dollar_gap_monthly, 2),
                "dollar_gap_annual_cad": round(dollar_gap_monthly * 12, 2),
                "private_pay_monthly_cad": result.private_pay_monthly_cad,
                "out_of_pocket_before_credits_monthly_cad": result.out_of_pocket_before_credits_monthly_cad,
                "out_of_pocket_after_credits_monthly_cad": result.out_of_pocket_after_credits_monthly_cad,
            })
            row_id += 1

    fieldnames = [
        "id", "jurisdiction_code", "scenario_id",
        "adl_katz_score", "iadl_lawton_score", "cognitive_status",
        "mobility_status", "diagnosis", "household_composition", "is_veteran",
        "model_recommended_personal_care_hours_per_week",
        "subsidised_hours_per_week_allocated",
        "hours_gap_per_week",
        "psw_hourly_rate_cad",
        "dollar_gap_monthly_cad",
        "dollar_gap_annual_cad",
        "private_pay_monthly_cad",
        "out_of_pocket_before_credits_monthly_cad",
        "out_of_pocket_after_credits_monthly_cad",
    ]
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {len(rows)} rows -> {OUTPUT_FILE}")


if __name__ == "__main__":
    generate_dataset()
