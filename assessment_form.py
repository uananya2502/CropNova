"""Render a dropdown-based field form with clear reference coverage and examples."""

from html import escape
from web_views import options, form_values, LEAF
from form_choices import (
    state_choices,
    district_choices,
    numeric_choices,
    TEXTURES,
    STATES,
    DISTRICTS,
)
from public_profiles import REFERENCE_PROFILES
from genai_explainer import provider_name


# The menu and example table share one crop list, preventing stale crop counts.
CROPS = [
    (profile["candidate_ids"][0], key.removeprefix("reference-").replace("_", " ").title())
    for key, profile in REFERENCE_PROFILES.items()
]


def select_field(name, label, choices, value, *, help_text="", required=False, full=False):
    required_attr = " required" if required else ""
    extra = " full" if full else ""
    hint = f'<small id="{name}-help">{escape(help_text)}</small>' if help_text else ""
    described = f' aria-describedby="{name}-help"' if help_text else ""
    return f'<div class="field{extra}"><label for="{name}">{escape(label)}</label><select id="{name}" name="{name}"{required_attr}{described}>{options(choices,value)}</select>{hint}</div>'


def coverage_table():
    rows = []
    for key, profile in REFERENCE_PROFILES.items():
        crop = key.removeprefix("reference-")
        basis = (
            "Seasonal supply"
            if profile["water_basis"] == "seasonal_crop_water"
            else "Supplemental irrigation"
        )
        rows.append(
            f'<tr><th scope="row">{crop.replace("_", " ").title()}</th><td>{profile["state"]}</td><td>{profile["season"].title()}</td><td>{profile["soil_texture"].replace("_", " ").title()}</td><td>{profile["soil_ph"]}</td><td>{profile["water_budget_mm"]} mm<br>{basis}</td><td><a href="/assess?preset={key}">Use profile →</a></td></tr>'
        )
    return (
        '<div class="coverage-table-wrap"><table class="coverage-table"><caption>Complete worked reference examples</caption><thead><tr><th>Crop</th><th>State</th><th>Season</th><th>Soil</th><th>pH</th><th>Water example</th><th>Open</th></tr></thead><tbody>'
        + "".join(rows)
        + "</tbody></table></div>"
    )


def profile_picker():
    choices = [("", "Select a covered example")] + [
        (key, key.removeprefix("reference-").replace("_", " ").title() + " / " + profile["state"])
        for key, profile in REFERENCE_PROFILES.items()
    ]
    return f'<section class="reference-picker"><h3>Start with a covered reference profile</h3><p>These example inputs match the available four-condition references. They are not measurements from your own field.</p><form action="/assess" method="get"><label for="preset">Reference profile</label><select id="preset" name="preset" required>{options(choices,"")}</select><button class="button" type="submit">Load profile →</button></form></section>'


