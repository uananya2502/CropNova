"""Convert form values to a consistent profile, then check allowed values.

Missing measurements stay None: guessing them could create a false match.
"""

from __future__ import annotations
import math
from typing import Any, Mapping

ALLOWED = {
    "season": {"kharif", "rabi", "zaid", "unknown"},
    "soil.texture": {
        "sandy_loam",
        "clay_loam",
        "silt_loam",
        "silty_clay_loam",
        "sandy",
        "loamy",
        "clayey",
        "other",
        "unknown",
    },
    "soil.fertility": {"low", "moderate", "high", "unknown"},
    "water.availability": {"low", "moderate", "high", "unknown"},
    "water.irrigation": {"available", "rainfed", "limited", "unknown"},
    "objective": {
        "find_suitable_crop",
        "conserve_water",
        "soil_improvement",
        "compare_alternatives",
    },
}


def _text(value: Any, default: str = "unknown") -> str:
    """Read a short label without turning objects into misleading text."""
    if value is not None and not isinstance(value, str):
        raise TypeError("Profile labels must be text.")
    text = (value or "").strip()
    if len(text) > 160:
        raise ValueError("Keep each field label or location within 160 characters.")
    return text or default


def _number(value, label):
    """Blank means missing; a boolean, object or overflowing number is invalid."""
    if value is None:
        return None
    if isinstance(value, str) and value.strip().casefold() in {"", "unknown"}:
        return None
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError(f"{label} must be a number.")
    try:
        return float(value)
    except (ValueError, OverflowError):
        raise ValueError(f"{label} must be a valid number.") from None


