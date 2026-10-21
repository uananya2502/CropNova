"""Small command-line demonstration of the integrated CropNova pipeline."""

import json

from agent import run_assessment


if __name__ == "__main__":
    demo_profile = {
        "state": "Demo State",
        "season": "rabi",
        "soil_texture": "loamy",
        "soil_ph": "7.0",
        "soil_fertility": "unknown",
        "water_availability": "moderate",
        "irrigation": "available",
        "objective": "find_suitable_crop",
    }
    print(json.dumps(run_assessment(demo_profile), indent=2, ensure_ascii=False))
