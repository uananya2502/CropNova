"""Small, repeatable retrieval check using example field inputs, not farm data.

Run manually after preparing the model. These six checks are smoke tests, not a
measurement of agricultural accuracy or a representative question benchmark.
"""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import assess
from cropnova.config.public_profiles import REFERENCE_PROFILES
from cropnova.ai.semantic_search import search_assessment, MODEL_ID, MODEL_REVISION

CASES = [
    ("reference-wheat", "Is my water supply enough for wheat?", "Water supply"),
    ("reference-wheat", "Is pH 7 suitable for wheat?", "Soil pH"),
    ("reference-wheat", "Can I grow wheat in the rabi season?", "Growing season"),
    ("reference-rice", "Does clayey soil match rice?", "Soil texture"),
    ("reference-maize", "What water requirement was checked for maize?", "Water supply"),
    ("reference-chickpea", "Does chickpea need supplemental irrigation?", "Water supply"),
]
if __name__ == "__main__":
    results = []
    for preset, question, expected in CASES:
        report = assess(REFERENCE_PROFILES[preset])
        found = search_assessment(report, question)
        titles = [row["title"] for row in found]
        results.append(
            {
                "question": question,
                "expected_finding": expected,
                "retrieved": titles,
                "found_in_top_three": any(expected in title for title in titles),
            }
        )
    output = {
        "model": MODEL_ID,
        "revision": MODEL_REVISION,
        "scope": "Six example-question smoke checks; not an accuracy benchmark.",
        "results": results,
    }
    destination = Path("tmp/transformer_checks.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output, indent=2))
    if not all(row["found_in_top_three"] for row in results):
        raise SystemExit("Review missed retrievals.")
