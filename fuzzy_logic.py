"""Explain gradual pH/water reference alignment with zero-order Sugeno rules.

This optional index never updates a CSP status or ranks rejected crops. The
membership settings are engineering choices, not validated agronomic limits.
Everything needed to follow the calculation is returned in a small trace.
"""

import math
from evidence import assessment_facts, numeric_range

# Consequents are points on an alignment index, never probabilities of success.
CONSEQUENTS = {"limited": 20.0, "moderate": 55.0, "close": 85.0}
RULES = (
    ("aligned", "covered", "close"),
    ("aligned", "partial", "moderate"),
    ("aligned", "low", "limited"),
    ("nearby", "covered", "moderate"),
    ("nearby", "partial", "limited"),
    ("nearby", "low", "limited"),
    ("distant", "covered", "limited"),
    ("distant", "partial", "limited"),
    ("distant", "low", "limited"),
)
NOTE = (
    "This index describes pH and water alignment with the recorded references. "
    "It is not a probability of crop success and does not change the crop findings. "
    "Its membership settings need local expert calibration before agricultural use."
)


def rising(value, low, high):
    """Right shoulder: 0 below low, 1 above high, linear in between."""
    return max(0.0, min(1.0, (value - low) / (high - low)))


def triangle(value, left, peak, right):
    return max(0.0, min((value - left) / (peak - left), (right - value) / (right - peak)))


def memberships(ph_distance, water_ratio):
    """Distance is measured in pH-range widths; water is budget / upper reference."""
    return {
        "ph": {
            "aligned": 1.0 - rising(ph_distance, 0.0, 0.25),
            "nearby": triangle(ph_distance, 0.0, 0.25, 0.75),
            "distant": rising(ph_distance, 0.25, 0.75),
        },
        "water": {
            "low": 1.0 - rising(water_ratio, 0.5, 0.8),
            "partial": triangle(water_ratio, 0.5, 0.8, 1.0),
            "covered": rising(water_ratio, 0.8, 1.0),
        },
    }


def infer_alignment(ph_distance, water_ratio):
    """AND uses min; zero-order Sugeno output is a weighted average of constants."""
    if not all(math.isfinite(x) and x >= 0 for x in (ph_distance, water_ratio)):
        raise ValueError("Alignment inputs must be finite and non-negative.")
    degrees = memberships(ph_distance, water_ratio)
    fired = []
    for number, (ph_set, water_set, conclusion) in enumerate(RULES, 1):
        strength = min(degrees["ph"][ph_set], degrees["water"][water_set])
        if strength > 0:
            fired.append(
                {
                    "rule_id": f"FUZZY_{number:02d}",
                    "ph_set": ph_set,
                    "water_set": water_set,
                    "conclusion": conclusion,
                    "strength": strength,
                    "consequent": CONSEQUENTS[conclusion],
                }
            )
    total = sum(rule["strength"] for rule in fired)
    score = sum(rule["strength"] * rule["consequent"] for rule in fired) / total
    return {
        "score": round(score, 1),
        "memberships": degrees,
        "fired_rules": fired,
        "method": "zero_order_sugeno_min_and_weighted_average",
    }


def supported_range(outcome, facts, crop_id, properties):
    """Require the exact evidence behind this check, not any similarly named fact."""
    ids = set(outcome.get("fact_ids", []))
    selected = [
        fact
        for fact in facts
        if fact["fact_id"] in ids
        and fact.get("crop_id") in {crop_id, "all"}
        and fact.get("property") in properties
    ]
    if not ids or {fact["fact_id"] for fact in selected} != ids:
        raise ValueError("Applicable numeric evidence is missing.")
    ranges = {numeric_range(fact["value"]) for fact in selected}
    if len(ranges) != 1:
        raise ValueError("The applicable numeric references disagree.")
    return ranges.pop(), selected


def analyze_crop(candidate, report, facts):
    """Only soften supported numeric comparisons; never soften a known violation."""
    crop_id = candidate["candidate_id"]
    result = {
        "crop_id": crop_id,
        "name": candidate["name"],
        "score": None,
        "status": "not_ready",
        "reason": "Comparable pH and water evidence is needed.",
    }
    if candidate["failed_constraints"]:
        return {
            **result,
            "status": "blocked",
            "reason": "Review the conditions that need attention before using an alignment index.",
        }
    outcomes = {
        row["constraint_id"]: row
        for key in ("satisfied_constraints", "unknown_constraints")
        for row in candidate[key]
    }
    # A good numeric profile must not hide missing season or soil knowledge.
    if any(
        outcomes.get(key, {}).get("status") != "satisfied"
        for key in ("CONSTRAINT001", "CONSTRAINT003")
    ):
        return {**result, "reason": "Season and soil checks need to be established first."}
    try:
        ph_check, water_check = (outcomes[key] for key in ("CONSTRAINT004", "CONSTRAINT002"))
        (ph_low, ph_high), ph_facts = supported_range(
            ph_check, facts, crop_id, {"soil_ph_range", "ph_range"}
        )
        (_, water_high), water_facts = supported_range(
            water_check, facts, crop_id, {"water_screening_range_mm"}
        )
        profile = report["profile"]
        ph, budget = profile["soil"]["ph"], profile["water"]["budget_mm"]
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            for value in (ph, budget)
        ):
            raise ValueError("Measurements are missing.")
        if water_high <= 0 or budget < 0 or not 0 <= ph <= 14:
            raise ValueError("Measurements cannot be compared.")
        if any(
            fact.get("unit") != "mm" or fact.get("water_basis") != profile["water"]["basis"]
            for fact in water_facts
        ):
            raise ValueError("Water measurement bases differ.")
        distance = max(ph_low - ph, 0, ph - ph_high) / max(ph_high - ph_low, 1.0)
        trace = infer_alignment(distance, budget / water_high)
    except (ValueError, TypeError, KeyError, OverflowError):
        return result
    source_ids = list(
        dict.fromkeys(source for fact in ph_facts + water_facts for source in fact["source_ids"])
    )
    return {
        **result,
        **trace,
        "status": "available",
        "reason": "Computed from the recorded pH and water references.",
        "inputs": {
            "ph_distance": distance,
            "water_ratio": budget / water_high,
            "ph": ph,
            "ph_range": [ph_low, ph_high],
            "water_budget_mm": budget,
            "water_reference_upper_mm": water_high,
        },
        "fact_ids": [fact["fact_id"] for fact in ph_facts + water_facts],
        "source_ids": source_ids,
        "needs_review": candidate["status"] != "feasible",
    }


def analyze_assessment(report):
    """Return a separate diagnostic. Do not mutate the profile, facts or decisions."""
    facts = assessment_facts(report)
    candidates = [
        crop
        for group in ("feasible_candidates", "unknown_candidates", "rejected_candidates")
        for crop in report.get("csp_result", {}).get(group, [])
    ]
    return {
        "method": "zero_order_sugeno",
        "note": NOTE,
        "candidates": [analyze_crop(crop, report, facts) for crop in candidates],
    }
