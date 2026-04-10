# Sources Manifest — Home Care Cost Model

This file catalogues every upstream data source referenced by the reference
tables (Class 2) and derived scenarios (Class 3) in this repository. Every
row in every derived dataset carries a `source_id` cell that joins back to
an entry in this manifest.

Raw downloaded files (Class 1) live under `datasets/sources/<organisation>/`
with a sibling `<filename>.source.json` recording upstream URL, retrieval
timestamp, license, and SHA256. Those files are committed verbatim and
never edited.

---

## Format

Each entry below has the following fields:

- **source_id** — short identifier used as a foreign key from dataset rows
- **organisation** — publishing body
- **title** — full title of the resource
- **url** — authoritative URL at time of retrieval
- **retrieved** — ISO date of retrieval into the Sources folder
- **license** — license or terms of use as stated by the publisher
- **used_for** — which reference or derived dataset depends on this source

---

## Statistics Canada

### `statcan-14-10-0417-01`
- **organisation**: Statistics Canada
- **title**: Employment and average weekly earnings (including overtime) for all employees by industry, monthly, seasonally adjusted — Table 14-10-0417-01
- **url**: https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1410041701
- **retrieved**: 2026-04-09
- **license**: Statistics Canada Open Licence
- **used_for**: rate bands in `home_care_services_canada.csv` for PSW (NOC 44101), HCA (NOC 33102), RN (NOC 31301), LPN (NOC 32101); CPI-adjusted rate derivation in `home_care_per_province_rate_bands.csv`

### `statcan-17-10-0005-01`
- **organisation**: Statistics Canada
- **title**: Population estimates on July 1, by age and sex — Table 17-10-0005-01
- **url**: https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1710000501
- **retrieved**: 2026-04-09
- **license**: Statistics Canada Open Licence
- **used_for**: province weighting for synthetic 65+ population in `home_care_scenarios.csv`

### `statcan-18-10-0004-01`
- **organisation**: Statistics Canada
- **title**: Consumer Price Index, monthly, not seasonally adjusted — Table 18-10-0004-01 (health and personal care subindices)
- **url**: https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1810000401
- **retrieved**: 2026-04-09
- **license**: Statistics Canada Open Licence
- **used_for**: rate trend 2019–2026 in `home_care_per_province_rate_bands.csv`

### `statcan-gss-2018-caregiving`
- **organisation**: Statistics Canada
- **title**: General Social Survey on Caregiving and Care Receiving, Cycle 32 (2018), public use microdata file
- **url**: https://www150.statcan.gc.ca/n1/en/catalogue/89M0033X
- **retrieved**: 2026-04-09
- **license**: Statistics Canada Open Licence (public use file)
- **used_for**: informal caregiver hour distributions in `home_care_scenarios.csv`

## Canadian Institute for Health Information (CIHI)

### `cihi-hcrs-indicators`
- **organisation**: Canadian Institute for Health Information
- **title**: Home Care Reporting System (HCRS) public indicator tables
- **url**: https://www.cihi.ca/en/home-care-reporting-system-metadata
- **retrieved**: 2026-04-09
- **license**: CIHI Terms of Use (research and educational use permitted with attribution)
- **used_for**: ADL/IADL distribution calibration, diagnosis-cognition-mobility joint distribution

### `cihi-your-health-system`
- **organisation**: Canadian Institute for Health Information
- **title**: Your Health System — home care volume, wait time, and access indicators
- **url**: https://yourhealthsystem.cihi.ca
- **retrieved**: 2026-04-09
- **license**: CIHI Terms of Use
- **used_for**: `subsidy_waitlist_typical_days` column in `home_care_services_canada.csv`

## Canada Revenue Agency (CRA)

### `cra-s1-f1-c1-metc`
- **organisation**: Canada Revenue Agency
- **title**: Income Tax Folio S1-F1-C1 — Medical Expense Tax Credit
- **url**: https://www.canada.ca/en/revenue-agency/services/tax/technical-information/income-tax/income-tax-folios-index/series-1-individuals/folio-1-health-medical/income-tax-folio-s1-f1-c1-medical-expense-tax-credit.html
- **retrieved**: 2026-04-09
- **license**: Government of Canada — permitted for personal and public non-commercial use with attribution
- **used_for**: METC formula, 3% of net income / $2,635 (2026) floor, qualifying expenses list in `home_care_tax_parameters_2026.csv`

