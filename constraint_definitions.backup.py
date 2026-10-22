"""Constraint definitions for CropNova's single-variable crop CSP.

Agricultural values are never defined in this module.  Each constraint reads
only user input and verified fact records supplied by the knowledge layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, Mapping, Sequence


class CheckStatus(str, Enum):
    """The three-valued result of checking one hard constraint."""

    SATISFIED = "satisfied"
    VIOLATED = "violated"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ConstraintOutcome:
    constraint_id: str
    name: str
    status: CheckStatus
    reason: str
    reason_code: str
    fact_ids: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    missing_fields: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "constraint_id": self.constraint_id,
            "name": self.name,
            "status": self.status.value,
            "reason": self.reason,
            "reason_code": self.reason_code,
            "fact_ids": list(self.fact_ids),
            "source_ids": list(self.source_ids),
            "missing_fields": list(self.missing_fields),
        }


def _normalise(value: Any) -> str:
    return str(value).strip().casefold()


def _is_unknown(value: Any) -> bool:
    return value is None or _normalise(value) in {"", "unknown", "i don't know", "none"}


def _nested(profile: Mapping[str, Any], *path: str) -> Any:
    value: Any = profile
    for key in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value


def _values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [_normalise(item) for item in value.split(",") if item.strip()]
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return [_normalise(item) for item in value]
    return [_normalise(value)] if value is not None else []


def _region_matches(fact: Mapping[str, Any], profile: Mapping[str, Any]) -> bool:
    applicability = fact.get("applicability")
    if not isinstance(applicability, Mapping):
        return True
    required_region = applicability.get("state", applicability.get("region"))
    if _is_unknown(required_region):
        return True
    allowed = set(_values(required_region))
    if allowed.intersection({"all", "any", "global", "documented scope"}):
        return True
    user_region = _nested(profile, "region", "state")
    return not _is_unknown(user_region) and _normalise(user_region) in allowed


def verified_facts(
    facts: Iterable[Mapping[str, Any]],
    properties: set[str],
    profile: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    """Return applicable facts that the knowledge layer marked as verified."""

    approved_statuses = {"verified", "verified_general", "verified_context_specific"}
    return [
        fact
        for fact in facts
        if isinstance(fact, Mapping)
        and _normalise(fact.get("verification_status")) in approved_statuses
        and _normalise(fact.get("property", fact.get("category"))) in properties
        and _region_matches(fact, profile)
    ]


def _evidence(facts: Iterable[Mapping[str, Any]]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    fact_ids: list[str] = []
    source_ids: list[str] = []
    for fact in facts:
        if fact.get("fact_id"):
            fact_ids.append(str(fact["fact_id"]))
        source_ids.extend(str(item) for item in fact.get("source_ids", []) if item)
    return tuple(dict.fromkeys(fact_ids)), tuple(dict.fromkeys(source_ids))


@dataclass(frozen=True)
class HardConstraint:
    constraint_id: str
    name: str

    def check(
        self,
        candidate: Mapping[str, Any],
        profile: Mapping[str, Any],
        facts: Sequence[Mapping[str, Any]],
    ) -> ConstraintOutcome:
        raise NotImplementedError

    def _unknown(
        self,
        reason: str,
        code: str,
        missing_fields: tuple[str, ...] = (),
    ) -> ConstraintOutcome:
        return ConstraintOutcome(
            self.constraint_id,
            self.name,
            CheckStatus.UNKNOWN,
            reason,
            code,
            missing_fields=missing_fields,
        )


class SeasonConstraint(HardConstraint):
    def __init__(self) -> None:
        super().__init__("CONSTRAINT001", "Growing season compatibility")

    def check(self, candidate, profile, facts):
        season = profile.get("season")
        if _is_unknown(season):
            return self._unknown(
                "The growing season is needed to check this candidate.",
                "MISSING_USER_INPUT",
                ("season",),
            )
        matches = verified_facts(facts, {"growing_season", "season", "seasons"}, profile)
        if not matches:
            return self._unknown(
                "No applicable verified season fact is available for this candidate.",
                "MISSING_VERIFIED_FACT",
            )
        allowed = {item for fact in matches for item in _values(fact.get("value"))}
        fact_ids, source_ids = _evidence(matches)
        passed = _normalise(season) in allowed
        return ConstraintOutcome(
            self.constraint_id,
            self.name,
            CheckStatus.SATISFIED if passed else CheckStatus.VIOLATED,
            (
                f"User season '{season}' is included in the verified season evidence."
                if passed
                else f"User season '{season}' is not included in the verified season evidence."
            ),
            "SEASON_MATCH" if passed else "SEASON_MISMATCH",
            fact_ids,
            source_ids,
        )




class WaterConstraint(HardConstraint):
    LEVELS = {"low": 1, "moderate": 2, "high": 3}

    def __init__(self) -> None:
        super().__init__("CONSTRAINT002", "Water availability")

    def check(self, candidate, profile, facts):
        available = _nested(profile, "water", "availability")

        if _is_unknown(available):
            return self._unknown(
                "Water availability is needed to check this candidate.",
                "MISSING_USER_INPUT",
                ("water.availability",),
            )

        available_key = _normalise(available)

        if available_key not in self.LEVELS:
            return self._unknown(
                "Water availability is not in the supported low/moderate/high scale.",
                "UNSUPPORTED_USER_VALUE",
                ("water.availability",),
            )

        matches = verified_facts(
            facts,
            {
                "water_requirement",
                "water_need",
                "minimum_water_availability",
                "water",
            },
            profile,
        )

        if not matches:
            return self._unknown(
                "No applicable verified water-requirement fact is available for this candidate.",
                "MISSING_VERIFIED_FACT",
            )

        # Separate numeric water-demand facts from qualitative requirements.
        numeric_ranges = [
            fact
            for fact in matches
            if isinstance(fact.get("value"), Mapping)
            and "min" in fact["value"]
            and "max" in fact["value"]
        ]

        if numeric_ranges:
            fact_ids, source_ids = _evidence(numeric_ranges)
            return ConstraintOutcome(
                self.constraint_id,
                self.name,
                CheckStatus.UNKNOWN,
                (
                    "Crop water requirement is expressed as a numeric range, "
                    "but farm water availability is qualitative. "
                    "These values cannot be compared reliably."
                ),
                "INCOMPATIBLE_WATER_UNITS",
                fact_ids,
                source_ids,
            )

        # Ignore general facts without a usable requirement value.
        requirements = {
            _normalise(fact.get("value"))
            for fact in matches
            if isinstance(fact.get("value"), str)
            and _normalise(fact.get("value")) in self.LEVELS
        }

        if len(requirements) != 1:
            return self._unknown(
                "No single compatible qualitative water requirement is available.",
                "INCOMPATIBLE_VERIFIED_FACT",
            )

        required = requirements.pop()
        fact_ids, source_ids = _evidence(matches)
        passed = self.LEVELS[available_key] >= self.LEVELS[required]

        return ConstraintOutcome(
            self.constraint_id,
            self.name,
            CheckStatus.SATISFIED if passed else CheckStatus.VIOLATED,
            (
                f"Available water ({available}) meets the verified '{required}' requirement."
                if passed
                else f"Available water ({available}) is below the verified '{required}' requirement."
            ),
            "WATER_SUFFICIENT" if passed else "WATER_INSUFFICIENT",
            fact_ids,
            source_ids,
        )


class SoilTextureConstraint(HardConstraint):
    def __init__(self) -> None:
        super().__init__("CONSTRAINT003", "Soil texture compatibility")

    def check(self, candidate, profile, facts):
        texture = _nested(profile, "soil", "texture")
        if _is_unknown(texture):
            return self._unknown(
                "Soil texture is unknown, so this check cannot be completed.",
                "MISSING_USER_INPUT",
                ("soil.texture",),
            )
        matches = verified_facts(
            facts,
            {"soil_texture", "suitable_soil_texture", "soil_textures"},
            profile,
        )
        if not matches:
            return self._unknown(
                "No applicable verified soil-texture fact is available for this candidate.",
                "MISSING_VERIFIED_FACT",
            )
        allowed = {item for fact in matches for item in _values(fact.get("value"))}
        fact_ids, source_ids = _evidence(matches)
        passed = _normalise(texture) in allowed
        return ConstraintOutcome(
            self.constraint_id,
            self.name,
            CheckStatus.SATISFIED if passed else CheckStatus.VIOLATED,
            (
                f"Soil texture '{texture}' is supported by verified evidence."
                if passed
                else f"Soil texture '{texture}' is outside the verified supported textures."
            ),
            "SOIL_TEXTURE_MATCH" if passed else "SOIL_TEXTURE_MISMATCH",
            fact_ids,
            source_ids,
        )


class SoilPHConstraint(HardConstraint):
    def __init__(self) -> None:
        super().__init__("CONSTRAINT004", "Soil pH range")

    def check(self, candidate, profile, facts):
        ph = _nested(profile, "soil", "ph")
        if _is_unknown(ph):
            return self._unknown(
                "Soil pH was not supplied; the pH check remains unknown.",
                "MISSING_USER_INPUT",
                ("soil.ph",),
            )
        matches = verified_facts(facts, {"soil_ph_range", "ph_range"}, profile)
        if not matches:
            return self._unknown(
                "No applicable verified soil-pH range is available for this candidate.",
                "MISSING_VERIFIED_FACT",
            )
        ranges: list[tuple[float, float]] = []
        for fact in matches:
            value = fact.get("value")
            try:
                if isinstance(value, Mapping):
                    ranges.append((float(value["min"]), float(value["max"])))
                elif isinstance(value, Sequence) and len(value) == 2:
                    ranges.append((float(value[0]), float(value[1])))
            except (KeyError, TypeError, ValueError):
                continue
        if len(ranges) != 1:
            return self._unknown(
                "Verified pH evidence is missing, malformed, or conflicting.",
                "CONFLICTING_VERIFIED_FACTS",
            )
        low, high = ranges[0]
        passed = low <= float(ph) <= high
        fact_ids, source_ids = _evidence(matches)
        return ConstraintOutcome(
            self.constraint_id,
            self.name,
            CheckStatus.SATISFIED if passed else CheckStatus.VIOLATED,
            (
                f"Soil pH {ph:g} is within the verified range {low:g}-{high:g}."
                if passed
                else f"Soil pH {ph:g} is outside the verified range {low:g}-{high:g}."
            ),
            "SOIL_PH_MATCH" if passed else "SOIL_PH_MISMATCH",
            fact_ids,
            source_ids,
        )


DEFAULT_CONSTRAINTS: tuple[HardConstraint, ...] = (
    SeasonConstraint(),
    WaterConstraint(),
    SoilTextureConstraint(),
    SoilPHConstraint(),
)

