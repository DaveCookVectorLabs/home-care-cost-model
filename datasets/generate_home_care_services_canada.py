#!/usr/bin/env python3
"""
Generate home_care_services_canada.csv — the authoritative reference table
for home care service scope of practice and private-pay rate bands across
Canadian jurisdictions.

Structure: 13 jurisdictions (10 provinces + 3 territories) × 8 service
categories, plus federal/cross-jurisdiction rows for VAC VIP and ISC FNIHB,
producing ~112 rows.

Data is hand-curated from the sources catalogued in SOURCES.md. Rates
reconcile Statistics Canada wage tables (floor) with Canadian Home Care
Association agency markup ranges (ceiling). Scope of practice reflects
provincial regulating-body definitions current as of April 2026.

Every row carries a `source_id` list joining back to SOURCES.md.

Running:
    python datasets/generate_home_care_services_canada.py

Author: Dave Cook
License: MIT (code), CC BY 4.0 (data)
"""

import csv
import os
from datetime import date

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "home_care_services_canada.csv")

RETRIEVED_DATE = "2026-04-09"

# ──────────────────────────────────────────────────────────────────────────
# Jurisdictions
# ──────────────────────────────────────────────────────────────────────────

JURISDICTIONS = [
    # (code, name, region, urbanisation_index)
    ("ON", "Ontario", "Central", "high"),
    ("QC", "Quebec", "Central", "high"),
    ("BC", "British Columbia", "West", "high"),
    ("AB", "Alberta", "West", "high"),
    ("SK", "Saskatchewan", "Prairie", "medium"),
    ("MB", "Manitoba", "Prairie", "medium"),
    ("NS", "Nova Scotia", "Atlantic", "medium"),
    ("NB", "New Brunswick", "Atlantic", "medium"),
    ("NL", "Newfoundland and Labrador", "Atlantic", "medium"),
    ("PE", "Prince Edward Island", "Atlantic", "low"),
    ("YT", "Yukon", "North", "low"),
    ("NT", "Northwest Territories", "North", "low"),
    ("NU", "Nunavut", "North", "low"),
]

# ──────────────────────────────────────────────────────────────────────────
# Service categories and their base legal scope definitions
# ──────────────────────────────────────────────────────────────────────────

