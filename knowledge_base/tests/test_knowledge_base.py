
import unittest

from knowledge_base.loader import load_knowledge
from knowledge_base.validator import validate_knowledge
from knowledge_base.query import find_crop


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
        self.assertEqual(crop["name"], "wheat")

    def test_missing_crop(self):
        knowledge = load_knowledge()
        crop = find_crop(knowledge, "unknown_crop")
        self.assertIsNone(crop)


if __name__ == "__main__":
    unittest.main()

