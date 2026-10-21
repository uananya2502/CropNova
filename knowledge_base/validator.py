from typing import Any


ALLOWED_STATUSES = {
    "verified_general",
    "verified_context_specific",
    "pending_research",
    "needs_review",
}


def validate_knowledge(data: dict[str, Any]) -> list[str]:
    """Validate CropNova knowledge records and their references."""

    errors = []

    if not isinstance(data, dict):
        return ["Knowledge base must be a dictionary."]

    if not isinstance(data.get("metadata"), dict):
        errors.append("Missing or invalid metadata object.")

    crops = data.get("crops", [])
    facts = data.get("facts", [])
    sources = data.get("sources", [])
    pending = data.get("pending_research", [])

    collections = {
        "crops": crops,
        "facts": facts,
        "sources": sources,
        "pending_research": pending,
    }

    for name, collection in collections.items():
        if not isinstance(collection, list):
            errors.append(f"'{name}' must be a list.")
            collections[name] = []

    crops = collections["crops"]
    facts = collections["facts"]
    sources = collections["sources"]
    pending = collections["pending_research"]

    # Check crop IDs.
    crop_ids = set()

    for index, crop in enumerate(crops):
        if not isinstance(crop, dict):
            errors.append(f"Crop record {index} must be an object.")
            continue

        crop_id = crop.get("crop_id")

        if not isinstance(crop_id, str) or not crop_id.strip():
            errors.append(f"Crop record {index} has an invalid crop_id.")
        elif crop_id in crop_ids:
            errors.append(f"Duplicate crop_id: {crop_id}")
        else:
            crop_ids.add(crop_id)

        if not isinstance(crop.get("fact_ids"), list):
            errors.append(f"Crop {crop_id} must have a fact_ids list.")

    # Check source IDs and URLs.
    source_ids = set()

    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            errors.append(f"Source record {index} must be an object.")
            continue

        source_id = source.get("source_id")

        if not isinstance(source_id, str) or not source_id.strip():
            errors.append(f"Source record {index} has an invalid source_id.")
        elif source_id in source_ids:
            errors.append(f"Duplicate source_id: {source_id}")
        else:
            source_ids.add(source_id)

        url = source.get("url")
        if not isinstance(url, str) or not url.startswith(("https://", "http://")):
            errors.append(f"Source {source_id} has an invalid URL.")

        if not isinstance(source.get("review_status"), str):
            errors.append(f"Source {source_id} must have a review_status.")

    # Check fact IDs, statuses, crop IDs and source references.
    fact_ids = set()

    for index, fact in enumerate(facts):
        if not isinstance(fact, dict):
            errors.append(f"Fact record {index} must be an object.")
            continue

        fact_id = fact.get("fact_id")

        if not isinstance(fact_id, str) or not fact_id.strip():
            errors.append(f"Fact record {index} has an invalid fact_id.")
        elif fact_id in fact_ids:
            errors.append(f"Duplicate fact_id: {fact_id}")
        else:
            fact_ids.add(fact_id)

        if not isinstance(fact.get("statement"), str) or not fact["statement"].strip():
            errors.append(f"Fact {fact_id} must have a non-empty statement.")

        if fact.get("verification_status") not in ALLOWED_STATUSES:
            errors.append(
                f"Fact {fact_id} has an invalid verification_status."
            )

        fact_crop = fact.get("crop_id")
        if fact_crop != "all" and fact_crop not in crop_ids:
            errors.append(f"Fact {fact_id} references unknown crop {fact_crop}.")

        refs = fact.get("source_ids")
        if not isinstance(refs, list) or not refs:
            errors.append(f"Fact {fact_id} must have at least one source.")
        else:
            for source_id in refs:
                if source_id not in source_ids:
                    errors.append(
                        f"Fact {fact_id} references unknown source {source_id}."
                    )

    # Check crop-to-fact references.
    for crop in crops:
        if not isinstance(crop, dict):
            continue

        crop_id = crop.get("crop_id")
        refs = crop.get("fact_ids", [])

        if not isinstance(refs, list):
            continue

        for fact_id in refs:
            if fact_id not in fact_ids:
                errors.append(
                    f"Crop {crop_id} references unknown fact {fact_id}."
                )

    # Check pending research IDs and safeguards.
    research_ids = set()

    for index, item in enumerate(pending):
        if not isinstance(item, dict):
            errors.append(
                f"Pending research record {index} must be an object."
            )
            continue

        research_id = item.get("research_id")

        if not isinstance(research_id, str) or not research_id.strip():
            errors.append(
                f"Pending research record {index} has an invalid research_id."
            )
        elif research_id in research_ids:
            errors.append(f"Duplicate research_id: {research_id}")
        else:
            research_ids.add(research_id)

        if item.get("status") == "pending_research":
            if item.get("rule_creation_allowed") is not False:
                errors.append(
                    f"Pending item {research_id} must explicitly set "
                    "rule_creation_allowed to false."
                )

    return errors
