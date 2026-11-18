"""Navigation, private saved pages and deployment readiness for the multi-page app."""

from html.parser import HTMLParser
from io import BytesIO
import json
import re
from unittest.mock import patch
from urllib.parse import urlencode, urlsplit

import pytest
from app import application, assess
from report_store import save_report, load_report
from public_profiles import REFERENCE_PROFILES


@pytest.fixture(autouse=True)
def private_storage(tmp_path, monkeypatch):
    monkeypatch.setattr("report_store.DATABASE_PATH", tmp_path / "reports.sqlite3")


def request(path="/", method="GET", values=None):
    parsed = urlsplit(path)
    body = urlencode(values or {}, doseq=True).encode()
    result = {}

    def start(status, headers):
        result.update(status=status, headers=dict(headers))

    result["body"] = b"".join(
        application(
            {
                "REQUEST_METHOD": method,
                "PATH_INFO": parsed.path,
                "QUERY_STRING": parsed.query,
                "CONTENT_LENGTH": str(len(body)),
                "wsgi.input": BytesIO(body),
            },
            start,
        )
    )
    return result


def saved():
    response = request("/assess", "POST", REFERENCE_PROFILES["reference-wheat"])
    assert response["status"] == "303 See Other"
    base = response["headers"]["Location"]
    return base, load_report(base.rsplit("/", 1)[-1])


def test_landing_page_is_separate_from_form():
    html = request()["body"].decode()
    assert "data-assessment-form" not in html
    assert 'href="/assess"' in html
    form = request("/assess")["body"].decode()
    assert "data-assessment-form" in form
    assert "Find crops for my field" in form


@pytest.mark.parametrize("path", ["/", "/assess", "/how-it-works", "/sources", "/privacy"])
def test_public_page_has_shared_navigation_and_one_heading(path):
    response = request(path)
    assert response["status"] == "200 OK"
    html = response["body"].decode()
    assert html.count("<h1>") == 1
    assert 'aria-label="Main navigation"' in html
    for link in ["/assess", "/how-it-works", "/sources", "/privacy"]:
        assert f'href="{link}"' in html


def test_result_report_and_plan_are_distinct_pages_without_embedded_forms():
    base, report = saved()
    result = request(base)["body"].decode()
    written = request(base + "/report")["body"].decode()
    plan = request(base + "/plan")["body"].decode()
    assert "Best matches for your field" in result
    assert 'id="field-report"' not in result
    assert "Your personalised report" in written and 'id="field-report"' in written
    assert "A practical order for following up" in plan
    assert "data-assessment-form" not in result + written + plan
    assert f'href="{base}/report"' in result
    assert f'href="{base}/plan"' in result
    assert f'href="{base}/edit"' in written


