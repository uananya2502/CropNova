"""Evidence-driven constraints. No agricultural thresholds are hard-coded here."""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import math
from typing import Mapping
from evidence import (
    normalise as _normalise,
    unknown as _is_unknown,
    values as _values,
    scope_matches as _region_matches,
    numeric_range,
)


class CheckStatus(str, Enum):
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

    def to_dict(self):
        return {
            **self.__dict__,
            "status": self.status.value,
            "fact_ids": list(self.fact_ids),
            "source_ids": list(self.source_ids),
            "missing_fields": list(self.missing_fields),
        }


def _nested(profile, *path):
    value = profile
    for key in path:
        value = value.get(key) if isinstance(value, Mapping) else None
    return value


def verified_facts(facts, properties, profile):
    return [
        f
        for f in facts
        if isinstance(f, Mapping)
        and _normalise(f.get("verification_status"))
        in {"verified", "verified_general", "verified_context_specific"}
        and _normalise(f.get("property", f.get("category"))) in properties
        and f.get("constraint_eligible", True) is not False
        and f.get("fact_id")
        and isinstance(f.get("source_ids"), list)
        and f["source_ids"]
        and _region_matches(f, profile)
    ]


def _evidence(facts):
    return (
        tuple(dict.fromkeys(str(f["fact_id"]) for f in facts)),
        tuple(dict.fromkeys(str(s) for f in facts for s in f.get("source_ids", []))),
    )


@dataclass(frozen=True)
class HardConstraint:
    constraint_id: str
    name: str

    def check(self, candidate, profile, facts):
        raise NotImplementedError

    def outcome(self, status, reason, code, facts=(), missing=()):
        ids, sources = _evidence(facts)
        return ConstraintOutcome(
            self.constraint_id, self.name, status, reason, code, ids, sources, missing
        )

    def _unknown(self, reason, code, missing_fields=(), facts=()):
        return self.outcome(CheckStatus.UNKNOWN, reason, code, facts, missing_fields)

    def selection(self, profile, facts, properties):
        return verified_facts(facts, properties, profile)


class _SetConstraint(HardConstraint):
    def check(self, candidate, profile, facts):
        actual = _nested(profile, *self.path)
        if _is_unknown(actual):
            return self._unknown(
                f"{self.name} needs a value from the farm profile.",
                "MISSING_USER_INPUT",
                (".".join(self.path),),
            )
        matches = self.selection(profile, facts, self.properties)
        if not matches:
            return self._unknown(
                f"No applicable verified {self.label} requirement is available.",
                "MISSING_VERIFIED_FACT",
            )
        if self.label == "soil texture" and any(
            f.get("requires_drainage") == "well_drained" for f in matches
        ):
            drainage = _nested(profile, "soil", "drainage")
            if _is_unknown(drainage):
                return self._unknown(
                    "The source requires well-drained soil; confirm field drainage.",
                    "MISSING_USER_INPUT",
                    ("soil.drainage",),
                    facts=matches,
                )
            if drainage != "well_drained":
                return self.outcome(
                    CheckStatus.VIOLATED,
                    "The published soil preference requires good drainage; the entered field is poorly drained.",
                    "DRAINAGE_MISMATCH",
                    matches,
                )
        choices = [frozenset(_values(f.get("value"))) for f in matches]
        if any(not c or not c.issubset(self.allowed) for c in choices):
            return self._unknown(
                f"{self.label.title()} evidence has an unsupported value.",
                "INCOMPATIBLE_VERIFIED_FACT",
                facts=matches,
            )
        if len(set(choices)) != 1:
            return self._unknown(
                f"Applicable verified {self.label} requirements disagree; review the evidence.",
                "CONFLICTING_VERIFIED_FACTS",
                facts=matches,
            )
        supported = choices[0]
        passed = _normalise(actual) in supported
        if not passed and any(f.get("closed_world") is False for f in matches):
            return self._unknown(
                f'The source documents {", ".join(sorted(supported))}; absence of {actual} does not establish incompatibility.',
                "NON_EXHAUSTIVE_EVIDENCE",
                facts=matches,
            )
        description = ", ".join(sorted(supported))
        return self.outcome(
            CheckStatus.SATISFIED if passed else CheckStatus.VIOLATED,
            f"Entered {self.label}: {actual}. Supported by this screening evidence: {description}.",
            self.codes[0] if passed else self.codes[1],
            matches,
        )