def render_form(profile=None, *, errors=None):
    v = form_values(profile)
    # Canonicalise labels for menus without changing the saved profile itself.
    v["state"] = next(
        (state for state in STATES if state.casefold() == str(v.get("state", "")).casefold()),
        v.get("state", ""),
    )
    v["district"] = next(
        (
            district
            for district in DISTRICTS.get(v["state"], [])
            if district.casefold() == str(v.get("district", "")).casefold()
        ),
        v.get("district", ""),
    )
    selected = v.get("candidate_ids", [])
    if isinstance(selected, str):
        selected = selected.split(",")
    selection = ",".join(selected) if selected else ""
    crop_choices = [
        ("", "Select a crop"),
        *CROPS,
        ("__all__", "Compare all crops"),
    ]
    if len(selected) > 1:
        crop_choices.append(
            (selection, "Current selection: " + ", ".join(c.title() for c in selected))
        )
    elif selection and selection not in {key for key, _ in CROPS}:
        crop_choices.append((selection, selection + " — check selection"))
    alert = ""
    if errors:
        alert = (
            '<div class="notice warning" role="alert"><strong>Please check these details</strong><ul>'
            + "".join(
                "<li>" + escape(error.get("message", "Please check the selected values.")) + "</li>"
                for error in errors
            )
            + "</ul></div>"
        )
    from farmer_language import rainfall_fields, LANGUAGES
    rain = rainfall_fields(v)
    language = select_field("language", "Explanation language / भाषा / ਭਾਸ਼ਾ", list(LANGUAGES.items()), v.get("language") or "en", full=True)
    language += select_field("multilingual_view", "Show languages together", [("no","My chosen language"),("yes","English + हिंदी + ਪੰਜਾਬੀ side by side")], v.get("multilingual_view") or "no", full=True)
    location = select_field(
        "state",
        "State / region",
        state_choices(v.get("state")),
        v.get("state", ""),
        required=True,
        help_text="Complete worked crop examples are available for Haryana, Rajasthan, Punjab and Maharashtra; crop coverage varies by state.",
    )
    location += select_field(
        "district",
        "District (optional)",
        district_choices(v.get("state", ""), v.get("district", "")),
        v.get("district", ""),
        help_text="Optional location label. Current crop references do not provide district-specific recommendations.",
    )
    location += select_field(
        "season",
        "When will you grow the crop?",
        [("unknown", "Not sure yet"), ("rabi", "Rabi — winter crop"), ("kharif", "Kharif — rainy-season crop"), ("zaid", "Zaid — summer crop")],
        v.get("season", "unknown"),
        full=True,
    )
    fields = select_field(
        "soil_texture", "Soil texture", TEXTURES, v.get("soil_texture") or "unknown"
    )
    fields += select_field(
        "soil_ph",
        "Soil test pH (if you know it)",
        numeric_choices(v.get("soil_ph", ""), kind="ph"),
        str(v.get("soil_ph", "")),
        help_text="Choose your measured pH. If it is unknown, leave the check open.",
    )
    fields += select_field(
        "soil_drainage",
        "Does rainwater drain out of your field?",
        [
            ("unknown", "Not sure yet"),
            ("well_drained", "Yes — water drains away"),
            ("poorly_drained", "No — water stays in the field"),
        ],
        v.get("soil_drainage") or "unknown",
        full=True,
    )
    water_fields = select_field(
        "water_budget_mm",
        "Usable water for the whole crop season (optional, mm)",
        numeric_choices(v.get("water_budget_mm", ""), kind="water"),
        str(v.get("water_budget_mm", "")),
        help_text="Select the actual estimated depth. Reference values depend on the crop and measurement basis; see the example table below.",
    )
    water_fields += select_field(
        "water_basis",
        "What is included in this water estimate?",
        [
            ("seasonal_crop_water", "Rainfall + usable soil water + irrigation"),
            ("supplemental_irrigation", "Supplemental irrigation only"),
        ],
        v.get("water_basis") or "seasonal_crop_water",
    )
    fields += select_field("irrigation", "Where does your field get water?",
        [("unknown","Not sure yet"),("rainfed","Rain only"),("available","Rain and irrigation"),("limited","Some irrigation, but water is limited")],
        v.get("irrigation") or "unknown", full=True)
    water_details_open = " open" if v.get("water_budget_mm") else ""
    water_details = f'<details class="water-advanced"{water_details_open}><summary>Have a measured water estimate? Add it here (optional)</summary><p>Rain and irrigation choices describe your field. An exact usable-water estimate is needed for a complete water check. Ask a local adviser if you do not know this value.</p><div class="field-grid">{water_fields}</div></details>'
    crop_menu = select_field(
        "candidate_ids",
        "Crop to assess",
        crop_choices,
        selection,
        required=True,
        full=True,
        help_text="Choose a crop, or compare all crops. We check your selected state and season separately.",
    )
    explanation = select_field(
        "use_genai",
        "Written explanation",
        [("no", "Standard explanation only"), ("yes", "Add a detailed AI explanation")],
        v.get("use_genai") or "no",
        full=True,
        help_text="The AI connects your recorded checks into a longer explanation of reasons, water needs, precautions and next actions. It does not change the crop result.",
    )
    return f"""<section class="assessment-section container" id="farm-form"><div class="form-card assessment-workspace">{alert}<form data-assessment-form method="post" action="/assess"><input type="hidden" name="objective" value="find_suitable_crop">
<div class="wizard-top"><span class="eyebrow">Your next crop.</span><span data-wizard-status aria-live="polite">Three simple sections</span></div>
<ol class="form-progress" aria-label="Field details progress"><li data-step-marker="0"><span>1</span><strong>Location</strong></li><li data-step-marker="1"><span>2</span><strong>Soil &amp; water</strong></li><li data-step-marker="2"><span>3</span><strong>Review &amp; compare</strong></li></ol>
<section class="form-section" data-form-step data-step-title="Location and growing season"><div class="step-intro"><h2>Where is your field?</h2><p>Start with your location and the season you plan to grow in.</p></div><div class="field-grid">{location}</div><div class="form-tip">Not sure about a measurement? You can leave it unknown and see what still needs checking.</div></section>
<section class="form-section" data-form-step data-step-title="Soil, rain and water"><div class="step-intro"><h2>Tell us about your field conditions.</h2><p>Use your own observations and soil-test results. Optional measurements help complete the comparison.</p></div>{rain}<div class="field-grid">{fields}</div>{water_details}<details class="field-help"><summary>What counts as usable water?</summary><p>Use a whole-season estimate, including useful rainfall, soil moisture and irrigation. Rain descriptions do not become a guessed water measurement. Chickpea’s current reference covers supplemental irrigation only.</p></details></section>
<section class="form-section" data-form-step data-step-title="Crops and explanation"><div class="step-intro"><h2>What would you like to compare?</h2><p>Choose a crop or compare all options. Your results will open on a separate page.</p></div><div class="field-grid">{crop_menu}{language}{explanation}</div><div class="coverage-preview" data-coverage-preview role="status" aria-live="polite">Choose a crop to preview the checks.</div><p class="small privacy-copy">An optional AI explanation sends recorded checks and evidence to {provider_name()}. Town and district inputs are omitted. <a href="/privacy">Read about your information →</a></p></section>
<div class="wizard-controls" data-wizard-controls hidden><button class="button button-secondary" type="button" data-wizard-back>← Back</button><button class="button" type="button" data-wizard-next>Continue →</button></div>
<div class="form-actions" data-wizard-submit><button class="button" type="submit">Find crops for my field →</button><p data-submit-status role="status" aria-live="polite" hidden></p><span class="privacy-note">No account or personal contact details needed.</span></div></form></div></section>
<details class="container reference-coverage" id="reference-coverage"><summary>Explore covered examples and published crop guidance</summary><div class="reference-coverage-content"><h2>Where complete example information is available</h2>{coverage_table()}{profile_picker()}<p>These inputs illustrate published-reference comparisons. They are not measurements from your own field. Use well-drained soil for the examples. Crop guidance is checked for your selected state and season.</p><p>Punjab guidance now covers wheat, rice, barley, cotton, groundnut, pearl millet, soybean and maize. <a href="/sources">Review sources and coverage →</a></p></div></details>"""
