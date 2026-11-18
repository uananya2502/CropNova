"""Fuzzy membership, traceability and separation from the hard crop checks."""

from copy import deepcopy
import math
import pytest

from agent import run_assessment
from fuzzy_logic import analyze_assessment, infer_alignment, memberships, rising, triangle
from public_profiles import REFERENCE_PROFILES
from web_views import result_page

PROFILE = REFERENCE_PROFILES["reference-wheat"]


def wheat(**changes):
    return run_assessment({**PROFILE, **changes})


@pytest.mark.parametrize("value,expected", [(0, 0), (0.5, 0.5), (1, 1), (2, 1)])
def test_rising_membership(value, expected):
    assert rising(value, 0, 1) == expected


@pytest.mark.parametrize("value,expected", [(0, 0), (0.5, 1), (1, 0), (-1, 0)])
def test_triangular_membership(value, expected):
    assert triangle(value, 0, 0.5, 1) == expected


def test_memberships_are_bounded_and_cover_input_domain():
    for ph in (0, 0.1, 0.25, 0.5, 0.75, 1, 10):
        for water in (0, 0.5, 0.7, 0.8, 0.9, 1, 2):
            for values in memberships(ph, water).values():
                assert all(0 <= value <= 1 for value in values.values())
                assert sum(values.values()) > 0


def test_sugeno_weighted_average_matches_fired_rule_trace():
    result = infer_alignment(0.1, 0.9)
    rows = result["fired_rules"]
    expected = sum(row["strength"] * row["consequent"] for row in rows) / sum(
        row["strength"] for row in rows
    )
    assert result["score"] == round(expected, 1)
    assert result["method"] == "zero_order_sugeno_min_and_weighted_average"


def test_alignment_changes_gradually_with_more_water():
    scores = [infer_alignment(0, ratio)["score"] for ratio in (0.5, 0.65, 0.8, 0.9, 1)]
    assert scores == sorted(scores)
    assert len(set(scores)) == len(scores)


def test_greater_distance_from_preferred_ph_does_not_raise_full_water_score():
    scores = [infer_alignment(distance, 1)["score"] for distance in (0, 0.1, 0.25, 0.5, 0.75)]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.parametrize("ph,water", [(math.nan, 1), (0, math.inf), (-1, 1), (0, -1)])
def test_invalid_fuzzy_inputs_are_rejected(ph, water):
    with pytest.raises(ValueError):
        infer_alignment(ph, water)


def test_reference_example_has_exact_support_and_does_not_mutate_report():
    report = wheat()
    before = deepcopy(report)
    analysis = analyze_assessment(report)
    result = analysis["candidates"][0]
    assert result["score"] == 85 and result["status"] == "available"
    assert result["source_ids"] and result["fact_ids"]
    assert not result["needs_review"]
    assert report == before


def test_soft_alignment_does_not_promote_an_unresolved_crop():
    report = wheat(water_budget_mm="600")
    assert report["status"] == "NO_SUPPORTED_KNOWLEDGE"
    result = report["fuzzy_analysis"]["candidates"][0]
    assert result["status"] == "available" and result["needs_review"]
    assert result["score"] < 85
    assert not report["feasible_options"]


def test_known_violation_blocks_soft_score():
    result = wheat(water_budget_mm="300")["fuzzy_analysis"]["candidates"][0]
    assert result["status"] == "blocked" and result["score"] is None


@pytest.mark.parametrize(
    "changes",
    [
        {"soil_ph": ""},
        {"water_basis": "supplemental_irrigation"},
        {"season": "unknown"},
        {"state": "Unsupported State"},
    ],
)
def test_missing_or_incompatible_context_never_gets_an_index(changes):
    assert wheat(**changes)["fuzzy_analysis"]["candidates"][0]["score"] is None


def test_ineligible_fact_cannot_be_replaced_by_another_fact_with_same_source():
    report = wheat()
    for fact in report["evidence_package"]["facts"]:
        if fact.get("property") == "soil_ph_range":
            fact["constraint_eligible"] = False
    assert analyze_assessment(report)["candidates"][0]["score"] is None


def test_public_panel_preserves_review_message_and_plain_language():
    html = result_page(wheat(water_budget_mm="600"), "private-token").decode()
    assert "How closely do pH and water align?" in html
    assert "not a probability" in html
    assert "does not turn an open finding into a match" in html
    assert "CSP" not in html and "Sugeno" not in html
