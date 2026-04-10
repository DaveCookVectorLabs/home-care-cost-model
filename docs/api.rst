API Reference
=============

The reference implementation is ``engines/python/engine.py``. The primary
entry point is ``calculate_home_care_costs()``.

Inputs
------

:adl_katz_score: int, 0–6. Katz Index of Independence in Activities of
    Daily Living. 6 = full independence, 0 = total dependence.
:iadl_lawton_score: int, 0–8. Lawton Instrumental ADL Scale.
:province: str, one of {ON, QC, BC, AB, SK, MB, NS, NB, NL, PE, YT, NT, NU}.
:household_composition: str, one of {alone, with_spouse, with_adult_child,
    multigen}.
:cognitive_status: str, one of {intact, mild, moderate, severe}.
:mobility_status: str, one of {independent, cane, walker, wheelchair,
    bedbound}.
:primary_diagnosis_category: str, one of {dementia, stroke, frailty,
    parkinson, post_surgical, mobility_only, chronic_mixed}.
:informal_caregiver_hours_per_week: float, default 0.
:net_family_income_cad: float, default 60000.
:is_veteran: bool, default False.
:has_dtc: bool, default False.
:agency_vs_private: str, {private, agency}, default private.
:include_subsidy: bool, default True.
:tax_year: int, default 2026.

Outputs
-------

Returns a ``HomeCareCostCalculation`` dataclass containing recommended
hours per service category, the hourly rate for each, private-pay cost,
subsidised hours allocated, tax credit stack breakdown, out-of-pocket
before and after credits, hybrid savings comparison, scope and
employment-law warnings, data source citations, and the mandatory
disclaimer.

REST API
--------

``POST /calculate`` accepts the same parameters as JSON and returns the
full result dataclass serialised to JSON. ``GET /health`` reports engine
status and reference table load counts. The reference Python engine runs
on port 8003 by default.
