"""Small HTML building blocks for the public CropNova website.

All user and provider text is escaped. Internal engine codes are kept in the
assessment data, rather than printed as product language.
"""
from html import escape
from datetime import datetime
from assessment_summary import build_summary, readable, explanation_text
from genai_explainer import provider_name

LEAF = '<svg viewBox="0 0 32 32" fill="none" aria-hidden="true"><path d="M25 5C12 4 5 11 8 20c8 7 18-1 17-15Z" fill="currentColor"/><path d="M5 28 21 12" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/></svg>'



def crop_icon(crop):
    """Small decorative crop drawings; the adjacent label provides the name."""
    drawings = {
        'wheat': '<path d="M19 35V10M19 30 9 22M19 24 29 16"/><ellipse cx="14" cy="23" rx="3" ry="6" transform="rotate(-40 14 23)"/><ellipse cx="24" cy="17" rx="3" ry="6" transform="rotate(40 24 17)"/><ellipse cx="14" cy="14" rx="3" ry="6" transform="rotate(-40 14 14)"/><ellipse cx="22" cy="8" rx="3" ry="6" transform="rotate(22 22 8)"/>',
        'rice': '<path d="M12 35c1-13 3-23 10-28 4 1 7 5 8 9M15 25l-7-6M14 29l9-7"/><ellipse cx="24" cy="11" rx="2" ry="4" transform="rotate(-30 24 11)"/><ellipse cx="28" cy="16" rx="2" ry="4" transform="rotate(-20 28 16)"/><ellipse cx="21" cy="16" rx="2" ry="4"/><ellipse cx="25" cy="22" rx="2" ry="4"/>',
        'maize': '<rect x="14" y="6" width="12" height="25" rx="6"/><path d="M18 8v21M22 8v21M15 13h10M14 18h12M14 23h12M10 18c-1 10 3 17 10 17 6-2 10-7 10-16-4 4-7 8-10 16M10 18c4 3 6 8 10 17"/>',
        'chickpea': '<path d="M13 34c2-10 4-16 10-23M17 23C9 24 6 20 8 16c6-2 10 0 11 5M21 16c0-7 4-11 10-10 1 7-2 11-8 12"/><path d="M27 23c7-1 10 8 5 12-6 4-14-2-11-8 1-3 3-4 6-4Z"/><path d="M27 25c-2 2-2 4 0 5"/>',
    }
    drawings.update({
        'barley': '<path d="M20 35V8M20 29 11 21M20 23 29 15M20 17 12 10M11 21V10M29 15V4M12 10V3M20 8V2"/><ellipse cx="15" cy="24" rx="3" ry="5" transform="rotate(-40 15 24)"/><ellipse cx="25" cy="18" rx="3" ry="5" transform="rotate(40 25 18)"/>',
        'cotton': '<path d="M20 36V24M20 29l-9-4M20 32l9-5M11 23c-9-1-9-13-1-15 1-8 14-8 17-1 10 0 12 15 3 17-7 3-13 2-19-1Z"/><path d="m12 23 8 5 10-4"/>',
        'groundnut': '<path d="M14 8c-8 2-10 10-3 15-3 8 4 15 11 11 5-3 2-9 7-13 9-6 4-17-4-15-5 1-6 4-11 2Z"/><path d="m11 14 8 4-5 9 7 3M25 10l-4 7 8 1M15 11l13 13M9 19l15 8"/>',
        'sorghum': '<path d="M20 36V13M20 27l-10-7M20 31l10-6"/><ellipse cx="20" cy="11" rx="8" ry="10"/><path d="M16 5v13M21 3v17M25 7v9M13 10h14M14 15h12"/>',
        'pearl_millet': '<path d="M20 36V25M20 31l-9-7M20 34l10-7"/><rect x="15" y="3" width="10" height="23" rx="5"/><path d="M18 6v17M22 6v17M16 10h8M15 15h10M16 20h8"/>',
        'soybean': '<path d="M19 36V8M19 26 9 18M19 21l10-9"/><path d="M9 18C1 15 5 8 10 10c7 1 6 10 5 12M29 12c-3-7 3-12 7-7 4 5-1 12-9 12M21 25c1-7 12-7 13-1 2 7-6 13-12 9Z"/><circle cx="28" cy="25" r="2"/><circle cx="26" cy="30" r="2"/>',
    })
    return '<svg class="crop-icon" viewBox="0 0 40 40" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + drawings.get(crop, drawings['wheat']) + '</svg>'


