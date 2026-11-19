"""Synthetic classroom fixtures. These are not agricultural recommendations."""


def demo_knowledge():
    crops, facts = [], []
    specifications = [
        ("wheat", "Wheat", "rabi", "low", "loamy", [6, 8]),
        ("rice", "Rice", "kharif", "high", "clayey", [5.5, 7.5]),
        ("maize", "Maize", "rabi", "moderate", "loamy", [6.5, 7.5]),
        ("chickpea", "Chickpea", "rabi", "low", "sandy", [6, 8]),
    ]
    for crop_id, name, season, water, soil, ph in specifications:
        crop_facts = []
        for prop, category, value in [
            ("growing_season", "season", season),
            ("water_requirement", "water", water),
            ("soil_texture", "soil", soil),
            ("soil_ph_range", "soil", ph),
        ]:
            fact = dict(
                fact_id=f"{crop_id}-{prop}",
                crop_id=crop_id,
                property=prop,
                category=category,
                statement="Synthetic requirement for illustrative algorithm evaluation only.",
                value=value,
                unit=None,
                verification_status="verified_context_specific",
                source_ids=["SYNTHETIC_SOURCE"],
                applicability={"state": "Haryana"},
                confidence="high",
                notes="Verified fixture consistency only; not an agricultural fact.",
            )
            facts.append(fact)
            crop_facts.append(fact["fact_id"])
        crops.append(
            dict(
                crop_id=crop_id,
                common_name=name,
                crop_group="pulse" if crop_id == "chickpea" else "cereal",
                scientific_name={
                    "wheat": "Triticum aestivum",
                    "rice": "Oryza sativa",
                    "maize": "Zea mays",
                    "chickpea": "Cicer arietinum",
                }[crop_id],
                status="active_prototype",
                fact_ids=crop_facts,
                source_ids=["SYNTHETIC_SOURCE"],
            )
        )
    return dict(
        metadata={"version": "classroom-1", "status": "synthetic_fixture"},
        crops=crops,
        facts=facts,
        sources=[
            dict(
                source_id="SYNTHETIC_SOURCE",
                title="Synthetic requirements — not agricultural evidence",
                url="https://example.test/classroom-fixtures",
                review_status="reviewed_for_inclusion",
            )
        ],
    )


BASE = dict(
    mode="demo",
    state="Haryana",
    season="rabi",
    soil_texture="loamy",
    soil_ph="7",
    water_availability="moderate",
    soil_fertility="unknown",
    irrigation="unknown",
    objective="find_suitable_crop",
)
PRESETS = {
    "match": ("1. Find feasible options", BASE),
    "water": ("2. Show water rejection", {**BASE, "water_availability": "low"}),
    "reject": ("3. Reject every candidate", {**BASE, "soil_ph": "9"}),
    "unknown": ("4. Ask for missing information", {**BASE, "season": "unknown"}),
    "research": ("5. Inspect research knowledge", {**BASE, "mode": "real"}),
}

# Published-reference examples: choose one crop to keep regional and water bases explicit.
for key, crop, state, season, texture, ph, water, basis in [
    ("wheat", "wheat", "Haryana", "rabi", "loamy", "7", "650", "seasonal_crop_water"),
    ("rice", "rice", "Haryana", "kharif", "clayey", "6", "700", "seasonal_crop_water"),
    ("chickpea", "chickpea", "Haryana", "rabi", "loamy", "7", "150", "supplemental_irrigation"),
    ("maize", "maize", "Rajasthan", "kharif", "loamy", "7", "800", "seasonal_crop_water"),
]:
    PRESETS["reference-" + key] = (
        "Published reference: " + crop.title(),
        {
            **BASE,
            "mode": "real",
            "state": state,
            "season": season,
            "soil_texture": texture,
            "soil_ph": ph,
            "water_budget_mm": water,
            "water_basis": basis,
            "water_availability": "unknown",
            "soil_drainage": "well_drained",
            "candidate_ids": [crop],
        },
    )