class SeasonConstraint(_SetConstraint):
    path = ("season",)
    properties = {"growing_season", "season", "seasons"}
    allowed = {"kharif", "rabi", "zaid"}
    label = "season"
    codes = ("SEASON_MATCH", "SEASON_MISMATCH")

    def __init__(self):
        super().__init__("CONSTRAINT001", "Growing season compatibility")


class SoilTextureConstraint(_SetConstraint):
    path = ("soil", "texture")
    properties = {"soil_texture", "suitable_soil_texture", "soil_textures"}
    allowed = {
        "sandy",
        "loamy",
        "clayey",
        "other",
        "sandy_loam",
        "clay_loam",
        "silt_loam",
        "silty_clay_loam",
    }
    label = "soil texture"
    codes = ("SOIL_TEXTURE_MATCH", "SOIL_TEXTURE_MISMATCH")

    def __init__(self):
        super().__init__("CONSTRAINT003", "Soil texture compatibility")


class WaterConstraint(HardConstraint):
    LEVELS = {"low": 1, "moderate": 2, "high": 3}
    properties = {"water_requirement", "water_need", "minimum_water_availability", "water"}

    def __init__(self):
        super().__init__("CONSTRAINT002", "Water availability")

    def check(self, candidate, profile, facts):
        numeric = self.selection(profile, facts, {"water_screening_range_mm"})
        if numeric:
            return self.check_numeric(profile, numeric)
        actual = _nested(profile, "water", "availability")
        if _is_unknown(actual):
            return self._unknown(
                "Water availability is needed.", "MISSING_USER_INPUT", ("water.availability",)
            )
        if _normalise(actual) not in self.LEVELS:
            return self._unknown(
                "Use low, moderate or high water availability.",
                "UNSUPPORTED_USER_VALUE",
                ("water.availability",),
            )
        matches = self.selection(profile, facts, self.properties)
        if not matches:
            return self._unknown(
                "No applicable verified categorical water requirement is available. Seasonal millimetres are not converted into categories.",
                "MISSING_VERIFIED_FACT",
            )
        requirements = {_normalise(f.get("value")) for f in matches}
        if not requirements.issubset(self.LEVELS):
            return self._unknown(
                "Water evidence does not use the required categorical scale.",
                "INCOMPATIBLE_VERIFIED_FACT",
                facts=matches,
            )
        if len(requirements) != 1:
            return self._unknown(
                "Applicable verified water requirements disagree.",
                "CONFLICTING_VERIFIED_FACTS",
                facts=matches,
            )
        required = next(iter(requirements))
        passed = self.LEVELS[_normalise(actual)] >= self.LEVELS[required]
        return self.outcome(
            CheckStatus.SATISFIED if passed else CheckStatus.VIOLATED,
            f'Available water ({actual}) {"meets" if passed else "is below"} the supported {required} requirement.',
            "WATER_SUFFICIENT" if passed else "WATER_INSUFFICIENT",
            matches,
        )

    def check_numeric(self, profile, facts):
        basis = _nested(profile, "water", "basis")
        available = _nested(profile, "water", "budget_mm")
        if _is_unknown(available):
            return self._unknown(
                "Enter a water budget in mm and select its measurement basis; categories cannot substitute for a numeric reference.",
                "MISSING_USER_INPUT",
                ("water.budget_mm",),
                facts=facts,
            )
        bases = {f.get("water_basis") for f in facts}
        if len(bases) != 1:
            return self._unknown(
                "Water references use incompatible measurement bases.",
                "CONFLICTING_VERIFIED_FACTS",
                facts=facts,
            )
        expected = next(iter(bases))
        if expected not in {"seasonal_crop_water", "supplemental_irrigation"} or any(
            f.get("unit") != "mm" for f in facts
        ):
            return self._unknown(
                "Water reference must declare a supported measurement basis and mm units.",
                "INCOMPATIBLE_VERIFIED_FACT",
                facts=facts,
            )
        if basis != expected:
            return self._unknown(
                f"This crop reference uses {expected}; the entered {basis} budget cannot be compared with it.",
                "INCOMPATIBLE_WATER_BASIS",
                facts=facts,
            )
        try:
            budget = float(available)
            ranges = {numeric_range(f.get("value")) for f in facts}
            if (
                isinstance(available, bool)
                or not math.isfinite(budget)
                or budget < 0
                or any(lo < 0 for lo, hi in ranges)
            ):
                raise ValueError()
        except (ValueError, TypeError, OverflowError):
            return self._unknown(
                "Water data must use finite non-negative numeric depths.",
                "INCOMPATIBLE_VERIFIED_FACT",
                facts=facts,
            )
        if len(ranges) != 1:
            return self._unknown(
                "Applicable water ranges disagree.", "CONFLICTING_VERIFIED_FACTS", facts=facts
            )
        low, high = next(iter(ranges))
        label = (
            "seasonal crop-water" if basis == "seasonal_crop_water" else "supplemental irrigation"
        )
        if budget < low:
            return self.outcome(
                CheckStatus.VIOLATED,
                f"{budget:g} mm is below the published {low:g}-{high:g} mm {label} reference. This is a screening shortfall, not a prediction of crop failure.",
                "WATER_REFERENCE_SHORTFALL",
                facts,
            )
        if budget < high:
            return self._unknown(
                f"{budget:g} mm falls within the {low:g}-{high:g} mm reference envelope. A local crop-water estimate is needed to decide sufficiency.",
                "LOCAL_WATER_ESTIMATE_REQUIRED",
                facts=facts,
            )
        return self.outcome(
            CheckStatus.SATISFIED,
            f"{budget:g} mm covers the upper end of the {low:g}-{high:g} mm {label} reference. Timing, losses and local requirements remain unverified.",
            "WATER_REFERENCE_COVERED",
            facts,
        )


