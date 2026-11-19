"""Rain observations, grounded multilingual explanations and saved-page continuity."""

from copy import deepcopy
from unittest.mock import patch
import json
import math
import pytest
from app import assess
from cropnova.core.agent import run_assessment
from cropnova.config.public_profiles import REFERENCE_PROFILES
from cropnova.ai.genai_explainer import (
    prepare_context,
    response_schema,
    validate_answer,
    generate_explanation,
)
from cropnova.web.farmer_explanations import farmer_explanation_panel
from cropnova.web.assessment_summary import build_summary
from knowledge_base.loader import load_knowledge
from knowledge_base.retrieval import get_usable_facts
from tests.test_multipage import request


def report(**updates):
    return assess({**REFERENCE_PROFILES["reference-wheat"], **updates})


def multilingual_answer(context):
    text = {
        "en": "Wheat matches the entered pH 7 and the 650 mm water reference. Confirm local water timing.",
        "hi": "गेहूँ के लिए आपके खेत का pH 7 और पानी 650 मिमी संदर्भ से मेल खाते हैं। पानी का समय स्थानीय सलाहकार से पक्का करें।",
        "pa": "ਕਣਕ ਲਈ ਤੁਹਾਡੇ ਖੇਤ ਦਾ pH 7 ਅਤੇ ਪਾਣੀ 650 ਮਿ.ਮੀ. ਹਵਾਲੇ ਨਾਲ ਮੇਲ ਖਾਂਦੇ ਹਨ। ਪਾਣੀ ਦਾ ਸਮਾਂ ਸਥਾਨਕ ਸਲਾਹਕਾਰ ਤੋਂ ਪੱਕਾ ਕਰੋ।",
    }
    return {
        "assessment_status": context["assessment_status"],
        "explanations": [
            {
                "crop_id": crop["crop_id"],
                "status": crop["status"],
                "text": text[context["selected_language"]],
                "fact_ids": list(
                    dict.fromkeys(fid for check in crop["checks"] for fid in check["fact_ids"])
                ),
                "translations": [
                    {
                        "language": lang,
                        "text": text[lang],
                        "precaution": {
                            "en": "Confirm local water timing before sowing.",
                            "hi": "बुवाई से पहले पानी का समय पक्का करें।",
                            "pa": "ਬਿਜਾਈ ਤੋਂ ਪਹਿਲਾਂ ਪਾਣੀ ਦਾ ਸਮਾਂ ਪੱਕਾ ਕਰੋ।",
                        }[lang],
                    }
                    for lang in context["requested_languages"]
                ],
            }
            for crop in context["candidates"]
        ],
    }


@pytest.mark.parametrize("level", ["none", "low", "medium", "high"])
def test_rain_choice_is_observation_and_never_guessed_water(level):
    result = report(rainfall_level=level, water_budget_mm="")
    assert result["profile"]["rainfall"]["level"] == level
    assert result["profile"]["water"]["budget_mm"] is None
    assert not result["feasible_options"]
    assert any(
        c["reason_code"] == "MISSING_USER_INPUT"
        for c in result["unknown_options"][0]["unknown_constraints"]
    )


def test_exact_rainfall_is_kept_separate_from_seasonal_water_and_used_in_context():
    result = report(rainfall_level="medium", rainfall_mm="350.5")
    context = prepare_context(result)
    assert context["reported_rainfall"] == {"level": "medium", "mm": 350.5}
    assert result["profile"]["water"]["budget_mm"] == 650
    assert context["field_conditions"]["Measured seasonal rainfall"] == "350.5 mm"


@pytest.mark.parametrize("value", ["nan", "inf", "-5", "10001", "not a number", True])
def test_invalid_exact_rainfall_is_rejected(value):
    assert report(rainfall_mm=value)["status"] == "INVALID_INPUT"


def test_new_optional_preferences_survive_edit_and_do_not_change_decisions(tmp_path, monkeypatch):
    monkeypatch.setattr("cropnova.reports.report_store.DATABASE_PATH", tmp_path / "report.sqlite3")
    values = {
        **REFERENCE_PROFILES["reference-wheat"],
        "language": "pa",
        "multilingual_view": "yes",
        "rainfall_level": "low",
        "rainfall_mm": "120.5",
        "irrigation": "available",
    }
    saved = request("/assess", "POST", values)
    base = saved["headers"]["Location"]
    html = request(base + "/edit")["body"].decode()
    assert 'value="pa" selected' in html and 'value="low" checked' in html
    assert 'value="120.5"' in html and 'value="available" selected' in html
    assert 'value="yes" selected' in html
    assert assess(values)["csp_result"] == report()["csp_result"]


@pytest.mark.parametrize(
    "language,side", [("hi", "no"), ("pa", "no"), ("hi", "yes"), ("en", "yes")]
)
def test_model_schema_and_validation_preserve_each_requested_language(language, side):
    context = prepare_context(report(language=language, multilingual_view=side))
    schema = response_schema(context)
    assert "translations" in schema["properties"]["explanations"]["items"]["required"]
    answer = multilingual_answer(context)
    assert validate_answer(answer, context) == answer["explanations"]