def safe_url(value):
    text = str(value or '')
    return escape(text, quote=True) if text.startswith(('https://', 'http://')) else '#'


def page(content, *, title='CropNova · Crop choices with clarity', active='', private=False, body_class='page-public', language='en'):
    ui = {
        'en': ('Home','How it works','Sources','Assess your field','Privacy','Skip to content','Better questions. Clearer crop choices.'),
        'hi': ('होम','यह कैसे काम करता है','स्रोत','अपने खेत की जाँच करें','गोपनीयता','मुख्य जानकारी पर जाएँ','बेहतर सवाल। फसल का स्पष्ट चुनाव।'),
        'pa': ('ਮੁੱਖ ਪੰਨਾ','ਇਹ ਕਿਵੇਂ ਕੰਮ ਕਰਦਾ ਹੈ','ਸਰੋਤ','ਆਪਣੇ ਖੇਤ ਦੀ ਜਾਂਚ ਕਰੋ','ਨਿੱਜਤਾ','ਮੁੱਖ ਜਾਣਕਾਰੀ ਉੱਤੇ ਜਾਓ','ਵਧੀਆ ਸਵਾਲ। ਫ਼ਸਲ ਦੀ ਸਪਸ਼ਟ ਚੋਣ।'),
    }.get(language)
    if ui is None:
        language='en'
        ui=('Home','How it works','Sources','Assess your field','Privacy','Skip to content','Better questions. Clearer crop choices.')
    links = [('home','/',ui[0]),('how','/how-it-works',ui[1]),('sources','/sources',ui[2])]
    nav = ''.join('<a href="'+url+'"'+(' aria-current="page"' if key==active else '')+'>'+label+'</a>' for key,url,label in links)
    return f'''<!doctype html><html lang="{language}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="description" content="Compare crop options with your soil, season and water. Understand your field assessment with clear reasons and published sources."><meta name="referrer" content="no-referrer"><title>{escape(title)}</title><link rel="icon" type="image/svg+xml" href="/static/icon.svg">{'<meta name="robots" content="noindex,nofollow,noarchive">' if private else ""}<link rel="stylesheet" href="/static/style.css?v=16"><link rel="stylesheet" href="/static/design.css?v=16"><script src="/static/app.js?v=16" defer></script></head>
<body class="{escape(body_class, quote=True)}"><a class="skip-link" href="#main">{ui[5]}</a><header class="site-header"><div class="container nav"><a class="brand" href="/">{LEAF}<span>CropNova</span></a><nav aria-label="Main navigation">{nav}<a class="nav-cta" href="/assess"{' aria-current="page"' if active=='assess' else ''}>{ui[3]} ↗</a></nav></div></header>
<main id="main">{content}</main><footer class="site-footer container"><a class="brand" href="/">{LEAF}<span>CropNova</span></a><p>{ui[6]}</p><nav aria-label="Footer navigation"><a href="/how-it-works">{ui[1]}</a><a href="/sources">{ui[2]}</a><a href="/privacy">{ui[4]}</a></nav></footer></body></html>'''.encode('utf-8')


def options(items, selected):
    return ''.join(f'<option value="{escape(value)}"{" selected" if str(selected) == value else ""}>{escape(label)}</option>' for value, label in items)


def form_values(profile=None):
    profile = profile or {}
    soil, water, region = (profile.get(key, {}) for key in ('soil', 'water', 'region'))
    values = {**profile, 'state':region.get('state',profile.get('state','')), 'district':region.get('district',profile.get('district','')) or ''}
    for name, field in [('soil_texture','texture'),('soil_ph','ph'),('soil_drainage','drainage')]:
        values[name] = soil.get(field,profile.get(name,''))
    for name, field in [('water_budget_mm','budget_mm'),('water_basis','basis')]:
        values[name] = water.get(field,profile.get(name,''))
    values['irrigation'] = water.get('irrigation', profile.get('irrigation','unknown'))
    values.update(rainfall_level=profile.get('rainfall', {}).get('level',profile.get('rainfall_level','')), rainfall_mm=profile.get('rainfall', {}).get('mm',profile.get('rainfall_mm','')))
    return {key:'' if value is None else value for key,value in values.items()}


