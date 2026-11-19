"""No paid API calls: use controlled replies to exercise success and failure."""

from copy import deepcopy
from io import BytesIO
import json
from unittest.mock import patch
from urllib.error import HTTPError, URLError
import pytest
from cropnova.core.agent import run_assessment
from app import genai_panel
from tests.fixtures.demo import PRESETS, demo_knowledge, BASE
from cropnova.ai.genai_explainer import (
    prepare_context,
    validate_answer,
    generate_explanation,
    call_openai,
)
from tests.test_app import request


def assessment():
    return run_assessment(PRESETS["reference-wheat"][1])


def valid_answer(context):
    return {
        "assessment_status": context["assessment_status"],
        "explanations": [
            {
                "crop_id": crop["crop_id"],
                "status": crop["status"],
                "text": "This crop matches the recorded screening checks. Local confirmation is still needed.",
                "fact_ids": list(
                    dict.fromkeys(fid for check in crop["checks"] for fid in check["fact_ids"])
                ),
            }
            for crop in context["candidates"]
        ],
    }


def test_generation_does_not_mutate_assessment_or_decisions():
    report = assessment()
    before = deepcopy(report)
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-only"}), patch(
        "cropnova.ai.genai_explainer.call_openai", side_effect=lambda c, k, m: valid_answer(c)
    ):
        result = generate_explanation(report, requested=True)
    assert result["status"] == "generated"
    assert report == before


def test_no_request_means_no_provider_call():
    with patch("cropnova.ai.genai_explainer.call_openai") as call:
        assert generate_explanation(assessment())["status"] == "not_requested"
    call.assert_not_called()


def test_missing_key_shows_honest_fallback():
    with patch.dict("os.environ", {}, clear=True), patch(
        "cropnova.ai.genai_explainer.call_openai"
    ) as call:
        result = generate_explanation(assessment(), requested=True)
    assert result["status"] == "not_configured"
    assert not result["explanations"]
    call.assert_not_called()


def test_invalid_assessment_never_calls_provider():
    with patch("cropnova.ai.genai_explainer.call_openai") as call:
        result = generate_explanation(run_assessment({"state": ""}), requested=True)
    assert result["status"] == "skipped"
    call.assert_not_called()


@pytest.mark.parametrize(
    "change",
    [
        "assessment_status",
        "crop_status",
        "unknown_crop",
        "duplicate",
        "missing_crop",
        "invented_fact",
        "missing_fact",
        "extra_field",
        "empty_text",
        "long_text",
    ],
)
def test_invalid_model_answers_are_rejected(change):
    context = prepare_context(assessment())
    answer = valid_answer(context)
    row = answer["explanations"][0]
    if change == "assessment_status":
        answer["assessment_status"] = "NO_FEASIBLE_OPTION"
    if change == "crop_status":
        row["status"] = "rejected"
    if change == "unknown_crop":
        row["crop_id"] = "banana"
    if change == "duplicate":
        answer["explanations"].append(deepcopy(row))
    if change == "missing_crop":
        answer["explanations"] = []
    if change == "invented_fact":
        row["fact_ids"] = ["MADE_UP"]
    if change == "missing_fact":
        row["fact_ids"] = []
    if change == "extra_field":
        row["new_recommendation"] = "banana"
    if change == "empty_text":
        row["text"] = " "
    if change == "long_text":
        row["text"] = "x" * 8001
    with pytest.raises(ValueError):
        validate_answer(answer, context)


@pytest.mark.parametrize(
    "error",
    [
        URLError("private details"),
        TimeoutError("private details"),
        HTTPError("https://api.openai.com", 401, "secret", {}, None),
        HTTPError("https://api.openai.com", 429, "secret", {}, None),
        ValueError("bad response"),
    ],
)
def test_provider_errors_preserve_fallback_and_hide_private_details(error):
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-only"}), patch(
        "cropnova.ai.genai_explainer.call_openai", side_effect=error
    ):
        result = generate_explanation(assessment(), requested=True)
    assert result["status"] == "unavailable"
    assert "private details" not in json.dumps(result)
    assert "secret" not in json.dumps(result)


def test_context_excludes_user_location_and_marks_synthetic_data():
    report = run_assessment(
        {**BASE, "district": "private-town"}, knowledge_override=demo_knowledge()
    )
    context = prepare_context(report)
    assert "private-town" not in json.dumps(context)
    assert context["dataset_kind"] == "synthetic"


def test_generated_html_is_escaped():
    result = {
        "status": "generated",
        "message": "Generated",
        "explanations": [{"crop_id": "wheat", "text": "<script>alert(1)</script>", "fact_ids": []}],
    }
    html = genai_panel({"generative_ai": result})
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_website_missing_key_still_displays_original_result():
    with patch.dict("os.environ", {}, clear=True):
        status, html = request(
            "POST", "/assess", {**PRESETS["reference-wheat"][1], "use_genai": "yes"}
        )
    assert status == "200 OK"
    assert "Your assessment explained" in html
    assert "optional written explanation is unavailable" in html
    assert "Options that match your conditions" in html


def test_website_and_export_include_generated_explanation():
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-only"}), patch(
        "cropnova.ai.genai_explainer.call_openai", side_effect=lambda c, k, m: valid_answer(c)
    ):
        profile = {**PRESETS["reference-wheat"][1], "use_genai": "yes"}
        _, html = request("POST", "/assess", profile)
        _, raw = request("POST", "/report", profile)
    assert "This crop matches the recorded screening checks." in html
    assert json.loads(raw)["generative_ai"]["status"] == "generated"
    assert "test-only" not in html + raw


def test_http_request_uses_schema_timeout_and_no_response_storage():
    context = prepare_context(assessment())
    answer = valid_answer(context)
    response = {
        "status": "completed",
        "output": [
            {"type": "message", "content": [{"type": "output_text", "text": json.dumps(answer)}]}
        ],
    }
    with patch(
        "cropnova.ai.genai_explainer.urlopen", return_value=BytesIO(json.dumps(response).encode())
    ) as opened:
        assert call_openai(context, "test-only", "gpt-4o-mini") == answer
    args, kwargs = opened.call_args
    payload = json.loads(args[0].data)
    assert payload["store"] is False
    assert payload["text"]["format"]["strict"] is True
    assert kwargs["timeout"] == 20


@pytest.mark.parametrize(
    "response",
    [
        {"status": "incomplete", "output": []},
        {"status": "completed", "output": []},
        {
            "status": "completed",
            "output": [
                {"type": "message", "content": [{"type": "refusal", "refusal": "declined"}]}
            ],
        },
    ],
)
def test_incomplete_refused_or_empty_responses_are_rejected(response):
    with patch(
        "cropnova.ai.genai_explainer.urlopen", return_value=BytesIO(json.dumps(response).encode())
    ):
        with pytest.raises(ValueError):
            call_openai(prepare_context(assessment()), "test-only", "gpt-4o-mini")


def test_exhausted_credit_message_is_distinct_from_temporary_rate_limit():
    body = BytesIO(
        json.dumps(
            {"error": {"code": "credit_balance_exhausted", "message": "private provider details"}}
        ).encode()
    )
    error = HTTPError("https://api.openai.com", 429, "quota", {}, body)
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-only"}), patch(
        "cropnova.ai.genai_explainer.call_openai", side_effect=error
    ):
        result = generate_explanation(assessment(), requested=True)
    assert "no available API credits" in result["message"]
    assert "private provider details" not in json.dumps(result)
    assert result["status"] == "unavailable"
