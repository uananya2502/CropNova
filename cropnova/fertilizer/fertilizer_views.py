"""Farmer-facing fertilizer form and explanations using the existing page styles."""

from csv import DictReader
from functools import lru_cache
from html import escape
from pathlib import Path
from cropnova.fertilizer.fertilizer_adviser import PRODUCTS, SOURCE

TITLES = {"en": "Fertilizer adviser", "hi": "खाद की सलाह", "pa": "ਖਾਦ ਦੀ ਸਲਾਹ"}


def select(name, label, options, values):
    items = ['<option value="">Choose an option</option>']
    for value, text in options:
        selected = " selected" if values.get(name) == value else ""
        items.append(f'<option value="{escape(value)}"{selected}>{escape(text)}</option>')
    return f'<div class="field"><label for="fert-{name}">{label}</label><select id="fert-{name}" name="{name}">{"".join(items)}</select></div>'


def input_field(name, label, values, *, kind="number", maximum=10000):
    numeric = f' min="0" max="{maximum}" step="any"' if kind == "number" else ""
    value = escape(str(values.get(name, "")), quote=True)
    return f'<div class="field"><label for="fert-{name}">{label}</label><input id="fert-{name}" type="{kind}" name="{name}" value="{value}"{numeric}></div>'


def checkbox(name, label, values):
    checked = " checked" if values.get(name) == "yes" else ""
    return f'<label class="fertilizer-check"><input type="checkbox" name="{name}" value="yes"{checked}><span>{label}</span></label>'


def source_panel(source):
    link = (
        f'<a href="{escape(source["url"], quote=True)}" target="_blank" rel="noopener noreferrer">{escape(source["title"])} ↗</a>'
        if source["url"]
        else escape(source["title"])
    )
    return f'<p>{link}</p><p>{escape(source["sections"])}</p>'


def plan_panel(result):
    nutrient_names = ("Nitrogen (N)", "Phosphate (P₂O₅)", "Potash (K₂O)")
    targets = "".join(
        f'<div><dt>{label}</dt><dd>{target:.2f} kg/acre<br>{target * result["acres"]:.2f} kg for your field</dd></div>'
        for label, target in zip(nutrient_names, result["target"])
    )
    cards = []
    for plan in result["plans"]:
        title = {"dap": "DAP with urea", "ssp": "SSP with urea", None: "Nitrogen and potash plan"}[
            plan["carrier"]
        ]
        rows = []
        for product, quantity in plan["amounts"].items():
            if quantity <= 1e-8:
                continue
            rows.append(
                f'<tr><th scope="row">{PRODUCTS[product]["name"]}</th><td>{quantity:.1f} kg</td><td>{quantity * result["acres"]:.1f} kg</td></tr>'
            )
        if not rows:
            rows.append(
                '<tr><td colspan="3">The entered recommendation specifies zero N, P₂O₅ and K₂O fertilizer.</td></tr>'
            )
        dap_n = plan["amounts"]["dap"] * 0.18
        reason = (
            f"DAP supplies {dap_n:.2f} kg nitrogen per acre as well as phosphate. The urea amount accounts for that nitrogen."
            if plan["carrier"] == "dap"
            else "This option supplies phosphate through SSP. Urea supplies the nitrogen target."
        )
        if plan["carrier"] is None:
            reason = "The recommendation calls for no phosphate fertilizer. Only nutrients with a positive target are included."
        cards.append(
            f'<article class="panel fertilizer-option"><h3>{title}</h3><div class="crop-comparison-scroll"><table class="crop-comparison"><thead><tr><th>Fertilizer</th><th>Per acre</th><th>Your field</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div><h4>Why this combination?</h4><p>{reason}</p><p>All three nutrient targets balance using the labelled grades. Displayed quantities are rounded to 0.1 kg; calculations use full precision.</p></article>'
        )
    if not cards:
        cards.append(
            '<section class="panel"><h3>No balanced combination from these products</h3><p>Try including the alternative phosphate source or ask your soil adviser for another product. A DAP option can be excluded when it would supply more nitrogen than the recommendation allows.</p></section>'
        )
    reasons = "".join(f'<li>{escape(row["reason"])}</li>' for row in result["trace"])
    return f"""<section class="panel fertilizer-targets" id="fertilizer-result" tabindex="-1"><h2>Your seasonal nutrient plan</h2>
<p>{escape(result['crop']['name'])} · {result['area']:g} {escape(result['area_unit'])}{'s' if result['area'] != 1 else ''}</p>
<dl class="profile-summary">{targets}</dl><p>These are full-season quantities for the upcoming crop. Follow your crop adviser’s timing and split applications. If fertilizer has already been used, have the remaining amount checked before applying this plan.</p></section>
<div class="fertilizer-options">{''.join(cards)}</div>
<section class="panel"><h2>Why these quantities were chosen</h2><ol class="fertilizer-reasons">{reasons}</ol>
<h3>Before applying</h3><p>Check the product grade on the bag. This plan covers N, P₂O₅ and K₂O. Soil salinity, micronutrients, manure and crop residues may need separate advice. Potash is included only when the selected recommendation calls for it.</p>
<details><summary>See the calculation</summary><p>Nitrogen from urea = urea kg × 0.46. DAP supplies N at 0.18 and P₂O₅ at 0.46 kg per kg. SSP supplies P₂O₅ at 0.16 kg per kg. MOP supplies K₂O at 0.60 kg per kg.</p><p>The calculation compares available product combinations and checks all three nutrient balances. Soil-test measurements of available nutrients have a different meaning from these fertilizer doses.</p></details>
<h3>Recommendation source</h3>{source_panel(result['source'])}
<p>Product nutrient contents follow PAU Appendix IV, p. 160. A soil-card dose is entered by the farmer and should be checked against the original document.</p></section>"""