### `cra-s1-f1-c2-dtc`
- **organisation**: Canada Revenue Agency
- **title**: Income Tax Folio S1-F1-C2 — Disability Tax Credit
- **url**: https://www.canada.ca/en/revenue-agency/services/tax/technical-information/income-tax/income-tax-folios-index/series-1-individuals/folio-1-health-medical/income-tax-folio-s1-f1-c2-disability-tax-credit.html
- **retrieved**: 2026-04-09
- **license**: Government of Canada
- **used_for**: DTC base amount and supplement in `home_care_tax_parameters_2026.csv`

### `cra-canada-caregiver-credit`
- **organisation**: Canada Revenue Agency
- **title**: Canada Caregiver Credit — guidance and Schedule 5 calculation
- **url**: https://www.canada.ca/en/revenue-agency/services/tax/individuals/topics/about-your-tax-return/tax-return/completing-a-tax-return/deductions-credits-expenses/canada-caregiver-amount.html
- **retrieved**: 2026-04-09
- **license**: Government of Canada
- **used_for**: CCC dependant amounts, income test phase-out in `home_care_tax_parameters_2026.csv`

## Veterans Affairs Canada

### `vac-vip-2026`
- **organisation**: Veterans Affairs Canada
- **title**: Veterans Independence Program — benefit rates and eligibility
- **url**: https://www.veterans.gc.ca/en/health-support/physical-health-and-wellness/compensation-illness-injury/veterans-independence-program
- **retrieved**: 2026-04-09
- **license**: Government of Canada
- **used_for**: VAC VIP reimbursement amounts in `home_care_tax_parameters_2026.csv` and `home_care_services_canada.csv`

## Indigenous Services Canada

### `isc-fnihb-home-community-care`
- **organisation**: Indigenous Services Canada, First Nations and Inuit Health Branch
- **title**: First Nations and Inuit Home and Community Care Program
- **url**: https://www.sac-isc.gc.ca/eng/1100100035250/1533317440443
- **retrieved**: 2026-04-09
- **license**: Government of Canada
- **used_for**: NIHB eligibility flag in `home_care_services_canada.csv`

## Provincial home care programs

### `hccss-ontario`
- **organisation**: Ontario Ministry of Health
- **title**: Home and Community Care Support Services — provincial program pages
- **url**: https://www.ontario.ca/page/homecare-seniors
- **retrieved**: 2026-04-09
- **license**: Queen's Printer for Ontario — Open Government Licence – Ontario
- **used_for**: Ontario rows in `home_care_subsidy_programs.csv`

### `gov-bc-home-community-care`
- **organisation**: Government of British Columbia, Ministry of Health
- **title**: Home and Community Care Policy Manual
- **url**: https://www2.gov.bc.ca/gov/content/health/accessing-health-care/home-community-care
- **retrieved**: 2026-04-09
- **license**: Open Government Licence – British Columbia
- **used_for**: BC rows in `home_care_subsidy_programs.csv`

### `ahs-continuing-care-at-home`
- **organisation**: Alberta Health Services
- **title**: Continuing Care at Home program
- **url**: https://www.albertahealthservices.ca/cc/page15517.aspx
- **retrieved**: 2026-04-09
- **license**: Government of Alberta – Open Government Licence
- **used_for**: Alberta rows in `home_care_subsidy_programs.csv`

### `quebec-clsc-sad`
- **organisation**: Gouvernement du Québec
- **title**: Soutien à domicile — Services des CLSC
- **url**: https://www.quebec.ca/en/health/health-system-and-services/home-support/home-care-services
- **retrieved**: 2026-04-09
- **license**: Creative Commons Attribution 4.0 Quebec
- **used_for**: Quebec rows in `home_care_subsidy_programs.csv`

### `sha-home-care`
- **organisation**: Saskatchewan Health Authority
- **title**: Home care — services and eligibility
- **url**: https://www.saskhealthauthority.ca/our-services/services-directory/home-care
- **retrieved**: 2026-04-09
- **license**: Government of Saskatchewan
- **used_for**: Saskatchewan row

