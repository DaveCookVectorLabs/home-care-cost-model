#!/usr/bin/env python3
"""
Generate home_care_cost_model_archetypes.csv — engine outputs for a grid
of canonical household archetypes. This is the "lookup table" form of the
calculator: a family can find the row matching their province and
assessment triple and read the costs directly without running Python.

Grid: 13 provinces × 7 ADL values × 5 cognitive × 5 mobility = 2,275 rows.
At constant household_composition=with_spouse and net_family_income_cad=55000.

Author: Dave Cook
License: MIT (code), CC BY 4.0 (data)
"""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engines" / "python"))
from engine import (  # noqa: E402
    calculate_home_care_costs, VALID_PROVINCES, VALID_COGNITIVE, VALID_MOBILITY,
)

OUTPUT_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = OUTPUT_DIR / "home_care_cost_model_archetypes.csv"

CONSTANT_HOUSEHOLD = "with_spouse"
CONSTANT_INCOME = 55000.0
CONSTANT_DIAGNOSIS = "chronic_mixed"
CONSTANT_IADL_DELTA_FROM_ADL = 0  # IADL = ADL by default in this grid


def generate_dataset():
    rows = []
    row_id = 1

    cognitive_order = ["intact", "mild", "moderate", "severe"]
    mobility_order = ["independent", "cane", "walker", "wheelchair", "bedbound"]

    for province in sorted(VALID_PROVINCES):
        for adl in range(0, 7):
            iadl = min(8, max(0, adl + 1))
            for cognitive in cognitive_order:
                for mobility in mobility_order:
                    result = calculate_home_care_costs(
                        adl_katz_score=adl,
                        iadl_lawton_score=iadl,
                        province=province,
                        household_composition=CONSTANT_HOUSEHOLD,
                        cognitive_status=cognitive,
                        mobility_status=mobility,
                        primary_diagnosis_category=CONSTANT_DIAGNOSIS,
                        informal_caregiver_hours_per_week=0.0,
                        net_family_income_cad=CONSTANT_INCOME,
                    )
                    rows.append({
                        "id": row_id,
                        "province": province,
                        "adl_katz_score": adl,
                        "iadl_lawton_score": iadl,
                        "cognitive_status": cognitive,
                        "mobility_status": mobility,
                        "household_composition": CONSTANT_HOUSEHOLD,
                        "primary_diagnosis_category": CONSTANT_DIAGNOSIS,
                        "net_family_income_cad": CONSTANT_INCOME,
                        "recommended_psw_hours_per_week": result.recommended_psw_hours_per_week,
                        "recommended_housekeeping_hours_per_week": result.recommended_housekeeping_hours_per_week,
                        "recommended_nursing_hours_per_week": result.recommended_nursing_hours_per_week,
                        "recommended_service_mix": result.recommended_service_mix,
                        "private_pay_monthly_cad": result.private_pay_monthly_cad,
                        "subsidy_value_monthly_cad": result.subsidy_value_monthly_cad,
                        "out_of_pocket_before_credits_monthly_cad": result.out_of_pocket_before_credits_monthly_cad,
                        "total_credits_value_cad_annual": result.total_credits_value_cad,
                        "out_of_pocket_after_credits_monthly_cad": result.out_of_pocket_after_credits_monthly_cad,
                        "out_of_pocket_after_credits_annual_cad": result.out_of_pocket_after_credits_annual_cad,
                        "all_psw_cost_comparison_monthly_cad": result.all_psw_cost_comparison_monthly_cad,
                        "hybrid_savings_vs_all_psw_monthly_cad": result.hybrid_savings_vs_all_psw_monthly_cad,
                        "scope_warning_triggered": len(result.scope_warnings) > 0,
                    })
                    row_id += 1

    fieldnames = [
        "id", "province", "adl_katz_score", "iadl_lawton_score",
        "cognitive_status", "mobility_status", "household_composition",
        "primary_diagnosis_category", "net_family_income_cad",
        "recommended_psw_hours_per_week", "recommended_housekeeping_hours_per_week",
        "recommended_nursing_hours_per_week", "recommended_service_mix",
        "private_pay_monthly_cad", "subsidy_value_monthly_cad",
        "out_of_pocket_before_credits_monthly_cad",
        "total_credits_value_cad_annual",
        "out_of_pocket_after_credits_monthly_cad",
        "out_of_pocket_after_credits_annual_cad",
        "all_psw_cost_comparison_monthly_cad",
        "hybrid_savings_vs_all_psw_monthly_cad",
        "scope_warning_triggered",
    ]
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {len(rows)} rows -> {OUTPUT_FILE}")


if __name__ == "__main__":
    generate_dataset()
