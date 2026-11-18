"""Build a useful website report from the saved measurements and evidence.

Comparisons and arithmetic describe the reference screen, never an irrigation
prescription or a prediction of harvest success. No LLM call happens here.
"""
from html import escape
from assessment_summary import build_summary, readable, explanation_text
from farmer_language import language_settings, native_value, NAMES
from farmer_narrative import LABELS, check_detail, crop_name, guidance_note, plan_wording, field_label
from evidence import numeric_range, scope_matches

LIMITS = {
 'en':'This assessment checks season, soil texture, preferred pH and a water reference. It does not measure local weather, pests, soil nutrients, salinity, crop variety, yield, profit or the timing of irrigation. Matching all checks supports a preliminary shortlist, not a guarantee of a successful crop. Seasonal water use is not the same as extra irrigation.',
 'hi':'यह आकलन मौसम, मिट्टी की बनावट, पसंदीदा pH और पानी के संदर्भ की जाँच करता है। इसमें स्थानीय मौसम का पूर्वानुमान, कीट, मिट्टी के पोषक तत्व, लवणता, किस्म, उपज, लाभ या सिंचाई का समय नहीं मापा जाता। सारी जाँच मेल खाने से शुरुआती सूची बनती है, अच्छी फसल की गारंटी नहीं। पूरे मौसम का पानी और अतिरिक्त सिंचाई अलग माप हैं।',
 'pa':'ਇਹ ਮੁਲਾਂਕਣ ਮੌਸਮ, ਮਿੱਟੀ ਦੀ ਬਣਤਰ, ਪਸੰਦੀਦਾ pH ਅਤੇ ਪਾਣੀ ਦੇ ਹਵਾਲੇ ਦੀ ਜਾਂਚ ਕਰਦਾ ਹੈ। ਇਸ ਵਿੱਚ ਸਥਾਨਕ ਮੌਸਮ ਦੀ ਭਵਿੱਖਬਾਣੀ, ਕੀੜੇ, ਮਿੱਟੀ ਦੇ ਪੋਸ਼ਕ ਤੱਤ, ਖਾਰਾਪਣ, ਕਿਸਮ, ਝਾੜ, ਲਾਭ ਜਾਂ ਸਿੰਚਾਈ ਦਾ ਸਮਾਂ ਨਹੀਂ ਮਾਪਿਆ ਜਾਂਦਾ। ਸਾਰੀਆਂ ਜਾਂਚਾਂ ਮੇਲ ਖਾਣ ਨਾਲ ਸ਼ੁਰੂਆਤੀ ਸੂਚੀ ਬਣਦੀ ਹੈ, ਚੰਗੀ ਫ਼ਸਲ ਦੀ ਗਾਰੰਟੀ ਨਹੀਂ। ਪੂਰੇ ਮੌਸਮ ਦਾ ਪਾਣੀ ਅਤੇ ਵਾਧੂ ਸਿੰਚਾਈ ਵੱਖਰੇ ਮਾਪ ਹਨ।',
}


