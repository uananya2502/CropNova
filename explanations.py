"""Deterministic, evidence-linked explanations for CropNova reports."""

from __future__ import annotations

from typing import Any, Mapping


STATUS_MESSAGES = {
    "FEASIBLE_OPTIONS_FOUND": "At least one option passed every implemented hard constraint using verified evidence.",
    "MORE_INFORMATION_NEEDED": "Some options could not be decided because required input or verified evidence is missing.",
    "NO_FEASIBLE_OPTION": "Every supported option violated at least one implemented hard constraint.",
    "NO_SUPPORTED_KNOWLEDGE": "CropNova does not yet have enough applicable verified knowledge for this assessment.",
    "INVALID_INPUT": "The submitted profile contains values that must be corrected.",
    "SYSTEM_ERROR": "CropNova could not safely complete the assessment.",
}


def candidate_explanation(candidate: Mapping[str, Any]) -> str:
    """Produce a plain-language summary without changing solver status."""

    name = str(candidate.get("name", candidate.get("candidate_id", "Candidate"))).title()
    status = candidate.get("status")
    if status == "feasible":
        count = len(candidate.get("satisfied_constraints", []))
        return f"{name} passed all {count} implemented hard constraints."
    if status == "rejected":
        reasons = [row.get("reason", "") for row in candidate.get("failed_constraints", [])]
        return f"{name} was rejected: " + " ".join(item for item in reasons if item)
    reasons = [row.get("reason", "") for row in candidate.get("unknown_constraints", [])]
    return f"{name} remains unknown: " + " ".join(item for item in reasons if item)


def build_explanations(status: str, csp_result: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "type": "assessment",
            "status": status,
            "text": STATUS_MESSAGES.get(status, "Assessment completed."),
        }
    ]
    for group in ("feasible_candidates", "rejected_candidates", "unknown_candidates"):
        for candidate in csp_result.get(group, []):
            rows.append(
                {
                    "type": "candidate",
                    "candidate_id": candidate.get("candidate_id"),
                    "status": candidate.get("status"),
                    "text": candidate_explanation(candidate),
                }
            )
    return rows


def build_evidence_package(report: Mapping[str, Any]) -> dict[str, Any]:
    """Return compact structured context suitable for a future GenAI adapter.

    This package contains decisions and IDs only; a language model may explain
    them but must not change their statuses.
    """

    csp = report.get("csp_result", {})
    used_fact_ids: list[str] = []
    used_source_ids: list[str] = []
    for group in ("feasible_candidates", "rejected_candidates", "unknown_candidates"):
        for candidate in csp.get(group, []):
            for outcome_group in (
                "satisfied_constraints",
                "failed_constraints",
                "unknown_constraints",
            ):
                for outcome in candidate.get(outcome_group, []):
                    used_fact_ids.extend(outcome.get("fact_ids", []))
                    used_source_ids.extend(outcome.get("source_ids", []))
    return {
        "profile": report.get("profile", {}),
        "assessment_status": report.get("status"),
        "candidate_outcomes": {
            key: csp.get(key, [])
            for key in ("feasible_candidates", "rejected_candidates", "unknown_candidates")
        },
        "rule_trace": report.get("rule_trace", []),
        "fact_ids_used": list(dict.fromkeys(used_fact_ids)),
        "source_ids_used": list(dict.fromkeys(used_source_ids)),
        "warnings": report.get("warnings", []),
        "missing_information": report.get("missing_information", []),
        "limitations": report.get("limitations", []),
    }


def follow_up_question(field: str) -> str:
    questions = {
        "season": "Which growing season applies: Kharif, Rabi, or Zaid?",
        "water.availability": "Is water availability low, moderate, or high?",
        "soil.texture": "What is the soil texture: sandy, loamy, clayey, or other?",
        "soil.ph": "If available, what is the measured soil pH?",
    }
    return questions.get(field, f"Please provide {field.replace('.', ' ')}.")

