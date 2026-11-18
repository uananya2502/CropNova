"""Preview the same recorded checks without saving a report or calling an AI API."""

from agent import run_assessment
from assessment_summary import build_summary


def preview_coverage(values):
    report = run_assessment(values)
    if report["status"] == "INVALID_INPUT":
        return {
            "state": "invalid",
            "title": "Check your selections",
            "messages": [error["message"] for error in report.get("errors", [])],
            "crops": [],
        }
    if report["status"] == "SYSTEM_ERROR":
        return {
            "state": "unavailable",
            "title": "Coverage preview is temporarily unavailable",
            "messages": ["You can try again shortly."],
            "crops": [],
        }
    summary = build_summary(report)
    crops = [
        {
            "name": crop["name"],
            "matched": crop["matched"],
            "total": len(crop["checks"]),
            "label": crop["label"],
            "checks": [
                {"name": check["name"], "status": check["status"], "reason": check["reason"]}
                for check in crop["checks"]
            ],
        }
        for crop in summary["candidates"]
    ]
    ready = bool(crops) and all(crop["matched"] == crop["total"] for crop in crops)
    return {
        "state": "ready" if ready else "review",
        "title": (
            "All four checks match these selections"
            if ready
            else "Review these comparisons before generating"
        ),
        "messages": (
            ["Generate your assessment to open the full findings and sources."] if ready else []
        ),
        "crops": crops,
    }