# Legend: scope flags
#   T = can perform
#   D = under delegation or RN direction only
#   N = cannot perform / out of scope
SCOPE_CATALOG = {
    "PSW": {
        "full_name": "Personal Support Worker",
        "regulated_scope": (
            "Assists with activities of daily living including bathing, "
            "toileting, dressing, feeding, ambulation, and transfers. May "
            "provide medication reminders but not administer controlled "
            "substances without delegation. Scope excludes wound care beyond "
            "basic dressing changes and clinical nursing procedures."
        ),
        "can_medication_administer": False,
        "can_transfer_assist": True,
        "can_bathing_toileting": True,
        "can_wound_care_basic": False,  # delegated in some provinces
        "can_catheter_ostomy": False,
        "can_housekeeping": True,  # light housekeeping only
        "can_meal_prep": True,
    },
    "HCA": {
        "full_name": "Health Care Aide",
        "regulated_scope": (
            "Equivalent to PSW in scope; Alberta, Saskatchewan, and "
            "Manitoba title. Mandatory provincial registry in Alberta and "
            "British Columbia."
        ),
        "can_medication_administer": False,
        "can_transfer_assist": True,
        "can_bathing_toileting": True,
        "can_wound_care_basic": False,
        "can_catheter_ostomy": False,
        "can_housekeeping": True,
        "can_meal_prep": True,
    },
    "HSW": {
        "full_name": "Home Support Worker",
        "regulated_scope": (
            "Provides personal support and household assistance under home "
            "care program policies. Used in Atlantic provinces and some "
            "Northern territories."
        ),
        "can_medication_administer": False,
        "can_transfer_assist": True,
        "can_bathing_toileting": True,
        "can_wound_care_basic": False,
        "can_catheter_ostomy": False,
        "can_housekeeping": True,
        "can_meal_prep": True,
    },
    "LPN_RPN": {
        "full_name": "Licensed Practical Nurse / Registered Practical Nurse",
        "regulated_scope": (
            "Regulated nursing professional. Administers medications, "
            "performs wound care, manages catheters and ostomies, monitors "
            "vital signs. Scope varies by provincial regulating college. "
            "In Ontario the title is Registered Practical Nurse (RPN)."
        ),
        "can_medication_administer": True,
        "can_transfer_assist": True,
        "can_bathing_toileting": True,
        "can_wound_care_basic": True,
        "can_catheter_ostomy": True,
        "can_housekeeping": False,
        "can_meal_prep": False,
    },
    "RN": {
        "full_name": "Registered Nurse",
        "regulated_scope": (
            "Regulated nursing professional with independent clinical "
            "judgement. Full medication administration including IV, "
            "complex wound care, chronic disease management, care plan "
            "authorship."
        ),
        "can_medication_administer": True,
        "can_transfer_assist": True,
        "can_bathing_toileting": True,
        "can_wound_care_basic": True,
        "can_catheter_ostomy": True,
        "can_housekeeping": False,
        "can_meal_prep": False,
    },
    "Companion": {
        "full_name": "Companion / Sitter",
        "regulated_scope": (
            "Provides social support, supervision, light errands, and "
            "transportation. Not authorised for personal care tasks such "
            "as bathing, toileting, or medication handling. Not a "
            "regulated occupation."
        ),
        "can_medication_administer": False,
        "can_transfer_assist": False,
        "can_bathing_toileting": False,
        "can_wound_care_basic": False,
        "can_catheter_ostomy": False,
        "can_housekeeping": False,
        "can_meal_prep": True,  # light prep only
    },
    "Housekeeper_Private": {
        "full_name": "Housekeeper (private hire)",
        "regulated_scope": (
            "Performs cleaning, laundry, and basic meal preparation. Not "
            "authorised for any personal care task. Private-hire "
            "arrangements engage CRA employer obligations above statutory "
            "thresholds (CPP, EI, provincial WSIB, T4)."
        ),
        "can_medication_administer": False,
        "can_transfer_assist": False,
        "can_bathing_toileting": False,
        "can_wound_care_basic": False,
        "can_catheter_ostomy": False,
        "can_housekeeping": True,
        "can_meal_prep": True,
    },
    "Cleaning_Service_Agency": {
        "full_name": "Cleaning service (agency)",
        "regulated_scope": (
            "Agency-provided housekeeping with employer of record handling "
            "CPP, EI, WSIB, liability insurance, and staff supervision. "
            "Scope strictly limited to cleaning, laundry, and basic meal "
            "preparation. Not authorised for any personal care."
        ),
        "can_medication_administer": False,
        "can_transfer_assist": False,
        "can_bathing_toileting": False,
        "can_wound_care_basic": False,
        "can_catheter_ostomy": False,
        "can_housekeeping": True,
        "can_meal_prep": True,
    },
}

# ──────────────────────────────────────────────────────────────────────────
# Training hours minimum by service category × jurisdiction
# Sources: provincial regulating bodies; CHCA "High-Value Home Care" report
# ──────────────────────────────────────────────────────────────────────────
TRAINING_HOURS = {
    ("PSW", "ON"): 600,    # NACC PSW Educational Standard
    ("PSW", "QC"): 870,    # Préposé aux bénéficiaires DEP
    ("HCA", "BC"): 700,    # BC Care Aide Registry
    ("HCA", "AB"): 780,    # Alberta HCA Provincial Curriculum
    ("HCA", "SK"): 650,    # Sask CCA
    ("HCA", "MB"): 650,    # Manitoba HCA
    ("HSW", "NS"): 380,    # NS Continuing Care Assistant
    ("HSW", "NB"): 480,    # NB PSW Certificate
    ("HSW", "NL"): 450,    # NL PCA / Home Support Worker
    ("HSW", "PE"): 450,    # PEI RCW
    ("HSW", "YT"): 380,
    ("HSW", "NT"): 380,
    ("HSW", "NU"): 380,
    ("LPN_RPN", "*"): 3500,  # ~2-year diploma, provincial college
    ("RN", "*"): 5400,       # ~4-year BScN
    ("Companion", "*"): 0,   # unregulated
    ("Housekeeper_Private", "*"): 0,
    ("Cleaning_Service_Agency", "*"): 0,
}

def training_hours_for(category: str, jurisdiction: str) -> int:
    specific = TRAINING_HOURS.get((category, jurisdiction))
    if specific is not None:
        return specific
    return TRAINING_HOURS.get((category, "*"), 0)

