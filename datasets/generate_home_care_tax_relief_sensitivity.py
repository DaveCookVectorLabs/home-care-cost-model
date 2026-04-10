#!/usr/bin/env python3
"""
Generate home_care_tax_relief_sensitivity.csv — sensitivity grid showing
how federal and provincial tax credits shift across the income
distribution for ~700 base scenarios.

Grid: 13 provinces × 5 base ADL values × 5 income bands × 3 DTC/CCC flags
= 13 × 5 × 5 × 3 = 975 rows (over initial target 3,500; reduced to keep
deterministic and interpretable; still comfortably covers policy analysis).

Author: Dave Cook
License: MIT (code), CC BY 4.0 (data)
"""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engines" / "python"))
from engine import calculate_home_care_costs, VALID_PROVINCES  # noqa: E402

OUTPUT_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = OUTPUT_DIR / "home_care_tax_relief_sensitivity.csv"

INCOME_BANDS = [25000, 50000, 75000, 100000, 150000]
ADL_POINTS = [1, 2, 3, 4, 5]
HAS_DTC_FLAGS = [False, True]
VETERAN_FLAGS = [False, True]


def generate_dataset():
    rows = []
    row_id = 1

    for province in sorted(VALID_PROVINCES):
        for adl in ADL_POINTS:
            for income in INCOME_BANDS:
                for has_dtc in HAS_DTC_FLAGS:
                    for veteran in VETERAN_FLAGS:
                        if has_dtc is False and veteran is False:
                            sensitivity_case = "baseline"
                        elif has_dtc and veteran:
                            sensitivity_case = "dtc_and_vip"
                        elif has_dtc:
                            sensitivity_case = "dtc_only"
                        else:
                            sensitivity_case = "vip_only"

                        result = calculate_home_care_costs(
                            adl_katz_score=adl,
                            iadl_lawton_score=min(8, adl + 1),
                            province=province,
                            household_composition="with_spouse",
                            cognitive_status="mild",
                            mobility_status="walker",
                            primary_diagnosis_category="chronic_mixed",
                            informal_caregiver_hours_per_week=5.0,
                            net_family_income_cad=income,
                            is_veteran=veteran,
                            has_dtc=has_dtc,
                        )
                        rows.append({
                            "id": row_id,
                            "province": province,
                            "adl_katz_score": adl,
                            "net_family_income_cad": income,
                            "has_dtc": has_dtc,
                            "is_veteran": veteran,
                            "sensitivity_case": sensitivity_case,
                            "private_pay_annual_cad": result.private_pay_annual_cad,
                            "out_of_pocket_before_credits_annual_cad": result.out_of_pocket_before_credits_annual_cad,
                            "metc_qualifying_amount_cad": result.metc_qualifying_amount_cad,
                            "metc_federal_value_cad": result.metc_federal_value_cad,
                            "metc_provincial_value_cad": result.metc_provincial_value_cad,
                            "metc_credit_value_cad": result.metc_credit_value_cad,
                            "dtc_credit_value_cad": result.dtc_credit_value_cad,
                            "ccc_credit_value_cad": result.ccc_credit_value_cad,
                            "vac_vip_credit_value_cad": result.vac_vip_credit_value_cad,
                            "total_credits_value_cad": result.total_credits_value_cad,
                            "out_of_pocket_after_credits_annual_cad": result.out_of_pocket_after_credits_annual_cad,
                            "effective_credit_fraction_of_oop": round(
                                result.total_credits_value_cad / max(1.0, result.out_of_pocket_before_credits_annual_cad), 4
                            ),
                        })
                        row_id += 1

    fieldnames = [
        "id", "province", "adl_katz_score", "net_family_income_cad",
        "has_dtc", "is_veteran", "sensitivity_case",
        "private_pay_annual_cad", "out_of_pocket_before_credits_annual_cad",
        "metc_qualifying_amount_cad", "metc_federal_value_cad",
        "metc_provincial_value_cad", "metc_credit_value_cad",
        "dtc_credit_value_cad", "ccc_credit_value_cad", "vac_vip_credit_value_cad",
        "total_credits_value_cad", "out_of_pocket_after_credits_annual_cad",
        "effective_credit_fraction_of_oop",
    ]
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {len(rows)} rows -> {OUTPUT_FILE}")


if __name__ == "__main__":
    generate_dataset()