def measurement_insight(report, crop, index, language='en'):
    """Only calculate against a single compatible numeric reference range."""
    if index not in (1,3):return ''
    check=crop['checks'][index]
    if check.get('reason_code') in {'CONFLICTING_VERIFIED_FACTS','INCOMPATIBLE_WATER_BASIS','INCOMPATIBLE_WATER_UNITS','MISSING_USER_INPUT'}:return ''
    facts={f['fact_id']:f for f in report.get('evidence_package',{}).get('facts',[])}
    supporting=[facts[fid] for fid in check['fact_ids'] if fid in facts]
    ranges=[]
    for fact in supporting:
        try:ranges.append(numeric_range(fact['value']))
        except (ValueError,TypeError,KeyError):return ''
    if not ranges or len(set(ranges))!=1:return ''
    low,high=ranges[0]
    profile=report.get('profile',{})
    actual=profile.get('water',{}).get('budget_mm') if index==1 else profile.get('soil',{}).get('ph')
    if not isinstance(actual,(int,float)) or isinstance(actual,bool):return ''
    if index==1:
        if any(f.get('water_basis') != profile.get('water',{}).get('basis') for f in supporting):return ''
        if actual<low:
            gap=low-actual
            return {'en':f'Your estimate is {gap:g} mm below the lower reference value of {low:g} mm. This is a gap against a rough reference, not the calculated amount of extra irrigation required.',
                    'hi':f'आपका अनुमान निचले संदर्भ {low:g} मिमी से {gap:g} मिमी कम है। यह मोटे संदर्भ से अंतर है, जरूरी अतिरिक्त सिंचाई की गणना नहीं।',
                    'pa':f'ਤੁਹਾਡਾ ਅੰਦਾਜ਼ਾ ਹੇਠਲੇ ਹਵਾਲੇ {low:g} ਮਿ.ਮੀ. ਤੋਂ {gap:g} ਮਿ.ਮੀ. ਘੱਟ ਹੈ। ਇਹ ਮੋਟੇ ਹਵਾਲੇ ਤੋਂ ਫ਼ਰਕ ਹੈ, ਲੋੜੀਂਦੀ ਵਾਧੂ ਸਿੰਚਾਈ ਦੀ ਗਿਣਤੀ ਨਹੀਂ।'}[language]
        position = 'at or above the upper reference' if actual>=high else 'inside the reference range'
        return {'en':f'Your {actual:g} mm estimate is {position} ({low:g}–{high:g} mm). The exact local requirement and water timing are not calculated by this comparison.',
                'hi':f'आपका {actual:g} मिमी अनुमान, संदर्भ {low:g}–{high:g} मिमी के '+('ऊपरी स्तर के बराबर या ऊपर है।' if actual>=high else 'बीच में है।')+' इस तुलना से सटीक स्थानीय जरूरत या पानी देने का समय तय नहीं होता।',
                'pa':f'ਤੁਹਾਡਾ {actual:g} ਮਿ.ਮੀ. ਅੰਦਾਜ਼ਾ, ਹਵਾਲੇ {low:g}–{high:g} ਮਿ.ਮੀ. ਦੇ '+('ਉੱਪਰਲੇ ਪੱਧਰ ਦੇ ਬਰਾਬਰ ਜਾਂ ਉੱਪਰ ਹੈ।' if actual>=high else 'ਵਿਚਕਾਰ ਹੈ।')+' ਇਸ ਤੁਲਨਾ ਨਾਲ ਸਹੀ ਸਥਾਨਕ ਲੋੜ ਜਾਂ ਪਾਣੀ ਦੇਣ ਦਾ ਸਮਾਂ ਤੈਅ ਨਹੀਂ ਹੁੰਦਾ।'}[language]
    gap=max(low-actual,0,actual-high)
    return {'en':f'Measured pH: {actual:g}; preferred reference: {low:g}–{high:g}. '+(f'The value is {gap:g} pH units outside that interval; this does not establish a treatment dose.' if gap else 'The value lies within the preferred interval. Nutrient availability and other soil properties are not established by this match.'),
            'hi':f'मापा pH: {actual:g}; पसंदीदा संदर्भ: {low:g}–{high:g}। '+(f'नतीजा इस सीमा से {gap:g} pH इकाई बाहर है; इससे उपचार की मात्रा तय नहीं होती।' if gap else 'नतीजा पसंदीदा सीमा के भीतर है। इससे पोषक तत्वों की स्थिति या मिट्टी के दूसरे गुण पक्के नहीं होते।'),
            'pa':f'ਮਾਪਿਆ pH: {actual:g}; ਪਸੰਦੀਦਾ ਹਵਾਲਾ: {low:g}–{high:g}। '+(f'ਨਤੀਜਾ ਇਸ ਹੱਦ ਤੋਂ {gap:g} pH ਇਕਾਈ ਬਾਹਰ ਹੈ; ਇਸ ਨਾਲ ਇਲਾਜ ਦੀ ਮਾਤਰਾ ਤੈਅ ਨਹੀਂ ਹੁੰਦੀ।' if gap else 'ਨਤੀਜਾ ਪਸੰਦੀਦਾ ਹੱਦ ਦੇ ਅੰਦਰ ਹੈ। ਇਸ ਨਾਲ ਪੋਸ਼ਕ ਤੱਤਾਂ ਦੀ ਹਾਲਤ ਜਾਂ ਮਿੱਟੀ ਦੇ ਹੋਰ ਗੁਣ ਪੱਕੇ ਨਹੀਂ ਹੁੰਦੇ।')}[language]


def planning_references(report, crop_id):
    guidance=report.get('field_guidance',{})
    reviewed={s['source_id']:s for s in guidance.get('sources',[]) if s.get('review_status')=='reviewed_for_inclusion'}
    facts=[f for f in guidance.get('facts',[]) if f.get('crop_id')==crop_id
           and f.get('verification_status') in {'verified_general','verified_context_specific'}
           and not f.get('historical_reference') and scope_matches(f,report.get('profile',{}))
           and f.get('source_ids') and all(sid in reviewed for sid in f['source_ids'])]
    return facts, reviewed