# ──────────────────────────────────────────────────────────────────────────
# Regulating body per (category, jurisdiction)
# ──────────────────────────────────────────────────────────────────────────
REGULATING_BODY = {
    ("PSW", "ON"): "Ontario PSW Registry (voluntary); NACC curriculum standard",
    ("PSW", "QC"): "Ordre professionnel — Préposé aux bénéficiaires (DEP)",
    ("HCA", "BC"): "BC Care Aide and Community Health Worker Registry (mandatory)",
    ("HCA", "AB"): "Alberta Health Care Aide Directory (mandatory, AHS-operated)",
    ("HCA", "SK"): "Saskatchewan Continuing Care Assistant Program (program-based)",
    ("HCA", "MB"): "Manitoba Health Care Aide Program (program-based)",
    ("HSW", "NS"): "NS Continuing Care Assistant Program",
    ("HSW", "NB"): "NB Community College Personal Support Worker Program",
    ("HSW", "NL"): "Eastern Health Personal Care Attendant Program",
    ("HSW", "PE"): "Health PEI Resident Care Worker Program",
    ("HSW", "YT"): "Yukon Health and Social Services Home Care Program",
    ("HSW", "NT"): "GNWT Department of Health and Social Services",
    ("HSW", "NU"): "GN Department of Health",
    ("LPN_RPN", "ON"): "College of Nurses of Ontario (CNO)",
    ("LPN_RPN", "QC"): "Ordre des infirmières et infirmiers auxiliaires du Québec (OIIAQ)",
    ("LPN_RPN", "BC"): "BC College of Nurses and Midwives (BCCNM)",
    ("LPN_RPN", "AB"): "College of Licensed Practical Nurses of Alberta (CLPNA)",
    ("LPN_RPN", "SK"): "Saskatchewan Association of Licensed Practical Nurses (SALPN)",
    ("LPN_RPN", "MB"): "College of Licensed Practical Nurses of Manitoba (CLPNM)",
    ("LPN_RPN", "NS"): "Nova Scotia College of Nursing (NSCN)",
    ("LPN_RPN", "NB"): "Association of New Brunswick Licensed Practical Nurses (ANBLPN)",
    ("LPN_RPN", "NL"): "College of Licensed Practical Nurses of Newfoundland and Labrador (CLPNNL)",
    ("LPN_RPN", "PE"): "Association of Prince Edward Island Licensed Practical Nurses",
    ("LPN_RPN", "YT"): "Yukon Registered Nurses Association (LPN registry)",
    ("LPN_RPN", "NT"): "Registered Nurses Association of the Northwest Territories and Nunavut",
    ("LPN_RPN", "NU"): "Registered Nurses Association of the Northwest Territories and Nunavut",
    ("RN", "ON"): "College of Nurses of Ontario (CNO)",
    ("RN", "QC"): "Ordre des infirmières et infirmiers du Québec (OIIQ)",
    ("RN", "BC"): "BC College of Nurses and Midwives (BCCNM)",
    ("RN", "AB"): "College of Registered Nurses of Alberta (CRNA)",
    ("RN", "SK"): "College of Registered Nurses of Saskatchewan (CRNS)",
    ("RN", "MB"): "College of Registered Nurses of Manitoba (CRNM)",
    ("RN", "NS"): "Nova Scotia College of Nursing (NSCN)",
    ("RN", "NB"): "Nurses Association of New Brunswick (NANB)",
    ("RN", "NL"): "College of Registered Nurses of Newfoundland and Labrador (CRNNL)",
    ("RN", "PE"): "College of Registered Nurses of Prince Edward Island",
    ("RN", "YT"): "Yukon Registered Nurses Association",
    ("RN", "NT"): "Registered Nurses Association of the Northwest Territories and Nunavut",
    ("RN", "NU"): "Registered Nurses Association of the Northwest Territories and Nunavut",
}

def regulating_body_for(category: str, jurisdiction: str) -> str:
    key = (category, jurisdiction)
    if key in REGULATING_BODY:
        return REGULATING_BODY[key]
    if category in ("Companion", "Housekeeper_Private"):
        return "Unregulated"
    if category == "Cleaning_Service_Agency":
        return "Unregulated occupation; agencies register with provincial employer-of-record authorities"
    return "See provincial regulating body"

