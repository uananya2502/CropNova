"""Run a published-reference example without starting the website.

This uses example inputs, not measurements collected from an actual farm.
"""

import argparse
import json

from agent import run_assessment
from public_profiles import REFERENCE_PROFILES


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--crop", choices=tuple(key.removeprefix("reference-") for key in REFERENCE_PROFILES), default="wheat")
    args = parser.parse_args()
    profile = REFERENCE_PROFILES["reference-" + args.crop]
    print(json.dumps(run_assessment(profile), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
