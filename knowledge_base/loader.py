
import json
from pathlib import Path
from typing import Any

DATA_FILE = Path(__file__).parent / "data" / "knowledge_facts.json"


def load_knowledge() -> dict[str, Any]:
    """Load the CropNova knowledge base from its JSON file."""
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Knowledge file not found: {DATA_FILE}"
        )

    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Invalid JSON in knowledge file: {error}"
        ) from error

    if not isinstance(data, dict):
        raise ValueError("Knowledge data must be a JSON object.")

    return data

