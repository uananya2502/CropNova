"""Public pages: each screen has one purpose and a shareable URL."""

from html import escape
from knowledge_base.loader import load_knowledge
from public_profiles import REFERENCE_PROFILES
from web_views import page, farm_form, safe_url, crop_icon


def breadcrumbs(label):
    return f'<nav class="breadcrumbs container" aria-label="Breadcrumb"><a href="/">Home</a><span aria-hidden="true">/</span><span>{escape(label)}</span></nav>'


def heading(kicker, title, text):
    return f'<header class="page-heading container"><span class="eyebrow">{escape(kicker)}</span><h1>{escape(title)}</h1><p>{escape(text)}</p></header>'


def home_page():
    crops = "".join(
        f'<article><span class="crop-portrait">{crop_icon(crop)}</span><h3>{crop.replace("_", " ").title()}</h3><p>Soil, season &amp; water</p></article>'
        for crop, profile in (
            (key.removeprefix("reference-"), value) for key, value in REFERENCE_PROFILES.items()
        )
    )
    content = """<section class="hero container"><div class="hero-copy"><span class="eyebrow">Make your next season a considered choice</span><h1>Find crops that fit<br>your field.</h1><p>Compare your soil, season and water with published crop guidance. See the reasons behind each result and know what to check next.</p><div class="hero-actions"><a class="button" href="/assess">Assess my field <span aria-hidden="true">↗</span></a><a class="text-link" href="/how-it-works">How it works →</a></div><div class="hero-caption">No account needed · Clear reasons · Your field details</div></div><div class="hero-art"><img src="/static/field-morning.webp" width="1672" height="941" alt="Illustrated green crop fields in warm morning light"></div></section>
<section class="steps-strip container"><div><span>01 / YOUR FIELD</span><h2>Start with what you know.</h2><p>Your location, soil and available water.</p></div><div><span>02 / YOUR OPTIONS</span><h2>Compare with confidence.</h2><p>Read the matches, shortfalls and open questions.</p></div><div><span>03 / YOUR NEXT STEP</span><h2>Make a practical plan.</h2><p>Know what to confirm before choosing a crop.</p></div></section>"""
    content += f"""<section class="coverage-section container"><div class="section-heading"><span class="eyebrow">Start with the available knowledge</span><h2>Ten crops. Reasons you can follow.</h2><p>References cover different crops and regions. We keep a comparison open when the evidence does not apply.</p></div><div class="coverage-grid">{crops}</div><a class="text-link" href="/sources">Explore the published references →</a></section>
<section class="start-banner container"><div><span class="eyebrow">Your field, your context</span><h2>Make the next decision a clearer one.</h2><p>Missing a measurement? You can still begin and see what needs checking.</p></div><a class="button" href="/assess">Start an assessment →</a></section>"""
    return page(content, active="home")


def assessment_page(profile=None, errors=None, *, editing=False):
    intro = (
        "Update your measurements and generate a new assessment. Your previous result stays unchanged."
        if editing
        else "Enter what you know about your field. Your results will open on their own page."
    )
    content = breadcrumbs("Edit field details" if editing else "Field assessment")
    content += heading("Field assessment", "A clearer choice starts here.", intro)
    content += farm_form(profile, errors=errors)
    return page(content, title="Field assessment · CropNova", active="assess", private=editing, body_class="page-assessment page-workflow")