def farm_form(profile=None, *, errors=None):
    """Keep field controls separate from the shared page and result components."""
    from assessment_form import render_form
    return render_form(profile, errors=errors)


def home(profile=None, errors=None):
    """Compatibility entry point; the home and form now have separate screens."""
    from public_pages import home_page, assessment_page
    return assessment_page(profile, errors) if profile is not None or errors else home_page()


def source_links(sources):
    return ''.join(f'<a class="source-chip" href="{safe_url(source.get("url"))}" target="_blank" rel="noopener noreferrer">{escape(source.get("organization") or source.get("publisher") or source.get("title","Published source"))} ↗</a>' for source in sources)


def genai_panel(report, leading_only=False):
    result = report.get('generative_ai', {})
    if result.get('status') in {None, 'not_requested'}:
        return ''
    if result.get('status') != 'generated':
        # Keep configuration, provider codes and service details out of the farm flow.
        return '<section class="explanation-panel"><span class="eyebrow">Your assessment explained</span><h2>Your crop checks are ready</h2><p>The optional written explanation is unavailable right now. The reasons and references for each crop are shown below.</p></section>'
    from farmer_explanations import generated_language_text
    chosen = result.get('explanations', [])
    if leading_only:
        candidates = build_summary(report)['candidates']
        focus = [c for c in candidates if c['status'] == 'feasible'] or candidates[:3]
        chosen = [row for row in chosen if row['crop_id'] in {c['id'] for c in focus}]
    rows = ''.join(f'<article><h3>{escape(row["crop_id"].replace("_", " ").title())}</h3>{generated_language_text({**row, "text":explanation_text(row["text"])})}</article>' for row in chosen)
    return f'<section class="explanation-panel"><span class="eyebrow">Your assessment explained</span><h2>The findings, in plain language.</h2>{rows}<p class="small">Generated from the assessment evidence. Check the recorded findings and sources before making decisions.</p></section>'



def inline_report(report):
    """Show interpretation, comparisons, evidence and actions from the snapshot."""
    from assessment_report_content import rich_report
    return rich_report(report)


def assessment_question_panel(report, token):
    crops = [(crop['id'],crop['name']) for crop in build_summary(report)['candidates']]
    return f'''<section class="panel question-panel" aria-labelledby="ask-heading"><span class="eyebrow">Understand your results</span><h2 id="ask-heading">Ask about your assessment</h2><p>Ask why a crop matches, what needs attention, or which information is missing. Each answer links back to your recorded findings.</p>
<form data-question-form action="/assessment/{escape(token,quote=True)}/ask" method="post">
<label for="question-crop">Crop</label><select id="question-crop" name="crop_id">{options([('','All assessed crops')]+crops,'')}</select>
<label for="assessment-question">Your question</label><textarea id="assessment-question" name="question" rows="3" minlength="3" maxlength="400" required placeholder="Is my water supply enough for this crop?"></textarea>
<div class="question-suggestions"><button type="button" data-question-suggestion>Why does this crop match my field?</button><button type="button" data-question-suggestion>What information is still missing?</button></div>
<p class="small">When you ask, your question and relevant assessment findings are sent to Google Gemini to write an explanation. Avoid personal details. Answers use this saved assessment; update the field form to check different inputs.</p><button class="button" type="submit">Ask a question →</button><noscript><p>Enable JavaScript to ask a question. Your crop findings and sources remain available below.</p></noscript>
</form><div data-question-result role="status" aria-live="polite" hidden></div></section>'''