def test_market_page_uses_saved_crop_and_keeps_private_access(tmp_path, monkeypatch):
    import csv
    from mandi_data import FIELDS

    monkeypatch.setenv("CROPNOVA_DATA_DIR", str(tmp_path))
    with (tmp_path / "mandi_prices.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(FIELDS)
        writer.writerow(("Haryana", "Karnal", "Karnal APMC", "Wheat", "Dara",
                         "FAQ", "2025-01-01", 2400))
        writer.writerow(("Punjab", "Ludhiana", "Ludhiana APMC", "Wheat", "Dara",
                         "FAQ", "2025-01-01", 2500))
    base, before = saved()
    assert f'href="{base}/market"' in request(base)["body"].decode()
    response = request(base + "/market?series=unknown")
    html = response["body"].decode()
    assert response["status"] == "200 OK"
    assert response["headers"]["X-Robots-Tag"].startswith("noindex")
    assert "Karnal APMC" in html and "Ludhiana APMC" not in html
    assert "₹2,400" in html and "Reported 01 January 2025" in html
    assert "Weekly price forecast" not in html and "Recent reported prices" not in html
    assert load_report(base.rsplit("/", 1)[-1]) == before
    assert request("/assessment/invalid/market")["status"] == "404 Not Found"


def test_edit_page_preserves_values_and_new_submission_preserves_old_result():
    base, before = saved()
    html = request(base + "/edit")["body"].decode()
    assert 'value="650.0"' in html and 'value="7.0"' in html
    second = request(
        "/assess", "POST", {**REFERENCE_PROFILES["reference-wheat"], "water_budget_mm": "300"}
    )
    assert second["headers"]["Location"] != base
    assert load_report(base.rsplit("/", 1)[-1]) == before


def test_page_navigation_and_download_do_not_call_provider_again():
    with patch(
        "app.generate_explanation", return_value={"status": "not_requested", "explanations": []}
    ) as provider:
        base, _ = saved()
        for suffix in ["", "/report", "/plan", "/edit"]:
            assert request(base + suffix)["status"] == "200 OK"
        assert request("/reports/" + base.rsplit("/", 1)[-1] + ".pdf")["status"] == "200 OK"
    assert provider.call_count == 1


@pytest.mark.parametrize("suffix", ["", "/report", "/plan", "/edit", "/unknown", "/report/extra"])
def test_expired_or_invalid_saved_page_is_not_available(suffix):
    assert request("/assessment/invalid" + suffix)["status"] == "404 Not Found"


@pytest.mark.parametrize(
    "path", ["/", "/assess", "/how-it-works", "/health", "/ready", "/static/style.css"]
)
def test_head_returns_get_headers_without_body(path):
    get = request(path)
    head = request(path, "HEAD")
    assert get["status"] == head["status"]
    assert head["body"] == b""
    assert head["headers"]["Content-Length"] == get["headers"]["Content-Length"]


def test_readiness_checks_database_and_knowledge_without_model_calls():
    with patch("app.generate_explanation") as provider:
        response = request("/ready")
    assert response["status"] == "200 OK" and json.loads(response["body"])["status"] == "ready"
    provider.assert_not_called()


def test_readiness_failure_is_unavailable_without_private_error_text():
    with patch("deployment_checks.connect", side_effect=RuntimeError("secret-path")):
        response = request("/ready")
    assert response["status"] == "503 Service Unavailable"
    assert b"secret-path" not in response["body"]


def test_invalid_form_stays_on_form_page_with_values():
    response = request(
        "/assess", "POST", {**REFERENCE_PROFILES["reference-wheat"], "soil_ph": "20"}
    )
    html = response["body"].decode()
    assert response["status"] == "422 Unprocessable Entity"
    assert "data-assessment-form" in html and 'value="20"' in html


def test_provider_limit_is_shared_and_does_not_queue_excess_calls(monkeypatch):
    import genai_explainer
    import assessment_questions

    assert genai_explainer.GENERATION_SLOTS is assessment_questions.GENERATION_SLOTS
    slots = genai_explainer.GENERATION_SLOTS
    slots.acquire()
    slots.acquire()
    try:
        monkeypatch.setenv("AI_PROVIDER", "gemini")
        monkeypatch.setenv("GEMINI_API_KEY", "fake")
        with patch("genai_explainer.call_gemini") as provider:
            result = genai_explainer.generate_explanation(
                assess(REFERENCE_PROFILES["reference-wheat"]), requested=True
            )
        assert result["status"] == "unavailable" and "busy" in result["message"]
        provider.assert_not_called()
    finally:
        slots.release()
        slots.release()


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href", "")
            if href.startswith("/"):
                self.links.append(href)


def test_rendered_internal_links_resolve_to_real_pages():
    base, _ = saved()
    pages = [
        "/",
        "/assess",
        "/how-it-works",
        "/sources",
        "/privacy",
        base,
        base + "/report",
        base + "/plan",
        base + "/edit",
    ]
    for path in pages:
        parsed = Links()
        parsed.feed(request(path)["body"].decode())
        for link in set(parsed.links):
            assert request(link)["status"].startswith(("200", "302")), (path, link)


def test_private_results_discourage_indexing_and_brand_icon_loads():
    base, _ = saved()
    for suffix in ["", "/report", "/plan", "/edit"]:
        response = request(base + suffix)
        assert response["headers"]["X-Robots-Tag"] == "noindex, nofollow, noarchive"
        assert b'name="robots" content="noindex,nofollow,noarchive"' in response["body"]
    assert request("/static/icon.svg")["status"] == "200 OK"
    assert b"Disallow: /assessment/" in request("/robots.txt")["body"]
    assert b'name="robots" content="noindex' not in request("/")["body"]
