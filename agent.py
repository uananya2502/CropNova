"""CropNova intelligent-agent workflow and integration adapters."""

from __future__ import annotations
import importlib
import logging
from typing import Any, Iterable, Mapping
from csp_solver import solve_constraints
from fuzzy_logic import analyze_assessment
from preparation_planner import plan_assessment
from profile_validation import normalize_profile, validate_profile
from explanations import build_evidence_package, build_explanations, follow_up_question
from knowledge_base.loader import load_knowledge
from knowledge_base.coverage import knowledge_coverage
from evidence import scope_matches
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
LIMITATIONS = [
    "CropNova is an educational decision-support prototype, not a guarantee of crop success.",
    "Only applicable facts explicitly marked verified may satisfy a hard constraint.",
    "The prototype does not provide pesticide prescriptions, fertilizer dosage, live weather, market prices, yield, or profit predictions.",
    "Consult a local agricultural extension professional before consequential decisions.",
]


def _rule_adapter(profile: Mapping[str, Any], crops: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Connect the Agent to the Rule Engine.

    The Rule Engine is evaluated independently for each
    crop using that crop's usable verified facts.
    """
    try:
        module = importlib.import_module("rule_engine")
        evaluator = getattr(module, "evaluate_rules")
    except (ImportError, AttributeError):
        return {
            "status": "not_available",
            "candidates": crops,
            "fired_rules": [],
            "rule_results": [],
            "warnings": [
                "Rule engine is not available; knowledge-base candidates were passed to the CSP."
            ],
            "missing_information": [],
        }
    rule_results: list[dict[str, Any]] = []
    fired_rules: list[dict[str, Any]] = []
    warnings: list[str] = []
    missing_information: list[dict[str, Any]] = []
    for crop in crops:
        crop_id = str(crop.get("crop_id", "")).strip()
        if not crop_id:
            continue
        crop_facts = crop.get("facts", [])
        if not isinstance(crop_facts, list):
            crop_facts = []
        # A copy prevents one crop from changing another crop's assessment.
        rule_profile = dict(profile)
        rule_profile["crop_id"] = crop_id
        evaluation = evaluator(rule_profile, crop_facts)
        if hasattr(evaluation, "to_dict"):
            evaluation_dict = evaluation.to_dict()
        elif isinstance(evaluation, Mapping):
            evaluation_dict = dict(evaluation)
        else:
            raise TypeError("Rule engine must return RuleEvaluation or a mapping.")
        results = evaluation_dict.get("results", [])
        crop_trace = {"crop_id": crop_id, "results": results}
        rule_results.append(crop_trace)
        for result in results:
            if not isinstance(result, Mapping):
                continue
            status = result.get("status")
            rule_id = result.get("rule_id")
            if status == "fired":
                fired_rules.append(
                    {
                        "crop_id": crop_id,
                        "rule_id": rule_id,
                        "status": status,
                        "conclusion": result.get("conclusion", ""),
                        "explanation": result.get("explanation", ""),
                        "fact_ids": result.get("fact_ids", []),
                        "source_ids": result.get("source_ids", []),
                        "reason_codes": result.get("reason_codes", []),
                    }
                )
            elif status == "unknown":
                missing_fields = result.get("missing_fields", [])
                reason_codes = result.get("reason_codes", [])
                missing_information.append(
                    {
                        "crop_id": crop_id,
                        "rule_id": rule_id,
                        "missing_fields": missing_fields,
                        "reason_codes": reason_codes,
                    }
                )
                warnings.append(
                    f"Rule {rule_id} for crop '{crop_id}' could not be fully evaluated because required information or evidence was unknown."
                )
    if fired_rules:
        overall_status = "fired"
    elif missing_information:
        overall_status = "unknown"
    else:
        overall_status = "not_fired"
    return {
        "status": overall_status,
        "candidates": crops,
        "fired_rules": fired_rules,
        "rule_results": rule_results,
        "warnings": list(dict.fromkeys(warnings)),
        "missing_information": missing_information,
    }


def _candidate_records(knowledge: Mapping[str, Any]) -> list[dict[str, Any]]:
    """
    Convert knowledge-base crop records into CSP candidates.

    Verified usable facts are attached to every candidate.
    """
    candidates: list[dict[str, Any]] = []
    for crop in knowledge.get("crops", []):
        if not isinstance(crop, Mapping) or not crop.get("crop_id"):
            continue
        crop_id = str(crop["crop_id"])
        facts = get_usable_facts(dict(knowledge), crop_id=crop_id)
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


def _select_candidates(crops, selected_ids):
    """Resolve names/IDs once, preserve user order and remove duplicates."""
    if not selected_ids:
        return crops
    selected = []
    seen = set()
    for crop_name in selected_ids:
        crop = find_crop({"crops": crops}, crop_name)
        if crop and crop["crop_id"] not in seen:
            selected.append(crop)
            seen.add(crop["crop_id"])
    return selected


def _knowledge_summary(knowledge: Mapping[str, Any]) -> dict[str, Any]:
    """Build a compact knowledge-base summary."""
    crops = [item for item in knowledge.get("crops", []) if isinstance(item, Mapping)]
    top_level_facts = knowledge.get("facts", [])
    if isinstance(top_level_facts, list) and top_level_facts:
        facts = [fact for fact in top_level_facts if isinstance(fact, Mapping)]
    else:
        facts = [
            fact for crop in crops for fact in crop.get("facts", []) if isinstance(fact, Mapping)
        ]
    statuses: dict[str, int] = {}
    for fact in facts:
        key = str(fact.get("verification_status", "unknown")).casefold()
        statuses[key] = statuses.get(key, 0) + 1
    verified_count = sum(
        (
            statuses.get(key, 0)
            for key in ("verified", "verified_general", "verified_context_specific")
        )
    )
    return {
        "total_crops": len(crops),
        "total_facts": len(facts),
        "verified_facts": verified_count,
        "usable_facts": len(get_usable_facts(dict(knowledge))),
        "fact_status_counts": statuses,
        "total_sources": len(knowledge.get("sources", [])),
        "dataset_status": knowledge.get("metadata", {}).get("status", "unknown"),
    }


def _resolve_evidence_sources(
    knowledge: Mapping[str, Any], source_ids: Iterable[str]
) -> list[dict[str, Any]]:
    """Resolve source IDs into source records."""
    wanted = set(source_ids)
    return [
        dict(source)
        for source in knowledge.get("sources", [])
        if isinstance(source, Mapping) and source.get("source_id") in wanted
    ]


def _missing(csp_result: Mapping[str, Any]) -> list[dict[str, str]]:
    """
    Extract missing information from unknown CSP results.
    """
    result: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for candidate in csp_result.get("unknown_candidates", []):
        for outcome in candidate.get("unknown_constraints", []):
            fields = outcome.get("missing_fields") or [""]
            for field in fields:
                key = (field, outcome.get("reason_code", "UNKNOWN"))
                if key in seen:
                    continue
                result.append(
                    {
                        "field": field,
                        "reason_code": outcome.get("reason_code", "UNKNOWN"),
                        "message": outcome.get("reason", "Information is missing."),
                    }
                )
                seen.add(key)
    return result


def _status(
    csp_result: Mapping[str, Any],
    missing: list[dict[str, str]],
) -> str:
    """Classify using actual constraint outcomes, not unrelated optional fields."""
    if csp_result.get("feasible_candidates"):
        return "FEASIBLE_OPTIONS_FOUND"
    if csp_result.get("unknown_candidates"):
        if any((item.get("reason_code") == "MISSING_USER_INPUT" for item in missing)):
            return "MORE_INFORMATION_NEEDED"
        return "NO_SUPPORTED_KNOWLEDGE"
    return "NO_FEASIBLE_OPTION"


def run_assessment(
    user_profile: Mapping[str, Any], *, knowledge_override: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """
    Execute the complete CropNova assessment workflow.

    Architecture:

        User Input
             ↓
        Profile Validation
             ↓
        Knowledge Base
             ↓
        Rule Engine
             ↓
        CSP Solver
             ↓
        Explainable Report
    """
    # 1. Normalise and validate before opening the knowledge base.
    try:
        if not isinstance(user_profile, Mapping):
            raise TypeError("Farm profile must be an object.")
        profile = normalize_profile(user_profile)
    except (TypeError, ValueError) as error:
        return {
            "status": "INVALID_INPUT",
            "errors": [{"field": "profile", "code": "INVALID_PROFILE", "message": str(error)}],
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
        # 2. Load and validate reference records, including their source links.
        knowledge = load_knowledge() if knowledge_override is None else dict(knowledge_override)
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
        selected_ids = profile["candidate_ids"]
        invalid_ids = [
            str(item) for item in selected_ids if not find_crop({"crops": crops}, str(item))
        ]
        if invalid_ids:
            return {
                "status": "INVALID_INPUT",
                "profile": profile,
                "errors": [
                    {
                        "code": "UNKNOWN_CROP",
                        "field": "candidate_ids",
                        "message": "Unknown crop selection: " + ", ".join(invalid_ids),
                    }
                ],
                "warnings": [],
                "limitations": LIMITATIONS,
            }
        # 3. Scope evidence to this location and evaluate each crop independently.
        candidates = _select_candidates(crops, selected_ids)
        for crop in candidates:
            crop["facts"] = [f for f in crop["facts"] if scope_matches(f, profile)]
        rule_result = _rule_adapter(profile, candidates)
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
        # 4. All four checks must pass. Unknown evidence never counts as a pass.
        csp_result = solve_constraints(candidates, profile)
        missing = _missing(csp_result)
        status = _status(csp_result, missing)
        # 5. Keep decisions, reasons and evidence IDs together for reproducible reports.
        report = {
            "status": status,
            "profile": profile,
            "knowledge_version": knowledge.get("metadata", {}).get("version", "unknown"),
            "knowledge_coverage": knowledge_coverage(candidates, profile),
            "knowledge_summary": _knowledge_summary(knowledge),
            "rule_status": rule_result.get("status", "unknown"),
            "rule_trace": rule_result.get("fired_rules", []),
            "rule_results": rule_result.get("rule_results", []),
            "csp_result": csp_result,
            "feasible_options": csp_result.get("feasible_candidates", []),
            "rejected_options": csp_result.get("rejected_candidates", []),
            "unknown_options": csp_result.get("unknown_candidates", []),
            "warnings": list(dict.fromkeys(rule_result.get("warnings", []))),
            "missing_information": missing,
            "follow_up_questions": list(
                dict.fromkeys(
                    [
                        follow_up_question(item["field"])
                        for item in missing
                        if item["field"] and item["reason_code"] == "MISSING_USER_INPUT"
                    ]
                )
            ),
            "errors": [],
            "limitations": LIMITATIONS,
        }
        report["explanations"] = build_explanations(status, csp_result)
        report["evidence_package"] = build_evidence_package(report)
        report["evidence"] = _resolve_evidence_sources(
            knowledge, report["evidence_package"]["source_ids_used"]
        )
        report["dataset_kind"] = (
            "synthetic"
            if knowledge.get("metadata", {}).get("status") == "synthetic_fixture"
            else "research"
        )
        report["assessment_basis"] = (
            "Preliminary published-reference screening only; preferred conditions and indicative water ranges do not establish field suitability."
            if report["dataset_kind"] == "research"
            else "Synthetic algorithm evaluation."
        )
        if report["dataset_kind"] == "research":
            report["warnings"].append(report["assessment_basis"])
            if status == "FEASIBLE_OPTIONS_FOUND":
                report["explanations"][0][
                    "text"
                ] = "At least one crop matches all four published-reference screens. This is a preliminary match; local agronomic confirmation is still needed."
            if any(
                (
                    f.get("water_basis") == "seasonal_crop_water"
                    for crop in candidates
                    for f in crop["facts"]
                )
            ):
                report["warnings"].append(
                    "Seasonal crop-water use excludes paddy land preparation, seepage and conveyance losses. It is not an irrigation allocation or schedule."
                )
        report["preference_order"] = []
        if profile["objective"] == "conserve_water" or profile.get("priority") == "water":
            from constraint_definitions import verified_facts, WaterConstraint

            requirements = {}
            for crop in candidates:
                facts = verified_facts(crop["facts"], WaterConstraint.properties, profile)
                levels = {str(f.get("value")).casefold() for f in facts}
                if len(levels) == 1 and levels.issubset(WaterConstraint.LEVELS):
                    requirements[crop["crop_id"]] = next(iter(levels))
            for item in sorted(
                report["feasible_options"],
                key=lambda c: WaterConstraint.LEVELS.get(requirements.get(c["candidate_id"]), 99),
            ):
                if item["candidate_id"] in requirements:
                    report["preference_order"].append(
                        {
                            "candidate_id": item["candidate_id"],
                            "name": item["name"],
                            "water_requirement": requirements[item["candidate_id"]],
                            "reason": "Ordered by supported water category; ties preserve input order.",
                        }
                    )
        if profile["objective"] == "soil_improvement":
            report["warnings"].append(
                "Soil improvement is recorded as context; no soil improvement ranking is implemented."
            )
        report["evidence_package"]["facts"] = [
            dict(f)
            for f in knowledge.get("facts", [])
            if f.get("fact_id") in report["evidence_package"]["fact_ids_used"]
        ]
        report["evidence_package"]["sources"] = report["evidence"]
        # Optional analysis and planning explain the result; they never rewrite it.
        from farm_next_steps import snapshot_guidance
        report["field_guidance"] = snapshot_guidance(knowledge, profile,
            {crop["candidate_id"] for group in ("feasible_candidates", "unknown_candidates", "rejected_candidates")
             for crop in report.get("csp_result", {}).get(group, [])})
        report["fuzzy_analysis"] = analyze_assessment(report)
        report["preparation_plan"] = plan_assessment(report)
        return report
    except Exception as error:
        # Keep raw exception messages out of public JSON; they may contain paths
        # or private settings. The error type still helps diagnose server logs.
        logging.getLogger(__name__).error("Assessment module failed: %s", type(error).__name__)
        return {
            "status": "SYSTEM_ERROR",
            "profile": profile,
            "errors": [
                {
                    "code": "MODULE_FAILURE",
                    "message": "The assessment could not be completed. Check the server configuration and knowledge records.",
                }
            ],
            "warnings": [],
            "limitations": LIMITATIONS,
        }


__all__ = ["RESULT_STATUSES", "normalize_profile", "validate_profile", "run_assessment"]
