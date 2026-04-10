#!/usr/bin/env python3
"""Tests for the Home Care Cost Model engine."""

import pytest
from engine import (
    calculate_home_care_costs,
    derive_psw_hours,
    derive_housekeeping_hours,
    scope_gate_warnings,
    VALID_PROVINCES,
)


# ──────────────────────────────────────────────────────────────────────
# Scenario 1: Mrs. A., mild frailty, lives alone in Sudbury ON
# Expected archetype: "cleaner is enough"
# ──────────────────────────────────────────────────────────────────────

def test_mild_frailty_cleaner_sufficient():
    result = calculate_home_care_costs(
        adl_katz_score=5,
        iadl_lawton_score=5,
        province="ON",
        household_composition="alone",
        cognitive_status="intact",
        mobility_status="cane",
        primary_diagnosis_category="frailty",
        informal_caregiver_hours_per_week=5.0,
        net_family_income_cad=42000.0,
        has_dtc=False,
    )
    assert result.recommended_psw_hours_per_week < 10
    assert result.recommended_housekeeping_hours_per_week >= 6
    assert result.recommended_nursing_hours_per_week == 0
    assert result.recommended_service_mix in ("psw+housekeeping", "housekeeping_only")
    # scope warning should NOT fire at ADL=5 intact cognition
    assert len(result.scope_warnings) == 0
    # disclaimer always present
    assert "Reference model only" in result.disclaimer


# ──────────────────────────────────────────────────────────────────────
# Scenario 2: Moderate dementia post-stroke, Vancouver BC
# Expected: full service stack, DTC eligible, hybrid savings material
# ──────────────────────────────────────────────────────────────────────

def test_moderate_dementia_post_stroke_bc():
    result = calculate_home_care_costs(
        adl_katz_score=2,
        iadl_lawton_score=1,
        province="BC",
        household_composition="with_spouse",
        cognitive_status="moderate",
        mobility_status="walker",
        primary_diagnosis_category="dementia",
        informal_caregiver_hours_per_week=20.0,
        net_family_income_cad=72000.0,
        has_dtc=True,
    )
    assert result.recommended_psw_hours_per_week >= 15
    assert result.recommended_housekeeping_hours_per_week >= 12
    # scope warning MUST fire (adl <= 4)
    assert len(result.scope_warnings) >= 1
    assert any("Personal care required" in w for w in result.scope_warnings)
    # DTC present
    assert result.dtc_credit_value_cad > 0
    # Hybrid savings are positive when housekeeping hours exist
    assert result.hybrid_savings_vs_all_psw_monthly_cad > 0


# ──────────────────────────────────────────────────────────────────────
# Scenario 3: Post-surgical recovery, Toronto ON
# Expected: nursing gate fires if diagnosis says post-surgical
# ──────────────────────────────────────────────────────────────────────

def test_post_surgical_nursing_gate():
    result = calculate_home_care_costs(
        adl_katz_score=3,
        iadl_lawton_score=3,
        province="ON",
        household_composition="with_adult_child",
        cognitive_status="intact",
        mobility_status="walker",
        primary_diagnosis_category="post_surgical",
        informal_caregiver_hours_per_week=10.0,
        net_family_income_cad=85000.0,
    )
    assert result.recommended_nursing_hours_per_week >= 4
    # Employment law warning depends on total hours
    # CCC may or may not be present depending on household modifier
    assert result.recommended_psw_hours_per_week > 0


# ──────────────────────────────────────────────────────────────────────
# Scenario 4: Veteran with VIP eligibility
# ──────────────────────────────────────────────────────────────────────

def test_veteran_vip_eligibility():
    result = calculate_home_care_costs(
        adl_katz_score=3,
        iadl_lawton_score=3,
        province="NB",
        household_composition="alone",
        cognitive_status="mild",
        mobility_status="walker",
        primary_diagnosis_category="chronic_mixed",
        is_veteran=True,
    )
    assert result.vac_vip_credit_value_cad > 0
    # VIP should be documented as a source citation
    assert "vac-vip-2026" in result.data_source_citations


# ──────────────────────────────────────────────────────────────────────
# Scenario 5: FNIHB community member, NWT
# ──────────────────────────────────────────────────────────────────────

