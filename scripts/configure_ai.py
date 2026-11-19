"""Enter an API key privately. Use --provider gemini for the free-tier option."""

import argparse
import getpass
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cropnova.config.local_settings import SETTINGS_PATH


def main(provider="openai"):
    if provider == "gemini":
        configure_gemini()
        return
    if SETTINGS_PATH.exists():
        print("A local .env file already exists. It was left unchanged.")
        print("Update OPENAI_API_KEY there, or use an environment variable.")
        return
    key = getpass.getpass("OpenAI API key (hidden): ").strip()
    if not key or any(character.isspace() for character in key):
        print("No valid key entered. No file was created.")
        return
    # Create the file with owner-only permissions before writing the key.
    descriptor = os.open(SETTINGS_PATH, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as settings:
        settings.write("OPENAI_API_KEY=" + key + "\nOPENAI_MODEL=gpt-4o-mini\n")
    print("Saved privately to .env. The key was not displayed.")
    print("Run: python3 scripts/verify_ai.py --live")
    print("Then restart CropNova with: python3 app.py")


def configure_gemini():
    """Add Google settings while preserving any existing private settings."""
    lines = SETTINGS_PATH.read_text().splitlines() if SETTINGS_PATH.exists() else []
    if any(line.startswith("GEMINI_API_KEY=") and line.split("=", 1)[1].strip() for line in lines):
        print("A Gemini key already exists; it was left unchanged.")
        return
    key = getpass.getpass("Gemini API key (hidden): ").strip()
    if not key or any(character.isspace() for character in key):
        print("No valid key entered. Settings were left unchanged.")
        return
    lines = [
        line
        for line in lines
        if not line.startswith(("AI_PROVIDER=", "GEMINI_MODEL=", "GEMINI_API_KEY="))
    ]
    lines.extend(
        ["AI_PROVIDER=gemini", "GEMINI_MODEL=gemini-3.5-flash-lite", "GEMINI_API_KEY=" + key]
    )
    descriptor = os.open(SETTINGS_PATH, os.O_WRONLY | os.O_CREAT, 0o600)
    os.fchmod(descriptor, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as settings:
        settings.seek(0)
        settings.truncate()
        settings.write("\n".join(lines) + "\n")
    print("Gemini selected and key saved privately. Restart the website to load it.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=["openai", "gemini"], default="openai")
    main(provider=parser.parse_args().provider)
