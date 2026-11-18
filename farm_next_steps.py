"""Turn saved findings into practical, sourced next steps for a farmer.

These actions explain how to verify a decision. They do not turn the A* task
sequence into an irrigation schedule, treatment prescription or yield forecast.
"""
from html import escape
from assessment_summary import build_summary
from evidence import scope_matches

GUIDANCE_PROPERTIES = {'sowing_window', 'indicative_duration_days'}


def snapshot_guidance(knowledge, profile, crop_ids):
    """Keep reviewed context with the assessment so older results never drift."""
    from knowledge_base.retrieval import get_usable_facts
    facts = [dict(f) for f in get_usable_facts(knowledge)
             if f['crop_id'] in crop_ids and f.get('property') in GUIDANCE_PROPERTIES
             and not f.get('historical_reference') and scope_matches(f, profile)]
    source_ids = {sid for fact in facts for sid in fact['source_ids']}
    return {'facts':facts, 'sources':[dict(s) for s in knowledge['sources']
                                     if s['source_id'] in source_ids]}


def action_wording(index, checks):
    """Change the action according to the actual unresolved or matched check."""
    reasons = ' '.join(c['reason'] for c in checks).lower()
    incomplete = any(c['status'] != 'satisfied' for c in checks)
    if index == 0:
        return ('Confirm the sowing season' if incomplete else 'Choose the local sowing window',
                'Confirm when you intend to sow and ask for the locally recommended variety and sowing dates. A season match does not establish the right date for every variety.')
    if index == 1:
        if 'different things' in reasons:
            return ('Use the same kind of water estimate',
                    'Check whether your number includes the whole season’s crop-water supply or only extra irrigation. Re-enter an estimate that matches the reference; these two amounts cannot be substituted for each other.')
        if any(c['status'] == 'violated' for c in checks):
            return ('Review the water shortfall before choosing',
                    'Ask your local agriculture adviser whether effective rainfall, usable soil moisture and reliable irrigation can cover the local crop-water requirement. Do not assume an extra water source is available.')
        return ('Get a usable water estimate' if incomplete else 'Confirm how water will be available',
                'List the water expected from useful rainfall, stored soil moisture and irrigation over the crop season. Have the estimate checked locally. The reference below is water use over a season, not an instruction to apply that amount as irrigation.')
    if index == 2:
        return ('Check soil and field drainage',
                'Confirm the soil type from a soil report or local assessment. Where the reference requires well-drained soil, check whether water leaves the field after rain. A soil-name match alone does not assess salinity or every field condition.')
    return ('Check the soil-test pH' if incomplete else 'Keep your soil-test report for planning',
            'Use a measured soil-test pH rather than a guess. If it is outside the preferred reference, ask for local advice before ruling the crop in or out. pH alone cannot tell you a fertiliser dose or whether a treatment is needed.')


def next_step_cards(report):
    summary = build_summary(report)
    # Focus on the most supported options instead of mixing every weak alternative
    # into the farmer’s main action list. All crops remain on the findings page.
    crops = [c for c in summary['candidates'] if c['status'] == 'feasible'] or summary['candidates'][:2]
    crops = crops[:3]
    guidance = report.get('field_guidance', {})
    reviewed = {s['source_id']:s for s in guidance.get('sources', [])
                if s.get('review_status') == 'reviewed_for_inclusion'}
    actions = []
    for index in range(4):
        rows = [(crop, crop['checks'][index]) for crop in crops if len(crop['checks']) == 4]
        if not rows:
            continue
        title, instruction = action_wording(index, [check for _,check in rows])
        references = []
        sources = {}
        for crop, check in rows:
            references.append({**check, 'crop':crop['name'], 'crop_id':crop['id']})
            sources.update({s['source_id']:s for s in check['sources']})
        notes = []
        note_records = []
        if index == 0:
            for fact in guidance.get('facts', []):
                if fact.get('crop_id') not in {crop['id'] for crop in crops}:
                    continue
                if not scope_matches(fact, report.get('profile', {})) or not fact.get('source_ids'):
                    continue
                if fact.get('verification_status') not in {'verified_general','verified_context_specific'} or fact.get('historical_reference'):
                    continue
                if not all(sid in reviewed for sid in fact['source_ids']):
                    continue
                note_records.append(fact)
                value = fact['value']
                if fact['property'] == 'sowing_window':
                    notes.append(f"{fact['crop_id'].replace('_',' ').title()}: published sowing window {value}. Confirm the current local recommendation.")
                elif fact['property'] == 'indicative_duration_days' and isinstance(value, list):
                    notes.append(f"{fact['crop_id'].replace('_',' ').title()}: indicative growing period {value[0]}–{value[1]} days. The actual variety and local conditions can differ.")
                sources.update({sid:reviewed[sid] for sid in fact['source_ids']})
        actions.append({'title':title, 'instruction':instruction, 'references':references,
                        'notes':notes, 'guidance_records':note_records, 'check_index':index, 'sources':list(sources.values())})
    return crops, actions


