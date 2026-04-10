---
license: cc-by-4.0
task_categories:
- tabular-regression
- tabular-classification
language:
- en
- fr
tags:
- home-care
- canada
- health-policy
- cost-model
- aging-in-place
- personal-support-worker
- tax-credit
size_categories:
- 1K<n<10K
pretty_name: Home Care Cost Model — Canadian Service Mix, Rate Bands, and Tax Relief Sensitivity
configs:
- config_name: services_canada
  data_files: home_care_services_canada.csv
- config_name: tax_parameters_2026
  data_files: home_care_tax_parameters_2026.csv
- config_name: subsidy_programs
  data_files: home_care_subsidy_programs.csv
- config_name: scenarios
  data_files: home_care_scenarios.csv
- config_name: per_province_rate_bands
  data_files: home_care_per_province_rate_bands.csv
- config_name: cost_model_archetypes
  data_files: home_care_cost_model_archetypes.csv
- config_name: tax_relief_sensitivity
  data_files: home_care_tax_relief_sensitivity.csv
- config_name: subsidy_gap
  data_files: home_care_subsidy_gap.csv
---

# Home Care Cost Model — Datasets

Open data companion to the Home Care Cost Model reference framework. Eight
CSV datasets totalling roughly 9,200 rows span three classes: raw source
retrievals, hand-curated reference tables, and engine-derived scenario
grids. All values are denominated in Canadian dollars (CAD) and indexed to
the 2026 taxation year.

## Dataset classes

### Class 1 — Sources (raw, credited)

Stored under `sources/<organisation>/`. Every file has a sibling
`<filename>.source.json` recording upstream URL, retrieval ISO timestamp,
declared license, and SHA256. A machine-readable provenance manifest is at
`SOURCES.md`. No Source file is ever edited post-download. See
`pull_sources.py` to reproduce.

Upstreams include Statistics Canada (wage, population, and CPI tables),
Canadian Institute for Health Information (home care indicators), Canada
Revenue Agency (tax folios), Veterans Affairs Canada, Indigenous Services
Canada (FNIHB), and the Ontario, BC, Alberta, Quebec, Saskatchewan,
Manitoba, Nova Scotia, New Brunswick, Prince Edward Island, Newfoundland
and Labrador, Yukon, Northwest Territories, and Nunavut ministries of
health.

### Class 2 — Reference tables (hand-curated, deterministic)

| File | Rows | Description |
|---|---|---|
| `home_care_services_canada.csv` | ~80 | Scope of practice, training hours, regulating body, and median private-pay rate bands for 8 service categories across 13 Canadian jurisdictions plus federal VAC VIP and ISC FNIHB cross-jurisdiction rows. |
| `home_care_tax_parameters_2026.csv` | ~65 | 2026 federal and provincial tax parameters for METC, DTC, CCC, VAC VIP, and provincial disability amounts. |
| `home_care_subsidy_programs.csv` | 15 | Provincial, territorial, VAC VIP, and FNIHB subsidised home care programs: administering body, eligibility, typical hours, wait time, URL. |

Each row in these tables cites one or more `source_id`s from the Sources
manifest. Rates were reconciled against StatsCan Table 14-10-0417-01 wages
as a floor and the Canadian Home Care Association agency markup range as a
ceiling.

### Class 3 — Derived scenarios (engine-generated)

Every row in every derived dataset is produced by importing
`engines/python/engine.py` and calling `calculate_home_care_costs()` with
a specific input combination. These are the tables most directly useful
for secondary analysis.

| File | Rows | Description |
|---|---|---|
| `home_care_scenarios.csv` | 5,000 | Synthetic household scenarios. Province sampled by StatsCan 65+ population share. Diagnosis-cognition-mobility joint distribution calibrated to CIHI home care indicators. Deterministic with `random.seed(42)`. |
| `home_care_per_province_rate_bands.csv` | 520 | Per-province, per-category, per-year (2019–2026) rate bands, CPI-adjusted from the 2026 reference using the StatsCan 18-10-0004-01 health subindex. |
| `home_care_cost_model_archetypes.csv` | 1,820 | Engine outputs for a (province × ADL × IADL × cognitive × mobility) grid at constant household composition and income. |
| `home_care_tax_relief_sensitivity.csv` | 1,300 | Sensitivity grid: 13 provinces × 5 ADL points × 5 income bands × 4 DTC/VIP flag combinations. |
| `home_care_subsidy_gap.csv` | 390 | 13 jurisdictions × 30 representative scenarios, showing subsidised hours vs model-recommended hours vs monthly dollar gap. Exposes cross-province home care program inequity. |

## "Synthetic. Generated from seed 42. Not survey data."

All Class 3 CSVs are produced deterministically from calibrated sampling
distributions and the reference tables. They are **not** survey data and
**must not** be cited as empirical observations of individual households.
They are intended for policy analysis, decision support, and cost model
validation, not for biostatistical inference.

## Reproducing the pipeline

```bash
# From the project root
python datasets/pull_sources.py                               # Class 1
python datasets/generate_home_care_services_canada.py          # Class 2a
python datasets/generate_home_care_tax_parameters.py           # Class 2b
python datasets/generate_home_care_subsidy_programs.py         # Class 2c
python datasets/generate_home_care_scenarios.py                # Class 3a
python datasets/generate_home_care_per_province_rate_bands.py  # Class 3b
python datasets/generate_home_care_cost_model_archetypes.py    # Class 3c
python datasets/generate_home_care_tax_relief_sensitivity.py   # Class 3d
python datasets/generate_home_care_subsidy_gap.py              # Class 3e
```

Regenerating any generator twice in the same Python environment must
yield a byte-identical output — all sampling uses `random.seed(42)`.

## License

- **Source code** (`generate_*.py`, `pull_sources.py`): MIT
- **Reference and derived CSVs**: Creative Commons Attribution 4.0
  International (CC BY 4.0). Attribution: *Dave Cook (2026). Home Care
  Cost Model — datasets companion to the working paper.*

## Citation

```
Cook, D. (2026). The Home Care Cost Model: Personal Support,
Housekeeping, and Service Mix Decisions for Aging in Place in Canada
— datasets. Version 0.1.0. https://doi.org/10.5281/zenodo.XXXXXXX
```

(The DOI will be populated after Zenodo deposit.)
