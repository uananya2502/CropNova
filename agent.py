"""CropNova intelligent-agent workflow and integration adapters."""

from __future__ import annotations

import importlib
from typing import Any, Iterable, Mapping

from csp_solver import solve_constraints
from explanations import build_evidence_package, build_explanations, follow_up_question
from knowledge_base.loader import load_knowledge
from knowledge_base.query import find_crop
from knowledge_base.retrieval import get_usable_facts
from knowledge_base.validator import validate_knowledge


RESULT_STATUSES = {
    "FEASIBLE_OPTIONS_FOUND",
    "MORE_INFORMATION_NEEDED",
    "NO_FEASIBLE_OPTION",
    "NO_SUPPORTED_KNOWLEDGE",
    "INVALID_INPUT",
    "SYSTEM_ERROR",
}

ALLOWED = {
    "season": {"kharif", "rabi", "zaid", "unknown"},
    "soil.texture": {"sandy", "loamy", "clayey", "other", "unknown"},
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

LIMITATIONS = [
    "CropNova is an educational decision-support prototype, not a guarantee of crop success.",
    "Only applicable facts explicitly marked verified may satisfy a hard constraint.",
    "The prototype does not provide pesticide prescriptions, fertilizer dosage, live weather, market prices, yield, or profit predictions.",
    "Consult a local agricultural extension professional before consequential decisions.",
]


def _text(value: Any, default: str = "unknown") -> str:
    if value is None or not str(value).strip():
        return default
    return str(value).strip()


def normalize_profile(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize either flat form fields or the shared nested profile contract."""

    region = raw.get("region") if isinstance(raw.get("region"), Mapping) else {}
    soil = raw.get("soil") if isinstance(raw.get("soil"), Mapping) else {}
    water = raw.get("water") if isinstance(raw.get("water"), Mapping) else {}
    ph_value = soil.get("ph", raw.get("soil_ph"))
    ph = None if ph_value is None or str(ph_value).strip().casefold() in {"", "unknown"} else float(ph_value)
    candidates = raw.get("candidate_ids", raw.get("candidates", []))
    if isinstance(candidates, str):
        candidates = [item.strip() for item in candidates.split(",") if item.strip()]
    return {
        "region": {
            "state": _text(region.get("state", raw.get("state")), ""),
            "district": _text(region.get("district", raw.get("district")), "") or None,
        },
        "season": _text(raw.get("season")).casefold(),
        "soil": {
            "texture": _text(soil.get("texture", raw.get("soil_texture"))).casefold(),
            "ph": ph,
            "fertility": _text(soil.get("fertility", raw.get("soil_fertility"))).casefold(),
        },
        "water": {
            "availability": _text(water.get("availability", raw.get("water_availability"))).casefold(),
            "irrigation": _text(water.get("irrigation", raw.get("irrigation"))).casefold(),
        },
        "objective": _text(raw.get("objective"), "find_suitable_crop").casefold(),
        "priority": _text(raw.get("priority"), "").casefold() or None,
        "candidate_ids": list(candidates) if isinstance(candidates, Iterable) else [],
    }


def validate_profile(profile: Mapping[str, Any]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    state = profile.get("region", {}).get("state")
    if not state:
        errors.append({"field": "state", "code": "REQUIRED", "message": "State or region is required."})
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
    if ph is not None and not 0 <= ph <= 14:
        errors.append({"field": "soil.ph", "code": "OUT_OF_RANGE", "message": "Soil pH must be between 0 and 14."})
    return errors


def _rule_adapter(profile: Mapping[str, Any], crops: list[dict[str, Any]]) -> dict[str, Any]:
    """Use the teammate rule engine when present, otherwise return a safe seed domain."""

    try:
        module = importlib.import_module("rule_engine")
        evaluator = getattr(module, "evaluate_rules")
    except (ImportError, AttributeError):
        return {
            "status": "not_available",
            "candidates": crops,
            "fired_rules": [],
            "warnings": [
                "Rule engine is not present yet; knowledge-base crops were used only as the CSP domain, not as recommendations."
            ],
            "missing_information": [],
        }
    result = evaluator(profile, crops)
    if not isinstance(result, Mapping):
        raise TypeError("Rule engine must return a mapping.")
    return dict(result)


def _candidate_records(knowledge: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Adapt knowledge-base crop/fact records to the shared CSP candidate contract."""

    candidates: list[dict[str, Any]] = []
    for crop in knowledge.get("crops", []):
        if not isinstance(crop, Mapping) or not crop.get("crop_id"):
            continue
        crop_id = str(crop["crop_id"])
        nested_facts = crop.get("facts", [])
        facts = (
            list(nested_facts)
            if isinstance(nested_facts, list) and nested_facts
            else get_usable_facts(dict(knowledge), crop_id=crop_id)
        )
        candidates.append(
            {
                **dict(crop),
                "candidate_id": crop_id,
                "name": crop.get("common_name", crop.get("name", crop_id)),
                "category": crop.get("crop_group", crop.get("category")),
                "verification_status": crop.get(
                    "status", crop.get("verification_status", "unknown")
                ),
                "facts": facts,
            }
        )
    return candidates


def _select_candidates(
    crops: list[dict[str, Any]], selected_ids: list[str], rule_result: Mapping[str, Any]
) -> list[dict[str, Any]]:
    knowledge_view = {"crops": crops}
    by_id = {str(crop.get("crop_id")): crop for crop in crops}
    if selected_ids:
        selected: list[dict[str, Any]] = []
        for item in selected_ids:
            found = find_crop(knowledge_view, str(item))
            crop = by_id.get(str(item)) or (by_id.get(str(found.get("crop_id"))) if found else None)
            if crop and crop not in selected:
                selected.append(crop)
        return selected
    candidates = rule_result.get("candidates", crops)
    resolved: list[dict[str, Any]] = []
    for item in candidates if isinstance(candidates, list) else crops:
        if isinstance(item, Mapping):
            resolved.append(dict(item))
        else:
            found = find_crop(knowledge_view, str(item))
            crop = by_id.get(str(item)) or (by_id.get(str(found.get("crop_id"))) if found else None)
            if crop:
                resolved.append(crop)
    return resolved


def _knowledge_summary(knowledge: Mapping[str, Any]) -> dict[str, Any]:
    crops = [item for item in knowledge.get("crops", []) if isinstance(item, Mapping)]
    top_level_facts = knowledge.get("facts", [])
    if isinstance(top_level_facts, list) and top_level_facts:
        facts = [fact for fact in top_level_facts if isinstance(fact, Mapping)]
    else:
        facts = [
            fact
            for crop in crops
            for fact in crop.get("facts", [])
            if isinstance(fact, Mapping)
        ]
    statuses: dict[str, int] = {}
    for fact in facts:
        key = str(fact.get("verification_status", "unknown")).casefold()
        statuses[key] = statuses.get(key, 0) + 1
    return {
        "total_crops": len(crops),
        "total_facts": len(facts),
        "verified_facts": sum(
            statuses.get(key, 0)
            for key in ("verified", "verified_general", "verified_context_specific")
        ),
        "usable_facts": len(get_usable_facts(dict(knowledge))),
        "fact_status_counts": statuses,
        "total_sources": len(knowledge.get("sources", [])),
        "dataset_status": knowledge.get("metadata", {}).get("status", "unknown"),
    }


def _resolve_evidence_sources(
    knowledge: Mapping[str, Any], source_ids: Iterable[str]
) -> list[dict[str, Any]]:
    wanted = set(source_ids)
    return [
        dict(source)
        for source in knowledge.get("sources", [])
        if isinstance(source, Mapping) and source.get("source_id") in wanted
    ]


def _missing(csp_result: Mapping[str, Any]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for candidate in csp_result.get("unknown_candidates", []):
        for outcome in candidate.get("unknown_constraints", []):
            fields = outcome.get("missing_fields") or [""]
            for field in fields:
                key = (field, outcome.get("reason_code", "UNKNOWN"))
                if key not in seen:
                    result.append(
                        {
                            "field": field,
                            "reason_code": outcome.get("reason_code", "UNKNOWN"),
                            "message": outcome.get("reason", "Information is missing."),
                        }
                    )
                    seen.add(key)
    return result


def _status(csp_result: Mapping[str, Any], missing: list[dict[str, str]]) -> str:
    if csp_result.get("feasible_candidates"):
        return "FEASIBLE_OPTIONS_FOUND"
    if csp_result.get("unknown_candidates"):
        only_knowledge_missing = missing and all(
            item["reason_code"]
            in {
                "MISSING_VERIFIED_FACT",
                "CONFLICTING_VERIFIED_FACTS",
                "INCOMPATIBLE_VERIFIED_FACT",
            }
            for item in missing
        )
        return "NO_SUPPORTED_KNOWLEDGE" if only_knowledge_missing else "MORE_INFORMATION_NEEDED"
    return "NO_FEASIBLE_OPTION"


def run_assessment(user_profile: Mapping[str, Any]) -> dict[str, Any]:
    """Validate, retrieve, invoke rules/CSP, and assemble a safe final report."""

    try:
        profile = normalize_profile(user_profile)
    except (TypeError, ValueError) as error:
        return {
            "status": "INVALID_INPUT",
            "errors": [{"field": "soil.ph", "code": "INVALID_NUMBER", "message": str(error)}],
            "warnings": [],
            "limitations": LIMITATIONS,
        }
    errors = validate_profile(profile)
    if errors:
        return {
            "status": "INVALID_INPUT",
            "profile": profile,
            "errors": errors,
            "warnings": [],
            "limitations": LIMITATIONS,
        }

    try:
        knowledge = load_knowledge()
        knowledge_errors = validate_knowledge(knowledge)
        if knowledge_errors:
            raise ValueError("Knowledge validation failed: " + "; ".join(knowledge_errors))
        crops = _candidate_records(knowledge)
        if not crops:
            return {
                "status": "NO_SUPPORTED_KNOWLEDGE",
                "profile": profile,
                "errors": [],
                "warnings": ["The knowledge base contains no crop records."],
                "missing_information": [],
                "follow_up_questions": [],
                "limitations": LIMITATIONS,
            }
        rule_result = _rule_adapter(profile, crops)
        candidates = _select_candidates(crops, profile["candidate_ids"], rule_result)
        if not candidates:
            return {
                "status": "NO_SUPPORTED_KNOWLEDGE",
                "profile": profile,
                "errors": [],
                "warnings": ["No requested candidates are present in the knowledge base."],
                "missing_information": [],
                "follow_up_questions": [],
                "limitations": LIMITATIONS,
            }
        csp_result = solve_constraints(candidates, profile)
        missing = _missing(csp_result)
        status = _status(csp_result, missing)
        report = {
            "status": status,
            "profile": profile,
            "knowledge_version": knowledge.get("metadata", {}).get("version", "unknown"),
            "knowledge_summary": _knowledge_summary(knowledge),
            "rule_status": rule_result.get("status", "unknown"),
            "rule_trace": rule_result.get("fired_rules", []),
            "csp_result": csp_result,
            "feasible_options": csp_result["feasible_candidates"],
            "rejected_options": csp_result["rejected_candidates"],
            "unknown_options": csp_result["unknown_candidates"],
            "warnings": list(rule_result.get("warnings", [])),
            "missing_information": missing,
            "follow_up_questions": [
                follow_up_question(item["field"])
                for item in missing
                if item["field"] and item["reason_code"] == "MISSING_USER_INPUT"
            ],
            "errors": [],
            "limitations": LIMITATIONS,
        }
        report["explanations"] = build_explanations(status, csp_result)
        report["evidence_package"] = build_evidence_package(report)
        report["evidence"] = _resolve_evidence_sources(
            knowledge, report["evidence_package"]["source_ids_used"]
        )
        return report
    except Exception as error:  # Safe module boundary: never return a fake success.
        return {
            "status": "SYSTEM_ERROR",
            "profile": profile,
            "errors": [{"code": "MODULE_FAILURE", "message": str(error)}],
            "warnings": [],
            "limitations": LIMITATIONS,
        }


__all__ = ["RESULT_STATUSES", "normalize_profile", "validate_profile", "run_assessment"]

