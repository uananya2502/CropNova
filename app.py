"""CropNova's public website and download routes.

The assessment engine, page templates, private report storage and PDF renderer
live in separate small modules. Run `python app.py` to start the local website.
"""

import json
import math
import os
from pathlib import Path
from socketserver import ThreadingMixIn
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server, WSGIServer

from cropnova.core.agent import run_assessment
from cropnova.ai.genai_explainer import generate_explanation
from cropnova.config.public_profiles import REFERENCE_PROFILES
from cropnova.web.form_choices import submitted_crops, public_options
from cropnova.reports.report_store import save_report, load_report
from cropnova.web.web_views import (
    message_page,
    genai_panel as genai_panel,
)  # Public compatibility export.
from cropnova.web.public_pages import (
    home_page,
    assessment_page,
    how_it_works_page,
    sources_page,
    privacy_page,
)
from cropnova.web.assessment_pages import saved_page

ROOT = Path(__file__).resolve().parent
STATIC_FILES = {
    "/static/field-morning.webp": ("field-morning.webp", "image/webp"),
    "/static/botanical-paper.webp": ("botanical-paper.webp", "image/webp"),
    "/static/harvest-banner.webp": ("harvest-banner.webp", "image/webp"),
    "/static/design.css": ("design.css", "text/css; charset=utf-8"),
    "/static/style.css": ("style.css", "text/css; charset=utf-8"),
    "/static/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/static/fields.svg": ("fields.svg", "image/svg+xml"),
    "/static/icon.svg": ("icon.svg", "image/svg+xml"),
}


class ThreadedWSGIServer(ThreadingMixIn, WSGIServer):
    """An AI request or spare browser connection must not block other pages."""

    daemon_threads = True

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(10)
        return connection, address


def create_server(host="127.0.0.1", port=8000):
    return make_server(host, port, application, server_class=ThreadedWSGIServer)


def respond(
    start_response, body, status="200 OK", content_type="text/html; charset=utf-8", extra=()
):
    headers = [
        ("Content-Type", content_type),
        ("Content-Length", str(len(body))),
        ("X-Content-Type-Options", "nosniff"),
        ("Referrer-Policy", "no-referrer"),
        ("Cache-Control", "no-store"),
        ("X-Frame-Options", "DENY"),
        (
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; base-uri 'none'; form-action 'self'; frame-ancestors 'none'",
        ),
    ]
    headers.extend(extra)
    start_response(status, headers)
    return [body]


def assess(values):
    """Public requests always use published knowledge, never classroom fixtures."""
    values = {**values, "mode": "real"}
    report = run_assessment(values)
    report["mode"] = "real"
    profile = report.setdefault("profile", {})
    profile["mode"] = "real"
    profile["use_genai"] = "yes" if values.get("use_genai") == "yes" else "no"
    for group, field in [("soil", "ph"), ("water", "budget_mm"), ("rainfall", "mm")]:
        measurement = profile.get(group, {}).get(field)
        if isinstance(measurement, float) and not math.isfinite(measurement):
            profile[group][field] = None
    report["generative_ai"] = generate_explanation(
        report, requested=values.get("use_genai") == "yes"
    )
    return report


class BodyTooLarge(ValueError):
    """A separate exception lets the route return HTTP 413, not a server error."""


def read_body(environ, limit=100_000):
    """Bound the body, require its declared size and decode strict UTF-8."""
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
    except (ValueError, TypeError):
        raise ValueError("Invalid submission size.") from None
    if length < 0:
        raise ValueError("Invalid submission size.")
    if length > limit:
        raise BodyTooLarge("Submission exceeds the size limit.")
    body = environ["wsgi.input"].read(length)
    if len(body) != length:
        raise ValueError("The submission was incomplete. Please try again.")
    return body.decode("utf-8")


def answer_request(environ, start_response, path):
    """Read a question only after checking its private report link."""
    from cropnova.ai.assessment_questions import cached_answer

    def question_response(value, status="200 OK"):
        return respond(
            start_response,
            json.dumps(value, ensure_ascii=False).encode(),
            status=status,
            content_type="application/json; charset=utf-8",
        )

    token = path[len("/assessment/") : -len("/ask")]
    report = load_report(token)
    if not report:
        return question_response(
            {"answer": "This report link has expired. Run a new assessment.", "evidence": []},
            "404 Not Found",
        )
    try:
        values = json.loads(read_body(environ, limit=5000))
        if not isinstance(values, dict):
            raise ValueError("Please submit a question.")
        result = cached_answer(token, report, values.get("question"), values.get("crop_id", ""))
    except BodyTooLarge:
        return question_response(
            {"answer": "Please submit a shorter question.", "evidence": []}, "413 Payload Too Large"
        )
    except (ValueError, UnicodeDecodeError) as error:
        # Parser error text can echo submitted data; show only a friendly message.
        message = (
            "Please submit a valid question."
            if isinstance(error, (json.JSONDecodeError, UnicodeDecodeError))
            else str(error)
        )
        return question_response({"answer": message, "evidence": []}, "400 Bad Request")
    return question_response(
        result, "429 Too Many Requests" if result.get("status") == "busy" else "200 OK"
    )


