"""All visible field inputs are menus, with source-scoped examples and live checks."""

from html.parser import HTMLParser
from io import BytesIO
import json
from unittest.mock import patch
from urllib.parse import urlencode

import pytest
from app import application
from cropnova.web.assessment_form import render_form
from cropnova.web.form_choices import DISTRICTS, STATES, numeric_choices, submitted_crops
from cropnova.config.public_profiles import REFERENCE_PROFILES


@pytest.fixture(autouse=True)
def private_storage(tmp_path, monkeypatch):
    monkeypatch.setattr("cropnova.reports.report_store.DATABASE_PATH", tmp_path / "reports.sqlite3")


def response(path, values=None, query=""):
    body = urlencode(values or {}, doseq=True).encode()
    result = {}

    def start(status, headers):
        result.update(status=status, headers=dict(headers))

    result["body"] = b"".join(
        application(
            {
                "REQUEST_METHOD": "POST" if values is not None else "GET",
                "PATH_INFO": path,
                "QUERY_STRING": query,
                "CONTENT_LENGTH": str(len(body)),
                "wsgi.input": BytesIO(body),
            },
            start,
        )
    )
    return result


class FieldParser(HTMLParser):
    """Read native form defaults just as a no-JavaScript submission would."""

    def __init__(self):
        super().__init__()
        self.active = False
        self.name = None
        self.values = {}
        self.selects = []
        self.visible_inputs = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form":
            self.active = "data-assessment-form" in attrs
        if not self.active:
            return
        if tag == "select":
            self.name = attrs["name"]
            self.selects.append(self.name)
        if tag == "option" and self.name:
            if self.name not in self.values or "selected" in attrs:
                self.values[self.name] = attrs.get("value", "")
        if tag == "input":
            if attrs.get("type") == "hidden":
                self.values[attrs["name"]] = attrs.get("value", "")
            else:
                self.visible_inputs.append(attrs)

    def handle_endtag(self, tag):
        if tag == "select":
            self.name = None
        if tag == "form":
            self.active = False


def test_field_menus_and_illustrated_rain_options_render_together():
    parser = FieldParser()
    parser.feed(response("/assess")["body"].decode())
    assert set(parser.selects) == {
        "state",
        "district",
        "season",
        "soil_texture",
        "soil_ph",
        "soil_drainage",
        "water_budget_mm",
        "water_basis",
        "candidate_ids",
        "use_genai",
        "language",
        "multilingual_view",
        "irrigation",
    }
    assert [i["type"] for i in parser.visible_inputs] == ["radio"] * 4 + ["number"]
    assert parser.values["soil_ph"] == "" and parser.values["water_budget_mm"] == ""
    assert parser.values["candidate_ids"] == ""


@pytest.mark.parametrize("preset", list(REFERENCE_PROFILES))
def test_loaded_profile_can_be_submitted_from_menus_and_matches_all_checks(preset):
    page = response("/assess", query="preset=" + preset)
    parser = FieldParser()
    parser.feed(page["body"].decode())
    with patch("app.generate_explanation") as provider, patch(
        "cropnova.reports.report_store.save_report"
    ) as store:
        preview = response("/coverage-preview", parser.values)
    data = json.loads(preview["body"])
    assert data["state"] == "ready"
    assert len(data["crops"]) == 1 and data["crops"][0]["matched"] == 4
    provider.assert_not_called()
    store.assert_not_called()
    result = response("/report", parser.values)
    assert json.loads(result["body"])["status"] == "FEASIBLE_OPTIONS_FOUND"


def test_punjab_wheat_now_has_sourced_season_coverage():
    result = response(
        "/coverage-preview",
        {**REFERENCE_PROFILES["reference-wheat"], "state": "Punjab", "district": "Ludhiana"},
    )
    data = json.loads(result["body"])
    assert data["state"] == "ready"
    season = next(
        check for check in data["crops"][0]["checks"] if check["name"] == "Growing season"
    )
    assert season["status"] == "satisfied"


def test_missing_water_preview_identifies_water_and_not_a_random_general_error():
    data = json.loads(
        response(
            "/coverage-preview", {**REFERENCE_PROFILES["reference-wheat"], "water_budget_mm": ""}
        )["body"]
    )
    check = next(check for check in data["crops"][0]["checks"] if check["name"] == "Water supply")
    assert check["status"] == "unknown" and "not provided" in check["reason"]
    assert data["crops"][0]["matched"] == 3


