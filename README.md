# Home Care Cost Model

[![PyPI version](https://badge.fury.io/py/home-care-cost-model.svg)](https://pypi.org/project/home-care-cost-model/)
[![npm version](https://badge.fury.io/js/%40davecook%2Fhome-care-cost-model.svg)](https://www.npmjs.com/package/@davecook/home-care-cost-model)
[![Crates.io](https://img.shields.io/crates/v/home-care-cost-model-engine.svg)](https://crates.io/crates/home-care-cost-model-engine)
[![Gem Version](https://badge.fury.io/rb/home_care_cost_model.svg)](https://rubygems.org/gems/home_care_cost_model)
[![Hex.pm](https://img.shields.io/hexpm/v/home_care_cost_model.svg)](https://hex.pm/packages/home_care_cost_model)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Data: CC BY 4.0](https://img.shields.io/badge/Data-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)

A reference cost model and open dataset collection for home care decisions in
Canada. The model quantifies the trade-off families face when combining
Personal Support Worker (PSW) hours, housekeeping services, nursing care, and
informal caregiving for an older adult or person with a disability remaining at
home. It spans all ten provinces and three territories, incorporates 2026 tax
relief parameters (Medical Expense Tax Credit, Disability Tax Credit, Canada
Caregiver Credit, Veterans Independence Program), and emits explicit scope of
practice warnings when inputs imply a service substitution that is not legally
permissible.

---

## Plain-language summary

Families across Canada routinely face a choice between hiring a Personal
Support Worker (PSW) and hiring a cleaner or housekeeper when a parent or
spouse begins to need help at home. The two roles are not interchangeable. A
PSW is trained and authorised to provide personal care — bathing, toileting,
transfers, feeding, medication reminders, and (in some provinces and under
delegation) basic wound and ostomy care. A housekeeper or cleaning service is
authorised to clean. Asking a cleaner to help with personal care is outside
their scope of practice and, in several provinces, outside the scope of their
insurance.

This repository publishes a parametric model that takes a recipient's
activities-of-daily-living (ADL) and instrumental-activities-of-daily-living
(IADL) scores, their province, a short description of their household and
diagnosis, and returns a service mix (PSW hours, housekeeping hours, nursing
hours), a monthly private-pay cost, the hours covered by the applicable
provincial subsidised program, and the federal and provincial tax credits
that typically apply. It also flags, in writing, any combination of inputs
where cleaning services cannot legally substitute for personal support.

The model is not clinical advice. It is a reference framework for comparing
options before a formal care assessment. All data sources are government or
peer-reviewed. All code is open source under MIT. All data is published under
CC BY 4.0.

---

## What This Does

Given an older adult or disability-care recipient's functional assessment and
jurisdiction, the model computes:

- **Recommended weekly service hours** across three categories (personal
  support, housekeeping, skilled nursing), derived from Katz ADL and Lawton
  IADL scores with diagnosis- and cognition-aware adjustments.
- **Scope of practice warnings** when the combination of inputs implies a
  legally-impermissible substitution (e.g. housekeeping for a recipient whose
  ADL score indicates need for bathing or transfer assistance).
- **Private-pay monthly cost** using per-province rate bands derived from
  Statistics Canada wage tables and Canadian Home Care Association agency
  markup ranges.
- **Subsidised hours allocation** for the recipient's province, following
  publicly-documented eligibility rules (Ontario HCCSS, BC Health Authority
  home care, Alberta Continuing Care at Home, Quebec CLSC Soutien à domicile,
  Saskatchewan Health Authority, Manitoba Home Care, Atlantic provinces,
  Territories).
- **Federal and provincial tax credit stack** — Medical Expense Tax Credit
  (METC), Disability Tax Credit (DTC), Canada Caregiver Credit (CCC),
  Veterans Affairs Canada VIP, and Indigenous Services Canada FNIHB Home and
  Community Care Program flags.
- **Out-of-pocket cost after credits**, monthly and annualised.
- **Hybrid-versus-all-PSW comparison**, showing how much a family saves by
  using a cleaning service for housekeeping hours rather than paying a PSW
  rate for those same hours.
- **Employment-law warnings** when private-hire arrangements exceed a
  threshold that triggers CRA employer obligations (CPP, EI, provincial
  WSIB, T4 filing).
- **Data source citations** linking every output field to the Sources
  manifest row that supplied its constants.

Every response includes a `disclaimer` field: *"Reference model only. Not
clinical or financial advice; consult a regulated health professional or
registered tax practitioner for individual decisions."*

---

## Datasets

Three classes of data ship with this repository. All live under `datasets/`.

### Class 1 — Sources (raw, verbatim, credited)

Fetched by `datasets/pull_sources.py` from authoritative portals and stored
under `datasets/sources/<organisation>/<filename>` with a sibling
`<filename>.source.json` that records upstream URL, retrieval timestamp,
license, and SHA256. A human-readable manifest is at
`datasets/SOURCES.md`. No Source file is ever edited after download.

Upstream organisations represented in Sources: Statistics Canada (wage,
population, CPI tables), Canadian Institute for Health Information (home
care indicators), Canada Revenue Agency (tax folios), Veterans Affairs
Canada (VIP rate schedule), Indigenous Services Canada (FNIHB Home and
Community Care), Canadian Home Care Association, the Ontario Ministry of
Health (HCCSS), and the equivalent provincial and territorial ministries.

### Class 2 — Reference tables (hand-curated, deterministic)

| File | Rows | Description |
|---|---|---|
| `home_care_services_canada.csv` | ~112 | Scope-of-practice and rate bands for 8 service categories across 13 Canadian jurisdictions, plus federal/cross-jurisdiction rows for VAC VIP and ISC FNIHB. Every row cites a `source_url`. |
| `home_care_tax_parameters_2026.csv` | ~40 | Tax-year 2026 parameters for METC, DTC, CCC, VAC VIP, and provincial disability supplements. Every row cites a CRA folio or equivalent. |
| `home_care_subsidy_programs.csv` | ~25 | Provincial and territorial subsidised home care programs: administering body, eligibility rules, typical hours awarded, wait time, URL, retrieval date. |

### Class 3 — Derived scenarios (engine-generated)

These are the analysis-ready tables published to Hugging Face, Kaggle,
Zenodo, Dryad, and Mendeley Data. Every row is produced by calling
`engines/python/engine.py` with a specific input grid.

| File | Rows | Description |
|---|---|---|
| `home_care_scenarios.csv` | 5,000 | Synthetic household scenarios with population-weighted province sampling, joint-distribution diagnosis/cognition/mobility sampling calibrated to CIHI home care indicators, and per-scenario engine outputs. Deterministic with `random.seed(42)`. |
| `home_care_per_province_rate_bands.csv` | ~650 | Product of the reference scope table × Statistics Canada CPI-adjusted wage data for 2019–2026, yielding implied private-pay and agency-billed rate ranges per (province, service, year). |
| `home_care_cost_model_archetypes.csv` | ~2,500 | Engine outputs for a grid of canonical household archetypes: every (province × ADL × IADL × cognitive × mobility) combination at constant household composition and income. The lookup-table form of the calculator. |
| `home_care_tax_relief_sensitivity.csv` | ~3,500 | Sensitivity grid: ~700 base scenarios × 5 net-income bands ($25k, $50k, $75k, $100k, $150k). Shows how tax-credit value shifts across the income distribution. |
| `home_care_subsidy_gap.csv` | ~390 | 13 jurisdictions × 30 representative scenarios. Reports subsidised hours awarded vs. model-recommended hours vs. monthly dollar gap, exposing cross-province variation in home care program generosity. |

All derived datasets are labelled **"Synthetic. Generated from seed 42. Not
survey data."** in their header comments and dataset cards.

---

## Calculation Model

```
# Inputs
adl_katz_score        ∈ [0, 6]
iadl_lawton_score     ∈ [0, 8]
province              ∈ {ON, QC, BC, AB, SK, MB, NS, NB, NL, PE, YT, NT, NU}
household_composition ∈ {alone, with_spouse, with_adult_child, multigen}
cognitive_status      ∈ {intact, mild, moderate, severe}
mobility_status       ∈ {independent, cane, walker, wheelchair, bedbound}
primary_diagnosis     ∈ {dementia, stroke, frailty, parkinson, post_surgical,
                         mobility_only, chronic_mixed}

# Hours derivation
psw_hours_per_week    = max(0, 7*(6 - adl) + cognitive_bump
                             - min(informal_hours*0.5, cap))
housekeeping_hours    = max(0, 2*(8 - iadl) + household_modifier)
nursing_hours         = diagnosis_map[primary_diagnosis]

# Gates
if adl <= 4 or cognitive in {moderate, severe}:
    require PSW or HCA for personal care         # scope gate
if diagnosis requires skilled nursing:
    require LPN/RN                               # nursing gate

# Cost stack
private_pay      = hours * province_rate_from(services_canada.csv)
subsidy          = province_subsidy_allocation(province, adl)
out_of_pocket    = private_pay - subsidy

# Tax relief (2026)
metc_qualifying  = max(0, out_of_pocket*12 - min(0.03*net_income,
                                                  METC_FLOOR_2026))
metc_value       = metc_qualifying * (0.15 + provincial_factor)
dtc_value        = DTC_BASE_2026 * (0.15 + provincial_factor)      if eligible
ccc_value        = CCC_BASE_2026 * (0.15 + provincial_factor)      if eligible
vac_vip_value    = VAC_VIP_SCHEDULE_2026                           if veteran
total_credits    = metc_value + dtc_value + ccc_value + vac_vip_value

# Comparison
all_psw_cost     = (psw_hours + housekeeping_hours + nursing_hours)
                   * psw_rate(province)
hybrid_savings   = all_psw_cost - private_pay
```

The reference implementation is `engines/python/engine.py`. Six additional
language ports implement identical logic; cross-language parity is verified
on three case studies from the PDF working paper.

---

## Engines

Seven language implementations. Each exposes `POST /calculate` and
`GET /health` and loads the reference CSVs at startup.

| Language | Directory | Package |
|----------|-----------|---------|
| Python (FastAPI) | `engines/python/` | `home-care-cost-model` on PyPI |
| Rust (axum) | `engines/rust/` | `home-care-cost-model-engine` on Crates.io |
| Java | `engines/java/` | `io.github.davecookvectorlabs:home-care-cost-model-engine` on Maven Central |
| Ruby (Sinatra) | `engines/ruby/` | `home_care_cost_model` on RubyGems |
| Elixir (Plug) | `engines/elixir/` | `home_care_cost_model` on Hex.pm |
| PHP | `engines/php/` | `davecook/home-care-cost-model` on Packagist |
| Go (net/http) | `engines/go/` | `github.com/DaveCookVectorLabs/home-care-cost-model` on pkg.go.dev |

### Quick Start (Python)

```bash
pip install home-care-cost-model
# or run from source:
cd engines/python
pip install -r requirements.txt
python engine.py              # CLI mode — runs a sample calculation
python engine.py --serve      # HTTP server on port 8003
```

### API Example

```bash
curl -X POST http://localhost:8003/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "adl_katz_score": 2,
    "iadl_lawton_score": 1,
    "province": "BC",
    "household_composition": "with_spouse",
    "cognitive_status": "moderate",
    "mobility_status": "walker",
    "primary_diagnosis_category": "dementia",
    "informal_caregiver_hours_per_week": 20,
    "net_family_income_cad": 72000,
    "is_veteran": false,
    "has_dtc": true,
    "agency_vs_private": "private",
    "include_subsidy": true,
    "tax_year": 2026
  }'
```

---

## Data Sources

Primary government and peer-reviewed sources referenced by the reference
tables and cited in every derived dataset row via `source_id`:

- Statistics Canada — wage and employment tables (NOC 44101 Home support
  workers; NOC 33102 Nurse aides, orderlies and patient service associates);
  population estimates by age and sex; health services CPI.
  <https://www.statcan.gc.ca>
- Canadian Institute for Health Information — Home Care Reporting System
  public indicators; Your Health System home care volume and wait time
  tables. <https://www.cihi.ca>
- Canada Revenue Agency — Income Tax Folio S1-F1-C1 (Medical Expense Tax
  Credit); S1-F1-C2 (Disability Tax Credit); Canada Caregiver Credit
  guidance. <https://www.canada.ca/en/revenue-agency.html>
- Veterans Affairs Canada — Veterans Independence Program rate schedule.
  <https://www.veterans.gc.ca>
- Indigenous Services Canada — First Nations and Inuit Home and Community
  Care Program. <https://www.sac-isc.gc.ca>
- Ontario Ministry of Health — Home and Community Care Support Services
  program pages. <https://www.ontario.ca/page/homecare-seniors>
- Government of British Columbia — Home and Community Care policy manual.
  <https://www2.gov.bc.ca>
- Alberta Health Services — Continuing Care at Home.
  <https://www.albertahealthservices.ca>
- Gouvernement du Québec — CLSC Soutien à domicile.
  <https://www.quebec.ca>
- Provincial ministry pages for Saskatchewan, Manitoba, New Brunswick, Nova
  Scotia, Prince Edward Island, Newfoundland and Labrador, Yukon, Northwest
  Territories, and Nunavut home care programs.
- Canadian Home Care Association — *High-Value Home Care* report series.
  <https://cdnhomecare.ca>
- Katz S, Ford AB, Moskowitz RW, Jackson BA, Jaffe MW. *Studies of Illness
  in the Aged. The Index of ADL: A Standardized Measure of Biological and
  Psychosocial Function.* JAMA. 1963.
- Lawton MP, Brody EM. *Assessment of older people: self-maintaining and
  instrumental activities of daily living.* The Gerontologist. 1969.

Full provenance is recorded in `datasets/SOURCES.md`, and every `source_url`
cell in `home_care_services_canada.csv` points at a specific page within
these portals.

---

## Project Structure

```
home-care-cost-model/
├── datasets/
│   ├── pull_sources.py                         # raw source fetcher
│   ├── SOURCES.md                              # provenance manifest
│   ├── sources/                                # raw files + .source.json sidecars
│   ├── generate_home_care_services_canada.py   # reference table 2a
│   ├── generate_home_care_tax_parameters.py    # reference table 2b
│   ├── generate_home_care_subsidy_programs.py  # reference table 2c
│   ├── generate_home_care_scenarios.py         # derived 3a
│   ├── generate_home_care_per_province_rate_bands.py   # derived 3b
│   ├── generate_home_care_cost_model_archetypes.py     # derived 3c
│   ├── generate_home_care_tax_relief_sensitivity.py    # derived 3d
│   ├── generate_home_care_subsidy_gap.py               # derived 3e
│   ├── home_care_services_canada.csv           # ~112 rows
│   ├── home_care_tax_parameters_2026.csv       # ~40 rows
│   ├── home_care_subsidy_programs.csv          # ~25 rows
│   ├── home_care_scenarios.csv                 # 5,000 rows
│   ├── home_care_per_province_rate_bands.csv   # ~650 rows
│   ├── home_care_cost_model_archetypes.csv     # ~2,500 rows
│   ├── home_care_tax_relief_sensitivity.csv    # ~3,500 rows
│   └── home_care_subsidy_gap.csv               # ~390 rows
├── engines/
│   ├── python/engine.py                        # reference implementation
│   ├── rust/                                   # port
│   ├── java/                                   # port
│   ├── ruby/                                   # port
│   ├── elixir/                                 # port
│   ├── php/                                    # port
│   └── go/                                     # port
├── notebooks/
│   └── home_care_cost_analysis.ipynb           # Jupyter analysis
├── pdfs/
│   ├── generate_pdfs.py                        # PDF working paper generator
│   └── home-care-cost-model-guide.pdf          # 28-page working paper
├── kaggle/                                     # Kaggle dataset + kernel
├── observable/                                 # Observable notebook
├── scribd/                                     # Scribd metadata
├── docs/                                       # Sphinx documentation
├── public/                                     # Minimal PHP web frontend
└── scripts/
    └── parity_check.sh                         # cross-language verification
```

---

## License

MIT License for code. CC BY 4.0 for datasets and the PDF working paper. See
[LICENSE](LICENSE) for the MIT text; the CC BY 4.0 attribution is specified
in `datasets/README.md` and on the PDF cover page.

---

Maintained by Dave Cook — [Binx Professional Cleaning](https://www.binx.ca/residential.php), North Bay and Sudbury, Ontario.