def render_next_steps(report):
    from web_views import source_links
    from farmer_language import language_settings, native_value, CROPS
    from farmer_narrative import LABELS, plan_wording, check_detail, crop_name, guidance_note
    language, _ = language_settings(report.get('profile', {}))
    text = LABELS[language]
    crops, actions = next_step_cards(report)
    if not actions:
        return f'<section class="panel" lang="{language}"><h2>{text["missing"]}</h2><p>{text["plan_intro"]}</p></section>'
    priority = {"violated":0, "unknown":1, "satisfied":2}
    actions = sorted(actions, key=lambda action:min(priority[row["status"]] for row in action["references"]))
    cards = []
    for number, action in enumerate(actions, 1):
        title, instruction = plan_wording(action, language)
        evidence = []
        for row in action['references']:
            name = CROPS.get(language, {}).get(row['crop_id'], row['crop'])
            reason, _ = check_detail(row, action['check_index'], language)
            evidence.append(f'<div class="step-evidence"><strong>{escape(name)}</strong><p>{text["entered"]}: {escape(native_value(row["entered"],language))} · {text["reference"]}: {escape(native_value(row["reference"],language))}</p><p>{escape(reason)}</p></div>')
        notes = ''.join('<p class="published-step-note">' + escape(guidance_note(fact,language)) + '</p>' for fact in action['guidance_records'])
        first = action['references'][0]
        name = CROPS.get(language, {}).get(first['crop_id'],first['crop'])
        current = f'<p class="step-current">{escape(name)} · {text["entered"]}: {escape(native_value(first["entered"],language))} · {text["reference"]}: {escape(native_value(first["reference"],language))}</p>'
        sources = source_links(action['sources']) or '<p class="small">'+text['no_source']+'</p>'
        cards.append(f'<article class="farm-step-card" data-farm-step="{number}"><span class="farm-step-number">0{number}</span><h3>{escape(title)}</h3>{current}<p class="step-instruction">{escape(instruction)}</p>{notes}<details><summary>{text["why"]}</summary>{"".join(evidence)}<div class="source-chips">{sources}</div></details></article>')
    names = ', '.join(crop_name(crop,language) for crop in crops)
    plan = report.get('preparation_plan', {})
    tasks = ''.join('<li>' + escape(step['title']) + '</li>' for step in plan.get('steps', []))
    organised = '<details class="planner-explanation"><summary>How the information tasks were organised</summary><p>This sequence groups missing measurements and evidence reviews. It does not schedule farming operations or guarantee that a crop will match.</p><ol>' + tasks + '</ol></details>' if tasks and language == 'en' else ''
    return f'<section class="farm-next-steps" lang="{language}" aria-labelledby="plan-heading"><span class="eyebrow">{text["plan"]}</span><h2 id="plan-heading">{text["plan_title"]}</h2><p class="steps-introduction">{text["focus"]}: {escape(names)}. {text["plan_intro"]}</p><div class="farm-step-grid">{"".join(cards)}</div>{organised}</section>'
