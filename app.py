"""Dependency-free browser interface for the CropNova prototype.

Run ``python app.py`` and open http://127.0.0.1:8000.
"""

from __future__ import annotations

import json
from html import escape
from typing import Any, Iterable, Mapping
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

from agent import run_assessment
from knowledge_base.loader import load_knowledge


CSS = """
:root{--ink:#19352c;--muted:#61756d;--paper:#fbfcf7;--cream:#f2f0e4;--leaf:#2e6b4e;--lime:#c8e26b;--rust:#b95d3f;--gold:#dda93d;--line:#dce4db}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;line-height:1.55}
header{background:var(--ink);color:white;padding:1rem 0}nav,main,.hero-inner{max-width:1120px;margin:auto;padding-left:1.25rem;padding-right:1.25rem}nav{display:flex;align-items:center;justify-content:space-between}.brand{font:800 1.25rem Georgia,serif;letter-spacing:.02em}.tag{font-size:.78rem;padding:.35rem .65rem;border:1px solid #ffffff55;border-radius:99px}
.hero{background:linear-gradient(125deg,var(--ink),#326c4f);color:white;padding:3.4rem 0 4.5rem}.hero-inner{display:grid;grid-template-columns:1.35fr .65fr;gap:2.5rem;align-items:end}.eyebrow{text-transform:uppercase;letter-spacing:.14em;color:var(--lime);font-size:.74rem;font-weight:800}.hero h1{font:700 clamp(2.6rem,6vw,5rem)/.96 Georgia,serif;margin:.5rem 0 1rem;max-width:760px}.hero p{max-width:680px;color:#e3ebe7;font-size:1.05rem}.hero-note{border-left:3px solid var(--lime);padding-left:1rem;color:#d5e0da;font-size:.9rem}
main{margin-top:-2rem;padding-bottom:4rem}.panel{background:white;border:1px solid var(--line);border-radius:18px;box-shadow:0 18px 50px #18352c12;padding:clamp(1.2rem,3vw,2.2rem);margin-bottom:1.25rem}.panel h2{font:700 1.65rem Georgia,serif;margin:0 0 .4rem}.intro{color:var(--muted);margin-top:0}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem 1.25rem}.field label,.label{display:block;font-size:.8rem;font-weight:800;letter-spacing:.035em;margin-bottom:.35rem}.field small{display:block;color:var(--muted);margin-top:.25rem}input,select{width:100%;font:inherit;color:var(--ink);padding:.75rem .8rem;border:1px solid #becbc3;border-radius:9px;background:#fff}input:focus,select:focus{outline:3px solid #c8e26b66;border-color:var(--leaf)}fieldset{border:0;padding:0;margin:1.3rem 0}.checks{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.65rem}.check{display:flex;align-items:center;gap:.55rem;border:1px solid var(--line);border-radius:9px;padding:.65rem .7rem}.check input{width:auto}.actions{display:flex;align-items:center;gap:1rem;margin-top:1.4rem}.button{border:0;border-radius:10px;background:var(--leaf);color:white;font-weight:800;padding:.85rem 1.2rem;cursor:pointer}.button:hover{background:#23543d}.privacy{color:var(--muted);font-size:.8rem}
.status{display:flex;gap:1rem;align-items:flex-start}.status-mark{width:12px;height:12px;border-radius:50%;background:var(--gold);margin-top:.45rem;box-shadow:0 0 0 6px #dda93d1e}.status.good .status-mark{background:var(--leaf)}.status.bad .status-mark{background:var(--rust)}.status h2{margin:0}.status-code{font-size:.72rem;font-weight:900;letter-spacing:.08em;color:var(--muted)}.columns{display:grid;grid-template-columns:1fr 1fr;gap:1.25rem}.candidate{border:1px solid var(--line);border-radius:12px;padding:1rem;margin:.7rem 0}.candidate h3{display:flex;justify-content:space-between;gap:.5rem;margin:0 0 .55rem;font-size:1rem}.pill{font-size:.68rem;text-transform:uppercase;letter-spacing:.05em;padding:.2rem .5rem;border-radius:99px;background:var(--cream)}.pill.feasible{background:#dff1e5;color:#1f6241}.pill.rejected{background:#f9e4dd;color:#873c27}.pill.unknown{background:#f5edcf;color:#755d16}.trace{font-size:.84rem;color:var(--muted);padding:.45rem 0;border-top:1px solid #edf0ed}.trace strong{color:var(--ink)}ul.clean{padding-left:1.1rem;margin-bottom:0}.warning{background:#fff8e2;border-left:4px solid var(--gold);padding:.8rem 1rem;border-radius:5px;margin:.55rem 0}.error{background:#fcebe7;border-left-color:var(--rust)}details{margin-top:1rem}pre{background:#12271f;color:#dce9e1;padding:1rem;border-radius:10px;overflow:auto;font-size:.75rem}.footnote{font-size:.8rem;color:var(--muted);margin-top:1rem}
@media(max-width:760px){.hero-inner,.grid,.columns{grid-template-columns:1fr}.checks{grid-template-columns:repeat(2,1fr)}.hero{padding-top:2.3rem}.hero-note{display:none}}
"""