def assessment_request(environ, start_response, path):
    """Validate form data, assess once, and save the exact result for reuse."""
    try:
        parsed = parse_qs(read_body(environ), keep_blank_values=True, max_num_fields=60)
    except BodyTooLarge:
        return respond(
            start_response,
            message_page("That submission is too large", "Please use a shorter farm profile."),
            status="413 Payload Too Large",
        )
    except (ValueError, UnicodeDecodeError):
        return respond(
            start_response,
            message_page(
                "Please check your submission",
                "Return to the form and enter your field details again.",
            ),
            status="400 Bad Request",
        )
    values = {key: items[-1] for key, items in parsed.items()}
    values["candidate_ids"] = submitted_crops(parsed.get("candidate_ids", []))
    report = assess(values)
    if path == "/report":
        # Retained as a machine-readable integration endpoint; the product
        # offers a personalised PDF rather than internal diagnostic output.
        body = json.dumps(report, ensure_ascii=False, allow_nan=False).encode("utf-8")
        return respond(start_response, body, content_type="application/json; charset=utf-8")
    if report["status"] == "INVALID_INPUT":
        return respond(
            start_response,
            assessment_page(values, errors=report.get("errors", [])),
            status="422 Unprocessable Entity",
        )
    if report["status"] == "SYSTEM_ERROR":
        return respond(
            start_response,
            message_page(
                "We could not finish this assessment",
                "Please try again shortly. Your field details have not been saved.",
            ),
            status="500 Internal Server Error",
        )
    from datetime import datetime
    from zoneinfo import ZoneInfo

    report["created_at"] = datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()
    token = save_report(report)
    # A redirect avoids resubmitting the form and calling the provider again
    # when the user refreshes the results page.
    return respond(
        start_response, b"", status="303 See Other", extra=[("Location", "/assessment/" + token)]
    )


def fertilizer_request(environ, start_response, path):
    """Calculate once, save a new snapshot, and redirect to avoid form resubmission."""
    from cropnova.web.assessment_summary import build_summary
    from cropnova.fertilizer.fertilizer_adviser import advise

    parts = path.strip("/").split("/")
    report = load_report(parts[1]) if len(parts) == 3 else None
    private_headers = [("X-Robots-Tag", "noindex, nofollow, noarchive")]
    if not report:
        return respond(
            start_response,
            message_page(
                "This assessment link has expired", "Start a new assessment to plan fertilizer."
            ),
            status="404 Not Found",
            extra=private_headers,
        )
    try:
        parsed = parse_qs(
            read_body(environ, limit=20000), keep_blank_values=True, max_num_fields=40
        )
        values = {key: items[-1] for key, items in parsed.items()}
    except BodyTooLarge:
        return respond(
            start_response,
            message_page("That submission is too large", "Use a shorter fertilizer plan."),
            status="413 Payload Too Large",
            extra=private_headers,
        )
    except (ValueError, UnicodeDecodeError):
        return respond(
            start_response,
            message_page(
                "Please check your submission", "Return to the fertilizer adviser and try again."
            ),
            status="400 Bad Request",
            extra=private_headers,
        )
    if set(values) <= {"crop"}:
        from cropnova.fertilizer.fertilizer_views import CROP_GUIDANCE

        if values.get("crop") not in CROP_GUIDANCE:
            body = saved_page(report, parts[1], "fertilizer", fertilizer_feedback={"values": values, "error": "Choose a crop from the list."})
            return respond(start_response, body, status="422 Unprocessable Entity", extra=private_headers)
        token = save_report({**report, "fertilizer_inputs": values, "fertilizer_plan": None})
        return respond(start_response, b"", status="303 See Other", extra=private_headers + [("Location", "/assessment/" + token + "/fertilizer#fertilizer-result")])
    try:
        result = advise(report.get("profile", {}), build_summary(report)["candidates"], values)
    except ValueError as error:
        body = saved_page(
            report,
            parts[1],
            "fertilizer",
            fertilizer_feedback={"values": values, "error": str(error)},
        )
        return respond(
            start_response, body, status="422 Unprocessable Entity", extra=private_headers
        )
    token = save_report({**report, "fertilizer_inputs": values, "fertilizer_plan": result})
    return respond(
        start_response,
        b"",
        status="303 See Other",
        extra=private_headers + [("Location", "/assessment/" + token + "/fertilizer")],
    )


