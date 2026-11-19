"""A readable view of the reviewed crop library, with scope and source links."""

from html import escape
from knowledge_base.retrieval import get_usable_facts
from cropnova.web.web_views import source_links

LABELS = {
    "growing_season": "Documented season",
    "soil_texture": "Documented soil",
    "soil_ph_range": "Preferred soil pH",
    "water_screening_range_mm": "Indicative seasonal water",
}


def reference_value(fact):
    value = fact.get("value")
    if isinstance(value, list):
        if len(value) == 2 and all(isinstance(v, (float, int)) for v in value):
            value = f"{value[0]:g}–{value[1]:g}"
        else:
            value = ", ".join(str(v).replace("_", " ") for v in value)
    if value is None:
        return fact["statement"]
    unit = fact.get("unit", "")
    return str(value).replace("_", " ") + (" " + unit if unit else "")


def crop_library(knowledge):
    sources = {s["source_id"]: s for s in knowledge["sources"]}
    cards = []
    for crop in knowledge["crops"]:
        facts = [
            f
            for f in get_usable_facts(knowledge, crop["crop_id"])
            if f["crop_id"] == crop["crop_id"]
        ]
        rows, background = [], []
        for fact in facts:
            prop = fact.get("property", "")
            if prop not in LABELS and fact.get("constraint_eligible", True) is not False:
                continue
            scope = fact.get("applicability", {}).get("state") or "General reference for India"
            if isinstance(scope, list):
                scope = ", ".join(scope)
            refs = source_links([sources[sid] for sid in fact["source_ids"]])
            if prop in LABELS:
                extra = " · Requires well-drained soil" if fact.get("requires_drainage") else ""
                if fact.get("water_basis") == "supplemental_irrigation":
                    extra += " · Supplemental irrigation only"
                elif prop == "water_screening_range_mm":
                    extra += " · Whole-season water use; not an irrigation schedule"
                rows.append(
                    f'<tr><th scope="row">{LABELS[prop]}</th><td>{escape(reference_value(fact))}<small>{escape(scope + extra)}</small>{refs}</td></tr>'
                )
            else:
                label = prop.replace("_", " ").capitalize()
                background.append(
                    f"<li><strong>{escape(label)}</strong>: {escape(reference_value(fact))}<small>{escape(scope)}</small>{refs}</li>"
                )
        context = (
            '<details class="library-context"><summary>Additional crop background</summary><p>These records provide context. They are not additional suitability checks or field-specific instructions.</p><ul>'
            + "".join(background)
            + "</ul></details>"
            if background
            else ""
        )
        cards.append(
            f'<details class="library-crop"><summary><strong>{escape(crop["common_name"])}</strong><span>{len(facts)} reviewed crop records</span></summary><p class="small"><em>{escape(crop["scientific_name"])}</em></p><div class="coverage-table-wrap"><table class="library-table"><caption>References and their scope</caption><tbody>{"".join(rows)}</tbody></table></div>{context}</details>'
        )
    usable = get_usable_facts(knowledge)
    context_count = sum(f.get("constraint_eligible", True) is False for f in usable)
    historical = [f for f in knowledge["facts"] if f.get("historical_reference")]
    archive_rows = "".join(
        f'<tr><td>{escape(f["scientific_name"])}</td><td>{escape(f["statement"].split(":",1)[-1])}</td><td>{escape(reference_value(f))}</td></tr>'
        for f in historical
    )
    archive = (
        f'<details class="library-crop historical-library"><summary><strong>Historical crop reference</strong><span>{len(historical)} original FAO attributes</span></summary><p>FAO discontinued ECOCROP around 2015. These global references are kept for study and future local review. They never decide which crop is recommended. Annual rainfall in this table is not water available for one crop season. <a href="https://www.fao.org/land-water/resources/tools/databases/ecocrop/en">About the original dataset ↗</a></p><div class="coverage-table-wrap"><table class="library-table"><thead><tr><th>Species</th><th>Reference field</th><th>Original value</th></tr></thead><tbody>{archive_rows}</tbody></table></div></details>'
        if historical
        else ""
    )
    return f'<section class="container knowledge-library"><span class="eyebrow">Inside the crop library</span><h2>{len(knowledge["crops"])} crops. {len(usable)} reviewed agricultural records.</h2><p>The stored library contains {len(knowledge["facts"])} records in total. {context_count} reviewed records are background only; four field conditions determine the assessment. Pending records do not support recommendations.</p><p>Open a crop to see the values, geographic scope and original sources. General references and local recommendations serve different purposes.</p>{"".join(cards)}{archive}</section>'