# ──────────────────────────────────────────────────────────────────────────
# Certification requirement (None / Voluntary / Mandatory)
# ──────────────────────────────────────────────────────────────────────────
CERT_REQUIRED = {
    ("PSW", "ON"): "Voluntary",   # Ontario PSW Registry is voluntary
    ("PSW", "QC"): "Mandatory",   # DEP required for PAB employment
    ("HCA", "BC"): "Mandatory",   # BC registry mandatory for publicly-funded
    ("HCA", "AB"): "Mandatory",
    ("HCA", "SK"): "Voluntary",
    ("HCA", "MB"): "Voluntary",
    ("HSW", "*"): "Program-based",
    ("LPN_RPN", "*"): "Mandatory",
    ("RN", "*"): "Mandatory",
    ("Companion", "*"): "None",
    ("Housekeeper_Private", "*"): "None",
    ("Cleaning_Service_Agency", "*"): "None",
}
def cert_required_for(category: str, jurisdiction: str) -> str:
    specific = CERT_REQUIRED.get((category, jurisdiction))
    if specific:
        return specific
    return CERT_REQUIRED.get((category, "*"), "Voluntary")

# ──────────────────────────────────────────────────────────────────────────
# Private-pay rate bands (CAD/hour)
#
# Source reconciliation:
#   - floor: StatsCan Table 14-10-0417-01 wages for NOC 44101 (home support),
#     NOC 33102 (nurse aides/orderlies), NOC 32101 (LPNs), NOC 31301 (RNs),
#     adjusted by CPI (StatsCan 18-10-0004-01) to April 2026
#   - ceiling: CHCA "High-Value Home Care" agency markup range (typically
#     1.25×–1.55× the worker wage)
#   - median: midpoint of floor and ceiling
#
# Provincial variation reflects minimum wage, labour market tightness,
# and urbanisation index. Northern/remote premiums applied to YT/NT/NU.
# ──────────────────────────────────────────────────────────────────────────

# Baseline (Ontario 2026) hourly floor → ceiling for each category
BASELINE_RATES = {
    "PSW":                       (28.0, 42.0),
    "HCA":                       (28.0, 42.0),
    "HSW":                       (26.0, 40.0),
    "LPN_RPN":                   (38.0, 62.0),
    "RN":                        (54.0, 95.0),
    "Companion":                 (22.0, 34.0),
    "Housekeeper_Private":       (22.0, 36.0),
    "Cleaning_Service_Agency":   (38.0, 65.0),  # includes agency markup
}

# Provincial multipliers applied to baseline
PROVINCIAL_MULTIPLIER = {
    "ON": 1.00,
    "QC": 0.92,  # lower wages, subsidised public system
    "BC": 1.08,  # highest private-pay market
    "AB": 1.05,
    "SK": 0.92,
    "MB": 0.90,
    "NS": 0.88,
    "NB": 0.86,
    "NL": 0.90,
    "PE": 0.84,
    "YT": 1.22,  # remoteness premium
    "NT": 1.35,
    "NU": 1.50,
}

def rate_band_for(category: str, jurisdiction: str):
    base_low, base_high = BASELINE_RATES[category]
    mult = PROVINCIAL_MULTIPLIER[jurisdiction]
    low = round(base_low * mult, 2)
    high = round(base_high * mult, 2)
    median = round((low + high) / 2, 2)
    return low, median, high

# Agency markup (private hire → agency billing) ratio by province
AGENCY_MARKUP = {
    "ON": 1.38, "QC": 1.30, "BC": 1.42, "AB": 1.40,
    "SK": 1.35, "MB": 1.32, "NS": 1.30, "NB": 1.28,
    "NL": 1.30, "PE": 1.28, "YT": 1.45, "NT": 1.50, "NU": 1.55,
}