def application(environ, start_response):
    method = environ.get("REQUEST_METHOD", "GET").upper()
    if method == "HEAD":
        # Preserve GET headers (including length) while omitting the response body.
        application({**environ, "REQUEST_METHOD": "GET"}, start_response)
        return [b""]
    path = environ.get("PATH_INFO", "/")
    if method == "POST" and path.startswith("/assessment/") and path.endswith("/fertilizer"):
        return fertilizer_request(environ, start_response, path)
    if method == "GET" and path in STATIC_FILES:
        filename, content_type = STATIC_FILES[path]
        return respond(
            start_response, (ROOT / "static" / filename).read_bytes(), content_type=content_type
        )
    if method == "GET" and path == "/robots.txt":
        return respond(
            start_response,
            b"User-agent: *\nDisallow: /assessment/\nDisallow: /reports/\nDisallow: /ready\n",
            content_type="text/plain; charset=utf-8",
        )
    if method == "GET" and path == "/form-options":
        return respond(
            start_response,
            json.dumps(public_options()).encode(),
            content_type="application/json; charset=utf-8",
        )
    if method == "GET" and path == "/health":
        return respond(start_response, b'{"status":"ok"}', content_type="application/json")
    if method == "GET" and path == "/ready":
        from cropnova.config.deployment_checks import readiness

        result = readiness()
        return respond(
            start_response,
            json.dumps(result).encode(),
            status="200 OK" if result["status"] == "ready" else "503 Service Unavailable",
            content_type="application/json",
        )
    if method == "GET" and path == "/":
        preset = parse_qs(environ.get("QUERY_STRING", "")).get("preset", [""])[0]
        if preset in REFERENCE_PROFILES:
            return respond(
                start_response,
                b"",
                status="302 Found",
                extra=[("Location", "/assess?preset=" + preset)],
            )
        return respond(start_response, home_page())
    if method == "GET" and path == "/assess":
        preset = parse_qs(environ.get("QUERY_STRING", "")).get("preset", [""])[0]
        return respond(start_response, assessment_page(REFERENCE_PROFILES.get(preset)))
    public_pages = {
        "/how-it-works": how_it_works_page,
        "/sources": sources_page,
        "/privacy": privacy_page,
    }
    if method == "GET" and path in public_pages:
        return respond(start_response, public_pages[path]())
    if method == "POST" and path == "/coverage-preview":
        from cropnova.web.coverage_preview import preview_coverage

        try:
            parsed = parse_qs(
                read_body(environ, limit=20_000), keep_blank_values=True, max_num_fields=60
            )
            values = {key: items[-1] for key, items in parsed.items()}
            values["candidate_ids"] = submitted_crops(parsed.get("candidate_ids", []))
            result = preview_coverage(values)
        except BodyTooLarge:
            return respond(
                start_response,
                b'{"title":"Submission is too large"}',
                status="413 Payload Too Large",
                content_type="application/json",
            )
        except (ValueError, UnicodeDecodeError):
            return respond(
                start_response,
                b'{"title":"Please check the selected values"}',
                status="400 Bad Request",
                content_type="application/json",
            )
        return respond(
            start_response,
            json.dumps(result, ensure_ascii=False, allow_nan=False).encode(),
            content_type="application/json; charset=utf-8",
        )
    if method == "POST" and path.startswith("/assessment/") and path.endswith("/ask"):
        return answer_request(environ, start_response, path)
    if method == "GET" and path.startswith("/assessment/"):
        parts = path.strip("/").split("/")
        view = parts[2] if len(parts) == 3 else "results"
        if len(parts) not in {2, 3} or view not in {
            "results",
            "report",
            "plan",
            "edit",
            "market",
            "fertilizer",
        }:
            return respond(
                start_response,
                message_page("We could not find that page", "Start a new assessment to continue."),
                status="404 Not Found",
            )
        token = parts[1]
        report = load_report(token)
        if report:
            market_selection = ""
            if view == "market":
                query = environ.get("QUERY_STRING", "")[:1024]
                market_selection = parse_qs(query).get("series", [""])[0]
            body = (
                assessment_page(report.get("profile"), editing=True)
                if view == "edit"
                else saved_page(report, token, view, market_selection)
            )
            return respond(
                start_response, body, extra=[("X-Robots-Tag", "noindex, nofollow, noarchive")]
            )
        return respond(
            start_response,
            message_page(
                "This report link has expired",
                "Saved assessments are available for one hour. Start a new assessment to see current findings.",
            ),
            status="404 Not Found",
        )
    if method == "GET" and path.startswith("/reports/") and path.endswith(".pdf"):
        token = path.removeprefix("/reports/")[:-4]
        report = load_report(token)
        if not report:
            return respond(
                start_response,
                message_page(
                    "This report is no longer available",
                    "Run a new assessment to create a fresh report.",
                ),
                status="404 Not Found",
            )
        from cropnova.reports.assessment_pdf import create_pdf

        pdf = create_pdf(report, reference=token)
        return respond(
            start_response,
            pdf,
            content_type="application/pdf",
            extra=[
                ("Content-Disposition", 'attachment; filename="CropNova-Farm-Assessment.pdf"'),
                ("X-Robots-Tag", "noindex, nofollow, noarchive"),
            ],
        )
    if method == "POST" and path in {"/assess", "/report"}:
        return assessment_request(environ, start_response, path)
    return respond(
        start_response,
        message_page(
            "We could not find that page", "Start a new field assessment from the home page."
        ),
        status="404 Not Found",
    )


def create_app():
    return application


if __name__ == "__main__":
    from cropnova.config.local_settings import load_local_settings

    load_local_settings()
    host = os.environ.get("HOST", "0.0.0.0" if "PORT" in os.environ else "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    print(f"CropNova is running at http://{host}:{port}")
    with create_server(host, port) as server:
        server.serve_forever()