def test_preview_does_not_request_generation_even_when_ai_menu_is_yes():
    with patch("cropnova.ai.genai_explainer.call_gemini") as google, patch(
        "cropnova.ai.genai_explainer.call_openai"
    ) as paid, patch("app.save_report") as save:
        result = response(
            "/coverage-preview", {**REFERENCE_PROFILES["reference-wheat"], "use_genai": "yes"}
        )
    assert json.loads(result["body"])["state"] == "ready"
    google.assert_not_called()
    paid.assert_not_called()
    save.assert_not_called()


@pytest.mark.parametrize(
    "kind,value",
    [("ph", 6.55), ("water", 681.25), ("ph", 7.0), ("water", 650.0), ("ph", 20), ("water", 0)],
)
def test_dropdown_preserves_exact_saved_or_invalid_values(kind, value):
    choices = numeric_choices(value, kind=kind)
    assert str(value) in [key for key, _ in choices]
    assert len([key for key, _ in choices if key == str(value)]) == 1


def test_unknown_and_zero_are_not_conflated():
    assert numeric_choices("", kind="water")[0][0] == ""
    parser = FieldParser()
    parser.feed(render_form({**REFERENCE_PROFILES["reference-wheat"], "water_budget_mm": "0"}))
    assert parser.values["water_budget_mm"] == "0"


def test_current_multi_crop_choice_can_be_edited_without_losing_selection():
    parser = FieldParser()
    parser.feed(
        render_form({**REFERENCE_PROFILES["reference-wheat"], "candidate_ids": ["wheat", "rice"]})
    )
    assert parser.values["candidate_ids"] == "wheat,rice"
    result = json.loads(response("/report", parser.values)["body"])
    assert result["profile"]["candidate_ids"] == ["wheat", "rice"]


def test_all_crops_is_explicit_and_legacy_checkbox_payloads_still_work():
    assert submitted_crops(["__all__"]) == []
    assert submitted_crops(["wheat", "rice"]) == ["wheat", "rice"]
    assert submitted_crops(["wheat,rice"]) == ["wheat", "rice"]
    result = json.loads(
        response("/report", {**REFERENCE_PROFILES["reference-wheat"], "candidate_ids": "__all__"})[
            "body"
        ]
    )
    assert result["csp_result"]["diagnostics"]["assignments_examined"] == 10


def test_district_catalogue_does_not_claim_crop_coverage_and_has_hansi():
    result = json.loads(response("/form-options")["body"])
    assert len(STATES) == 36
    assert len(DISTRICTS["Haryana"]) == 23 and "Hansi" in DISTRICTS["Haryana"]
    assert len(DISTRICTS["Rajasthan"]) == 41 and len(DISTRICTS["Punjab"]) == 23
    assert "does not add crop-specific evidence" in result["district_note"]


def test_lowercase_saved_locations_get_canonical_menu_selection():
    parser = FieldParser()
    parser.feed(
        render_form(
            {**REFERENCE_PROFILES["reference-wheat"], "state": "punjab", "district": "ludhiana"}
        )
    )
    assert parser.values["state"] == "Punjab" and parser.values["district"] == "Ludhiana"


def test_saved_unlisted_location_is_preserved_and_escaped():
    html = render_form(
        {**REFERENCE_PROFILES["reference-wheat"], "district": "<script>bad</script>"}
    )
    assert "<script>bad</script>" not in html
    assert "&lt;script&gt;bad&lt;/script&gt;" in html


def test_preview_invalid_inputs_return_friendly_data():
    data = json.loads(
        response("/coverage-preview", {**REFERENCE_PROFILES["reference-wheat"], "soil_ph": "20"})[
            "body"
        ]
    )
    assert data["state"] == "invalid" and data["messages"] and data["crops"] == []


def test_form_shows_scope_and_all_ten_loadable_examples():
    html = response("/assess")["body"].decode()
    assert "Complete worked reference examples" in html
    for preset in REFERENCE_PROFILES:
        assert "/assess?preset=" + preset in html
    assert "Punjab guidance now covers" in html
