
from typing import Any


def find_crop(
    knowledge: dict[str, Any],
    crop_name: str,
) -> dict[str, Any] | None:
    """Find a crop by name, ignoring capitalization and outer spaces."""
    target = crop_name.strip().casefold()

    for crop in knowledge.get("crops", []):
        if isinstance(crop, dict):
            name = crop.get("name", "")
            if isinstance(name, str) and name.strip().casefold() == target:
                return crop

    return None

