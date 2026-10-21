from typing import Any

from .models import ConditionResult, Rule, RuleResult, RuleStatus


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

    matching_facts = [
        fact
        for fact in facts
        if fact.get("crop_id") in (crop_id, "all")
    ]

    if matching_facts:
        fact_ids = tuple(
            fact["fact_id"]
            for fact in matching_facts
            if fact.get("fact_id")
        )

        source_ids = tuple(
            source_id
            for fact in matching_facts
            for source_id in fact.get("source_ids", [])
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
        if fact.get("crop_id") in (crop_id, "all")
        and fact.get("category") == "water"
    ]

    if water_facts:
        fact_ids = tuple(
            fact["fact_id"]
            for fact in water_facts
            if fact.get("fact_id")
        )

        source_ids = tuple(
            source_id
            for fact in water_facts
            for source_id in fact.get("source_ids", [])
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


def evaluate_crop_knowledge_rule(
    user_profile: dict[str, Any],
    facts: list[dict[str, Any]],
) -> RuleResult:
    """
    RULE_KB_001:
    IF a crop is provided AND usable verified knowledge exists
    THEN verified knowledge is available for evaluation.
    """

    condition = condition_has_crop(user_profile, facts)

    if condition.status == RuleStatus.FIRED:
        return RuleResult(
            rule_id="RULE_KB_001",
            status=RuleStatus.FIRED,
            evaluated_conditions=(condition,),
            conclusion="Verified knowledge is available for this crop.",
            explanation=(
                "The rule fired because usable source-reviewed knowledge "
                "was found for the requested crop."
            ),
            fact_ids=condition.fact_ids,
            source_ids=condition.source_ids,
            reason_codes=("FACT_AVAILABLE",),
        )

    if condition.status == RuleStatus.UNKNOWN:
        return RuleResult(
            rule_id="RULE_KB_001",
            status=RuleStatus.UNKNOWN,
            evaluated_conditions=(condition,),
            conclusion="The knowledge-supported assessment is undetermined.",
            explanation=(
                "The rule could not establish crop-specific usable knowledge "
                "from the available verified evidence."
            ),
            missing_fields=condition.missing_fields,
            reason_codes=condition.reason_codes,
        )

    return RuleResult(
        rule_id="RULE_KB_001",
        status=RuleStatus.NOT_FIRED,
        evaluated_conditions=(condition,),
        conclusion="Verified knowledge was not established.",
        explanation="The required knowledge condition was not satisfied.",
        reason_codes=("KNOWLEDGE_NOT_ESTABLISHED",),
    )


def evaluate_water_evidence_rule(
    user_profile: dict[str, Any],
    facts: list[dict[str, Any]],
) -> RuleResult:
    """
    RULE_WATER_001:
    IF verified water-related evidence exists
    THEN report that evidence is available.

    This does NOT determine irrigation suitability or an irrigation schedule.
    """

    condition = condition_has_water_evidence(user_profile, facts)

    if condition.status == RuleStatus.FIRED:
        return RuleResult(
            rule_id="RULE_WATER_001",
            status=RuleStatus.FIRED,
            evaluated_conditions=(condition,),
            conclusion=(
                "Verified water-related reference evidence is available."
            ),
            explanation=(
                "The rule fired because the knowledge base contains "
                "verified water-related evidence for this crop. "
                "This evidence is indicative and does not by itself "
                "establish a local irrigation schedule or crop suitability."
            ),
            fact_ids=condition.fact_ids,
            source_ids=condition.source_ids,
            reason_codes=("WATER_EVIDENCE_AVAILABLE",),
        )

    return RuleResult(
        rule_id="RULE_WATER_001",
        status=RuleStatus.UNKNOWN,
        evaluated_conditions=(condition,),
        conclusion=(
            "Water-related evidence could not be established."
        ),
        explanation=(
            "No verified water-related evidence could be established "
            "for the requested crop from the available knowledge."
        ),
        fact_ids=condition.fact_ids,
        source_ids=condition.source_ids,
        missing_fields=condition.missing_fields,
        reason_codes=condition.reason_codes,
    )


def get_rules() -> tuple[Rule, ...]:
    """Return all enabled CropNova rule definitions."""

    return (
        Rule(
            rule_id="RULE_KB_001",
            description=(
                "Check whether usable verified knowledge exists "
                "for the requested crop."
            ),
            conditions=(condition_has_crop,),
            conclusion=(
                "Verified knowledge is available for evaluation."
            ),
        ),
        Rule(
            rule_id="RULE_WATER_001",
            description=(
                "Check whether verified water-related evidence "
                "exists for the requested crop."
            ),
            conditions=(condition_has_water_evidence,),
            conclusion=(
                "Verified water-related reference evidence is available."
            ),
        ),
    )