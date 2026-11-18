"""Shared evidence scope and numeric parsing for rules, CSP and coverage checks."""

from __future__ import annotations
import math
from collections.abc import Mapping


def normalise(value):
    return str(value).strip().casefold()


def unknown(value):
    return value is None or normalise(value) in {"", "unknown", "i don't know", "none"}


def values(value):
    if isinstance(value, str):
        return [normalise(v) for v in value.split(",") if v.strip()]
    if isinstance(value, (list, tuple)) and all(isinstance(v, str) and v.strip() for v in value):
        return [normalise(v) for v in value]
    return []


def scope_matches(fact, profile):
    scope = fact.get("applicability", {})
    if not isinstance(scope, Mapping):
        return False
    region = profile.get("region", {})
    checks = [
        ("country", region.get("country", "India")),
        ("state", region.get("state")),
        ("district", region.get("district")),
        ("season", profile.get("season")),
        ("soil_type", profile.get("soil", {}).get("texture")),
        ("irrigation", profile.get("water", {}).get("irrigation")),
    ]
    if "region" in scope:
        checks.append(("region", region.get("state")))
    # Unsupported restrictions must not silently become global evidence.
    supported = {key for key, _ in checks} | {"region", "notes"}
    if any(not unknown(v) for k, v in scope.items() if k not in supported):
        return False
    for key, actual in checks:
        required = scope.get(key)
        if unknown(required):
            continue
        allowed = set(values(required))
        if allowed & {"all", "any", "global"}:
            continue
        if unknown(actual) or normalise(actual) not in allowed:
            return False
    return True


def numeric_range(value):
    if isinstance(value, Mapping):
        pair = (value.get("min"), value.get("max"))
    elif isinstance(value, (list, tuple)) and len(value) == 2:
        pair = value
    else:
        raise ValueError("A numeric range needs two endpoints.")
    if any(isinstance(v, bool) for v in pair):
        raise ValueError("Boolean endpoints are invalid.")
    low, high = map(float, pair)
    if not all(math.isfinite(v) for v in (low, high)) or low > high:
        raise ValueError("Range must be finite and ordered.")
    return low, high


def assessment_facts(report):
    """Return only eligible, reviewed facts from this saved assessment snapshot.

    Both fuzzy analysis and question retrieval use the same evidence policy.
    A source document shared by several facts does not make every fact eligible.
    """
    reviewed = {
        source["source_id"]
        for source in report.get("evidence", [])
        if source.get("review_status") == "reviewed_for_inclusion"
    }
    return [
        fact
        for fact in report.get("evidence_package", {}).get("facts", [])
        if fact.get("verification_status") in {"verified_general", "verified_context_specific"}
        and fact.get("constraint_eligible", True) is not False
        and scope_matches(fact, report.get("profile", {}))
        and fact.get("source_ids")
        and all(source in reviewed for source in fact["source_ids"])
    ]
