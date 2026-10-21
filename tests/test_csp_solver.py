import unittest

from csp_solver import solve_constraints


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

    def test_unverified_fact_is_not_satisfied(self):
        item = candidate("A")
        item["facts"][0]["verification_status"] = "pending_research"
        result = solve_constraints([item], PROFILE)
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["feasible_candidates"], [])


if __name__ == "__main__":
    unittest.main()

