"""One project root keeps data paths stable when code is moved into packages."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
