from typing import Any

from .models import RuleEvaluation, RuleResult, RuleStatus
from .rules import get_rules


def evaluate_rule(
    rule: Any,
    user_profile: dict[str, Any],
    facts: list[dict[str, Any]],
) -> RuleResult:
    """
    Evaluate one CropNova rule.

    A rule:
    - FIRES when all conditions are satisfied.
    - is NOT_FIRED when a condition fails.
    - is UNKNOWN when a required condition cannot be evaluated.
    """

    condition_results = tuple(
        condition(user_profile, facts)
        for condition in rule.conditions
    )

    statuses = {
        result.status
        for result in condition_results
    }

    if RuleStatus.UNKNOWN in statuses:
        status = RuleStatus.UNKNOWN
    elif RuleStatus.NOT_FIRED in statuses:
        status = RuleStatus.NOT_FIRED
    else:
        status = RuleStatus.FIRED

    fact_ids = tuple(
        fact_id
        for result in condition_results
        for fact_id in result.fact_ids
    )

    source_ids = tuple(
        source_id
        for result in condition_results
        for source_id in result.source_ids
    )

    missing_fields = tuple(
        field
        for result in condition_results
        for field in result.missing_fields
    )

    reason_codes = tuple(
        code
        for result in condition_results
        for code in result.reason_codes
    )

    if status == RuleStatus.FIRED:
        explanation = (
            f"Rule {rule.rule_id} fired because all required "
            "conditions were satisfied."
        )
    elif status == RuleStatus.NOT_FIRED:
        explanation = (
            f"Rule {rule.rule_id} did not fire because at least "
            "one condition was not satisfied."
        )
    else:
        explanation = (
            f"Rule {rule.rule_id} could not be fully evaluated "
            "because required information or evidence is unknown."
        )

    return RuleResult(
        rule_id=rule.rule_id,
        status=status,
        evaluated_conditions=condition_results,
        conclusion=rule.conclusion,
        explanation=explanation,
        fact_ids=tuple(dict.fromkeys(fact_ids)),
        source_ids=tuple(dict.fromkeys(source_ids)),
        missing_fields=tuple(dict.fromkeys(missing_fields)),
        reason_codes=tuple(dict.fromkeys(reason_codes)),
    )


def evaluate_rules(
    user_profile: dict[str, Any],
    facts: list[dict[str, Any]],
) -> RuleEvaluation:
    """
    Evaluate all enabled CropNova rules.
    """

    results = []

    for rule in get_rules():
        if not rule.enabled:
            continue

        result = evaluate_rule(
            rule=rule,
            user_profile=user_profile,
            facts=facts,
        )

        results.append(result)

    return RuleEvaluation(results=results)