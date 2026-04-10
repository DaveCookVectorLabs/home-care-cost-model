Datasets
========

Eight CSV datasets ship with this repository, totalling roughly 9,200
rows across three classes: raw source retrievals, hand-curated reference
tables, and engine-derived scenario grids.

Reference tables
----------------

* ``home_care_services_canada.csv`` — ~112 rows. Scope of practice and
  private-pay rate bands for 8 service categories across 13 Canadian
  jurisdictions plus federal cross-jurisdiction rows for VAC VIP and
  ISC FNIHB.
* ``home_care_tax_parameters_2026.csv`` — ~40 rows. Federal and
  provincial tax parameters for METC, DTC, CCC, and VAC VIP, indexed to
  the 2026 taxation year.
* ``home_care_subsidy_programs.csv`` — 15 rows. Provincial and
  territorial subsidised home care programs.

Derived scenario grids
----------------------

* ``home_care_scenarios.csv`` — 5,000 synthetic household scenarios with
  engine outputs. Deterministic with ``random.seed(42)``.
* ``home_care_per_province_rate_bands.csv`` — 520 rows of CPI-adjusted
  per-province rate bands 2019–2026.
* ``home_care_cost_model_archetypes.csv`` — 1,820 rows of engine outputs
  for a canonical archetype grid.
* ``home_care_tax_relief_sensitivity.csv`` — 1,300 rows of tax credit
  sensitivity across income bands.
* ``home_care_subsidy_gap.csv`` — 390 rows of cross-province subsidy
  gap analysis.

Provenance
----------

Every row in every reference and derived dataset cites one or more
``source_id`` values that join back to the manifest at
``datasets/SOURCES.md``. Raw source retrievals are stored verbatim
under ``datasets/sources/<organisation>/`` with sibling
``.source.json`` sidecars recording upstream URL, retrieval timestamp,
license, and SHA256.