def executive_text(summary, language):
    names=', '.join(crop_name(c,language) for c in summary['candidates'] if c['status']=='feasible')
    total=len(summary['candidates']); matches=summary['matches']
    if matches:
        text={'en':f'{matches} of the {total} assessed crops match all four checked conditions: {names}.',
              'hi':f'जाँची गई {total} फसलों में {matches} फसलें चारों बातों से मेल खाती हैं: {names}।',
              'pa':f'ਜਾਂਚੀਆਂ {total} ਫ਼ਸਲਾਂ ਵਿੱਚੋਂ {matches} ਫ਼ਸਲਾਂ ਚਾਰਾਂ ਗੱਲਾਂ ਨਾਲ ਮੇਲ ਖਾਂਦੀਆਂ ਹਨ: {names}।'}[language]
        text+=' '+{'en':'When several crops match, these checks do not establish a single best variety, yield or profit.','hi':'कई फसलें मेल खाने पर इन जाँचों से एक ही सबसे अच्छी किस्म, उपज या लाभ तय नहीं होता।','pa':'ਕਈ ਫ਼ਸਲਾਂ ਮੇਲ ਖਾਣ ਉੱਤੇ ਇਨ੍ਹਾਂ ਜਾਂਚਾਂ ਨਾਲ ਇੱਕੋ ਸਭ ਤੋਂ ਵਧੀਆ ਕਿਸਮ, ਝਾੜ ਜਾਂ ਲਾਭ ਤੈਅ ਨਹੀਂ ਹੁੰਦਾ।'}[language]
    else:
        text={'en':f'None of the {total} assessed crops currently matches every check. Compare the unresolved measurements and recorded shortfalls below. A missing reference is not evidence that the crop cannot grow.',
              'hi':f'जाँची गई {total} फसलों में अभी कोई फसल हर जाँच से मेल नहीं खाती। नीचे अधूरे माप और दर्ज कमियों की तुलना करें। संदर्भ न मिलने का मतलब यह नहीं कि फसल उग नहीं सकती।',
              'pa':f'ਜਾਂਚੀਆਂ {total} ਫ਼ਸਲਾਂ ਵਿੱਚੋਂ ਅਜੇ ਕੋਈ ਫ਼ਸਲ ਹਰ ਜਾਂਚ ਨਾਲ ਮੇਲ ਨਹੀਂ ਖਾਂਦੀ। ਹੇਠਾਂ ਅਧੂਰੇ ਮਾਪ ਅਤੇ ਦਰਜ ਘਾਟਾਂ ਦੀ ਤੁਲਨਾ ਕਰੋ। ਹਵਾਲਾ ਨਾ ਮਿਲਣ ਦਾ ਮਤਲਬ ਇਹ ਨਹੀਂ ਕਿ ਫ਼ਸਲ ਉੱਗ ਨਹੀਂ ਸਕਦੀ।'}[language]
    return text


