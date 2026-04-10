#!/usr/bin/env python3
"""
Generate home_care_tax_parameters_2026.csv — tax year 2026 federal and
provincial tax parameters for the home care cost model.

Captures:
  - Medical Expense Tax Credit (METC) — federal and provincial factors,
    3% of net income floor, $2,759 absolute floor (2026)
  - Disability Tax Credit (DTC) — base amount, supplement for under-18
  - Canada Caregiver Credit (CCC) — base, supplement, income test
  - Veterans Independence Program (VIP) — reimbursement ceilings
  - Provincial disability supplements (where available)

All monetary values are stated in CAD and indexed to the 2026 taxation year.
Every row cites a CRA folio or equivalent source via `source_id`.

Author: Dave Cook
License: MIT (code), CC BY 4.0 (data)
"""

import csv
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "home_care_tax_parameters_2026.csv")

RETRIEVED_DATE = "2026-04-09"
TAX_YEAR = 2026

# ──────────────────────────────────────────────────────────────────────────
# Federal parameters
# ──────────────────────────────────────────────────────────────────────────

# METC 2026 — CRA S1-F1-C1
METC_FEDERAL_RATE = 0.15      # lowest federal bracket rate
METC_NET_INCOME_FLOOR = 0.03   # 3% of net income
METC_ABSOLUTE_FLOOR = 2759     # $2,759 ceiling on the 3% floor (indexed 2026)

# DTC 2026 — CRA S1-F1-C2
DTC_BASE_2026 = 9872
DTC_SUPPLEMENT_UNDER_18 = 5758
DTC_SUPPLEMENT_CLAWBACK_THRESHOLD = 33730

# Canada Caregiver Credit 2026
CCC_INFIRM_DEPENDANT_BASE = 2635     # infirm dependant amount
CCC_CAREGIVER_BASE = 8375            # caregiver amount
CCC_INCOME_PHASEOUT_START = 19666    # threshold where CCC starts to reduce
CCC_INCOME_PHASEOUT_END = 28041      # threshold where CCC is fully clawed back

# VAC VIP 2026 (approximate annual ceilings — see VAC for individual amounts)
VIP_HOUSEKEEPING_ANNUAL_CEILING = 3072
VIP_GROUNDS_ANNUAL_CEILING = 1884
VIP_PERSONAL_CARE_ANNUAL_CEILING = 9324

# ──────────────────────────────────────────────────────────────────────────
# Provincial tax factors (lowest bracket rate for non-refundable credits)
# Source: provincial budgets + CRA T1 General Schedule for each province
# ──────────────────────────────────────────────────────────────────────────

