"""Turn the engine's evidence into plain-language website and report content.

This module does not make crop decisions. It explains the decisions already
recorded in the assessment, using the same input values and source references.
"""

import re
from datetime import datetime
from zoneinfo import ZoneInfo

CHECK_NAMES = {
    "CONSTRAINT001": "Growing season",
    "CONSTRAINT002": "Water supply",
    "CONSTRAINT003": "Soil texture",
    "CONSTRAINT004": "Soil pH",
}
STATUS_TITLES = {
    "FEASIBLE_OPTIONS_FOUND": "Options that match your conditions",
    "MORE_INFORMATION_NEEDED": "A few details need a closer look",
    "NO_FEASIBLE_OPTION": "Some conditions need attention",
    "NO_SUPPORTED_KNOWLEDGE": "More local guidance is needed",
    "INVALID_INPUT": "Please check your farm details",
    "SYSTEM_ERROR": "We could not complete this assessment",
}


def ordered_candidates(candidates):
    """Decision group first, then evidence matches; names break display ties."""
    order = {'feasible': 0, 'unknown': 1, 'rejected': 2}
    return sorted(candidates, key=lambda crop: (
        order.get(crop['status'], 3), -crop['matched'], crop['name'].casefold()))


def readable(value):
    """Show a friendly measurement or label without changing its meaning."""
    if value is None or str(value).lower() in {"", "unknown", "none"}:
        return "Not provided"
    if isinstance(value, float):
        return f"{value:g}"
    return str(value).replace("_", " ").capitalize()


def explanation_text(text):
    """Use everyday equivalents for technical labels in generated wording.

    Measurements, crop names, decisions and qualifications are left intact.
    """
    for pattern, replacement in [
        (r"\bresearch dataset(?: screening)?\b", "published agricultural guidance"),
        (r"\bCSP\b", "crop checks"),
        (r"\brule engine\b", "assessment checks"),
        (r"\bconstraints\b", "conditions"),
    ]:
        text = re.sub(pattern, replacement, str(text), flags=re.IGNORECASE)
    return text


def profile_fields(profile):
    region, soil, water = (profile.get(key, {}) for key in ("region", "soil", "water"))
    depth = water.get("budget_mm")
    fields = [
        ("State / region", readable(region.get("state"))),
        ("District / town", readable(region.get("district"))),
        ("Growing season", readable(profile.get("season"))),
        ("Soil texture", readable(soil.get("texture"))),
        ("Soil pH", readable(soil.get("ph"))),
        ("Field drainage", readable(soil.get("drainage"))),
        ("Water budget", f"{depth:g} mm" if isinstance(depth, (int, float)) else "Not provided"),
        (
            "Water measurement",
            (
                "Supplemental irrigation only"
                if water.get("basis") == "supplemental_irrigation"
                else "Total seasonal crop-water supply"
            ),
        ),
    ]

    rain = profile.get("rainfall", {})
    if rain.get("level") not in {None, "unknown"}:
        from farmer_language import RAIN_LABELS
        fields.append(("Observed rain this season", RAIN_LABELS.get(rain["level"], "Not provided")))
    if rain.get("mm") is not None:
        fields.append(("Measured seasonal rainfall", f'{rain["mm"]:g} mm'))
    if profile.get("water", {}).get("irrigation") not in {None, "unknown"}:
        fields.append(("Field water source", readable(profile["water"]["irrigation"])))
    return fields


def reference_text(facts, check_id):
    descriptions = []
    for fact in facts:
        value = fact.get("value")
        if value is None:
            continue
        if check_id in {"CONSTRAINT002", "CONSTRAINT004"}:
            if isinstance(value, dict):
                value = [value.get("min"), value.get("max")]
            if isinstance(value, list) and len(value) == 2:
                text = f"{value[0]:g}–{value[1]:g}"
                if check_id == "CONSTRAINT002":
                    text += " mm " + (
                        "supplemental irrigation"
                        if fact.get("water_basis") == "supplemental_irrigation"
                        else "seasonal crop-water use"
                    )
                else:
                    text += " preferred pH" if fact.get("range_kind") == "preferred" else " pH"
                descriptions.append(text)
        else:
            items = value if isinstance(value, list) else [value]
            descriptions.append(", ".join(readable(item) for item in items))
    return "; ".join(dict.fromkeys(descriptions)) or "No applicable published reference"