@pytest.mark.parametrize(
    "fault",
    [
        "missing",
        "duplicate",
        "unsupported",
        "wrong_script",
        "new_number",
        "percentage",
        "status_changed",
        "invented_source",
        "missing_precaution",
        "wrong_evidence_label",
    ],
)
def test_multilingual_answers_reject_changed_evidence_and_language_structure(fault):
    context = prepare_context(report(language="hi", multilingual_view="yes"))
    answer = multilingual_answer(context)
    row = answer["explanations"][0]
    if fault == "missing":
        row["translations"].pop()
    if fault == "duplicate":
        row["translations"][1] = deepcopy(row["translations"][0])
    if fault == "unsupported":
        row["translations"][0]["language"] = "fr"
    if fault == "wrong_script":
        row["translations"][2]["text"] = "Only English words."
    if fault == "primary_changed":
        row["text"] = "A different sentence."
    if fault == "new_number":
        row["translations"][0]["text"] = "Use 9999 mm of water."
    if fault == "percentage":
        row["translations"][0]["text"] = "Success is 100% certain."
    if fault == "status_changed":
        row["status"] = "rejected"
    if fault == "invented_source":
        row["fact_ids"] = ["NOT_A_SOURCE"]
    if fault == "missing_precaution":
        row["translations"][0]["precaution"] = ""
    if fault == "wrong_evidence_label":
        row["translations"][0]["text"] = "This is synthetic data."
    with pytest.raises(ValueError):
        validate_answer(answer, context)


def test_multilingual_provider_is_called_once_and_receives_actual_factors():
    original = report(language="pa", multilingual_view="yes")
    with patch.dict("os.environ", {"AI_PROVIDER": "gemini", "GEMINI_API_KEY": "test-only"}), patch(
        "cropnova.ai.genai_explainer.call_gemini",
        side_effect=lambda c, *args: multilingual_answer(c),
    ) as provider:
        result = generate_explanation(original, requested=True)
    assert provider.call_count == 1 and result["status"] == "generated"
    context = provider.call_args.args[0]
    assert context["field_conditions"]["Water budget"] == "650 mm"
    assert "District / town" not in context["field_conditions"]
    assert all(not f.get("historical_reference") for f in context["facts"])


def test_native_fallback_explains_exact_values_without_an_api():
    original = report(language="pa", multilingual_view="yes")
    with patch("cropnova.ai.genai_explainer.call_gemini") as provider:
        html = farmer_explanation_panel(original, build_summary(original))
    assert all('lang="' + language + '"' in html for language in ["en", "hi", "pa"])
    assert "650" in html and "ਕਣਕ" in html and "गेहूँ" in html
    provider.assert_not_called()


def test_historical_528_entries_never_enter_active_evidence_or_decisions():
    knowledge = load_knowledge()
    historical = [f for f in knowledge["facts"] if f.get("historical_reference")]
    assert len(historical) == 528 and len(knowledge["facts"]) >= 500
    assert all(
        f["constraint_eligible"] is False and f["verification_status"] == "needs_review"
        for f in historical
    )
    assert not any(f.get("historical_reference") for f in get_usable_facts(knowledge))
    assert all(not f.get("historical_reference") for f in report()["evidence_package"]["facts"])


def test_incomplete_water_can_produce_review_shortlist_but_never_full_match():
    from cropnova.web.crop_results import crop_findings

    result = report(water_budget_mm="")
    html = crop_findings(build_summary(result)["candidates"])
    assert "Worth checking first" in html and "Not yet a complete match" in html
    assert "data-leading-crop=" not in html


def test_weather_cards_are_four_native_choices_with_optional_exact_input():
    html = request("/assess")["body"].decode()
    assert html.count('name="rainfall_level"') == 4
    assert all(label in html for label in ["No Rain", "Low Rain", "Medium Rain", "High Rain"])
    assert 'name="rainfall_mm"' in html and 'step="0.1"' in html
    assert 'name="language"' in html and 'name="multilingual_view"' in html


def test_invalid_rainfall_returns_json_without_a_serialization_error():
    from tests.test_dropdown_form import response

    result = response("/report", {**REFERENCE_PROFILES["reference-wheat"], "rainfall_mm": "nan"})
    body = json.loads(result["body"])
    assert body["status"] == "INVALID_INPUT" and body["profile"]["rainfall"]["mm"] is None


def test_selected_language_and_multilingual_columns_appear_before_other_crops(
    tmp_path, monkeypatch
):
    monkeypatch.setattr("cropnova.reports.report_store.DATABASE_PATH", tmp_path / "reports.sqlite3")
    result = request(
        "/assess",
        "POST",
        {
            **REFERENCE_PROFILES["reference-barley"],
            "candidate_ids": "__all__",
            "language": "hi",
            "multilingual_view": "yes",
        },
    )
    html = request(result["headers"]["Location"])["body"].decode()
    assert all('lang="' + language + '"' in html for language in ["en", "hi", "pa"])
    assert html.index('lang="hi"') < html.index("Other crop options")


def test_longer_native_language_response_budget_is_bounded():
    from cropnova.ai.gemini_provider import output_token_limit

    assert output_token_limit({"candidates": [{}]}) == 3500
    assert (
        output_token_limit({"candidates": [{}], "requested_languages": ["en", "hi", "pa"]}) >= 6000
    )
    assert (
        output_token_limit({"candidates": [{}] * 10, "requested_languages": ["en", "hi", "pa"]})
        <= 22000
    )


def test_selected_native_translation_becomes_primary_even_if_provider_repeats_english():
    context = prepare_context(report(language="pa", multilingual_view="yes"))
    answer = multilingual_answer(context)
    answer["explanations"][0]["text"] = "Legacy English duplicate."
    checked = validate_answer(answer, context)
    punjabi = next(
        t["text"] for t in answer["explanations"][0]["translations"] if t["language"] == "pa"
    )
    assert checked[0]["text"] == punjabi
    assert answer["explanations"][0]["text"] == "Legacy English duplicate."