PROVINCIAL_FACTORS = {
    "ON": {
        "name": "Ontario",
        "lowest_bracket_rate": 0.0505,
        "metc_net_income_floor": 0.03,
        "metc_absolute_floor": 2923,
        "dtc_provincial_base": 10250,
        "ccc_provincial_base": 5933,
        "notes": "Ontario Disability Amount separate from federal DTC; computed on Schedule ON428",
        "source": "cra-s1-f1-c1-metc; ontario-428",
    },
    "QC": {
        "name": "Quebec",
        "lowest_bracket_rate": 0.14,  # Quebec has its own tax system
        "metc_net_income_floor": 0.03,
        "metc_absolute_floor": 2759,
        "dtc_provincial_base": 3494,
        "ccc_provincial_base": 1311,
        "notes": "Quebec administers its own provincial tax credits via Revenu Québec; amounts from Schedule B",
        "source": "cra-s1-f1-c1-metc; revenu-quebec-tp1",
    },
    "BC": {
        "name": "British Columbia",
        "lowest_bracket_rate": 0.0506,
        "metc_net_income_floor": 0.03,
        "metc_absolute_floor": 2605,
        "dtc_provincial_base": 9428,
        "ccc_provincial_base": 5014,
        "notes": "BC credits computed on BC428",
        "source": "cra-s1-f1-c1-metc; bc-428",
    },
    "AB": {
        "name": "Alberta",
        "lowest_bracket_rate": 0.10,
        "metc_net_income_floor": 0.03,
        "metc_absolute_floor": 2824,
        "dtc_provincial_base": 16066,
        "ccc_provincial_base": 12307,
        "notes": "Alberta has flat 10% lowest bracket; generous DTC base",
        "source": "cra-s1-f1-c1-metc; ab-428",
    },
    "SK": {
        "name": "Saskatchewan",
        "lowest_bracket_rate": 0.105,
        "metc_net_income_floor": 0.03,
        "metc_absolute_floor": 2837,
        "dtc_provincial_base": 10405,
        "ccc_provincial_base": 10405,
        "notes": "SK credits computed on SK428",
        "source": "cra-s1-f1-c1-metc; sk-428",
    },
    "MB": {
        "name": "Manitoba",
        "lowest_bracket_rate": 0.108,
        "metc_net_income_floor": 0.03,
        "metc_absolute_floor": 1728,
        "dtc_provincial_base": 6180,
        "ccc_provincial_base": 3605,
        "notes": "Lower provincial DTC base than most provinces",
        "source": "cra-s1-f1-c1-metc; mb-428",
    },
    "NS": {
        "name": "Nova Scotia",
        "lowest_bracket_rate": 0.0879,
        "metc_net_income_floor": 0.03,
        "metc_absolute_floor": 1637,
        "dtc_provincial_base": 7341,
        "ccc_provincial_base": 4898,
        "notes": "NS credits computed on NS428",
        "source": "cra-s1-f1-c1-metc; ns-428",
    },
    "NB": {
        "name": "New Brunswick",
        "lowest_bracket_rate": 0.094,
        "metc_net_income_floor": 0.03,
        "metc_absolute_floor": 2344,
        "dtc_provincial_base": 8552,
        "ccc_provincial_base": 5197,
        "notes": "NB credits computed on NB428",
        "source": "cra-s1-f1-c1-metc; nb-428",
    },
    "NL": {
        "name": "Newfoundland and Labrador",
        "lowest_bracket_rate": 0.087,
        "metc_net_income_floor": 0.03,
        "metc_absolute_floor": 2116,
        "dtc_provincial_base": 7064,
        "ccc_provincial_base": 3497,
        "notes": "NL credits computed on NL428",
        "source": "cra-s1-f1-c1-metc; nl-428",
    },
    "PE": {
        "name": "Prince Edward Island",
        "lowest_bracket_rate": 0.098,
        "metc_net_income_floor": 0.03,
        "metc_absolute_floor": 1768,
        "dtc_provincial_base": 6890,
        "ccc_provincial_base": 2446,
        "notes": "PE credits computed on PE428",
        "source": "cra-s1-f1-c1-metc; pe-428",
    },
    "YT": {
        "name": "Yukon",
        "lowest_bracket_rate": 0.064,
        "metc_net_income_floor": 0.03,
        "metc_absolute_floor": 2759,
        "dtc_provincial_base": 9872,  # matches federal
        "ccc_provincial_base": 8375,
        "notes": "Yukon tax system tracks federal closely",
        "source": "cra-s1-f1-c1-metc; yt-428",
    },
    "NT": {
        "name": "Northwest Territories",
        "lowest_bracket_rate": 0.059,
        "metc_net_income_floor": 0.03,
        "metc_absolute_floor": 2759,
        "dtc_provincial_base": 14160,
        "ccc_provincial_base": 5167,
        "notes": "NWT provides additional deductions for northern residents",
        "source": "cra-s1-f1-c1-metc; nt-428",
    },
    "NU": {
        "name": "Nunavut",
        "lowest_bracket_rate": 0.04,
        "metc_net_income_floor": 0.03,
        "metc_absolute_floor": 2759,
        "dtc_provincial_base": 15440,
        "ccc_provincial_base": 5560,
        "notes": "Nunavut has the lowest federal-provincial combined rate for low-income earners",
        "source": "cra-s1-f1-c1-metc; nu-428",
    },
}