CROP_GUIDANCE = {
    "oats": ("Oats", "Choose guidance for the intended use. PAU gives separate fertilizer schedules for single-cut and two-cut fodder oats.", "https://www.pau.edu/content/ccil/pf/pp_rabi.pdf"),
    "wheat": ("Wheat", "Nitrogen and phosphorus are commonly considered for wheat. Potassium depends on the soil test. Irrigation and sowing time affect the recommendation.", "https://www.pau.edu/content/ccil/pf/pp_rabi.pdf"),
    "barley": ("Barley", "Nitrogen and phosphorus are considered for barley. Water availability and soil texture affect the amount, and potassium depends on the soil test.", "https://www.pau.edu/content/ccil/pf/pp_rabi.pdf"),
    "chickpea": ("Chickpea", "Chickpea fertilizer needs depend on soil fertility and the crop's nitrogen fixation. Check phosphorus and seed inoculation guidance for your field.", "https://www.pau.edu/content/ccil/pf/pp_rabi.pdf"),
    "rice": ("Rice", "Nitrogen management is important for rice. Phosphorus needs depend on the soil test and the fertilizer used for the previous crop.", "https://www.pau.edu/content/ccil/pf/pp_kharif.pdf"),
    "maize": ("Maize", "Maize needs a nutrient plan suited to the variety, growing season and soil fertility. Nitrogen and phosphorus recommendations vary with the field.", "https://www.pau.edu/content/ccil/pf/pp_kharif.pdf"),
    "cotton": ("Cotton", "Cotton fertilizer requirements vary by variety and soil fertility. Check nitrogen and phosphorus needs with a local soil test.", "https://www.pau.edu/content/ccil/pf/pp_kharif.pdf"),
    "groundnut": ("Groundnut", "Groundnut nutrient needs depend on soil fertility. Check local phosphorus and calcium guidance and suitable seed inoculation.", "https://www.pau.edu/content/ccil/pf/pp_kharif.pdf"),
    "soybean": ("Soybean", "Soybean nutrient needs depend on the soil and seed inoculation. Check local phosphorus advice and the soil test before applying fertilizer.", "https://www.pau.edu/content/ccil/pf/pp_kharif.pdf"),
}


# Product options from the crop chapters. Each crop explains when they apply.
CROP_PRODUCTS = {
    "oats": ("urea", "ssp"),
    "wheat": ("urea", "dap", "ssp", "mop"),
    "barley": ("urea", "dap", "ssp", "mop"),
    "chickpea": ("urea", "ssp"),
    "rice": ("urea", "dap", "ssp", "mop"),
    "maize": ("urea", "dap", "ssp", "mop"),
    "cotton": ("urea", "dap", "ssp"),
    "groundnut": ("urea", "ssp"),
    "soybean": ("urea", "ssp"),
}

PRODUCT_HELP = {
    "urea": "Supplies nitrogen.",
    "dap": "Supplies phosphate and nitrogen. Count its nitrogen when planning urea.",
    "ssp": "Supplies phosphate. Where the crop guide lists DAP as an alternative, choose one phosphate source.",
    "mop": "Supplies potash. Use only if the soil test or applicable local recommendation calls for it.",
}