def normalize_profile(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Accept a flat form or nested API profile without silently coercing objects."""
    if not isinstance(raw, Mapping):
        raise TypeError("Farm profile must be an object.")
    nested = {}
    for key in ("region", "soil", "water"):
        value = raw.get(key, {})
        if not isinstance(value, Mapping):
            raise TypeError(f"{key} must be an object.")
        nested[key] = value
    (region, soil, water) = (nested[key] for key in ("region", "soil", "water"))

    # Form inputs are flat strings; API inputs can already be nested objects.
    text = _text
    ph = _number(soil.get("ph", raw.get("soil_ph")), "Soil pH")
    budget = _number(water.get("budget_mm", raw.get("water_budget_mm")), "Water budget")
    candidates = raw.get("candidate_ids", raw.get("candidates", []))
    if isinstance(candidates, str):
        candidates = [item.strip() for item in candidates.split(",") if item.strip()]
    if not isinstance(candidates, (list, tuple)) or any(
        (not isinstance(c, str) for c in candidates)
    ):
        raise TypeError("Candidate IDs must be a list of crop names or IDs.")
    if len(candidates) > 40 or any(len(c) > 160 for c in candidates):
        raise ValueError("Choose a shorter list of crop names or IDs.")
    candidates = [crop.strip() for crop in candidates]
    return {
        "region": {
            "country": text(region.get("country", raw.get("country")), "India"),
            "state": text(region.get("state", raw.get("state")), ""),
            "district": text(region.get("district", raw.get("district")), "") or None,
        },
        "season": text(raw.get("season")).casefold(),
        "soil": {
            "texture": text(soil.get("texture", raw.get("soil_texture"))).casefold(),
            "ph": ph,
            "drainage": text(soil.get("drainage", raw.get("soil_drainage"))).casefold(),
            "fertility": text(soil.get("fertility", raw.get("soil_fertility"))).casefold(),
        },
        "water": {
            "budget_mm": budget,
            "basis": text(water.get("basis", raw.get("water_basis")), "seasonal_crop_water"),
            "availability": text(
                water.get("availability", raw.get("water_availability"))
            ).casefold(),
            "irrigation": text(water.get("irrigation", raw.get("irrigation"))).casefold(),
        },
        "rainfall": {
            "level": text(raw.get("rainfall", {}).get("level", raw.get("rainfall_level")), "unknown").casefold()
                if isinstance(raw.get("rainfall", {}), Mapping) else "invalid",
            "mm": _number(raw.get("rainfall", {}).get("mm", raw.get("rainfall_mm")), "Rainfall")
                if isinstance(raw.get("rainfall", {}), Mapping) else None,
        },
        "language": text(raw.get("language"), "en"),
        "multilingual_view": text(raw.get("multilingual_view"), "no"),
        "objective": text(raw.get("objective"), "find_suitable_crop").casefold(),
        "priority": text(raw.get("priority"), "").casefold() or None,
        "candidate_ids": list(dict.fromkeys(candidates)),
    }


def validate_profile(profile: Mapping[str, Any]) -> list[dict[str, str]]:
    """Validate the normalized user profile."""
    errors: list[dict[str, str]] = []
    rain = profile.get("rainfall", {})
    if rain.get("level", "unknown") not in {"unknown", "none", "low", "medium", "high"}:
        errors.append({"field":"rainfall_level", "code":"INVALID", "message":"Choose one of the four rain options."})
    mm = rain.get("mm")
    if mm is not None and (not math.isfinite(mm) or not 0 <= mm <= 10000):
        errors.append({"field":"rainfall_mm", "code":"INVALID", "message":"Rainfall must be between 0 and 10,000 mm."})
    if profile.get("language", "en") not in {"en", "hi", "pa"}:
        errors.append({"field":"language", "code":"INVALID", "message":"Choose English, Hindi or Punjabi."})
    if profile.get("multilingual_view", "no") not in {"yes", "no"}:
        errors.append({"field":"multilingual_view", "code":"INVALID", "message":"Choose a language view."})
    state = profile.get("region", {}).get("state")
    if not state:
        errors.append(
            {"field": "state", "code": "REQUIRED", "message": "State or region is required."}
        )
    # Optional fields may stay unknown. They do not become guessed measurements.
    checks = {
        "season": profile.get("season"),
        "soil.texture": profile.get("soil", {}).get("texture"),
        "soil.fertility": profile.get("soil", {}).get("fertility"),
        "water.availability": profile.get("water", {}).get("availability"),
        "water.irrigation": profile.get("water", {}).get("irrigation"),
        "objective": profile.get("objective"),
    }
    for field, value in checks.items():
        if value not in ALLOWED[field]:
            errors.append(
                {
                    "field": field,
                    "code": "UNSUPPORTED_VALUE",
                    "message": f"Choose a supported value for {field.replace('.', ' ')}.",
                }
            )
    ph = profile.get("soil", {}).get("ph")
    if ph is not None and (not 0 <= ph <= 14):
        errors.append(
            {
                "field": "soil.ph",
                "code": "OUT_OF_RANGE",
                "message": "Soil pH must be between 0 and 14.",
            }
        )
    budget = profile.get("water", {}).get("budget_mm")
    if budget is not None and (not math.isfinite(budget) or not 0 <= budget <= 10000):
        errors.append(
            {
                "field": "water.budget_mm",
                "code": "OUT_OF_RANGE",
                "message": "Water budget must be a finite depth from 0 to 10000 mm.",
            }
        )
    if profile.get("water", {}).get("basis") not in {
        "seasonal_crop_water",
        "supplemental_irrigation",
    }:
        errors.append(
            {
                "field": "water.basis",
                "code": "UNSUPPORTED_VALUE",
                "message": "Choose the water measurement basis.",
            }
        )
    if profile.get("soil", {}).get("drainage") not in {"unknown", "well_drained", "poorly_drained"}:
        errors.append(
            {
                "field": "soil.drainage",
                "code": "UNSUPPORTED_VALUE",
                "message": "Choose a supported drainage value.",
            }
        )
    if profile.get("priority") not in {None, "water", "soil-season", "resources", "compare"}:
        errors.append(
            {
                "field": "priority",
                "code": "UNSUPPORTED_VALUE",
                "message": "Choose a supported priority.",
            }
        )
    return errors