def generate_dataset():
    rows = []
    row_id = 1

    # Row 1: federal METC
    rows.append({
        "id": row_id, "jurisdiction_code": "CA-FED",
        "parameter_category": "METC", "parameter_name": "federal_rate",
        "value_cad": 0.0, "rate": METC_FEDERAL_RATE,
        "tax_year": TAX_YEAR,
        "description": "Federal Medical Expense Tax Credit rate (lowest bracket)",
        "source_id": "cra-s1-f1-c1-metc",
        "source_retrieved_date": RETRIEVED_DATE,
    }); row_id += 1

    rows.append({
        "id": row_id, "jurisdiction_code": "CA-FED",
        "parameter_category": "METC", "parameter_name": "net_income_floor_fraction",
        "value_cad": 0.0, "rate": METC_NET_INCOME_FLOOR,
        "tax_year": TAX_YEAR,
        "description": "METC: lesser of 3% of net income or the absolute floor is subtracted from qualifying expenses",
        "source_id": "cra-s1-f1-c1-metc",
        "source_retrieved_date": RETRIEVED_DATE,
    }); row_id += 1

    rows.append({
        "id": row_id, "jurisdiction_code": "CA-FED",
        "parameter_category": "METC", "parameter_name": "absolute_floor",
        "value_cad": METC_ABSOLUTE_FLOOR, "rate": 0.0,
        "tax_year": TAX_YEAR,
        "description": f"METC absolute floor for 2026 (${METC_ABSOLUTE_FLOOR} CAD)",
        "source_id": "cra-s1-f1-c1-metc",
        "source_retrieved_date": RETRIEVED_DATE,
    }); row_id += 1

    # Row n: federal DTC
    rows.append({
        "id": row_id, "jurisdiction_code": "CA-FED",
        "parameter_category": "DTC", "parameter_name": "base_amount",
        "value_cad": DTC_BASE_2026, "rate": 0.0,
        "tax_year": TAX_YEAR,
        "description": f"Federal Disability Tax Credit base amount (2026: ${DTC_BASE_2026})",
        "source_id": "cra-s1-f1-c2-dtc",
        "source_retrieved_date": RETRIEVED_DATE,
    }); row_id += 1

    rows.append({
        "id": row_id, "jurisdiction_code": "CA-FED",
        "parameter_category": "DTC", "parameter_name": "supplement_under_18",
        "value_cad": DTC_SUPPLEMENT_UNDER_18, "rate": 0.0,
        "tax_year": TAX_YEAR,
        "description": "DTC supplement for persons under 18 (subject to clawback on childcare expenses)",
        "source_id": "cra-s1-f1-c2-dtc",
        "source_retrieved_date": RETRIEVED_DATE,
    }); row_id += 1

    rows.append({
        "id": row_id, "jurisdiction_code": "CA-FED",
        "parameter_category": "DTC", "parameter_name": "supplement_clawback_threshold",
        "value_cad": DTC_SUPPLEMENT_CLAWBACK_THRESHOLD, "rate": 0.0,
        "tax_year": TAX_YEAR,
        "description": "DTC under-18 supplement begins to phase out at this income",
        "source_id": "cra-s1-f1-c2-dtc",
        "source_retrieved_date": RETRIEVED_DATE,
    }); row_id += 1

    # Canada Caregiver Credit
    rows.append({
        "id": row_id, "jurisdiction_code": "CA-FED",
        "parameter_category": "CCC", "parameter_name": "infirm_dependant_base",
        "value_cad": CCC_INFIRM_DEPENDANT_BASE, "rate": 0.0,
        "tax_year": TAX_YEAR,
        "description": "Canada Caregiver Credit: infirm dependant amount added to the basic personal amount",
        "source_id": "cra-canada-caregiver-credit",
        "source_retrieved_date": RETRIEVED_DATE,
    }); row_id += 1

    rows.append({
        "id": row_id, "jurisdiction_code": "CA-FED",
        "parameter_category": "CCC", "parameter_name": "caregiver_base",
        "value_cad": CCC_CAREGIVER_BASE, "rate": 0.0,
        "tax_year": TAX_YEAR,
        "description": "Canada Caregiver Credit: full caregiver amount for dependant relatives over 18",
        "source_id": "cra-canada-caregiver-credit",
        "source_retrieved_date": RETRIEVED_DATE,
    }); row_id += 1

    rows.append({
        "id": row_id, "jurisdiction_code": "CA-FED",
        "parameter_category": "CCC", "parameter_name": "phaseout_start_income",
        "value_cad": CCC_INCOME_PHASEOUT_START, "rate": 0.0,
        "tax_year": TAX_YEAR,
        "description": "CCC begins to reduce at this dependant net income",
        "source_id": "cra-canada-caregiver-credit",
        "source_retrieved_date": RETRIEVED_DATE,
    }); row_id += 1

    rows.append({
        "id": row_id, "jurisdiction_code": "CA-FED",
        "parameter_category": "CCC", "parameter_name": "phaseout_end_income",
        "value_cad": CCC_INCOME_PHASEOUT_END, "rate": 0.0,
        "tax_year": TAX_YEAR,
        "description": "CCC fully clawed back at this dependant net income",
        "source_id": "cra-canada-caregiver-credit",
        "source_retrieved_date": RETRIEVED_DATE,
    }); row_id += 1

    # VAC VIP
    rows.append({
        "id": row_id, "jurisdiction_code": "CA-FED",
        "parameter_category": "VIP", "parameter_name": "housekeeping_annual_ceiling",
        "value_cad": VIP_HOUSEKEEPING_ANNUAL_CEILING, "rate": 0.0,
        "tax_year": TAX_YEAR,
        "description": "VAC Veterans Independence Program housekeeping reimbursement ceiling (approximate, 2026)",
        "source_id": "vac-vip-2026",
        "source_retrieved_date": RETRIEVED_DATE,
    }); row_id += 1

    rows.append({
        "id": row_id, "jurisdiction_code": "CA-FED",
        "parameter_category": "VIP", "parameter_name": "grounds_annual_ceiling",
        "value_cad": VIP_GROUNDS_ANNUAL_CEILING, "rate": 0.0,
        "tax_year": TAX_YEAR,
        "description": "VAC VIP grounds maintenance reimbursement ceiling",
        "source_id": "vac-vip-2026",
        "source_retrieved_date": RETRIEVED_DATE,
    }); row_id += 1

    rows.append({
        "id": row_id, "jurisdiction_code": "CA-FED",
        "parameter_category": "VIP", "parameter_name": "personal_care_annual_ceiling",
        "value_cad": VIP_PERSONAL_CARE_ANNUAL_CEILING, "rate": 0.0,
        "tax_year": TAX_YEAR,
        "description": "VAC VIP personal care reimbursement ceiling",
        "source_id": "vac-vip-2026",
        "source_retrieved_date": RETRIEVED_DATE,
    }); row_id += 1

    # Provincial rows
    for code, info in PROVINCIAL_FACTORS.items():
        rows.append({
            "id": row_id, "jurisdiction_code": code,
            "parameter_category": "METC",
            "parameter_name": "provincial_rate",
            "value_cad": 0.0, "rate": info["lowest_bracket_rate"],
            "tax_year": TAX_YEAR,
            "description": f"{info['name']} METC rate — lowest bracket provincial rate applied to qualifying expenses",
            "source_id": info["source"],
            "source_retrieved_date": RETRIEVED_DATE,
        }); row_id += 1

        rows.append({
            "id": row_id, "jurisdiction_code": code,
            "parameter_category": "METC",
            "parameter_name": "provincial_absolute_floor",
            "value_cad": info["metc_absolute_floor"], "rate": 0.0,
            "tax_year": TAX_YEAR,
            "description": f"{info['name']} METC absolute floor (2026)",
            "source_id": info["source"],
            "source_retrieved_date": RETRIEVED_DATE,
        }); row_id += 1

        rows.append({
            "id": row_id, "jurisdiction_code": code,
            "parameter_category": "DTC",
            "parameter_name": "provincial_base_amount",
            "value_cad": info["dtc_provincial_base"], "rate": 0.0,
            "tax_year": TAX_YEAR,
            "description": f"{info['name']} provincial Disability Amount",
            "source_id": info["source"],
            "source_retrieved_date": RETRIEVED_DATE,
        }); row_id += 1

        rows.append({
            "id": row_id, "jurisdiction_code": code,
            "parameter_category": "CCC",
            "parameter_name": "provincial_base_amount",
            "value_cad": info["ccc_provincial_base"], "rate": 0.0,
            "tax_year": TAX_YEAR,
            "description": f"{info['name']} provincial caregiver amount",
            "source_id": info["source"],
            "source_retrieved_date": RETRIEVED_DATE,
        }); row_id += 1

    fieldnames = [
        "id", "jurisdiction_code", "parameter_category", "parameter_name",
        "value_cad", "rate", "tax_year", "description",
        "source_id", "source_retrieved_date",
    ]
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {len(rows)} rows -> {OUTPUT_FILE}")
    return len(rows)


if __name__ == "__main__":
    count = generate_dataset()
    print(f"Tax parameters complete: {count} rows for tax year {TAX_YEAR}.")