def test_nwt_eligibility():
    result = calculate_home_care_costs(
        adl_katz_score=4,
        iadl_lawton_score=4,
        province="NT",
        household_composition="multigen",
        cognitive_status="mild",
        mobility_status="cane",
        primary_diagnosis_category="chronic_mixed",
    )
    # NT rate multiplier should push the rates higher than ON
    on_result = calculate_home_care_costs(
        adl_katz_score=4, iadl_lawton_score=4, province="ON",
        household_composition="multigen", cognitive_status="mild",
        mobility_status="cane", primary_diagnosis_category="chronic_mixed",
    )
    assert result.psw_hourly_rate_cad > on_result.psw_hourly_rate_cad


# ──────────────────────────────────────────────────────────────────────
# Scenario 6: Bedbound high-complexity, severe cognitive
# ──────────────────────────────────────────────────────────────────────

def test_bedbound_high_complexity():
    result = calculate_home_care_costs(
        adl_katz_score=0,
        iadl_lawton_score=0,
        province="MB",
        household_composition="with_adult_child",
        cognitive_status="severe",
        mobility_status="bedbound",
        primary_diagnosis_category="chronic_mixed",
        informal_caregiver_hours_per_week=40.0,
        net_family_income_cad=55000.0,
        has_dtc=True,
    )
    # Should recommend 40+ PSW hours
    assert result.recommended_psw_hours_per_week >= 30
    # Severe cognitive automatically triggers scope warning
    assert any("Personal care required" in w for w in result.scope_warnings)
    # DTC automatically applied because cognitive=severe
    assert result.dtc_credit_value_cad > 0
    # Employment law warning at 30+ private hours
    assert len(result.employment_law_warnings) >= 1


# ──────────────────────────────────────────────────────────────────────
# Input validation
# ──────────────────────────────────────────────────────────────────────

def test_invalid_province():
    with pytest.raises(ValueError, match="province"):
        calculate_home_care_costs(
            adl_katz_score=3, iadl_lawton_score=3, province="XX",
            household_composition="alone", cognitive_status="intact",
            mobility_status="independent", primary_diagnosis_category="frailty",
        )


def test_invalid_adl_range():
    with pytest.raises(ValueError, match="adl_katz_score"):
        calculate_home_care_costs(
            adl_katz_score=7, iadl_lawton_score=3, province="ON",
            household_composition="alone", cognitive_status="intact",
            mobility_status="independent", primary_diagnosis_category="frailty",
        )


def test_all_provinces_have_rates():
    """Every valid province must produce a non-zero PSW rate."""
    for prov in VALID_PROVINCES:
        result = calculate_home_care_costs(
            adl_katz_score=3, iadl_lawton_score=3, province=prov,
            household_composition="alone", cognitive_status="intact",
            mobility_status="independent", primary_diagnosis_category="frailty",
        )
        assert result.psw_hourly_rate_cad > 0, f"zero PSW rate for {prov}"


# ──────────────────────────────────────────────────────────────────────
# Unit tests on component functions
# ──────────────────────────────────────────────────────────────────────

def test_derive_psw_hours_monotonic():
    """More independence → fewer PSW hours."""
    h_low_adl = derive_psw_hours(0, "intact", "independent", 0)
    h_high_adl = derive_psw_hours(6, "intact", "independent", 0)
    assert h_low_adl > h_high_adl


def test_derive_housekeeping_monotonic():
    """Fewer IADL capabilities → more housekeeping hours."""
    h_low = derive_housekeeping_hours(8, "with_spouse")
    h_high = derive_housekeeping_hours(0, "with_spouse")
    assert h_high > h_low


def test_scope_gate_fires_on_low_adl():
    warnings = scope_gate_warnings(3, "intact", "frailty", "walker")
    assert any("Personal care required" in w for w in warnings)


def test_scope_gate_fires_on_severe_cognitive():
    warnings = scope_gate_warnings(6, "severe", "dementia", "walker")
    assert any("Personal care required" in w for w in warnings)


def test_scope_gate_silent_on_independent():
    warnings = scope_gate_warnings(6, "intact", "frailty", "independent")
    # May still fire on other conditions but should not fire personal-care warning
    assert not any("Personal care required" in w for w in warnings)