class SoilPHConstraint(HardConstraint):
    properties = {"soil_ph_range", "ph_range"}

    def __init__(self):
        super().__init__("CONSTRAINT004", "Soil pH range")

    def check(self, candidate, profile, facts):
        actual = _nested(profile, "soil", "ph")
        if _is_unknown(actual):
            return self._unknown("Measured soil pH is needed.", "MISSING_USER_INPUT", ("soil.ph",))
        try:
            ph = float(actual)
            if isinstance(actual, bool) or not math.isfinite(ph) or not 0 <= ph <= 14:
                raise ValueError()
        except (TypeError, ValueError, OverflowError):
            return self._unknown(
                "Soil pH must be a finite number from 0 to 14.",
                "UNSUPPORTED_USER_VALUE",
                ("soil.ph",),
            )
        matches = self.selection(profile, facts, self.properties)
        if not matches:
            return self._unknown(
                "No applicable verified pH screening range is available.", "MISSING_VERIFIED_FACT"
            )
        try:
            ranges = {numeric_range(f.get("value")) for f in matches}
            if any(low < 0 or high > 14 for low, high in ranges):
                raise ValueError()
        except (TypeError, ValueError, OverflowError):
            return self._unknown(
                "Verified pH evidence has a malformed range.",
                "INCOMPATIBLE_VERIFIED_FACT",
                facts=matches,
            )
        if len(ranges) != 1:
            return self._unknown(
                "Applicable verified pH ranges disagree.",
                "CONFLICTING_VERIFIED_FACTS",
                facts=matches,
            )
        low, high = next(iter(ranges))
        passed = low <= ph <= high
        if not passed and any(f.get("range_kind") == "preferred" for f in matches):
            return self._unknown(
                f"pH {ph:g} is outside the published preferred range {low:g}-{high:g}. This does not prove the crop cannot grow; local review is needed.",
                "OUTSIDE_PREFERRED_RANGE",
                facts=matches,
            )
        return self.outcome(
            CheckStatus.SATISFIED if passed else CheckStatus.VIOLATED,
            f'Soil pH {ph:g} is {"within" if passed else "outside"} the supported screening range {low:g}-{high:g}.',
            "SOIL_PH_MATCH" if passed else "SOIL_PH_MISMATCH",
            matches,
        )


DEFAULT_CONSTRAINTS = (
    SeasonConstraint(),
    WaterConstraint(),
    SoilTextureConstraint(),
    SoilPHConstraint(),
)
