from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RuleStatus(str, Enum):
    """Status of a rule evaluation."""

    FIRED = "fired"
    NOT_FIRED = "not_fired"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ConditionResult:
    """Result of evaluating one rule condition."""

    condition_id: str
    status: RuleStatus
    description: str
    fact_ids: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    missing_fields: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class RuleResult:
    """Complete explainable result produced by the rule engine."""

    rule_id: str
    status: RuleStatus
    evaluated_conditions: tuple[ConditionResult, ...]
    conclusion: str
    explanation: str
    fact_ids: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    missing_fields: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Convert the rule result into a JSON-friendly dictionary."""

        return {
            "rule_id": self.rule_id,
            "status": self.status.value,
            "evaluated_conditions": [
                {
                    "condition_id": condition.condition_id,
                    "status": condition.status.value,
                    "description": condition.description,
                    "fact_ids": list(condition.fact_ids),
                    "source_ids": list(condition.source_ids),
                    "missing_fields": list(condition.missing_fields),
                    "reason_codes": list(condition.reason_codes),
                }
                for condition in self.evaluated_conditions
            ],
            "conclusion": self.conclusion,
            "explanation": self.explanation,
            "fact_ids": list(self.fact_ids),
            "source_ids": list(self.source_ids),
            "missing_fields": list(self.missing_fields),
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class Rule:
    """Definition of one deterministic IF-THEN rule."""

    rule_id: str
    description: str
    conditions: tuple[Any, ...]
    conclusion: str
    priority: int = 0
    enabled: bool = True


@dataclass
class RuleEvaluation:
    """Collection of results from evaluating multiple rules."""

    results: list[RuleResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert all rule results into a JSON-friendly dictionary."""

        return {
            "results": [result.to_dict() for result in self.results]
        }