def candidate_card(candidate, opened=False, compact_title=False):
    rows = []
    for check in candidate['checks']:
        state = check['status']
        label = {'satisfied':'Matches', 'violated':'Needs attention', 'unknown':'Open question'}[state]
        symbol = {'satisfied':'✓', 'violated':'!', 'unknown':'?'}[state]
        rows.append(f'''<div class="check-row {state}"><div class="check-label"><span class="check-symbol" aria-hidden="true">{symbol}</span><h4>{escape(check['name'])}</h4><span class="check-state">{label}</span></div><div class="comparison"><div><span>Your entry</span><strong>{escape(check['entered'])}</strong></div><div><span>Published reference</span><strong>{escape(check['reference'])}</strong></div></div><p>{escape(check['reason'])}</p><div class="source-chips">{source_links(check['sources'])}</div></div>''')
    actions = ''
    if candidate['actions']:
        actions = '<div class="next-steps"><h4>What would help clarify this result?</h4><ul>' + ''.join(f'<li>{escape(action)}</li>' for action in candidate['actions']) + '</ul></div>'
    heading = (f'<span class="trace-label">View checks and sources</span><span class="expand-mark" aria-hidden="true">+</span>'
               if compact_title else
               f'<div class="crop-identity"><span class="crop-initial">{crop_icon(candidate["id"])}</span><div><h3>{escape(candidate["name"])}</h3><span>{candidate["matched"]} of {len(candidate["checks"])} conditions matched</span></div></div><span class="badge {candidate["status"]}">{escape(candidate["label"])}</span><span class="expand-mark" aria-hidden="true">+</span>')
    return f'<details class="crop-result {candidate["status"]}"{ " open" if opened else ""}><summary>{heading}</summary><div class="crop-details">{"".join(rows)}{actions}</div></details>'



def condition_alignment_panel(report):
    """Show the optional soft index beside, never instead of, the crop findings."""
    analysis = report.get('fuzzy_analysis')
    if not analysis:
        return ''
    sources = {source['source_id']: source for source in report.get('evidence', [])}
    cards = []
    for crop in analysis['candidates']:
        if crop['score'] is None:
            detail = f'<p>{escape(crop["reason"])}</p>'
        else:
            score = crop['score']
            measures = crop['inputs']
            label = 'Closer alignment' if score >= 70 else 'Mixed alignment' if score >= 40 else 'Limited alignment'
            review = '<p class="small">The crop still needs local review. This index does not turn an open finding into a match.</p>' if crop['needs_review'] else ''
            used = [sources[key] for key in crop['source_ids'] if key in sources]
            rules = ''.join(f'<li>{escape(rule["ph_set"].replace("_"," "))} pH alignment and {escape(rule["water_set"])} water coverage: {rule["strength"]:.2f} strength, {rule["consequent"]:g} points.</li>' for rule in crop['fired_rules'])
            detail = f'''<strong class="alignment-score">{score:g}<span> index points</span></strong><p>{label}</p><meter min="0" max="100" value="{score}" aria-label="{escape(crop['name'])} reference alignment">{score:g}</meter><p class="small">pH {measures['ph']:g}; water budget {measures['water_budget_mm']:g} mm compared with an upper reference of {measures['water_reference_upper_mm']:g} mm.</p>{review}<details><summary>How the index was formed</summary><p>Partially matching descriptions are combined using their membership strengths. The rule outputs are 20, 55 or 85 index points; the displayed result is their weighted average.</p><ul>{rules}</ul><div class="source-chips">{source_links(used)}</div></details>'''
        cards.append(f'<article class="alignment-card"><h3>{escape(crop["name"].title())}</h3>{detail}</article>')
    return f'<section class="panel condition-alignment" aria-labelledby="alignment-heading"><span class="eyebrow">A closer look at the measurements</span><h2 id="alignment-heading">How closely do pH and water align?</h2><p>Some comparisons are gradual. This separate index shows how the recorded measurements align with the available references.</p><div class="alignment-grid">{"".join(cards)}</div><p class="small">{escape(analysis["note"])}</p></section>'


def preparation_plan_panel(report):
    """Show practical actions grounded in the saved crop findings."""
    from farm_next_steps import render_next_steps
    return render_next_steps(report)


def result_page(report, token):
    """Compatibility entry point for the dedicated saved-results screen."""
    from assessment_pages import saved_page
    return saved_page(report, token)


def message_page(title, message):
    return page(f'<section class="container message-page"><span class="eyebrow">CropNova</span><h1>{escape(title)}</h1><p>{escape(message)}</p><a class="button" href="/assess">Start an assessment →</a></section>')
