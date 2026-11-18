"""Optimality, admissibility, transitions and honest follow-up planning."""

from copy import deepcopy
from itertools import combinations
import json
import math
import pytest

from agent import run_assessment
from astar_search import Action, remaining_cost, search_plan
from preparation_planner import plan_assessment, available_actions
from public_profiles import REFERENCE_PROFILES
from web_views import result_page
from assessment_pages import saved_page

PROFILE = REFERENCE_PROFILES["reference-wheat"]
ACTIONS = (
    Action("ph", "Measure pH", 3, frozenset({"ph"})),
    Action("soil", "Identify texture", 2, frozenset({"texture"})),
    Action("combined", "Get both soil results", 4, frozenset({"ph", "texture"})),
    Action("review", "Review results", 1, frozenset({"review"}), frozenset({"ph", "texture"})),
)
GOALS = frozenset({"ph", "texture", "review"})


def test_astar_finds_cheaper_combined_action_and_respects_prerequisites():
    result = search_plan(GOALS, ACTIONS)
    assert result["status"] == "goal_reached" and result["cost"] == 5
    assert [step["action_id"] for step in result["steps"]] == ["combined", "review"]
    assert result["steps"][0]["state_after"] == ["ph", "texture"]
    assert result["steps"][-1]["state_after"] == sorted(GOALS)
    assert all(row["f"] == row["g"] + row["h"] for row in result["trace"])


def test_heuristic_is_admissible_and_consistent_on_every_toy_state():
    for count in range(len(GOALS) + 1):
        for subset in combinations(GOALS, count):
            state = frozenset(subset)
            h = remaining_cost(state, GOALS, ACTIONS)
            exact = search_plan(GOALS, ACTIONS, algorithm="uniform_cost", initial=state)
            assert h <= exact["cost"]
            for action in ACTIONS:
                if action.requires <= state:
                    successor = state | action.covers
                    assert h <= action.cost + remaining_cost(successor, GOALS, ACTIONS)


def test_astar_and_uniform_cost_agree_for_all_initial_states():
    for count in range(len(GOALS) + 1):
        for subset in combinations(GOALS, count):
            astar = search_plan(GOALS, ACTIONS, initial=subset)
            uniform = search_plan(GOALS, ACTIONS, algorithm="uniform_cost", initial=subset)
            assert astar["cost"] == uniform["cost"]


def test_already_complete_has_zero_cost_and_no_actions():
    result = search_plan(GOALS, ACTIONS, initial=GOALS)
    assert result["cost"] == 0 and result["steps"] == []


def test_uncoverable_goal_does_not_emit_infinite_json():
    result = search_plan({"absent"}, ACTIONS)
    assert result["status"] == "no_plan"
    json.dumps(result, allow_nan=False)


def test_circular_prerequisite_is_not_an_executable_plan():
    action = Action("loop", "Impossible action", 1, frozenset({"x"}), frozenset({"x"}))
    assert search_plan({"x"}, [action])["status"] == "no_plan"


def test_expansion_limit_is_not_reported_as_an_optimal_plan():
    result = search_plan(GOALS, ACTIONS, max_expanded=1)
    assert result["status"] == "limit_reached" and result["cost"] is None and result["steps"] == []


@pytest.mark.parametrize("cost", [-1, 0, math.nan, math.inf, True, "one"])
def test_invalid_action_cost_is_rejected(cost):
    with pytest.raises(ValueError):
        search_plan({"x"}, [Action("bad", "Bad", cost, frozenset({"x"}))])


def test_duplicate_action_ids_are_rejected():
    with pytest.raises(ValueError):
        search_plan(GOALS, [ACTIONS[0], ACTIONS[0]])


def test_all_measurement_tasks_are_covered_with_no_report_mutation():
    report = run_assessment(
        {
            **PROFILE,
            "soil_ph": "",
            "soil_texture": "unknown",
            "season": "unknown",
            "water_budget_mm": "",
        }
    )
    before = deepcopy(report)
    result = plan_assessment(report)
    assert result["cost"] == 7 and result["status"] == "goal_reached"
    assert any(step["action_id"] == "gather-soil-results" for step in result["steps"])
    assert len(result["steps"]) == 3
    assert result["goal"] == "cover_follow_up_tasks"
    assert report == before and report["status"] == "MORE_INFORMATION_NEEDED"


def test_missing_input_tasks_are_shared_across_crops():
    report = run_assessment({**PROFILE, "candidate_ids": [], "soil_ph": ""})
    needs = report["preparation_plan"]["needs"]
    assert sum(need["id"] == "input:soil.ph" for need in needs) == 1


def test_known_violation_is_a_review_task_not_a_fake_fix():
    report = run_assessment({**PROFILE, "water_budget_mm": "300"})
    plan = report["preparation_plan"]
    assert any(need["kind"] == "review" for need in plan["needs"])
    assert report["status"] == "NO_FEASIBLE_OPTION"
    assert plan["goal"] == "cover_follow_up_tasks" and "does not guarantee" in plan["note"]


@pytest.mark.parametrize("preset", list(REFERENCE_PROFILES))
def test_fully_matched_examples_have_no_artificial_follow_up_tasks(preset):
    plan = run_assessment(REFERENCE_PROFILES[preset])["preparation_plan"]
    assert plan["status"] == "goal_reached" and plan["cost"] == 0 and plan["steps"] == []


def test_public_plan_uses_friendly_wording_and_retains_limitations():
    report = run_assessment({**PROFILE, "soil_ph": ""})
    html = saved_page(report, "private-token", "plan").decode()
    assert "A practical order for following up" in html
    assert "relative effort points" not in html and "guarantee that a crop will match" in html
    assert "A*" not in html and "heuristic" not in html
