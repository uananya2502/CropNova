"""Regression tests for issues found during the beginner-code review."""

from copy import deepcopy
from io import BytesIO
import json
from unittest.mock import patch

import pytest

from cropnova.core.agent import run_assessment, normalize_profile
from app import application
from cropnova.ai.assessment_questions import cached_answer, validate_written_answer
from cropnova.core.evidence import scope_matches
from cropnova.config.public_profiles import REFERENCE_PROFILES
from cropnova.reports.report_store import load_report


PROFILE = REFERENCE_PROFILES["reference-wheat"]


@pytest.mark.parametrize("field", ["soil_ph", "water_budget_mm"])
@pytest.mark.parametrize("value", [10**1000, [], {}, True])
def test_malformed_numbers_return_input_errors_instead_of_crashing(field, value):
    assert run_assessment({**PROFILE, field: value})["status"] == "INVALID_INPUT"


def test_normalization_preserves_missing_measurements_and_does_not_mutate_input():
    original = {**PROFILE, "soil_ph": "", "water_budget_mm": ""}
    before = deepcopy(original)
    normalized = normalize_profile(original)
    assert normalized["soil"]["ph"] is None
    assert normalized["water"]["budget_mm"] is None
    assert original == before


@pytest.mark.parametrize("field", ["state", "district", "season"])
def test_excessive_labels_are_rejected(field):
    assert run_assessment({**PROFILE, field: "x" * 161})["status"] == "INVALID_INPUT"


def test_names_and_ids_are_resolved_once_without_duplicate_assessments():
    result = run_assessment({**PROFILE, "candidate_ids": [" Wheat ", "wheat", "WHEAT"]})
    assert result["status"] == "FEASIBLE_OPTIONS_FOUND"
    assert result["csp_result"]["diagnostics"]["assignments_examined"] == 1


def test_conflicting_region_alias_cannot_bypass_scope():
    fact = {"applicability": {"state": "Haryana", "region": "Punjab"}}
    assert not scope_matches(fact, {"region": {"state": "Haryana"}})
    fact["applicability"]["region"] = "Haryana"
    assert scope_matches(fact, {"region": {"state": "Haryana"}})


def web_post(body, declared_size=None):
    result = {}

    def start(status, headers):
        result.update(status=status, headers=dict(headers))

    result["body"] = b"".join(
        application(
            {
                "REQUEST_METHOD": "POST",
                "PATH_INFO": "/assess",
                "CONTENT_LENGTH": str(len(body) if declared_size is None else declared_size),
                "wsgi.input": BytesIO(body),
            },
            start,
        )
    )
    return result


@pytest.mark.parametrize("declared_size", [-1, "wrong", 100001])
def test_invalid_or_oversized_bodies_have_clear_http_errors(declared_size):
    response = web_post(b"", declared_size)
    assert response["status"].startswith("413" if declared_size == 100001 else "400")


def test_truncated_form_is_not_silently_accepted():
    assert web_post(b"state=Haryana", 100)["status"] == "400 Bad Request"


def test_excessive_form_field_count_is_rejected():
    body = "&".join(f"field{n}=x" for n in range(61)).encode()
    assert web_post(body)["status"] == "400 Bad Request"


def test_response_limits_script_and_form_origins():
    policy = web_post(b"")["headers"]["Content-Security-Policy"]
    assert "default-src 'self'" in policy and "form-action 'self'" in policy


def test_temporary_answer_failure_does_not_stay_cached_for_ten_minutes():
    import cropnova.ai.assessment_questions as module

    module.CACHE.clear()
    module.WINDOWS.clear()
    report = run_assessment(PROFILE)
    with patch.object(module.time, "monotonic", return_value=100), patch.object(
        module, "answer_question", return_value={"status": "search_unavailable"}
    ) as first:
        cached_answer("review-report", report, "Why wheat?")
        cached_answer("review-report", report, "Why wheat?")
        assert first.call_count == 1
    with patch.object(module.time, "monotonic", return_value=116), patch.object(
        module, "answer_question", return_value={"status": "answered"}
    ) as recovered:
        assert cached_answer("review-report", report, "Why wheat?")["status"] == "answered"
        assert recovered.call_count == 1


@pytest.mark.parametrize("token", [None, [], {}, 123, "bad"])
def test_invalid_report_link_types_are_safely_rejected(token):
    assert load_report(token) is None


def test_malformed_answer_kind_is_a_validation_error():
    report = run_assessment(PROFILE)
    answer = {
        "kind": [],
        "answer": "Text",
        "assessment_status": report["status"],
        "crop_statuses": [{"crop_id": "wheat", "status": "feasible"}],
        "evidence_ids": [],
    }
    with pytest.raises(ValueError):
        validate_written_answer(answer, report, [])


def test_rule_compatibility_helpers_use_registered_rule_logic():
    from rule_engine.rules import evaluate_crop_knowledge_rule, evaluate_water_evidence_rule
    from rule_engine.engine import evaluate_rule
    from rule_engine.rules import _evidence_rules

    facts = [{"fact_id": "F", "crop_id": "wheat", "category": "water", "source_ids": ["S"]}]
    profile = {"crop_id": "wheat"}
    for helper, rule in zip(
        (evaluate_crop_knowledge_rule, evaluate_water_evidence_rule), _evidence_rules()
    ):
        assert helper(profile, facts) == evaluate_rule(rule, profile, facts)


def test_search_cannot_borrow_another_facts_shared_source():
    from cropnova.ai.semantic_search import assessment_documents

    report = run_assessment(PROFILE)
    # pH and soil texture share a source. Disqualifying the pH fact must remove
    # the pH finding even though that source still supports soil texture.
    for fact in report["evidence_package"]["facts"]:
        if fact.get("property") == "soil_ph_range":
            fact["constraint_eligible"] = False
    records = assessment_documents(report)
    assert not any(record["title"] == "Wheat · Soil pH" for record in records)
    assert any(record["title"] == "Wheat · Soil texture" for record in records)


def test_public_system_error_hides_raw_exception_details():
    with patch(
        "cropnova.core.agent.load_knowledge", side_effect=RuntimeError("private-setting-or-path")
    ):
        result = run_assessment(PROFILE)
    assert result["status"] == "SYSTEM_ERROR"
    assert "private-setting-or-path" not in json.dumps(result)


@pytest.mark.parametrize("category", [[], {}, None, ""])
def test_bad_knowledge_categories_are_validation_errors(category):
    from tests.fixtures.demo import demo_knowledge
    from knowledge_base.validator import validate_knowledge

    knowledge = demo_knowledge()
    knowledge["facts"][0]["category"] = category
    assert any("category" in error for error in validate_knowledge(knowledge))