def _page(content: str) -> bytes:
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CropNova</title><style>{CSS}</style></head><body>
    <header><nav><div class="brand">CropNova</div><div class="tag">Explainable AI prototype</div></nav></header>
    <section class="hero"><div class="hero-inner"><div><div class="eyebrow">Evidence before answers</div><h1>Find what fits. See every reason.</h1><p>CropNova checks candidate crops against explicit season, water, soil-texture and pH constraints. Unknown information stays unknown.</p></div><div class="hero-note">The symbolic pipeline decides outcomes. Explanations communicate the trace without changing it.</div></div></section>
    <main>{content}</main></body></html>"""
    return html.encode("utf-8")


def _options(values: Iterable[tuple[str, str]], selected: str = "") -> str:
    return "".join(
        f'<option value="{escape(value)}"{" selected" if value == selected else ""}>{escape(label)}</option>'
        for value, label in values
    )


def _form(crops: list[Mapping[str, Any]], values: Mapping[str, Any] | None = None) -> str:
    values = values or {}
    region = values.get("region", {}) if isinstance(values.get("region"), Mapping) else {}
    soil = values.get("soil", {}) if isinstance(values.get("soil"), Mapping) else {}
    water = values.get("water", {}) if isinstance(values.get("water"), Mapping) else {}
    form_values = {
        **values,
        "state": region.get("state", values.get("state", "")),
        "district": region.get("district", values.get("district", "")) or "",
        "soil_texture": soil.get("texture", values.get("soil_texture", "unknown")),
        "soil_ph": soil.get("ph", values.get("soil_ph", "")) if soil.get("ph", values.get("soil_ph")) is not None else "",
        "soil_fertility": soil.get("fertility", values.get("soil_fertility", "unknown")),
        "water_availability": water.get("availability", values.get("water_availability", "unknown")),
        "irrigation": water.get("irrigation", values.get("irrigation", "unknown")),
    }
    selected = set(form_values.get("candidate_ids", []))
    crop_checks = "".join(
        f'<label class="check"><input type="checkbox" name="candidate_ids" value="{escape(str(crop.get("crop_id")))}"{" checked" if crop.get("crop_id") in selected else ""}> {escape(str(crop.get("common_name", crop.get("name", crop.get("crop_id", "")))).title())}</label>'
        for crop in crops
    )
    enum = {
        "season": [("unknown", "I don't know"), ("kharif", "Kharif"), ("rabi", "Rabi"), ("zaid", "Zaid")],
        "texture": [("unknown", "I don't know"), ("sandy", "Sandy"), ("loamy", "Loamy"), ("clayey", "Clayey"), ("other", "Other")],
        "level": [("unknown", "I don't know"), ("low", "Low"), ("moderate", "Moderate"), ("high", "High")],
        "irrigation": [("unknown", "I don't know"), ("available", "Available"), ("rainfed", "Rainfed"), ("limited", "Limited")],
    }
    return f"""<section class="panel"><h2>Farm profile</h2><p class="intro">Required fields are marked. Measurements can remain unknown.</p>
    <form method="post" action="/assess"><div class="grid">
      <div class="field"><label for="state">State / region *</label><input id="state" name="state" required maxlength="80" value="{escape(str(form_values.get('state','')))}" placeholder="e.g. your state"></div>
      <div class="field"><label for="district">District / town</label><input id="district" name="district" maxlength="80" value="{escape(str(form_values.get('district','')))}" placeholder="Optional"></div>
      <div class="field"><label for="season">Growing season</label><select id="season" name="season">{_options(enum['season'],str(form_values.get('season','unknown')))}</select></div>
      <div class="field"><label for="water_availability">Water availability</label><select id="water_availability" name="water_availability">{_options(enum['level'],str(form_values.get('water_availability','unknown')))}</select></div>
      <div class="field"><label for="soil_texture">Soil texture</label><select id="soil_texture" name="soil_texture">{_options(enum['texture'],str(form_values.get('soil_texture','unknown')))}</select></div>
      <div class="field"><label for="soil_ph">Measured soil pH</label><input id="soil_ph" name="soil_ph" type="number" min="0" max="14" step="0.1" value="{escape(str(form_values.get('soil_ph','')))}" placeholder="Unknown"><small>Compared only with verified ranges.</small></div>
      <div class="field"><label for="soil_fertility">Soil fertility</label><select id="soil_fertility" name="soil_fertility">{_options(enum['level'],str(form_values.get('soil_fertility','unknown')))}</select></div>
      <div class="field"><label for="irrigation">Irrigation access</label><select id="irrigation" name="irrigation">{_options(enum['irrigation'],str(form_values.get('irrigation','unknown')))}</select></div>
      <div class="field"><label for="objective">Objective *</label><select id="objective" name="objective">{_options([('find_suitable_crop','Find a suitable crop'),('conserve_water','Conserve water'),('soil_improvement','Soil improvement'),('compare_alternatives','Compare alternatives')],str(form_values.get('objective','find_suitable_crop')))}</select></div>
      <div class="field"><label for="priority">Priority</label><select id="priority" name="priority">{_options([('','No preference'),('water','Water'),('soil-season','Soil and season'),('resources','Resources'),('compare','Compare')],str(form_values.get('priority','') or ''))}</select></div>
    </div><fieldset><legend class="label">Candidates to compare</legend><div class="checks">{crop_checks}</div><small class="privacy">Leave all unchecked to consider every knowledge-base crop.</small></fieldset>
    <div class="actions"><button class="button" type="submit">Run transparent assessment</button><span class="privacy">No name, phone number, or exact address is collected.</span></div></form></section>"""


def _constraint_rows(candidate: Mapping[str, Any]) -> str:
    rows = []
    for key, label in (
        ("satisfied_constraints", "Passed"),
        ("failed_constraints", "Failed"),
        ("unknown_constraints", "Unknown"),
    ):
        for item in candidate.get(key, []):
            ids = ", ".join(item.get("fact_ids", [])) or "no verified fact ID"
            rows.append(
                f'<div class="trace"><strong>{escape(label)} · {escape(str(item.get("constraint_id","")))}</strong><br>{escape(str(item.get("reason","")))}<br><small>Evidence: {escape(ids)}</small></div>'
            )
    return "".join(rows)


def _candidate_cards(candidates: Iterable[Mapping[str, Any]], empty: str) -> str:
    cards = []
    for candidate in candidates:
        status = str(candidate.get("status", "unknown"))
        identity = " · ".join(
            str(value).title() if key == "category" else str(value)
            for key, value in (
                ("category", candidate.get("category")),
                ("scientific_name", candidate.get("scientific_name")),
            )
            if value
        )
        cards.append(
            f'<article class="candidate"><h3>{escape(str(candidate.get("name", candidate.get("candidate_id"))).title())}<span class="pill {escape(status)}">{escape(status)}</span></h3>'
            f'{f"<p class=\"intro\">{escape(identity)}</p>" if identity else ""}{_constraint_rows(candidate)}</article>'
        )
    return "".join(cards) or f'<p class="intro">{escape(empty)}</p>'


def _list(items: Iterable[str]) -> str:
    return "<ul class=" + '"clean">' + "".join(f"<li>{escape(str(item))}</li>" for item in items) + "</ul>"


def _results(report: Mapping[str, Any]) -> str:
    status = str(report.get("status", "SYSTEM_ERROR"))
    mood = "good" if status == "FEASIBLE_OPTIONS_FOUND" else "bad" if status in {"NO_FEASIBLE_OPTION", "INVALID_INPUT", "SYSTEM_ERROR"} else ""
    summary = next((item.get("text") for item in report.get("explanations", []) if item.get("type") == "assessment"), "Assessment could not be completed.")
    alerts = "".join(f'<div class="warning">{escape(str(item))}</div>' for item in report.get("warnings", []))
    alerts += "".join(f'<div class="warning error">{escape(str(item.get("message", item)))}</div>' for item in report.get("errors", []))
    questions = report.get("follow_up_questions", [])
    if questions:
        alerts += '<div class="warning"><strong>Helpful follow-up</strong>' + _list(questions) + "</div>"
    csp = report.get("csp_result", {})
    knowledge = report.get("knowledge_summary", {})
    sources = report.get("evidence", [])
    source_html = "".join(
        f'<div class="trace"><strong>{escape(str(item.get("source_id", "Source")))}</strong><br>{escape(str(item.get("title", item.get("organization", "Verified source"))))}</div>'
        for item in sources
    ) or '<p class="intro">No verified source was used in this assessment.</p>'
    raw = escape(json.dumps(report.get("evidence_package", {}), indent=2, ensure_ascii=False))
    return f"""<section class="panel"><div class="status {mood}"><span class="status-mark"></span><div><div class="status-code">{escape(status)}</div><h2>Assessment result</h2><p>{escape(str(summary))}</p></div></div>{alerts}</section>
    <section class="columns"><div class="panel"><h2>Feasible options</h2>{_candidate_cards(csp.get('feasible_candidates',[]),'No option has passed every hard constraint.')}</div>
    <div class="panel"><h2>Rejected options</h2>{_candidate_cards(csp.get('rejected_candidates',[]),'No candidate was definitively rejected.')}</div></section>
    <section class="panel"><h2>Unknown / needs review</h2><p class="intro">These options are neither passed nor rejected. Missing input or verified knowledge prevents a decision.</p>{_candidate_cards(csp.get('unknown_candidates',[]),'No unresolved candidates.')}</section>
    <section class="columns"><div class="panel"><h2>Trace & diagnostics</h2><p>Knowledge version: <strong>{escape(str(report.get('knowledge_version','unknown')))}</strong></p><p>Knowledge records: <strong>{escape(str(knowledge.get('total_crops',0)))} crops · {escape(str(knowledge.get('usable_facts',0)))} usable facts · {escape(str(knowledge.get('total_sources',0)))} sources</strong></p><p>Dataset status: <strong>{escape(str(knowledge.get('dataset_status','unknown')))}</strong></p><p>Rule adapter: <strong>{escape(str(report.get('rule_status','not run')))}</strong></p><p>Assignments examined: <strong>{escape(str(csp.get('diagnostics',{}).get('assignments_examined',0)))}</strong></p><p>Unknown treated as satisfied: <strong>No</strong></p><details><summary>Structured evidence package</summary><pre>{raw}</pre></details></div>
    <div class="panel"><h2>Evidence used</h2>{source_html}<h2>Limitations & next step</h2>{_list(report.get('limitations',[]))}<p class="footnote">Update the form when more information becomes available and run the same deterministic pipeline again.</p></div></section>
    {_form(_crops(), report.get('profile',{}))}"""


def _crops() -> list[Mapping[str, Any]]:
    try:
        return list(load_knowledge().get("crops", []))
    except Exception:
        return []


def application(environ, start_response):
    method = environ.get("REQUEST_METHOD", "GET").upper()
    path = environ.get("PATH_INFO", "/")
    if method == "GET" and path == "/":
        body = _page(_form(_crops()))
        status = "200 OK"
    elif method == "POST" and path == "/assess":
        try:
            length = min(int(environ.get("CONTENT_LENGTH") or 0), 100_000)
        except ValueError:
            length = 0
        parsed = parse_qs(environ["wsgi.input"].read(length).decode("utf-8"), keep_blank_values=True)
        values: dict[str, Any] = {key: items[-1] for key, items in parsed.items()}
        values["candidate_ids"] = parsed.get("candidate_ids", [])
        report = run_assessment(values)
        body = _page(_results(report))
        status = "200 OK" if report.get("status") != "SYSTEM_ERROR" else "500 Internal Server Error"
    else:
        body = _page('<section class="panel"><h2>Page not found</h2><p><a href="/">Return to CropNova</a></p></section>')
        status = "404 Not Found"
    start_response(status, [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(body)))])
    return [body]


def create_app():
    """Return the WSGI application for servers and tests."""

    return application


if __name__ == "__main__":
    host, port = "127.0.0.1", 8000
    print(f"CropNova is running at http://{host}:{port}")
    with make_server(host, port, application) as server:
        server.serve_forever()