def rich_report(report):
    from web_views import source_links
    from farm_next_steps import next_step_cards
    from farmer_narrative import LABELS
    summary=build_summary(report); language,_=language_settings(report.get('profile',{})); t=LABELS[language]
    label=lambda c:t[{'feasible':'match','unknown':'unknown','rejected':'rejected'}[c['status']]]
    check_names=NAMES.get(language,['Growing season','Water supply','Soil texture','Soil pH'])
    rows=''.join(f'<tr><th>{escape(crop_name(c,language))}</th><td>{escape(label(c))}</td><td>{c["matched"]} / {len(c["checks"])}</td><td>'+escape(', '.join(check_names[i] for i,check in enumerate(c['checks']) if check['status']!='satisfied') or '—')+'</td></tr>' for c in summary['candidates'])
    table='<div class="coverage-table-wrap"><table class="crop-comparison report-comparison"><thead><tr><th>'+{'en':'Crop','hi':'फसल','pa':'ਫ਼ਸਲ'}[language]+'</th><th>'+{'en':'Finding','hi':'नतीजा','pa':'ਨਤੀਜਾ'}[language]+'</th><th>'+{'en':'Matches','hi':'मेल','pa':'ਮੇਲ'}[language]+'</th><th>'+t['missing']+'</th></tr></thead><tbody>'+rows+'</tbody></table></div>'
    generated={row['crop_id']:row['text'] for row in report.get('generative_ai',{}).get('explanations',[]) if report.get('generative_ai',{}).get('status')=='generated'}
    articles=[]
    for crop in summary['candidates']:
        details=[]
        for i,check in enumerate(crop['checks']):
            reason,implication=check_detail(check,i,language)
            numeric=measurement_insight(report,crop,i,language)
            details.append(f'<section class="report-condition"><h4>{check_names[i]}</h4><p class="report-record">{t["entered"]}: <strong>{escape(native_value(check["entered"],language))}</strong> · {t["reference"]}: {escape(native_value(check["reference"],language))}</p><p>{escape(reason)}</p><p>{escape(implication)}</p>'+('<p class="report-measurement">'+escape(numeric)+'</p>' if numeric else '')+f'<div class="source-chips">{source_links(check["sources"])}</div></section>')
        facts,sources=planning_references(report,crop['id'])
        context='<h4>'+t['published']+'</h4>'+''.join('<p>'+escape(guidance_note(f,language))+'</p>'+source_links([sources[sid] for sid in f['source_ids']]) for f in facts) if facts else ''
        ai='<aside class="report-ai-note"><h4>'+t['ai']+'</h4><p>'+escape(explanation_text(generated[crop['id']]))+'</p><small>'+t['ai_note']+'</small></aside>' if crop['id'] in generated else ''
        articles.append(f'<details class="report-crop"'+(' open' if crop['status']=='feasible' else '')+f'><summary class="report-crop-heading"><h3>{escape(crop_name(crop,language))}</h3><span class="badge {crop["status"]}">{escape(label(crop))}</span></summary><div class="report-crop-content">{"".join(details)}{context}{ai}</div></details>')
    _,actions=next_step_cards(report)
    actions=sorted(actions,key=lambda a:min({'violated':0,'unknown':1,'satisfied':2}[r['status']] for r in a['references']))
    checklist=''.join('<li><strong>'+escape(plan_wording(a,language)[0])+'</strong><p>'+escape(plan_wording(a,language)[1])+'</p></li>' for a in actions)
    fields=''.join('<div><dt>'+escape(field_label(k,language))+'</dt><dd>'+escape(native_value(v,language))+'</dd></div>' for k,v in summary['profile'])
    unresolved=[(crop,check,i) for crop in summary['candidates'] for i,check in enumerate(crop['checks']) if check['status']!='satisfied']
    followup=''.join('<li><strong>'+escape(crop_name(crop,language))+' · '+check_names[i]+'</strong><p>'+escape(check_detail(check,i,language)[0])+'</p></li>' for crop,check,i in unresolved)
    if not followup:followup='<li>'+{'en':'No required inputs remain missing for these checks. Confirm local variety, water timing and sowing guidance before planting.','hi':'इन जाँचों की जरूरी जानकारी पूरी है। बोने से पहले स्थानीय किस्म, पानी का समय और बुवाई की सलाह पक्की करें।','pa':'ਇਨ੍ਹਾਂ ਜਾਂਚਾਂ ਦੀ ਲੋੜੀਂਦੀ ਜਾਣਕਾਰੀ ਪੂਰੀ ਹੈ। ਬੀਜਣ ਤੋਂ ਪਹਿਲਾਂ ਸਥਾਨਕ ਕਿਸਮ, ਪਾਣੀ ਦਾ ਸਮਾਂ ਅਤੇ ਬਿਜਾਈ ਦੀ ਸਲਾਹ ਪੱਕੀ ਕਰੋ।'}[language]+'</li>'
    return f'<section class="explanation-panel inline-report detailed-report" id="field-report" lang="{language}" aria-labelledby="report-heading"><span class="eyebrow">{escape(summary["location"])}</span><h2 id="report-heading">{t["report"]}</h2><section class="report-executive"><h3>{t["overview"]}</h3><p>{escape(executive_text(summary,language))}</p></section><h3>{t["comparison"]}</h3>{table}<h3>{t["detailed"]}</h3>{"".join(articles)}<h3>{t["missing"]}</h3><ul class="report-open-questions">{followup}</ul><h3>{t["actions"]}</h3><ol class="report-action-checklist">{checklist}</ol><aside class="report-boundaries"><h3>{t["boundaries"]}</h3><p>{LIMITS[language]}</p></aside><details class="report-input-record"><summary>{t["input_record"]}</summary><dl class="profile-summary">{fields}</dl></details><a class="text-link" href="#assessment-sources">{t["sources"]} →</a></section>'