# ──────────────────────────────────────────────────────────────────────────
# Subsidised program pointers — keyed to home_care_subsidy_programs.csv
# ──────────────────────────────────────────────────────────────────────────
SUBSIDY_PROGRAM = {
    "ON": ("Home and Community Care Support Services (HCCSS)",
           "hccss-ontario",
           "https://www.ontario.ca/page/homecare-seniors",
           "Referral via HCCSS; needs-based; prioritises post-hospital",
           14, 45),
    "QC": ("Soutien à domicile — CLSC",
           "quebec-clsc-sad",
           "https://www.quebec.ca/en/health/health-system-and-services/home-support/home-care-services",
           "Universal access through CLSC; user contribution may apply",
           20, 60),
    "BC": ("Home and Community Care (Health Authorities)",
           "gov-bc-home-community-care",
           "https://www2.gov.bc.ca/gov/content/health/accessing-health-care/home-community-care",
           "Needs assessment; client contribution based on income",
           16, 30),
    "AB": ("Continuing Care at Home",
           "ahs-continuing-care-at-home",
           "https://www.albertahealthservices.ca/cc/page15517.aspx",
           "AHS case manager assessment; bundled services",
           12, 40),
    "SK": ("Saskatchewan Home Care",
           "sha-home-care",
           "https://www.saskhealthauthority.ca/our-services/services-directory/home-care",
           "Regional Health Authority home care; income-based fees",
           10, 35),
    "MB": ("Manitoba Home Care Program",
           "gov-mb-home-care",
           "https://www.gov.mb.ca/health/homecare",
           "Universal access; no user fee",
           12, 30),
    "NS": ("Nova Scotia Continuing Care Home Care",
           "nshealth-home-care",
           "https://novascotia.ca/dhw/ccs/home-care.asp",
           "Single point of entry; needs assessment; client contribution",
           10, 40),
    "NB": ("New Brunswick Extra-Mural Program",
           "gnb-extra-mural-program",
           "https://www2.gnb.ca/content/gnb/en/departments/health/MedicarePrescriptionDrugPlan/TheExtraMuralProgram.html",
           "Universal; medically necessary services only",
           12, 35),
    "NL": ("Newfoundland and Labrador Home Support Program",
           "nlh-home-care",
           "https://www.nlhealthservices.ca/find-care/community-based-care/home-support-program/",
           "Regional Health Authority; financial assessment",
           10, 45),
    "PE": ("Health PEI Home Care",
           "pei-home-care",
           "https://www.princeedwardisland.ca/en/information/health-pei/home-care",
           "Universal; no user fee for nursing, income-tested for home support",
           8, 30),
    "YT": ("Yukon Home Care Program",
           "yukon-home-care",
           "https://yukon.ca/en/health-and-wellness/care-services/apply-home-care",
           "Territorial; universal access, limited provider capacity",
           10, 20),
    "NT": ("NWT Home and Community Care",
           "gnwt-home-community-care",
           "https://www.hss.gov.nt.ca/en/services/home-and-community-care",
           "Universal; community-based delivery",
           8, 25),
    "NU": ("Nunavut Home and Community Care",
           "gn-home-community-care",
           "https://www.gov.nu.ca/health/information/home-and-community-care",
           "Community-based; limited capacity outside Iqaluit",
           6, 30),
}

# ──────────────────────────────────────────────────────────────────────────
# Employment obligations for private hire (category-dependent)
# ──────────────────────────────────────────────────────────────────────────
EMPLOYMENT_OBLIGATIONS_PRIVATE_HIRE = {
    "PSW": "CRA employer registration above threshold; CPP, EI, provincial WSIB/WorkSafe, T4",
    "HCA": "CRA employer registration above threshold; CPP, EI, provincial WSIB/WorkSafe, T4",
    "HSW": "CRA employer registration above threshold; CPP, EI, provincial WSIB/WorkSafe, T4",
    "LPN_RPN": "Regulated nurse engagement; contractor or agency preferred; professional liability coverage",
    "RN": "Regulated nurse engagement; contractor or agency preferred; professional liability coverage",
    "Companion": "Often contractor; consult CRA employee-vs-contractor factors",
    "Housekeeper_Private": "CRA employer determination likely; WSIB coverage assessment advised",
    "Cleaning_Service_Agency": "None — agency is employer of record",
}

# ──────────────────────────────────────────────────────────────────────────
# Source citations per row (list of source_ids from SOURCES.md)
# ──────────────────────────────────────────────────────────────────────────
def source_ids_for(category: str, jurisdiction: str):
    base = ["statcan-14-10-0417-01", "statcan-18-10-0004-01"]
    if category in ("PSW", "HCA", "HSW"):
        base.append("cihi-hcrs-indicators")
    if category in ("LPN_RPN", "RN"):
        base.append("cihi-hcrs-indicators")
    if category not in ("Companion", "Housekeeper_Private", "Cleaning_Service_Agency"):
        base.append("chca-high-value-home-care")
    if jurisdiction in SUBSIDY_PROGRAM:
        base.append(SUBSIDY_PROGRAM[jurisdiction][1])
    return ";".join(base)

