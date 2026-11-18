"""Order and present recorded crop findings without inventing suitability scores.

All four checks must pass before a crop can enter the leading group. Equal
matches stay equal: this screening does not estimate yield or profitability.
"""
from html import escape
from web_views import candidate_card, crop_icon
from assessment_summary import ordered_candidates


def leading_card(crop, tied):
    reasons = ''.join(
        f'<li><span aria-hidden="true">✓</span><div><strong>{escape(check["name"])}</strong>'
        f'<span>{escape(check["entered"])} · Reference: {escape(check["reference"])}</span></div></li>'
        for check in crop['checks'] if check['status'] == 'satisfied'
    )
    label = 'Joint leading match' if tied else 'Leading match'
    limitations = ''.join('<p class="crop-limitation">' + escape(text) + '</p>'
                          for text in crop.get('limitations', []))
    return f'''<article class="leading-crop" data-leading-crop="{escape(crop['id'])}">
<div class="leading-crop-header"><span class="crop-portrait">{crop_icon(crop['id'])}</span><div><span class="eyebrow">{label}</span><h3>{escape(crop['name'])}</h3></div><span class="match-count" aria-label="Matches checked conditions: 4 of 4">4 / 4<span>checks matched</span></span></div>
<h4>Why this crop is shown first</h4><p>Its growing season, water reference, soil texture and preferred pH all match the details you entered.</p><ul class="match-reasons">{reasons}</ul>
{limitations}{candidate_card(crop, compact_title=True)}
</article>'''


def comparison_table(crops):
    rows = []
    labels = {'satisfied': 'Matches', 'unknown': 'Needs checking', 'violated': 'Shortfall / mismatch'}
    for crop in crops:
        checks = ''.join(
            f'<td><span class="comparison-state {check["status"]}">{labels[check["status"]]}</span></td>'
            for check in crop['checks']
        )
        rows.append(f'<tr><th scope="row">{escape(crop["name"])}</th><td><span class="badge {crop["status"]}">{escape(crop["label"])}</span></td>{checks}</tr>')
    return '<div class="crop-comparison-scroll"><table class="crop-comparison"><caption>Compare the four checked conditions</caption><thead><tr><th>Crop</th><th>Overall finding</th><th>Season</th><th>Water</th><th>Soil</th><th>pH</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>'


def crop_findings(candidates, explanation_panel=""):
    crops = ordered_candidates(candidates)
    matches = [c for c in crops if c['status'] == 'feasible']
    others = [c for c in crops if c['status'] != 'feasible']
    if matches:
        intro = ('These crops jointly match all four checked conditions. The available checks do not establish a single best crop.'
                 if len(matches) > 1 else
                 'This crop matches all four checked conditions among the options assessed.')
        content = '<section class="leading-matches" aria-labelledby="crop-findings"><div class="section-heading"><span class="eyebrow">Your strongest supported options</span><h2 id="crop-findings">Best matches for your field</h2><p>' + intro + '</p></div><div class="leading-grid">'
        content += ''.join(leading_card(c, len(matches) > 1) for c in matches) + '</div></section>'
    else:
        content = '<section class="panel no-leading-match" aria-labelledby="crop-findings"><span class="eyebrow">Before choosing a crop</span><h2 id="crop-findings">No complete match yet</h2><p>None of the assessed crops currently matches every check. The comparisons below show what is missing or needs attention; an open question is not a failed crop.</p></section>'
    if not matches:
        shortlist = [crop for crop in others if crop['status'] == 'unknown' and crop['matched'] >= 3]
        if shortlist:
            cards = []
            for crop in shortlist[:3]:
                pending = ', '.join(c['name'].lower() for c in crop['checks'] if c['status'] != 'satisfied')
                cards.append(f'<article class="review-shortlist"><h3>{escape(crop["name"])}</h3><strong>{crop["matched"]} of 4 conditions match</strong><p>Before choosing, confirm: {escape(pending)}.</p><span class="badge unknown">Not yet a complete match</span></article>')
            content += '<section class="panel"><h2>Worth checking first</h2><p>These crops match most of your entered details. Resolve the open check before treating them as suitable.</p><div class="leading-grid">' + ''.join(cards) + '</div></section>'
    content += explanation_panel
    if others:
        content += '<section class="other-crops"><div class="section-heading"><span class="eyebrow">The rest of the picture</span><h2>Other crop options</h2><p>Compare the open questions and shortfalls. Expand a crop for its measurements, reasons and sources.</p></div>'
        content += comparison_table(others)
        content += '<details class="comparison-details"><summary>Read detailed reasons and sources for each crop</summary><div class="compact-crop-list">' + ''.join(candidate_card(c) for c in others) + '</div></details></section>'
    content += '<p class="ranking-note">Order: complete matches first, then crops needing more information, then crops with a recorded shortfall. Within each group, more matched checks appear first. Equal findings are displayed alphabetically. This is not a prediction of yield or profit.</p>'
    return content
