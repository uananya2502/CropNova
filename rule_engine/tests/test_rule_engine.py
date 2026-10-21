from rule_engine.engine import evaluate_rule, evaluate_rules
from rule_engine.models import (
    ConditionResult,
    Rule,
    RuleStatus,
)

from knowledge_base.loader import load_knowledge
from knowledge_base.retrieval import get_usable_facts


def test_rule_fires_with_verified_crop_knowledge():
    """A crop with usable verified facts should fire the knowledge rule."""

    user_profile = {
        "crop_id": "wheat",
    }

    facts = [
        {
            "fact_id": "FACT_WHEAT_001",
            "crop_id": "wheat",
            "category": "water",
            "source_ids": ["SRC_FAO_CROP_WATER"],
        }
    ]

    evaluation = evaluate_rules(user_profile, facts)

    kb_result = next(
        result
        for result in evaluation.results
        if result.rule_id == "RULE_KB_001"
    )

    assert kb_result.status == RuleStatus.FIRED
    assert "FACT_WHEAT_001" in kb_result.fact_ids
    assert "SRC_FAO_CROP_WATER" in kb_result.source_ids


def test_rule_is_unknown_when_crop_is_missing():
    """Missing crop information should produce UNKNOWN."""

    evaluation = evaluate_rules({}, [])

    for result in evaluation.results:
        assert result.status == RuleStatus.UNKNOWN
        assert "crop_id" in result.missing_fields
        assert "MISSING_CROP" in result.reason_codes


def test_rule_is_unknown_when_no_verified_facts_exist():
    """A crop without usable facts should not automatically pass."""

    user_profile = {
        "crop_id": "unknown_crop",
    }

    evaluation = evaluate_rules(user_profile, [])

    for result in evaluation.results:
        assert result.status == RuleStatus.UNKNOWN


def test_not_fired_condition_is_handled_correctly():
    """The engine must preserve an explicitly false condition."""

    def condition_always_false(user_profile, facts):
        return ConditionResult(
            condition_id="COND_TEST_FALSE",
            status=RuleStatus.NOT_FIRED,
            description="Test condition intentionally failed.",
            reason_codes=("TEST_CONDITION_FALSE",),
        )

    test_rule = Rule(
        rule_id="RULE_TEST_NOT_FIRED",
        description="Test rule for NOT_FIRED behavior.",
        conditions=(condition_always_false,),
        conclusion="This conclusion should not be reached.",
    )

    result = evaluate_rule(
        rule=test_rule,
        user_profile={},
        facts=[],
    )

    assert result.status == RuleStatus.NOT_FIRED
    assert result.rule_id == "RULE_TEST_NOT_FIRED"
    assert "TEST_CONDITION_FALSE" in result.reason_codes


def test_multiple_rules_are_evaluated():
    """The engine should evaluate all enabled rules."""

    evaluation = evaluate_rules(
        {"crop_id": "wheat"},
        [
            {
                "fact_id": "FACT_WHEAT_001",
                "crop_id": "wheat",
                "category": "water",
                "source_ids": ["SRC_FAO_CROP_WATER"],
            }
        ],
    )

    rule_ids = {
        result.rule_id
        for result in evaluation.results
    }

    assert "RULE_KB_001" in rule_ids
    assert "RULE_WATER_001" in rule_ids


def test_rule_result_contains_traceability():
    """Rule results should preserve fact and source traceability."""

    evaluation = evaluate_rules(
        {"crop_id": "wheat"},
        [
            {
                "fact_id": "FACT_WHEAT_001",
                "crop_id": "wheat",
                "category": "water",
                "source_ids": ["SRC_FAO_CROP_WATER"],
            }
        ],
    )

    result = evaluation.results[0]

    assert result.fact_ids
    assert result.source_ids
    assert result.explanation
    assert result.rule_id


def test_rule_engine_with_real_knowledge_base():
    """
    The rule engine should work with CropNova's
    actual knowledge base.
    """

    knowledge = load_knowledge()

    facts = get_usable_facts(
        knowledge,
        crop_id="wheat",
    )

    assert facts

    evaluation = evaluate_rules(
        {"crop_id": "wheat"},
        facts,
    )

    assert evaluation.results

    rule_ids = {
        result.rule_id
        for result in evaluation.results
    }

    assert "RULE_KB_001" in rule_ids
    assert "RULE_WATER_001" in rule_ids

    for result in evaluation.results:
        assert result.fact_ids
        assert result.source_ids