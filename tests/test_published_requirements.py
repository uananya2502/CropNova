"""Published evidence integration: units, scope, boundaries and unknown outcomes."""

import json
import re
import pytest
from cropnova.core.agent import run_assessment
from tests.fixtures.demo import PRESETS
from tests.test_app import request


def profile(crop="wheat", **updates):
    return {**PRESETS["reference-" + crop][1], **updates}


def water_check(report):
    csp = report["csp_result"]
    row = (csp["feasible_candidates"] + csp["rejected_candidates"] + csp["unknown_candidates"])[0]
    checks = row["satisfied_constraints"] + row["failed_constraints"] + row["unknown_constraints"]
    return next(c for c in checks if c["constraint_id"] == "CONSTRAINT002")


@pytest.mark.parametrize("crop", ["wheat", "rice", "chickpea", "maize"])
def test_reference_profiles_have_four_supported_screens(crop):
    r = run_assessment(profile(crop))
    assert r["status"] == "FEASIBLE_OPTIONS_FOUND"
    assert r["dataset_kind"] == "research"
    assert len(r["feasible_options"][0]["satisfied_constraints"]) == 4
    assert r["knowledge_coverage"][0]["ready_checks"] == 4
    assert r["evidence_package"]["sources"]
    assert all(s["source_id"] != "SYNTHETIC_SOURCE" for s in r["evidence_package"]["sources"])


@pytest.mark.parametrize(
    "budget,code,status",
    [
        (449, "WATER_REFERENCE_SHORTFALL", "violated"),
        (450, "LOCAL_WATER_ESTIMATE_REQUIRED", "unknown"),
        (649, "LOCAL_WATER_ESTIMATE_REQUIRED", "unknown"),
        (650, "WATER_REFERENCE_COVERED", "satisfied"),
    ],
)
def test_water_reference_envelope_does_not_invent_local_requirement(budget, code, status):
    c = water_check(run_assessment(profile(water_budget_mm=budget)))
    assert (c["reason_code"], c["status"]) == (code, status)


def test_water_measurement_bases_are_not_interchangeable():
    r = run_assessment(profile("chickpea", water_basis="seasonal_crop_water"))
    assert water_check(r)["reason_code"] == "INCOMPATIBLE_WATER_BASIS"
    assert not r["feasible_options"]


def test_water_categories_cannot_replace_numeric_depth():
    r = run_assessment(profile(water_budget_mm="", water_availability="high"))
    assert r["status"] == "MORE_INFORMATION_NEEDED"
    assert water_check(r)["reason_code"] == "MISSING_USER_INPUT"
    assert r["follow_up_questions"]


def test_drainage_is_required_only_where_source_requires_it():
    assert run_assessment(profile("wheat", soil_drainage="unknown"))["feasible_options"]
    r = run_assessment(profile("chickpea", soil_drainage="unknown"))
    assert r["status"] == "MORE_INFORMATION_NEEDED"
    assert any("drain" in q.lower() for q in r["follow_up_questions"])
    r = run_assessment(profile("chickpea", soil_drainage="poorly_drained"))
    assert not r["feasible_options"]


def test_preferred_ph_is_not_a_claim_of_crop_failure():
    r = run_assessment(profile(soil_ph=8))
    assert not r["rejected_options"]
    assert any(
        c["reason_code"] == "OUTSIDE_PREFERRED_RANGE"
        for c in r["unknown_options"][0]["unknown_constraints"]
    )


def test_rajasthan_maize_reference_does_not_transfer_to_haryana():
    r = run_assessment(profile("maize", state="Haryana"))
    assert not r["feasible_options"]
    assert r["unknown_options"]


@pytest.mark.parametrize("value", ["nan", "inf", "-inf", -1, 10001, True])
def test_invalid_water_budget_never_passes(value):
    assert run_assessment(profile(water_budget_mm=value))["status"] == "INVALID_INPUT"


def test_numeric_controls_survive_html_and_json_round_trip():
    p = profile("chickpea")
    status, html = request("POST", "/assess", p)
    assert status == "200 OK"
    assert "Options that match your conditions" in html
    edit_path = re.search(r'href="(/assessment/[^/]+/edit)"', html).group(1)
    _, html = request("GET", edit_path)
    assert 'name="water_budget_mm"' in html
    assert 'value="150.0"' in html
    assert '<option value="supplemental_irrigation" selected>' in html
    _, body = request("POST", "/report", p)
    data = json.loads(body)
    assert data["profile"]["water"]["budget_mm"] == 150
    assert data["profile"]["soil"]["drainage"] == "well_drained"


def test_invalid_nonfinite_water_download_remains_valid_json():
    _, body = request("POST", "/report", profile(water_budget_mm="nan"))
    assert json.loads(body)["status"] == "INVALID_INPUT"


@pytest.mark.parametrize("texture", ["clay_loam", "silt_loam", "silty_clay_loam", "sandy_loam"])
def test_detailed_soil_textures_are_accepted_inputs(texture):
    assert run_assessment(profile(soil_texture=texture))["status"] != "INVALID_INPUT"


def test_numeric_water_reference_requires_mm_units():
    from cropnova.core.constraint_definitions import WaterConstraint

    p = {
        "water": {"budget_mm": 650, "basis": "seasonal_crop_water"},
        "region": {"country": "India"},
    }
    f = {
        "fact_id": "bad-unit",
        "verification_status": "verified_general",
        "property": "water_screening_range_mm",
        "value": [450, 650],
        "water_basis": "seasonal_crop_water",
        "unit": "cm",
        "source_ids": ["source"],
    }
    assert WaterConstraint().check({}, p, [f]).reason_code == "INCOMPATIBLE_VERIFIED_FACT"
