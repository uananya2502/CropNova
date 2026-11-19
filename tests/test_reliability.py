"""Regression cases for evidence conflicts, scope boundaries and integration."""

from copy import deepcopy
import json
import math
import pytest
from cropnova.core.agent import run_assessment
from cropnova.core.csp_solver import solve_constraints
from tests.fixtures.demo import BASE, demo_knowledge
from cropnova.core.evidence import scope_matches
from knowledge_base.validator import validate_knowledge
from rule_engine.engine import evaluate_rule, evaluate_rules
from rule_engine.models import Rule, ConditionResult, RuleStatus
from tests.test_csp_solver import candidate, PROFILE, fact
from tests.test_app import request


def checked(item, profile=PROFILE):
    r = solve_constraints([item], profile)
    return (r["feasible_candidates"] + r["rejected_candidates"] + r["unknown_candidates"])[0]


@pytest.mark.parametrize(
    "property,value",
    [
        ("growing_season", "kharif"),
        ("soil_texture", "sandy"),
        ("water_requirement", "high"),
        ("soil_ph_range", [5, 9]),
    ],
)
def test_conflicting_requirements_never_become_a_pass(property, value):
    item = candidate("A")
    item["facts"].append(fact("conflict", property, value))
    row = checked(item)
    assert row["status"] == "unknown"
    conflict = next(
        c for c in row["unknown_constraints"] if c["reason_code"] == "CONFLICTING_VERIFIED_FACTS"
    )
    assert "conflict" in conflict["fact_ids"]
    assert conflict["source_ids"]


def test_duplicate_identical_ph_evidence_is_consistent():
    item = candidate("A")
    item["facts"].append(fact("second-source", "soil_ph_range", [6, 8]))
    assert checked(item)["status"] == "feasible"


@pytest.mark.parametrize(
    "value", [[8, 6], [float("nan"), 8], [6, float("inf")], ["bad", 8], [], [True, 8]]
)
def test_malformed_ph_fact_is_unknown(value):
    item = candidate("A")
    item["facts"][-1]["value"] = value
    assert checked(item)["status"] == "unknown"


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), True, "bad", -1, 15])
def test_invalid_direct_solver_ph_never_passes(value):
    p = deepcopy(PROFILE)
    p["soil"]["ph"] = value
    assert checked(candidate("A"), p)["status"] == "unknown"


@pytest.mark.parametrize("ph", [6, 8])
def test_inclusive_ph_boundaries(ph):
    p = deepcopy(PROFILE)
    p["soil"]["ph"] = ph
    assert checked(candidate("A"), p)["status"] == "feasible"


@pytest.mark.parametrize(
    "scope",
    [
        {"district": "Karnal"},
        {"state": "Punjab"},
        {"country": "Portugal"},
        {"season": "kharif"},
        {"growth_stage": "flowering"},
        {"irrigation": "available"},
    ],
)
def test_restricted_fact_does_not_leak_into_other_context(scope):
    item = candidate("A")
    item["facts"][0]["applicability"] = scope
    assert checked(item)["status"] == "unknown"


def test_matching_district_and_season_are_accepted():
    p = deepcopy(PROFILE)
    p["region"]["district"] = "Karnal"
    item = candidate("A")
    item["facts"][0]["applicability"] = {
        "state": "Test State",
        "district": "KARNAL",
        "season": "rabi",
    }
    assert checked(item, p)["status"] == "feasible"


def test_other_crop_fact_cannot_support_a_candidate():
    item = candidate("A")
    item["facts"][0]["crop_id"] = "B"
    assert checked(item)["status"] == "unknown"


def test_non_exhaustive_season_list_does_not_prove_rejection():
    item = candidate("A", season="kharif")
    item["facts"][0]["closed_world"] = False
    row = checked(item)
    assert row["status"] == "unknown"
    assert row["unknown_constraints"][0]["reason_code"] == "NON_EXHAUSTIVE_EVIDENCE"


@pytest.mark.parametrize("selection", [["typo"], ["wheat", "typo"], [123], {"crop": "wheat"}])
def test_invalid_selection_is_reported(selection):
    assert (
        run_assessment({**BASE, "candidate_ids": selection}, knowledge_override=demo_knowledge())[
            "status"
        ]
        == "INVALID_INPUT"
    )


def test_rules_only_evaluate_selected_crops():
    r = run_assessment({**BASE, "candidate_ids": ["Wheat"]}, knowledge_override=demo_knowledge())
    assert [c["crop_id"] for c in r["rule_results"]] == ["wheat"]
    assert r["csp_result"]["diagnostics"]["assignments_examined"] == 1


