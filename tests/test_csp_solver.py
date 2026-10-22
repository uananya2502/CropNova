import unittest

from csp_solver import solve_constraints
from constraint_definitions import SeasonConstraint


def fact(fact_id, prop, value):
    return {
        "fact_id": fact_id,
        "property": prop,
        "value": value,
        "verification_status": "verified",
        "source_ids": ["SRC-TEST"],
        "applicability": {"region": "Test State"},
    }


def candidate(candidate_id, *, season="rabi", water="low", texture="loamy", ph=(6, 8)):
    return {
        "crop_id": candidate_id,
        "name": candidate_id,
        "facts": [
            fact(f"{candidate_id}-S", "growing_season", season),
            fact(f"{candidate_id}-W", "water_requirement", water),
            fact(f"{candidate_id}-T", "soil_texture", texture),
            fact(f"{candidate_id}-P", "soil_ph_range", list(ph)),
        ],
    }


PROFILE = {
    "region": {"state": "Test State", "district": None},
    "season": "rabi",
    "soil": {"texture": "loamy", "ph": 7.0, "fertility": "unknown"},
    "water": {"availability": "moderate", "irrigation": "unknown"},
    "objective": "find_suitable_crop",
}


class TestCSPSolver(unittest.TestCase):
    def test_one_feasible_assignment(self):
        result = solve_constraints([candidate("A")], PROFILE)
        self.assertEqual(result["status"], "satisfiable")
        self.assertEqual([row["candidate_id"] for row in result["feasible_candidates"]], ["A"])
        self.assertEqual(result["diagnostics"]["assignments_examined"], 1)

    def test_hard_constraint_rejection(self):
        result = solve_constraints([candidate("A", water="high")], PROFILE)
        self.assertEqual(result["status"], "unsatisfiable")
        failed = result["rejected_candidates"][0]["failed_constraints"]
        self.assertIn("CONSTRAINT002", {row["constraint_id"] for row in failed})

    def test_multiple_feasible_candidates_are_deterministic(self):
        result = solve_constraints([candidate("A"), candidate("B")], PROFILE)
        self.assertEqual([row["candidate_id"] for row in result["feasible_candidates"]], ["A", "B"])

    def test_no_feasible_assignment_returns_conflicts(self):
        result = solve_constraints(
            [candidate("A", season="kharif"), candidate("B", texture="sandy")],
            PROFILE,
        )
        self.assertEqual(result["status"], "unsatisfiable")
        self.assertEqual(len(result["conflicts"]), 2)

    def test_unknown_user_input_is_not_satisfied(self):
        profile = {**PROFILE, "season": "unknown"}
        result = solve_constraints([candidate("A")], profile)
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["feasible_candidates"], [])
        self.assertEqual(
            result["unknown_candidates"][0]["unknown_constraints"][0]["reason_code"],
            "MISSING_USER_INPUT",
        )
        self.assertFalse(result["diagnostics"]["unknown_is_satisfied"])
    
    def test_wheat_rabi_season_uses_verified_fact(self):
        from knowledge_base.loader import load_knowledge
        from knowledge_base.retrieval import get_usable_facts

        knowledge = load_knowledge()
        facts = get_usable_facts(knowledge, crop_id="wheat")

        candidate_record = {
            "candidate_id": "wheat",
            "name": "Wheat",
        }

        profile = {
            "season": "rabi",
            "region": {
                "state": "Haryana",
                "district": "Rewari",
            },
        }

        result = SeasonConstraint().check(
            candidate_record,
            profile,
            facts,
        )

        self.assertEqual(result.status.value, "satisfied")
        self.assertIn("FACT_WHEAT_004", result.fact_ids)
        self.assertIn("SRC_CCSHAU_RABI_SEED_001", result.source_ids)


    def test_unverified_fact_is_not_satisfied(self):
        item = candidate("A")
        item["facts"][0]["verification_status"] = "pending_research"
        result = solve_constraints([item], PROFILE)
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["feasible_candidates"], [])
    
    def test_numeric_wheat_water_range_returns_unknown_with_evidence(self):
        from knowledge_base.loader import load_knowledge
        from knowledge_base.retrieval import get_usable_facts
        from constraint_definitions import WaterConstraint

        knowledge = load_knowledge()
        facts = get_usable_facts(knowledge, crop_id="wheat")

        profile = {
            "region": {"state": "Haryana", "district": "Rewari"},
            "water": {"availability": "moderate"},
        }

        result = WaterConstraint().check(
            {"candidate_id": "wheat", "name": "Wheat"},
            profile,
            facts,
        )

        self.assertEqual(result.status.value, "unknown")
        self.assertEqual(result.reason_code, "INCOMPATIBLE_WATER_UNITS")
        self.assertIn("FACT_WHEAT_001", result.fact_ids)
        self.assertIn("SRC_FAO_WATER_001", result.source_ids)
    
    def test_missing_real_soil_evidence_returns_unknown(self):
        from knowledge_base.loader import load_knowledge
        from knowledge_base.retrieval import get_usable_facts
        from constraint_definitions import (
            SoilTextureConstraint,
            SoilPHConstraint,
        )

        knowledge = load_knowledge()
        facts = get_usable_facts(knowledge, crop_id="wheat")

        candidate = {"candidate_id": "wheat", "name": "Wheat"}
        profile = {
            "region": {"state": "Haryana", "district": "Rewari"},
            "soil": {"texture": "loamy", "ph": 7.0},
        }

        for constraint in (
            SoilTextureConstraint(),
            SoilPHConstraint(),
        ):
            with self.subTest(constraint=constraint.name):
                result = constraint.check(candidate, profile, facts)

                self.assertEqual(result.status.value, "unknown")
                self.assertEqual(result.reason_code, "MISSING_VERIFIED_FACT")
                self.assertEqual(result.fact_ids, ())
                self.assertEqual(result.source_ids, ())


if __name__ == "__main__":
    unittest.main()