def crop_product_list(crop):
    rows = "".join(
        f'<tr><th scope="row">{escape(PRODUCTS[key]["name"])}</th><td>{escape(PRODUCT_HELP[key])}</td></tr>'
        for key in CROP_PRODUCTS[crop]
    )
    return (
        '<h3>Fertilizer options to check for your field</h3>'
        '<div class="crop-comparison-scroll"><table class="crop-comparison">'
        '<thead><tr><th scope="col">Fertilizer</th><th scope="col">What it supplies</th></tr></thead>'
        f'<tbody>{rows}</tbody></table></div>'
    )


@lru_cache(maxsize=1)
def nutrient_references():
    path = Path(__file__).with_name("crop_nutrient_requirements.csv")
    with path.open(encoding="utf-8", newline="") as stream:
        return tuple(row for row in DictReader(stream) if row["verification_status"] == "verified_source")


def reference_panel(crop, profile):
    region = profile.get("region", {}).get("state", "").strip().casefold()
    season = profile.get("season", "").casefold()
    rows = [
        row for row in nutrient_references()
        if row["crop_id"] == crop and row["state"].casefold() == region
        and row["season"].casefold() == season
    ]
    if not rows:
        crop_rows = [row for row in nutrient_references() if row["crop_id"] == crop]
        if crop_rows:
            location = profile.get("region", {}).get("state") or "your selected location"
            return (
                '<h3>Published fertilizer amounts</h3>'
                f'<p>CropNova has a Punjab Rabi reference for this crop. Your assessment is for '
                f'{escape(location)} ({escape(season.title() or "season unspecified")}). '
                'Use a crop-specific soil-test recommendation for your field.</p>'
            )
        return '<h3>Published fertilizer amounts</h3><p>A verified dose is still needed for this crop. Use a crop-specific soil-test recommendation for your field.</p>'
    items = "".join(
        f'<li>{escape(row["growth_stage"].capitalize())}: {escape(row["source_value"])} '
        f'kg {escape(row["nutrient"])} per acre ({float(row["recommended_min_kg_ha"]):g} kg/ha)</li>'
        for row in rows
    )
    first = rows[0]
    return (
        '<section><h3>Published nutrient reference for Punjab Rabi</h3>'
        f'<p>Applies to: {escape(first["production_system"])}. These are nutrient amounts for that published scenario.</p>'
        f'<ul>{items}</ul><p>PAU Rabi 2025–26, printed page(s) {escape(first["page"])}.</p></section>'
    )


def fertilizer_panel(report, summary, token, feedback=None):
    """Show source-linked crop guidance after a single crop selection."""
    feedback = feedback or {}
    values = feedback.get("values", report.get("fertilizer_inputs", {}))
    selected = values.get("crop", "")
    guidance = CROP_GUIDANCE.get(selected)
    options = [(key, info[0]) for key, info in CROP_GUIDANCE.items()]
    result = plan_panel(report["fertilizer_plan"]) if report.get("fertilizer_plan") and not feedback and len(values) > 1 else ""
    if guidance and not result:
        name, advice, url = guidance
        region = report.get("profile", {}).get("region", {}).get("state", "")
        result = f'''<section class="panel" id="fertilizer-result" tabindex="-1"><h2>Fertilizer guidance for {escape(name)}</h2>{crop_product_list(selected)}{reference_panel(selected, report.get("profile", {}))}<h3>What matters for {escape(name)}</h3><p>{escape(advice)}</p><h3>Confirm the amount and timing</h3><p>A fertilizer dose cannot be determined from the crop name alone. Use your soil test and ask a local agricultural adviser to confirm the product, amount and application timing for your field{(' in ' + escape(region)) if region else ''}.</p><p>The source below is guidance for Punjab. Conditions and recommendations can differ elsewhere.</p><a href="{escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">Read the Punjab Agricultural University crop guide ↗</a></section>'''
    elif selected and not result:
        result = '<section class="panel" role="alert"><h2>Choose a crop from the list</h2></section>'
    return f'''<section class="panel fertilizer-intro"><h2>Fertilizer guidance</h2><p>Choose a crop to see what to consider when planning fertilizer.</p><form method="post" action="/assessment/{escape(token, quote=True)}/fertilizer">{select("crop", "Choose your crop", options, values)}<button class="button" type="submit">Show fertilizer guidance →</button></form></section>{result}'''
