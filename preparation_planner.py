"""Turn unresolved findings into an A* plan for gathering and reviewing information.

The goal is to COVER FOLLOW-UP TASKS, not to make crops feasible. Completing a
planned action still needs real observations or a review; saved findings stay
unchanged. Relative effort points are design settings, not time or money quotes.
"""

from astar_search import Action, search_plan
from assessment_summary import CHECK_NAMES

INPUT_TASKS = {
    "season": ("Confirm the intended growing season", 1.0),
    "soil.ph": ("Obtain the measured soil pH", 3.0),
    "soil.texture": ("Identify the soil texture", 2.0),
    "soil.drainage": ("Check the field drainage", 1.0),
    "water.budget_mm": ("Estimate the seasonal water budget and its basis", 2.0),
    "water.availability": ("Confirm the available water category", 2.0),
}
NOTE = (
    "This plan organises follow-up tasks using relative effort points, not hours or money. "
    "It does not change your inputs or findings. Completing a task means gathering or "
    "reviewing information; it does not guarantee a crop will match."
)


def follow_up_needs(report):
    """Share missing input tasks across crops, but keep evidence reviews crop-specific."""
    needs = {}
    for group in ("feasible_candidates", "unknown_candidates", "rejected_candidates"):
        for crop in report.get("csp_result", {}).get(group, []):
            for outcome in crop["unknown_constraints"] + crop["failed_constraints"]:
                if outcome["reason_code"] == "MISSING_USER_INPUT" and outcome.get("missing_fields"):
                    for field in outcome["missing_fields"]:
                        key = "input:" + field
                        label = INPUT_TASKS.get(field, ("Confirm " + field.replace(".", " "), 2))[0]
                        needs[key] = {"id": key, "label": label, "kind": "input", "field": field}
                else:
                    key = "review:" + crop["candidate_id"] + ":" + outcome["constraint_id"]
                    name = CHECK_NAMES.get(outcome["constraint_id"], "Field condition")
                    needs[key] = {
                        "id": key,
                        "label": crop["name"].title() + " - review " + name.lower(),
                        "kind": "review",
                        "check_id": outcome["constraint_id"],
                        "reason": outcome["reason"],
                        "source_ids": outcome.get("source_ids", []),
                    }
    return list(needs.values())


def available_actions(needs):
    """Offer individual measurements, a combined soil task and grouped reviews."""
    ids = {need["id"] for need in needs}
    actions = []
    for field, (title, cost) in INPUT_TASKS.items():
        key = "input:" + field
        if key in ids:
            actions.append(Action("confirm-" + field, title, cost, frozenset({key})))
    soil_needs = ids & {"input:soil.ph", "input:soil.texture"}
    if len(soil_needs) == 2:
        actions.append(
            Action(
                "gather-soil-results",
                "Obtain pH and texture results together",
                4.0,
                frozenset(soil_needs),
            )
        )
    prerequisites = {
        "CONSTRAINT001": {"input:season"},
        "CONSTRAINT002": {"input:water.budget_mm", "input:water.availability"},
        "CONSTRAINT003": {"input:soil.texture", "input:soil.drainage"},
        "CONSTRAINT004": {"input:soil.ph"},
    }
    reviews = [need for need in needs if need["kind"] == "review"]
    titles = {
        "CONSTRAINT001": "Review local season guidance",
        "CONSTRAINT002": "Review water estimates and measurement bases",
        "CONSTRAINT003": "Review local soil guidance",
        "CONSTRAINT004": "Review the pH result against local guidance",
    }
    for check_id, title in titles.items():
        covers = {need["id"] for need in reviews if need["check_id"] == check_id}
        if covers:
            actions.append(
                Action(
                    "review-" + check_id,
                    title,
                    3.0,
                    frozenset(covers),
                    frozenset(ids & prerequisites[check_id]),
                )
            )
    if reviews:
        actions.append(
            Action(
                "combined-guidance-review",
                "Discuss the open findings together with a local adviser",
                6.0,
                frozenset(need["id"] for need in reviews),
                frozenset(key for key in ids if key.startswith("input:")),
            )
        )
    return actions


def plan_assessment(report, *, algorithm="astar"):
    needs = follow_up_needs(report)
    actions = available_actions(needs)
    result = search_plan([need["id"] for need in needs], actions, algorithm=algorithm)
    # This is a plan for future information work. No observations are fabricated.
    return {
        **result,
        "goal": "cover_follow_up_tasks",
        "needs": needs,
        "note": NOTE,
        "cost_unit": "relative_effort_points",
        "actions": [
            {
                "action_id": action.action_id,
                "title": action.title,
                "cost": action.cost,
                "covers": sorted(action.covers),
                "requires": sorted(action.requires),
            }
            for action in actions
        ],
    }
