
from typing import Any


def validate_knowledge(data: dict[str, Any]) -> list[str]:
    """Return a list of structural problems in the knowledge base."""
    errors = []

    if not isinstance(data, dict):
        return ["Knowledge base must be a dictionary."]

    metadata = data.get("metadata")
    if not isinstance(metadata, dict):
        errors.append("Missing or invalid metadata object.")

    crops = data.get("crops")
    if not isinstance(crops, list):
        errors.append("'crops' must be a list.")
        crops = []

    sources = data.get("sources")
    if not isinstance(sources, list):
        errors.append("'sources' must be a list.")
        sources = []

    crop_ids = set()
    crop_names = set()

    for index, crop in enumerate(crops):
        if not isinstance(crop, dict):
            errors.append(f"Crop record {index} must be an object.")
            continue

        for field in (
            "crop_id",
            "name",
            "category",
            "verification_status",
            "source_ids",
            "facts",
        ):
            if field not in crop:
                errors.append(
                    f"Crop record {index} is missing '{field}'."
                )

        crop_id = crop.get("crop_id")
        name = crop.get("name")

        if not isinstance(crop_id, str) or not crop_id.strip():
            errors.append(f"Crop record {index} has an invalid crop_id.")
        elif crop_id in crop_ids:
            errors.append(f"Duplicate crop_id: {crop_id}")
        else:
            crop_ids.add(crop_id)

        if not isinstance(name, str) or not name.strip():
            errors.append(f"Crop record {index} has an invalid name.")
        elif name.lower() in crop_names:
            errors.append(f"Duplicate crop name: {name}")
        else:
            crop_names.add(name.lower())

        if not isinstance(crop.get("facts"), list):
            errors.append(f"Facts for crop {crop_id} must be a list.")

        if not isinstance(crop.get("source_ids"), list):
            errors.append(f"Source IDs for crop {crop_id} must be a list.")

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

    return errors

