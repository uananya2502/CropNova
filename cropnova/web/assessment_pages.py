"""Saved-assessment screens share navigation but have separate URLs and purposes."""

from html import escape
from datetime import datetime
from cropnova.web.assessment_summary import build_summary, readable
from cropnova.web.farmer_language import language_settings, native_value
from cropnova.web.farmer_narrative import LABELS, field_label
from cropnova.web.assessment_report_content import LIMITS
from cropnova.market.mandi_page import TITLE as MARKET_TITLE, market_panel
from cropnova.fertilizer.fertilizer_views import TITLES as FERTILIZER_TITLES, fertilizer_panel
from cropnova.web.web_views import (
    page,
    inline_report,
    next_steps_panel,
    assessment_question_panel,
    safe_url,
    genai_panel,
)


def assessment_navigation(token, current, language="en"):
    base = "/assessment/" + token
    tabs = [
        ("results", base, "Crop findings"),
        ("report", base + "/report", "Your report"),
        ("plan", base + "/plan", "Next steps"),
        ("market", base + "/market", MARKET_TITLE[language]),
        ("fertilizer", base + "/fertilizer", FERTILIZER_TITLES[language]),
    ]
    translated = {
        "hi": {"results": "फसल के नतीजे", "report": "आपकी रिपोर्ट", "plan": "अगले कदम"},
        "pa": {"results": "ਫ਼ਸਲਾਂ ਦੇ ਨਤੀਜੇ", "report": "ਤੁਹਾਡੀ ਰਿਪੋਰਟ", "plan": "ਅਗਲੇ ਕਦਮ"},
    }
    links = []
    for key, url, label in tabs:
        label = translated.get(language, {}).get(key, label)
        selected = ' aria-current="page"' if key == current else ""
        links.append(f'<a href="{url}"{selected}>{label}</a>')
    links = "".join(links)
    return f'<nav class="assessment-tabs container" aria-label="Your assessment">{links}<a class="edit-tab" href="{base}/edit">{LABELS[language]["edit"]} ↗</a></nav>'


def source_section(summary):
    language = summary.get("language", "en")
    links = "".join(
        f'<li><a href="{safe_url(source.get("url"))}" target="_blank" rel="noopener noreferrer">{escape(source.get("title","Published source"))} ↗</a><span>{escape(source.get("organization") or source.get("publisher") or "")}</span></li>'
        for source in summary["sources"]
    )
    return f'<section class="panel sources-panel" id="assessment-sources"><span class="eyebrow">Follow the evidence</span><h2>{LABELS[language]["sources"]}</h2><ul>{links or "<li>No applicable source was available for these checks.</li>"}</ul></section>'


def open_questions(summary, token):
    if not summary["questions"]:
        return ""
    questions = "".join(f"<li>{escape(question)}</li>" for question in summary["questions"])
    return f'<section class="panel open-questions"><span class="eyebrow">Still to confirm</span><h2>A few details would help</h2><ul>{questions}</ul><a class="text-link" href="/assessment/{token}/edit">Update your field details →</a></section>'


def field_sidebar(summary, token, current="results"):
    language = summary.get("language", "en")
    fields = "".join(
        f"<div><dt>{escape(field_label(label,language))}</dt><dd>{escape(native_value(value,language))}</dd></div>"
        for label, value in summary["profile"]
        if label != "District / town" or value != "Not provided"
    )
    return f'<aside class="result-sidebar"><details class="field-overview"><summary><span><strong>{escape(summary["location"])}</strong><small>{LABELS[language]["input_record"]}</small></span><span class="overview-action">{LABELS[language]["input_record"]} <span aria-hidden="true">⌄</span></span></summary><div class="overview-content"><dl class="profile-summary">{fields}</dl><a class="text-link" href="/assessment/{token}/edit">{LABELS[language]["edit"]} →</a></div></details></aside>'