def explanation_for(check, entered, reference):
    """Translate known result reasons into actionable language, not engine jargon."""
    code, state = check.get("reason_code"), check.get("status")
    messages = {
        "MISSING_USER_INPUT": (
            "This check needs a value that was not provided.",
            "Add the missing measurement or field detail and reassess.",
        ),
        "MISSING_VERIFIED_FACT": (
            "We do not yet have enough published guidance for this crop and location.",
            "Ask a local agricultural adviser for guidance specific to your field.",
        ),
        "CONFLICTING_VERIFIED_FACTS": (
            "The available references disagree, so we have left this check open.",
            "Have a local adviser review the conflicting references.",
        ),
        "NON_EXHAUSTIVE_EVIDENCE": (
            "The source lists preferred or documented conditions. It does not establish whether your different conditions are suitable.",
            "Check local guidance before ruling this crop in or out.",
        ),
        "OUTSIDE_PREFERRED_RANGE": (
            f"Your pH is outside {reference}. This is a preferred range, not a limit beyond which the crop cannot grow.",
            "Review the measured pH with a local soil adviser.",
        ),
        "INCOMPATIBLE_WATER_BASIS": (
            "Your water measurement and this crop reference describe different things, so they cannot be compared.",
            "Use a water estimate with the same measurement basis as the source.",
        ),
        "INCOMPATIBLE_WATER_UNITS": (
            "The water measurements use different units or categories.",
            "Confirm the water depth in millimetres and its measurement basis.",
        ),
        "WATER_REFERENCE_SHORTFALL": (
            f"Your budget of {entered} is below the published reference of {reference}. This indicates a shortfall in this comparison, not a prediction of crop failure.",
            "Obtain a local crop-water estimate before deciding whether the available supply is adequate.",
        ),
        "LOCAL_WATER_ESTIMATE_REQUIRED": (
            f"Your budget falls within {reference}. Local conditions determine where the actual requirement falls within that range.",
            "Confirm a local crop-water estimate, effective rainfall and usable soil moisture.",
        ),
        "WATER_REFERENCE_COVERED": (
            f"Your budget of {entered} covers the upper end of {reference}. Water timing, losses and local requirements still need confirmation.",
            None,
        ),
        "DRAINAGE_MISMATCH": (
            "The source calls for well-drained soil, while your field is described as poorly drained.",
            "Ask a local adviser whether field drainage is adequate for this crop.",
        ),
    }
    if code in messages:
        return messages[code]
    if state == "satisfied":
        return f"Your entry, {entered}, matches the published reference: {reference}.", None
    if state == "violated":
        return (
            f"Your entry, {entered}, does not meet the documented conditions: {reference}.",
            "Review this condition before selecting the crop.",
        )
    return (
        "The available information does not support a clear answer for this check.",
        "Confirm the measurement and seek relevant local guidance.",
    )


def build_summary(report):
    profile = report.get("profile", {})
    sources = report.get("evidence", [])
    source_map = {source["source_id"]: source for source in sources}
    facts = {fact["fact_id"]: fact for fact in report.get("evidence_package", {}).get("facts", [])}
    fields = dict(profile_fields(profile))
    actual = {
        "CONSTRAINT001": fields["Growing season"],
        "CONSTRAINT002": fields["Water budget"],
        "CONSTRAINT003": fields["Soil texture"],
        "CONSTRAINT004": fields["Soil pH"],
    }
    candidates = []
    csp = report.get("csp_result", {})
    for group in ("feasible_candidates", "unknown_candidates", "rejected_candidates"):
        for candidate in csp.get(group, []):
            checks, actions = [], []
            outcomes = sum(
                (
                    candidate.get(key, [])
                    for key in (
                        "satisfied_constraints",
                        "failed_constraints",
                        "unknown_constraints",
                    )
                ),
                [],
            )
            for outcome in sorted(outcomes, key=lambda item: item["constraint_id"]):
                identity = outcome["constraint_id"]
                supporting = [facts[fid] for fid in outcome.get("fact_ids", []) if fid in facts]
                reference = reference_text(supporting, identity)
                if outcome.get("reason_code") == "MISSING_USER_INPUT" and not supporting:
                    reference = "Not compared until this detail is provided"
                entered = actual.get(identity, "Not provided")
                reason, action = explanation_for(outcome, entered, reference)
                if outcome.get(
                    "reason_code"
                ) == "MISSING_USER_INPUT" and "soil.drainage" in outcome.get("missing_fields", []):
                    reason, action = (
                        "This soil reference requires good drainage, but your field drainage is not provided.",
                        "Confirm whether the field is well drained.",
                    )
                if action:
                    actions.append(action)
                checks.append(
                    {
                        "name": CHECK_NAMES.get(identity, "Field condition"),
                        "reason_code": outcome.get("reason_code", ""),
                        "status": outcome["status"],
                        "entered": entered,
                        "reference": reference,
                        "reason": reason,
                        "fact_ids": list(outcome.get("fact_ids", [])),
                        "sources": [
                            source_map[sid]
                            for sid in outcome.get("source_ids", [])
                            if sid in source_map
                        ],
                    }
                )
            candidates.append(
                {
                    "id": candidate["candidate_id"],
                    "name": candidate["name"].title(),
                    "status": candidate["status"],
                    "checks": checks,
                    "matched": sum(check["status"] == "satisfied" for check in checks),
                    "actions": list(dict.fromkeys(actions)),
                    "limitations": list(dict.fromkeys(
                        limitation for check in checks for fid in check["fact_ids"]
                        for limitation in facts.get(fid, {}).get("limitations", [])
                    )),
                    "label": {
                        "feasible": "Matches checked conditions",
                        "unknown": "Needs more information",
                        "rejected": "Needs attention",
                    }.get(candidate["status"], "Needs review"),
                }
            )
    candidates = ordered_candidates(candidates)
    questions = list(dict.fromkeys(report.get("follow_up_questions", [])))
    region = profile.get("region", {})
    return {
        "title": STATUS_TITLES.get(report.get("status"), "Your farm assessment"),
        "location": ", ".join(str(v) for v in (region.get("district"), region.get("state")) if v)
        or "Your field",
        "created": report.get("created_at") or datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(),
        "profile": profile_fields(profile),
        "candidates": candidates,
        "language": profile.get("language", "en"),
        "sources": sources,
        "questions": questions,
        "matches": sum(c["status"] == "feasible" for c in candidates),
        "reviews": sum(c["status"] == "unknown" for c in candidates),
        "attention": sum(c["status"] == "rejected" for c in candidates),
        "note": "This is a preliminary comparison with published guidance. Crop variety, weather, field conditions and local advice still matter. A match is not a guarantee of crop success.",
        "water_note": "Seasonal crop-water use and supplemental irrigation are different measurements. These references do not provide an irrigation schedule or account for every water loss.",
    }