def how_it_works_page():
    sections = [
        (
            "Tell us about the field",
            "Choose the growing season and crops, then enter soil and water details. Unknown measurements remain open rather than being guessed.",
        ),
        (
            "Compare the relevant guidance",
            "The assessment checks growing season, soil texture, pH and water against published references that apply to the stated context.",
        ),
        (
            "Read the reasons",
            "Each finding shows your input, the reference and a reason. A match is a preliminary comparison, not a guarantee of crop success.",
        ),
        (
            "Review the measurements and next steps",
            "Where supported, a separate index describes gradual pH and water alignment. A follow-up plan organises measurement and evidence-review tasks; neither changes the recorded findings.",
        ),
        (
            "Ask about the assessment",
            "Optional written explanations use your recorded evidence. Questions can show supporting findings and source links. If the service is unavailable, the original crop findings remain available.",
        ),
    ]
    cards = "".join(
        f'<article class="process-card"><span class="process-number">{i:02d}</span><div><h2>{escape(title)}</h2><p>{escape(text)}</p></div></article>'
        for i, (title, text) in enumerate(sections, 1)
    )
    content = breadcrumbs("How it works") + heading(
        "From inputs to understanding",
        "A reason behind every finding.",
        "A focused comparison of your field details with applicable published guidance.",
    )
    content += f'<div class="reading-column container">{cards}<aside class="panel"><h2>What this assessment cannot establish</h2><p>Weather, variety, water timing and local field conditions still matter. CropNova does not predict yield or profit, prescribe treatments, or replace local agricultural advice.</p><a class="text-link" href="/sources">See the references and coverage →</a></aside><a class="button" href="/assess">Assess your field →</a></div>'
    return page(content, title="How it works · CropNova", active="how")


def sources_page():
    knowledge = load_knowledge()
    reviewed = [
        source
        for source in knowledge.get("sources", [])
        if source.get("review_status") == "reviewed_for_inclusion"
    ]
    items = "".join(
        f'<article class="reference-card"><span class="eyebrow">{escape(source.get("organization") or source.get("publisher") or "Published reference")}</span><h2><a href="{safe_url(source.get("url"))}" target="_blank" rel="noopener noreferrer">{escape(source.get("title","Published guidance"))} ↗</a></h2><p>{escape(source.get("section") or "Use the linked source to review its stated conditions and scope.")}</p></article>'
        for source in reviewed
    )
    content = breadcrumbs("Sources") + heading(
        "Follow the evidence",
        "Published guidance, visible sources.",
        "Review the references behind the comparisons. A source applies only within its recorded crop, location and measurement context.",
    )
    content += '<section class="panel container coverage-note"><h2>Know the current coverage</h2><p>The library covers ten crops, including barley, cotton, groundnut, sorghum, pearl millet and soybean. Punjab references expand local season and soil guidance; Haryana and Rajasthan records remain available. Other references may describe general soil preferences or water ranges. Coverage is not complete for every state or crop. Background records on crop duration and drought sensitivity add context and do not change the four assessment checks.</p><p>Seasonal crop-water use and supplemental irrigation are different measurements. Preferred soil and pH ranges do not establish absolute growing limits.</p></section>'
    from knowledge_library import crop_library
    content += crop_library(knowledge)
    content += f'<div class="reference-grid container">{items}</div><section class="start-banner container"><div><h2>Put the references in context.</h2><p>Enter your field details to see which guidance applies.</p></div><a class="button" href="/assess">Start an assessment →</a></section>'
    return page(content, title="Sources and coverage · CropNova", active="sources")


def privacy_page():
    content = breadcrumbs("Privacy") + heading(
        "Your information",
        "Understand what is saved and shared.",
        "You can use CropNova without providing a name, phone number or exact address.",
    )
    content += """<div class="reading-column container"><section class="panel"><h2>Your assessment details</h2><p>The field details and completed findings are saved on the application server so you can reopen the result and its report. A random private link provides access; anyone holding that link can read it.</p><p>Links expire after one hour. Storage keeps at most 100 assessments, so older links can become unavailable sooner. Expired records are cleaned up when new assessments are saved; expiry is not a guarantee of immediate physical deletion.</p></section>
<section class="panel"><h2>Optional written explanations</h2><p>When you select a written explanation, the recorded checks and supporting evidence are sent to the configured AI provider. Town and district input fields are omitted. When you submit a follow-up question, the question and relevant findings may be sent to Google Gemini.</p><p>Questions can remain in a short-lived server memory cache to avoid repeated requests. Avoid typing personal details. Provider data handling and quotas depend on the configured service and account terms.</p></section>
<section class="panel"><h2>Server and hosting</h2><p>Crop comparison and evidence search run on the application server. The app does not require advertising trackers or an account cookie. The hosting provider may maintain its own operational logs. Downloaded PDFs remain wherever you choose to save them.</p><p>Keep assessment links private. Start a new assessment if a link expires.</p></section><a class="button" href="/assess">Start an assessment →</a></div>"""
    return page(content, title="Privacy · CropNova")
