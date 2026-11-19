"""Check production prerequisites without printing keys or calling a paid API."""

import argparse
from importlib.util import find_spec
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cropnova.config.deployment_checks import readiness


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-model", action="store_true", help="Also load the prepared local encoder."
    )
    args = parser.parse_args()
    missing = [
        name
        for name in ("reportlab", "gunicorn", "sentence_transformers", "torch")
        if find_spec(name) is None
    ]
    if missing:
        print("Missing packages:", ", ".join(missing))
        raise SystemExit(1)
    result = readiness()
    if result["status"] != "ready":
        print("Readiness failed:", result["component"])
        raise SystemExit(1)
    print("Published knowledge and assessment storage: ready")
    if args.require_model:
        from cropnova.ai.semantic_search import load_encoder, SearchUnavailable

        try:
            load_encoder()
        except SearchUnavailable:
            print("Prepare the encoder with python scripts/prepare_transformer.py first.")
            raise SystemExit(1)
        print("Prepared local encoder: ready")
    print(
        "Core deployment checks passed. Public DNS, HTTPS and host resources still need host-specific verification."
    )


if __name__ == "__main__":
    main()
