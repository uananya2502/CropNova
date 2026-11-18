"""Load optional local AI settings when starting the website.

The .env file is ignored by Git. Existing environment variables take priority.
This small reader supports only the AI settings CropNova actually uses.
"""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SETTINGS_PATH = PROJECT_ROOT / '.env'
ALLOWED_SETTINGS = {'OPENAI_API_KEY', 'OPENAI_MODEL', 'AI_PROVIDER', 'GEMINI_API_KEY', 'GEMINI_MODEL'}


def load_local_settings(path=None):
    """Read simple NAME=value lines without running them as shell commands."""
    path = Path(path) if path is not None else SETTINGS_PATH
    if not path.is_file():
        return
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        name, value = line.split('=', 1)
        name, value = name.strip(), value.strip()
        if name not in ALLOWED_SETTINGS:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        if value:
            os.environ.setdefault(name, value)