def saved_page(report, token, view="results", market_selection="", *, fertilizer_feedback=None):
    summary = build_summary(report)
    language, _ = language_settings(report.get("profile", {}))
    text = LABELS[language]
    base = "/assessment/" + token
    date = datetime.fromisoformat(summary["created"]).strftime("%d %B %Y")
    title = {
        "results": summary["title"],
        "report": text["report"],
        "plan": text["plan"],
        "market": MARKET_TITLE[language],
        "fertilizer": FERTILIZER_TITLES[language],
    }[view]
    subtitle = {
        "results": "See what matches, what needs attention and which comparisons remain open.",
        "report": "Your field details and findings, explained in one place.",
        "plan": text["plan_intro"],
        "market": "See reported wholesale prices and any available weekly estimate for your assessed crops.",
        "fertilizer": "Plan crop nutrients and see why each fertilizer is included.",
    }[view]
    top = f'<header class="result-heading workflow-header container"><a class="back-link" href="/assess">← {text["new"]}</a><div class="result-title-row"><div><span class="eyebrow">Your field assessment · {escape(date)}</span><h1>{escape(title)}</h1><p>{escape(summary["location"])} · {escape(readable(report.get("profile",{}).get("season")))}</p><p class="result-subtitle">{subtitle}</p></div>'
    top += (
        f'<a class="button" href="{base}/report">{text["report_link"]} →</a>'
        if view == "results"
        else f'<a class="button" href="{base}">{text["view"]} →</a>'
    )
    top += "</div></header>" + assessment_navigation(token, view, language)
    if view == "results":
        counts = f'<div class="result-counts"><div><strong>{summary["matches"]}</strong><span>Match checked conditions</span></div><div><strong>{summary["reviews"]}</strong><span>Need more information</span></div><div><strong>{summary["attention"]}</strong><span>Need attention</span></div></div>'
        from cropnova.web.crop_results import crop_findings
        from cropnova.web.farmer_explanations import farmer_explanation_panel

        explained = (
            genai_panel(report, leading_only=True)
            if report.get("generative_ai", {}).get("status") == "generated"
            else genai_panel(report) + farmer_explanation_panel(report, summary)
        )
        body = counts + crop_findings(summary["candidates"], explanation_panel=explained)
        body += f'<section class="panel next-page-card"><h2>{MARKET_TITLE[language]}</h2><p>Compare reported market prices alongside your field findings.</p><a class="button" href="{base}/market">{MARKET_TITLE[language]} →</a></section>'
        body += f'<section class="panel next-page-card"><h2>{FERTILIZER_TITLES[language]}</h2><p>Use your soil-test recommendation to plan nutrients and compare fertilizer options.</p><a class="button" href="{base}/fertilizer">{FERTILIZER_TITLES[language]} →</a></section>'
        body += open_questions(summary, token)
        body += f'<section class="panel next-page-card"><h2>Turn the findings into a next step.</h2><p>Review the information tasks identified for this assessment.</p><a class="button" href="{base}/plan">Open your next steps →</a></section>'
        body += (
            '<details class="secondary-disclosure question-disclosure"><summary><span>Ask a question about your field</span><small>Personalised help</small></summary>'
            + assessment_question_panel(report, token)
            + "</details>"
            + source_section(summary)
        )
    elif view == "report":
        body = (
            inline_report(report)
            + f'<div class="report-page-actions"><a class="button" href="/reports/{token}.pdf">{"Save an English PDF copy ↓" if report.get("profile", {}).get("language", "en") != "en" else "Save a PDF copy ↓"}</a><a class="text-link" href="{base}/plan">Review next steps →</a></div>'
        )
        body += (
            '<details class="secondary-disclosure question-disclosure"><summary><span>Ask a question about your field</span><small>Personalised help</small></summary>'
            + assessment_question_panel(report, token)
            + "</details>"
            + source_section(summary)
        )
    elif view == "market":
        body = market_panel(
            report.get("profile", {}), summary["candidates"], token, market_selection
        )
    elif view == "fertilizer":
        body = fertilizer_panel(report, summary, token, fertilizer_feedback)
    else:
        body = next_steps_panel(report)
        body += f'<section class="panel"><h2>{text["edit_title"]}</h2><p>{text["edit_body"]}</p><a class="button" href="{base}/edit">{text["edit"]} →</a></section>'
    content = (
        top
        + f'<div class="container result-layout"><div class="results-main">{body}</div>{field_sidebar(summary,token,view)}</div>'
    )
    if view != "report":
        content += f'<section class="guidance-note container" lang="{language}"><strong>{text["boundaries"]}</strong><p>{LIMITS[language]}</p></section>'
    return page(
        content,
        title=title + " · CropNova",
        active="assess",
        private=True,
        body_class="page-workflow page-" + view,
        language=language,
    )