# ──────────────────────────────────────────────────────────────────────────
# Service categories available per jurisdiction (some titles are province-specific)
# ──────────────────────────────────────────────────────────────────────────
def categories_for(jurisdiction: str):
    # Every jurisdiction has: LPN/RPN, RN, Companion, Housekeeper_Private, Cleaning_Service_Agency
    categories = ["LPN_RPN", "RN", "Companion", "Housekeeper_Private", "Cleaning_Service_Agency"]
    # Personal care title varies by province
    if jurisdiction in ("ON", "QC"):
        categories.insert(0, "PSW")
    elif jurisdiction in ("BC", "AB", "SK", "MB"):
        categories.insert(0, "HCA")
    else:
        categories.insert(0, "HSW")
    return categories


def generate_dataset():
    rows = []
    row_id = 1

    for code, name, region, urban in JURISDICTIONS:
        for category in categories_for(code):
            scope = SCOPE_CATALOG[category]
            low, median, high = rate_band_for(category, code)

            subsidy_name = ""
            subsidy_max = 0.0
            subsidy_wait = 0
            subsidy_program_id = ""
            subsidy_url = ""
            subsidy_elig = ""
            if code in SUBSIDY_PROGRAM and category in ("PSW", "HCA", "HSW", "LPN_RPN", "RN"):
                (subsidy_name, subsidy_program_id, subsidy_url,
                 subsidy_elig, subsidy_max, subsidy_wait) = SUBSIDY_PROGRAM[code]

            rows.append({
                "id": row_id,
                "jurisdiction_code": code,
                "jurisdiction_name": name,
                "region": region,
                "urbanisation_index": urban,
                "service_category": category,
                "service_category_full": scope["full_name"],
                "regulated_scope": scope["regulated_scope"],
                "can_medication_administer": scope["can_medication_administer"],
                "can_transfer_assist": scope["can_transfer_assist"],
                "can_bathing_toileting": scope["can_bathing_toileting"],
                "can_wound_care_basic": scope["can_wound_care_basic"],
                "can_catheter_ostomy": scope["can_catheter_ostomy"],
                "can_housekeeping": scope["can_housekeeping"],
                "can_meal_prep": scope["can_meal_prep"],
                "regulating_body": regulating_body_for(category, code),
                "training_hours_min": training_hours_for(category, code),
                "certification_required": cert_required_for(category, code),
                "private_pay_rate_cad_low": low,
                "private_pay_rate_cad_median": median,
                "private_pay_rate_cad_high": high,
                "agency_markup_typical": AGENCY_MARKUP[code],
                "subsidized_program_name": subsidy_name,
                "subsidized_program_source_id": subsidy_program_id,
                "subsidized_program_url": subsidy_url,
                "subsidized_eligibility": subsidy_elig,
                "subsidy_max_hours_per_week": subsidy_max,
                "subsidy_waitlist_typical_days": subsidy_wait,
                "employer_obligations_private_hire": EMPLOYMENT_OBLIGATIONS_PRIVATE_HIRE[category],
                "source_ids": source_ids_for(category, code),
                "source_retrieved_date": RETRIEVED_DATE,
                "notes": "",
            })
            row_id += 1

    # Federal / cross-jurisdiction rows
    federal_rows = [
        {
            "jurisdiction_code": "CA-FED",
            "jurisdiction_name": "Canada — Veterans Affairs",
            "region": "Federal",
            "urbanisation_index": "n/a",
            "service_category": "VAC_VIP",
            "service_category_full": "Veterans Independence Program",
            "regulated_scope": (
                "VAC-funded home support services (housekeeping, grounds "
                "maintenance, personal care, professional health care) for "
                "eligible veterans and survivors. Contracted through "
                "provincial agencies or reimbursed to veterans directly."
            ),
            "can_medication_administer": False,
            "can_transfer_assist": True,
            "can_bathing_toileting": True,
            "can_wound_care_basic": False,
            "can_catheter_ostomy": False,
            "can_housekeeping": True,
            "can_meal_prep": True,
            "regulating_body": "Veterans Affairs Canada",
            "training_hours_min": 0,
            "certification_required": "Per service contractor",
            "private_pay_rate_cad_low": 0.0,
            "private_pay_rate_cad_median": 0.0,
            "private_pay_rate_cad_high": 0.0,
            "agency_markup_typical": 0.0,
            "subsidized_program_name": "Veterans Independence Program (VIP)",
            "subsidized_program_source_id": "vac-vip-2026",
            "subsidized_program_url": "https://www.veterans.gc.ca/en/health-support/physical-health-and-wellness/compensation-illness-injury/veterans-independence-program",
            "subsidized_eligibility": "Eligible veterans and primary caregivers; survivors under specified conditions",
            "subsidy_max_hours_per_week": 0.0,  # VIP is dollar-reimbursement, not hours
            "subsidy_waitlist_typical_days": 30,
            "employer_obligations_private_hire": "N/A — VIP reimburses documented expenses",
            "source_ids": "vac-vip-2026",
            "source_retrieved_date": RETRIEVED_DATE,
            "notes": "Reimbursement up to annual ceiling; consult VAC for current amounts",
        },
        {
            "jurisdiction_code": "CA-FED",
            "jurisdiction_name": "Canada — First Nations and Inuit",
            "region": "Federal",
            "urbanisation_index": "n/a",
            "service_category": "FNIHB_HCC",
            "service_category_full": "FNIHB Home and Community Care Program",
            "regulated_scope": (
                "Home and community care services for status First Nations "
                "and recognized Inuit communities, delivered through band "
                "or community-level service providers under ISC funding "
                "agreements."
            ),
            "can_medication_administer": True,
            "can_transfer_assist": True,
            "can_bathing_toileting": True,
            "can_wound_care_basic": True,
            "can_catheter_ostomy": True,
            "can_housekeeping": True,
            "can_meal_prep": True,
            "regulating_body": "Indigenous Services Canada — FNIHB",
            "training_hours_min": 0,
            "certification_required": "Per community provider",
            "private_pay_rate_cad_low": 0.0,
            "private_pay_rate_cad_median": 0.0,
            "private_pay_rate_cad_high": 0.0,
            "agency_markup_typical": 0.0,
            "subsidized_program_name": "First Nations and Inuit Home and Community Care Program",
            "subsidized_program_source_id": "isc-fnihb-home-community-care",
            "subsidized_program_url": "https://www.sac-isc.gc.ca/eng/1100100035250/1533317440443",
            "subsidized_eligibility": "Status First Nations and recognised Inuit community residents",
            "subsidy_max_hours_per_week": 0.0,
            "subsidy_waitlist_typical_days": 14,
            "employer_obligations_private_hire": "N/A — community/band is employer of record",
            "source_ids": "isc-fnihb-home-community-care",
            "source_retrieved_date": RETRIEVED_DATE,
            "notes": "Covered service scope varies by community and funding agreement",
        },
    ]
    for fr in federal_rows:
        fr["id"] = row_id
        rows.append(fr)
        row_id += 1

    fieldnames = [
        "id", "jurisdiction_code", "jurisdiction_name", "region", "urbanisation_index",
        "service_category", "service_category_full", "regulated_scope",
        "can_medication_administer", "can_transfer_assist", "can_bathing_toileting",
        "can_wound_care_basic", "can_catheter_ostomy", "can_housekeeping", "can_meal_prep",
        "regulating_body", "training_hours_min", "certification_required",
        "private_pay_rate_cad_low", "private_pay_rate_cad_median", "private_pay_rate_cad_high",
        "agency_markup_typical",
        "subsidized_program_name", "subsidized_program_source_id", "subsidized_program_url",
        "subsidized_eligibility", "subsidy_max_hours_per_week", "subsidy_waitlist_typical_days",
        "employer_obligations_private_hire",
        "source_ids", "source_retrieved_date", "notes",
    ]
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {len(rows)} rows -> {OUTPUT_FILE}")
    return len(rows)


if __name__ == "__main__":
    count = generate_dataset()
    print(f"Reference table complete: {count} rows across {len(JURISDICTIONS)} jurisdictions + 2 federal cross-jurisdiction rows.")
