import unittest
from unittest.mock import patch

from agent import run_assessment


VALID = {
    "state": "Test State",
    "season": "rabi",
    "soil_texture": "loamy",
    "soil_ph": "7.0",
    "soil_fertility": "moderate",
    "water_availability": "moderate",
    "irrigation": "available",
    "objective": "find_suitable_crop",
}


class TestAgent(unittest.TestCase):

    def test_invalid_profile_has_structured_error(self):
        result = run_assessment(
            {**VALID, "soil_ph": "20"}
        )

        self.assertEqual(
            result["status"],
            "INVALID_INPUT",
        )

        self.assertEqual(
            result["errors"][0]["code"],
            "OUT_OF_RANGE",
        )

    def test_pending_knowledge_is_not_presented_as_supported(self):
        result = run_assessment(VALID)

        self.assertEqual(
            result["status"],
            "NO_SUPPORTED_KNOWLEDGE",
        )

        self.assertEqual(
            result["feasible_options"],
            [],
        )

        self.assertTrue(
            result["unknown_options"]
        )

        self.assertEqual(
            result["knowledge_summary"]["total_crops"],
            4,
        )

        self.assertGreater(
            result["knowledge_summary"]["usable_facts"],
            0,
        )

        self.assertGreater(
            result["knowledge_summary"]["total_sources"],
            0,
        )

    def test_missing_input_creates_targeted_follow_up(self):
        result = run_assessment(
            {
                **VALID,
                "season": "unknown",
            }
        )

        self.assertEqual(
            result["status"],
            "MORE_INFORMATION_NEEDED",
        )

        self.assertTrue(
            any(
                "season" in question.casefold()
                for question in result["follow_up_questions"]
            )
        )

    def test_evidence_package_preserves_status(self):
        result = run_assessment(VALID)

        self.assertEqual(
            result["evidence_package"]["assessment_status"],
            result["status"],
        )

    def test_verified_repository_shape_flows_through_full_pipeline(self):

        def fact(fact_id, prop, value):
            return {
                "fact_id": fact_id,
                "crop_id": "fixture-crop",
                "category": prop,
                "statement": (
                    f"Synthetic {prop} fact "
                    "for integration testing."
                ),
                "value": value,
                "unit": None,
                "verification_status": (
                    "verified_context_specific"
                ),
                "source_ids": ["SRC001"],
                "applicability": {
                    "country": "India",
                    "state": "Test State",
                },
                "confidence": "high",
                "notes": "Synthetic test fixture only.",
            }

        facts = [
            fact(
                "FACT001",
                "growing_season",
                "rabi",
            ),
            fact(
                "FACT002",
                "water_requirement",
                "low",
            ),
            fact(
                "FACT003",
                "soil_texture",
                "loamy",
            ),
            fact(
                "FACT004",
                "soil_ph_range",
                [6.0, 8.0],
            ),
        ]

        knowledge = {
            "metadata": {
                "version": "test",
                "status": "verified_fixture",
            },
            "crops": [
                {
                    "crop_id": "fixture-crop",
                    "common_name": "Fixture crop",
                    "crop_group": "test-only",
                    "scientific_name": "Fixture example",
                    "status": "active_prototype",
                    "source_ids": ["SRC001"],
                    "fact_ids": [
                        item["fact_id"]
                        for item in facts
                    ],
                }
            ],
            "facts": facts,
            "sources": [
                {
                    "source_id": "SRC001",
                    "title": (
                        "Synthetic integration fixture"
                    ),
                    "url": (
                        "https://example.test/source"
                    ),
                    "review_status": (
                        "reviewed_for_inclusion"
                    ),
                }
            ],
        }

        with patch(
            "agent.load_knowledge",
            return_value=knowledge,
        ):
            result = run_assessment(VALID)

        self.assertEqual(
            result["status"],
            "FEASIBLE_OPTIONS_FOUND",
        )

        self.assertEqual(
            result["feasible_options"][0][
                "candidate_id"
            ],
            "fixture-crop",
        )

        self.assertEqual(
            result["knowledge_summary"][
                "verified_facts"
            ],
            4,
        )

        self.assertEqual(
            result["evidence"][0]["source_id"],
            "SRC001",
        )

    def test_agent_integrates_rule_engine(self):
        """
        Verify that the Agent actually invokes the
        Rule Engine and receives structured rule results.
        """

        profile = {
            "state": "Haryana",
            "season": "rabi",
            "soil_texture": "loamy",
            "soil_fertility": "moderate",
            "water_availability": "moderate",
            "irrigation": "available",
            "objective": "find_suitable_crop",
            "candidate_ids": ["wheat"],
        }

        result = run_assessment(profile)

        # The Agent should not fail at the Rule Engine
        # integration boundary.
        self.assertNotEqual(
            result["status"],
            "SYSTEM_ERROR",
        )

        # Rule Engine fields must be present.
        self.assertIn(
            "rule_status",
            result,
        )

        self.assertIn(
            "rule_trace",
            result,
        )

        self.assertIn(
            "rule_results",
            result,
        )

        # rule_results should be a list.
        self.assertIsInstance(
            result["rule_results"],
            list,
        )

        # At least one crop should have been evaluated.
        self.assertTrue(
            result["rule_results"]
        )

        # Wheat should be among the evaluated crops.
        wheat_result = next(
            item
            for item in result["rule_results"]
            if item["crop_id"] == "wheat"
        )

        # Each crop should contain Rule Engine results.
        self.assertIn(
            "results",
            wheat_result,
        )

        self.assertTrue(
            wheat_result["results"]
        )

        # Verify that our actual Rule Engine rules
        # reached the Agent.
        rule_ids = {
            result_item["rule_id"]
            for result_item in wheat_result["results"]
        }

        self.assertIn(
            "RULE_KB_001",
            rule_ids,
        )

        self.assertIn(
            "RULE_WATER_001",
            rule_ids,
        )


if __name__ == "__main__":
    unittest.main()