### `gov-mb-home-care`
- **organisation**: Government of Manitoba
- **title**: Manitoba Home Care Program
- **url**: https://www.gov.mb.ca/health/homecare
- **retrieved**: 2026-04-09
- **license**: Government of Manitoba
- **used_for**: Manitoba row

### `nshealth-home-care`
- **organisation**: Nova Scotia Health
- **title**: Home Care — Nova Scotia Continuing Care
- **url**: https://novascotia.ca/dhw/ccs/home-care.asp
- **retrieved**: 2026-04-09
- **license**: Government of Nova Scotia
- **used_for**: Nova Scotia row

### `gnb-extra-mural-program`
- **organisation**: Government of New Brunswick
- **title**: Extra-Mural Program
- **url**: https://www2.gnb.ca/content/gnb/en/departments/health/MedicarePrescriptionDrugPlan/TheExtraMuralProgram.html
- **retrieved**: 2026-04-09
- **license**: Government of New Brunswick
- **used_for**: New Brunswick row

### `pei-home-care`
- **organisation**: Government of Prince Edward Island
- **title**: Home Care — Health PEI
- **url**: https://www.princeedwardisland.ca/en/information/health-pei/home-care
- **retrieved**: 2026-04-09
- **license**: Government of PEI
- **used_for**: Prince Edward Island row

### `nlh-home-care`
- **organisation**: Newfoundland and Labrador Health Services
- **title**: Home Support Program
- **url**: https://www.nlhealthservices.ca/find-care/community-based-care/home-support-program/
- **retrieved**: 2026-04-09
- **license**: Government of Newfoundland and Labrador
- **used_for**: Newfoundland and Labrador row

### `yukon-home-care`
- **organisation**: Government of Yukon
- **title**: Home Care Program
- **url**: https://yukon.ca/en/health-and-wellness/care-services/apply-home-care
- **retrieved**: 2026-04-09
- **license**: Government of Yukon
- **used_for**: Yukon row

### `gnwt-home-community-care`
- **organisation**: Government of Northwest Territories
- **title**: Home and Community Care
- **url**: https://www.hss.gov.nt.ca/en/services/home-and-community-care
- **retrieved**: 2026-04-09
- **license**: Government of Northwest Territories
- **used_for**: Northwest Territories row

### `gn-home-community-care`
- **organisation**: Government of Nunavut, Department of Health
- **title**: Home and Community Care Program
- **url**: https://www.gov.nu.ca/health/information/home-and-community-care
- **retrieved**: 2026-04-09
- **license**: Government of Nunavut
- **used_for**: Nunavut row

## Non-governmental organisations

### `chca-high-value-home-care`
- **organisation**: Canadian Home Care Association
- **title**: High-Value Home Care — report series
- **url**: https://cdnhomecare.ca/category/publications/
- **retrieved**: 2026-04-09
- **license**: CHCA Terms of Use — permitted for citation with attribution
- **used_for**: agency markup ranges in `home_care_services_canada.csv`

## Academic assessment instruments

### `katz-1963-adl-index`
- **organisation**: Katz S, Ford AB, Moskowitz RW, Jackson BA, Jaffe MW
- **title**: Studies of Illness in the Aged. The Index of ADL: A Standardized Measure of Biological and Psychosocial Function. *JAMA* 185 (12): 914–919
- **url**: https://jamanetwork.com/journals/jama/article-abstract/666768
- **retrieved**: 2026-04-09
- **license**: Fair use — abstract and scoring methodology for non-commercial reference
- **used_for**: Katz ADL scale in `engines/python/engine.py` and PDF Part II

### `lawton-brody-1969-iadl`
- **organisation**: Lawton MP, Brody EM
- **title**: Assessment of older people: self-maintaining and instrumental activities of daily living. *The Gerontologist* 9 (3): 179–186
- **url**: https://academic.oup.com/gerontologist/article-abstract/9/3_Part_1/179/569496
- **retrieved**: 2026-04-09
- **license**: Fair use — abstract and scoring methodology for non-commercial reference
- **used_for**: Lawton IADL scale in `engines/python/engine.py` and PDF Part II

---

Last updated: 2026-04-09. If you spot a broken link or an out-of-date
retrieval, please open an issue on the repository.