def test_false_and_unknown_rule_is_false_and_does_not_claim_conclusion():
    def false(p, f):
        return ConditionResult("false", RuleStatus.NOT_FIRED, "Known mismatch")

    def unknown(p, f):
        return ConditionResult("unknown", RuleStatus.UNKNOWN, "Missing input")

    r = evaluate_rule(Rule("TEST", "test", (false, unknown), "Should not claim this"), {}, [])
    assert r.status is RuleStatus.NOT_FIRED
    assert r.conclusion != "Should not claim this"


def test_season_rule_fires_or_not_fires_using_actual_evidence():
    facts = demo_knowledge()["facts"][:4]
    yes = next(
        r
        for r in evaluate_rules(
            {"crop_id": "wheat", "region": {"state": "Haryana"}, "season": "rabi"}, facts
        ).results
        if r.rule_id == "RULE_SEASON_001"
    )
    no = next(
        r
        for r in evaluate_rules(
            {"crop_id": "wheat", "region": {"state": "Haryana"}, "season": "kharif"}, facts
        ).results
        if r.rule_id == "RULE_SEASON_001"
    )
    assert yes.status is RuleStatus.FIRED
    assert no.status is RuleStatus.NOT_FIRED


def test_incomplete_optional_fields_do_not_hide_missing_knowledge():
    knowledge = demo_knowledge()
    for fact in knowledge["facts"]:
        if fact["property"] == "water_requirement":
            fact["constraint_eligible"] = False
    r = run_assessment(BASE, knowledge_override=knowledge)
    assert r["status"] == "NO_SUPPORTED_KNOWLEDGE"
    assert not r["follow_up_questions"]


def test_missing_ph_prompts_even_with_other_inputs_complete():
    r = run_assessment(
        {**BASE, "soil_ph": "", "soil_fertility": "high", "irrigation": "available"},
        knowledge_override=demo_knowledge(),
    )
    assert r["status"] == "MORE_INFORMATION_NEEDED"
    assert any("pH" in q for q in r["follow_up_questions"])


def test_unreviewed_source_cannot_support_nested_or_top_level_facts():
    k = demo_knowledge()
    k["sources"][0]["review_status"] = "pending"
    assert not run_assessment(BASE, knowledge_override=k)["feasible_options"]
    k = demo_knowledge()
    k["crops"][0]["facts"] = [k["facts"][0]]
    assert validate_knowledge(k)


def test_coverage_distinguishes_research_gaps_and_synthetic_readiness():
    synthetic = run_assessment(BASE, knowledge_override=demo_knowledge())
    assert all(c["ready_checks"] == 4 for c in synthetic["knowledge_coverage"])
    research = run_assessment(BASE)
    assert any(c["ready_checks"] < 4 for c in research["knowledge_coverage"])
    assert synthetic["dataset_kind"] == "synthetic"
    assert research["dataset_kind"] == "research"


def test_water_preference_never_includes_rejected_crops():
    r = run_assessment({**BASE, "objective": "conserve_water"}, knowledge_override=demo_knowledge())
    assert [c["candidate_id"] for c in r["preference_order"]] == ["wheat", "maize"]
    assert [c["water_requirement"] for c in r["preference_order"]] == ["low", "moderate"]


def test_download_is_valid_json_with_decisions_and_sources():
    from cropnova.config.public_profiles import REFERENCE_PROFILES

    status, body = request("POST", "/report", REFERENCE_PROFILES["reference-wheat"])
    report = json.loads(body)
    assert status == "200 OK"
    assert report["status"] == "FEASIBLE_OPTIONS_FOUND"
    assert report["evidence_package"]["facts"]
    assert report["evidence_package"]["sources"]


def test_invalid_json_download_still_returns_valid_json():
    status, body = request("POST", "/report", {**BASE, "soil_ph": "nan"})
    assert json.loads(body)["status"] == "INVALID_INPUT"
    assert "NaN" not in body


@pytest.mark.parametrize(
    "field,value",
    [("crop_id", []), ("verification_status", {}), ("source_ids", [{}]), ("property", [])],
)
def test_validator_reports_malformed_types_without_crashing(field, value):
    k = demo_knowledge()
    k["facts"][0][field] = value
    assert validate_knowledge(k)


def test_explicitly_pending_fact_does_not_fire_public_rule_api():
    facts = [
        {
            "fact_id": "pending",
            "crop_id": "wheat",
            "category": "water",
            "source_ids": ["S"],
            "verification_status": "pending_research",
        }
    ]
    results = evaluate_rules({"crop_id": "wheat"}, facts).results
    assert all(r.status is RuleStatus.UNKNOWN for r in results)


def test_malformed_web_encoding_is_rejected():
    import io
    from app import application

    result = {}

    def start(status, headers):
        result["status"] = status

    application(
        {
            "REQUEST_METHOD": "POST",
            "PATH_INFO": "/assess",
            "CONTENT_LENGTH": "1",
            "wsgi.input": io.BytesIO(b"\xff"),
        },
        start,
    )
    assert result["status"] == "400 Bad Request"
