"""The staged design retains native submission and separate saved-page purposes."""

from html.parser import HTMLParser
from pathlib import Path
import shutil
import re
import subprocess
import pytest
from tests.test_multipage import request
from cropnova.config.public_profiles import REFERENCE_PROFILES


class FormSections(HTMLParser):
    def __init__(self):
        super().__init__()
        self.sections = []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if "data-form-step" in attrs:
            self.sections.append(attrs)


def test_no_javascript_fallback_keeps_all_form_sections_available():
    html = request("/assess")["body"].decode()
    parsed = FormSections()
    parsed.feed(html)
    assert len(parsed.sections) == 3
    assert not any("hidden" in section for section in parsed.sections)
    assert "data-wizard-controls hidden" in html
    assert "form-intro" not in html


def test_guided_form_navigation_and_validation_behaviour():
    if not shutil.which("node"):
        pytest.skip("Node is needed only for the standalone JavaScript unit check.")
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        ["node", "scripts/check_form_wizard.cjs"],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "Wizard checks passed" in result.stdout


@pytest.mark.parametrize("view,suffix", [("results", ""), ("report", "/report"), ("plan", "/plan")])
def test_new_design_applies_to_each_saved_assessment_page(view, suffix, tmp_path, monkeypatch):
    monkeypatch.setattr("cropnova.reports.report_store.DATABASE_PATH", tmp_path / "reports.sqlite3")
    response = request("/assess", "POST", REFERENCE_PROFILES["reference-barley"])
    html = request(response["headers"]["Location"] + suffix)["body"].decode()
    assert "page-workflow page-" + view in html
    assert "workflow-header" in html and re.search(r"/static/design\.css\?v=\d+", html)
    assert "data-assessment-form" not in html
    if view == "report":
        assert "report-crop-heading" in html
    if view == "plan":
        assert "farm-step-grid" in html
    if view == "results":
        assert 'data-leading-crop="barley"' in html
