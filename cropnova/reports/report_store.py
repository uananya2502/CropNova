"""Keep assessments briefly so downloads reuse the exact displayed result.

SQLite is included with Python. Random report links act as private access links;
reports expire after one hour. Each operation uses its own database connection.
"""

from contextlib import contextmanager
import json
import os
from pathlib import Path
import secrets
import sqlite3
import time
from cropnova.paths import PROJECT_ROOT

DATA_DIR = Path(os.environ.get("CROPNOVA_DATA_DIR", PROJECT_ROOT / "instance"))
DATABASE_PATH = DATA_DIR / "assessments.sqlite3"
REPORT_LIFETIME = 3600


@contextmanager
def connect():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    connection = sqlite3.connect(DATABASE_PATH, timeout=5)
    os.chmod(DATABASE_PATH, 0o600)
    connection.execute(
        "CREATE TABLE IF NOT EXISTS assessments (token TEXT PRIMARY KEY, created REAL NOT NULL, report TEXT NOT NULL)"
    )
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def save_report(report):
    token = secrets.token_urlsafe(24)
    now = time.time()
    payload = json.dumps(report, ensure_ascii=False, allow_nan=False)
    with connect() as database:
        database.execute("DELETE FROM assessments WHERE created < ?", (now - REPORT_LIFETIME,))
        database.execute("INSERT INTO assessments VALUES (?, ?, ?)", (token, now, payload))
        database.execute(
            "DELETE FROM assessments WHERE token NOT IN (SELECT token FROM assessments ORDER BY created DESC LIMIT 100)"
        )
    return token


def load_report(token):
    if (
        not isinstance(token, str)
        or len(token) != 32
        or any(
            c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
            for c in token
        )
    ):
        return None
    with connect() as database:
        row = database.execute(
            "SELECT report FROM assessments WHERE token = ? AND created >= ?",
            (token, time.time() - REPORT_LIFETIME),
        ).fetchone()
    return json.loads(row[0]) if row else None
