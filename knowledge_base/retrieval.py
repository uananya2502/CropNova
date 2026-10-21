from typing import Any


ALLOWED_STATUSES = {
    "verified_general",
    "verified_context_specific",
}

# These are CropNova system policies, not agricultural facts.
EXCLUDED_AGRICULTURAL_CATEGORIES = {
    "uncertainty",
    "traceability",
}


def get_usable_facts(
    knowledge: dict[str, Any],
    crop_id: str | None = None,
) -> list[dict[str, Any]]:
    """Return source-reviewed agricultural facts for a crop."""

    sources = {
        source.get("source_id"): source
        for source in knowledge.get("sources", [])
        if isinstance(source, dict) and source.get("source_id")
    }

    known_crops = {
        crop.get("crop_id")
        for crop in knowledge.get("crops", [])
        if isinstance(crop, dict)
    }

    if crop_id is not None and crop_id not in known_crops:
        return []

    usable_facts = []

    for fact in knowledge.get("facts", []):
        if not isinstance(fact, dict):
            continue

        if fact.get("verification_status") not in ALLOWED_STATUSES:
            continue

        if fact.get("category") in EXCLUDED_AGRICULTURAL_CATEGORIES:
            continue

        fact_crop = fact.get("crop_id")

        if crop_id is not None and fact_crop not in ("all", crop_id):
            continue

        source_ids = fact.get("source_ids", [])

        if not isinstance(source_ids, list) or not source_ids:
            continue

        sources_reviewed = all(
            source_id in sources
            and sources[source_id].get("review_status")
            == "reviewed_for_inclusion"
            for source_id in source_ids
        )

        if not sources_reviewed:
            continue

        usable_facts.append(fact)

    return usable_facts
