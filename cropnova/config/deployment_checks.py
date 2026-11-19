"""Core readiness checks. No external model requests or private settings in output."""

from knowledge_base.loader import load_knowledge
from knowledge_base.validator import validate_knowledge
from cropnova.reports.report_store import connect


def readiness():
    try:
        if validate_knowledge(load_knowledge()):
            return {"status": "unavailable", "component": "knowledge"}
        with connect() as database:
            database.execute("SELECT 1").fetchone()
    except Exception:
        # A readiness failure must not reveal a filesystem path or database details.
        return {"status": "unavailable", "component": "assessment_storage_or_knowledge"}
    return {"status": "ready", "checks": ["published_knowledge", "assessment_storage"]}
