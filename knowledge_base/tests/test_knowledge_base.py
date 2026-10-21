import unittest

from knowledge_base.loader import load_knowledge
from knowledge_base.validator import validate_knowledge
from knowledge_base.query import find_crop
from knowledge_base.retrieval import get_usable_facts


class TestKnowledgeBase(unittest.TestCase):

    def test_load_knowledge(self):
        knowledge = load_knowledge()
        self.assertIn("crops", knowledge)

    def test_validate_knowledge(self):
        knowledge = load_knowledge()
        errors = validate_knowledge(knowledge)
        self.assertEqual(errors, [])

    def test_find_wheat(self):
        knowledge = load_knowledge()
        crop = find_crop(knowledge, "WHEAT")

        self.assertIsNotNone(crop)
        self.assertEqual(crop["crop_id"], "wheat")
        self.assertEqual(crop["common_name"], "Wheat")

    def test_missing_crop(self):
        knowledge = load_knowledge()
        crop = find_crop(knowledge, "unknown_crop")
        self.assertIsNone(crop)

    def test_usable_facts_have_approved_status_and_sources(self):
        knowledge = load_knowledge()
        facts = get_usable_facts(knowledge)

        self.assertGreater(len(facts), 0)

        sources = {
            source["source_id"]: source
            for source in knowledge["sources"]
        }

        for fact in facts:
            self.assertIn(
                fact["verification_status"],
                {"verified_general", "verified_context_specific"},
            )
            self.assertGreater(len(fact["source_ids"]), 0)

            for source_id in fact["source_ids"]:
                self.assertIn(source_id, sources)
                self.assertEqual(
                    sources[source_id]["review_status"],
                    "reviewed_for_inclusion",
                )

    def test_crop_filter_includes_general_facts(self):
        knowledge = load_knowledge()
        facts = get_usable_facts(knowledge, crop_id="wheat")

        self.assertTrue(
            all(fact["crop_id"] in ("all", "wheat") for fact in facts)
        )

    def test_unreviewed_facts_are_not_retrieved(self):
        knowledge = load_knowledge()

        for crop in ["wheat", "rice", "maize", "chickpea"]:
            facts = get_usable_facts(knowledge, crop_id=crop)

            for fact in facts:
                self.assertIn(
                    fact["verification_status"],
                    {"verified_general", "verified_context_specific"},
                )

    def test_reclassified_notes_are_not_retrieved(self):
        knowledge = load_knowledge()

        blocked_ids = {
            "FACT_WHEAT_003",
            "FACT_RICE_003",
            "FACT_MAIZE_003",
            "FACT_CHICKPEA_001",
            "FACT_CHICKPEA_003",
        }

        for crop in ["wheat", "rice", "maize", "chickpea"]:
            facts = get_usable_facts(knowledge, crop_id=crop)
            retrieved_ids = {fact["fact_id"] for fact in facts}

            self.assertTrue(blocked_ids.isdisjoint(retrieved_ids))

    def test_cropnova_policies_are_not_agricultural_facts(self):
        knowledge = load_knowledge()
        fact_ids = {fact["fact_id"] for fact in knowledge["facts"]}

        self.assertNotIn("FACT_GENERAL_009", fact_ids)
        self.assertNotIn("FACT_GENERAL_010", fact_ids)


if __name__ == "__main__":
    unittest.main()
