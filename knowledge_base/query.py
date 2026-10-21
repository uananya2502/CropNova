
from typing import Any


def find_crop(
    knowledge: dict[str, Any],
    crop_name: str,
) -> dict[str, Any] | None:
    """Find a crop by its name or ID."""

    target = crop_name.strip().casefold()

    if not target:
        return None

    for crop in knowledge.get("crops", []):
        if not isinstance(crop, dict):
            continue

        possible_names = [
            crop.get("common_name", ""),
            crop.get("crop_id", ""),
            crop.get("name", ""),
        ]

        for name in possible_names:
            if isinstance(name, str) and name.strip().casefold() == target:
                return crop

    return None
