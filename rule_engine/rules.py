"""Three explicit IF-THEN rules; all crop suitability checks remain in the CSP."""

from typing import Any

from .models import ConditionResult, Rule, RuleStatus


def condition_has_crop(
    user_profile: dict[str, Any],
    facts: list[dict[str, Any]],
) -> ConditionResult:
    """Check whether a crop has been provided and exists in the facts."""

    crop_id = user_profile.get("crop_id")

    if not crop_id:
        return ConditionResult(
            condition_id="COND_CROP_PRESENT",
            status=RuleStatus.UNKNOWN,
            description="A crop must be provided.",
            missing_fields=("crop_id",),
            reason_codes=("MISSING_CROP",),
        )

    matching_facts = [fact for fact in facts if fact.get("crop_id") in (crop_id, "all")]

    if matching_facts:
        fact_ids = tuple(fact["fact_id"] for fact in matching_facts if fact.get("fact_id"))

        source_ids = tuple(
            source_id for fact in matching_facts for source_id in fact.get("source_ids", [])
        )

        return ConditionResult(
            condition_id="COND_CROP_PRESENT",
            status=RuleStatus.FIRED,
            description=f"Usable knowledge exists for crop '{crop_id}'.",
            fact_ids=fact_ids,
            source_ids=source_ids,
            reason_codes=("FACT_AVAILABLE",),
        )

    return ConditionResult(
        condition_id="COND_CROP_PRESENT",
        status=RuleStatus.UNKNOWN,
        description=f"No usable verified knowledge was found for crop '{crop_id}'.",
        reason_codes=("NO_USABLE_FACT",),
    )


def condition_has_water_evidence(
    user_profile: dict[str, Any],
    facts: list[dict[str, Any]],
) -> ConditionResult:
    """Check whether verified water-related evidence exists for the crop."""

    crop_id = user_profile.get("crop_id")

    if not crop_id:
        return ConditionResult(
            condition_id="COND_WATER_EVIDENCE",
            status=RuleStatus.UNKNOWN,
            description="Water evidence cannot be evaluated without a crop.",
            missing_fields=("crop_id",),
            reason_codes=("MISSING_CROP",),
        )

    water_facts = [
        fact
        for fact in facts
        if fact.get("crop_id") in (crop_id, "all") and fact.get("category") == "water"
    ]

    if water_facts:
        fact_ids = tuple(fact["fact_id"] for fact in water_facts if fact.get("fact_id"))

        source_ids = tuple(
            source_id for fact in water_facts for source_id in fact.get("source_ids", [])
        )

        return ConditionResult(
            condition_id="COND_WATER_EVIDENCE",
            status=RuleStatus.FIRED,
            description="Verified water-related evidence is available.",
            fact_ids=fact_ids,
            source_ids=source_ids,
            reason_codes=("WATER_EVIDENCE_AVAILABLE",),
        )

    return ConditionResult(
        condition_id="COND_WATER_EVIDENCE",
        status=RuleStatus.UNKNOWN,
        description="No verified water-related evidence is available for this crop.",
        reason_codes=("NO_WATER_EVIDENCE",),
    )


def evaluate_crop_knowledge_rule(user_profile, facts):
    """Compatibility helper: use the same evaluator as the full rule engine."""
    from .engine import evaluate_rule

    return evaluate_rule(_evidence_rules()[0], user_profile, facts)


def evaluate_water_evidence_rule(user_profile, facts):
    """Evidence availability is not a crop suitability decision."""
    from .engine import evaluate_rule

    return evaluate_rule(_evidence_rules()[1], user_profile, facts)


def _evidence_rules() -> tuple[Rule, ...]:
    """Return all enabled CropNova rule definitions."""

    return (
        Rule(
            rule_id="RULE_KB_001",
            description=(
                "Check whether usable verified knowledge exists " "for the requested crop."
            ),
            conditions=(condition_has_crop,),
            conclusion=("Verified knowledge is available for evaluation."),
        ),
        Rule(
            rule_id="RULE_WATER_001",
            description=(
                "Check whether verified water-related evidence " "exists for the requested crop."
            ),
            conditions=(condition_has_water_evidence,),
            conclusion=("Verified water-related reference evidence is available."),
        ),
    )


def condition_season_matches(user_profile, facts):
    """Infer a seasonal candidate without bypassing the other CSP requirements."""
    from cropnova.core.constraint_definitions import SeasonConstraint, CheckStatus

    crop_id = user_profile.get("crop_id")
    if not crop_id:
        return condition_has_crop(user_profile, facts)
    outcome = SeasonConstraint().check({"crop_id": crop_id}, user_profile, facts)
    # Evidence is retained for audit even when this specific property is absent.
    fallback_ids = tuple(f["fact_id"] for f in facts if f.get("fact_id"))
    fallback_sources = tuple(dict.fromkeys(s for f in facts for s in f.get("source_ids", [])))
    return ConditionResult(
        "COND_SEASON_MATCH",
        {
            CheckStatus.SATISFIED: RuleStatus.FIRED,
            CheckStatus.VIOLATED: RuleStatus.NOT_FIRED,
            CheckStatus.UNKNOWN: RuleStatus.UNKNOWN,
        }[outcome.status],
        outcome.reason,
        outcome.fact_ids or fallback_ids,
        outcome.source_ids or fallback_sources,
        outcome.missing_fields,
        (outcome.reason_code,),
    )


def get_rules():
    return (
        *_evidence_rules(),
        Rule(
            rule_id="RULE_SEASON_001",
            priority=10,
            description="IF applicable season evidence matches the entered season THEN flag a seasonal candidate.",
            conditions=(condition_has_crop, condition_season_matches),
            conclusion="Season matches; keep this crop for full water, soil and pH assessment.",
        ),
    )
