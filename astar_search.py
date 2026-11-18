"""Small A* graph search for covering follow-up requirements with positive-cost actions.

States are frozensets of completed requirements. Actions can cover several
requirements and can require earlier tasks. No action changes a real farm.
"""

from dataclasses import dataclass
import heapq
from itertools import count
import math


@dataclass(frozen=True)
class Action:
    action_id: str
    title: str
    cost: float
    covers: frozenset[str]
    requires: frozenset[str] = frozenset()


def remaining_cost(state, goals, actions):
    """An admissible, consistent lower bound, even when one action covers many needs.

    Every unmet requirement needs at least one covering action. Take the MAX of
    those cheapest costs, not their sum (summing could count a shared action twice).
    Ignoring prerequisites can only make this estimate more optimistic.
    """
    cheapest_costs = []
    for need in goals - state:
        covering_costs = [action.cost for action in actions if need in action.covers]
        cheapest_costs.append(min(covering_costs, default=math.inf))
    return max(cheapest_costs, default=0.0)


def reconstruct(goal, parents):
    steps = []
    state = goal
    while state in parents:
        previous, action = parents[state]
        steps.append(
            {
                "action_id": action.action_id,
                "title": action.title,
                "cost": action.cost,
                "covers": sorted(state - previous),
                "state_after": sorted(state),
            }
        )
        state = previous
    return list(reversed(steps))


def search_plan(requirements, actions, *, algorithm="astar", initial=(), max_expanded=4096):
    """A* chooses min(g+h); uniform-cost search uses h=0 for comparison tests."""
    if algorithm not in {"astar", "uniform_cost"}:
        raise ValueError("Choose astar or uniform_cost.")
    goals, start = frozenset(requirements), frozenset(initial)
    actions = tuple(actions)
    if not start <= goals:
        raise ValueError("Initial state must contain only declared requirements.")
    if len({action.action_id for action in actions}) != len(actions):
        raise ValueError("Action IDs must be unique.")
    for action in actions:
        if (
            isinstance(action.cost, bool)
            or not isinstance(action.cost, (int, float))
            or not math.isfinite(action.cost)
            or action.cost <= 0
        ):
            raise ValueError("Action costs must be finite and positive.")
    # Uncoverable goals have no finite solution; keep diagnostics valid JSON.
    available = set()
    for action in actions:
        available.update(action.covers)
    if goals - start - available:
        return {
            "status": "no_plan",
            "algorithm": algorithm,
            "cost": None,
            "steps": [],
            "expanded": 0,
            "initial_state": sorted(start),
            "goal_state": sorted(goals),
            "trace": [],
        }

    def estimate(state):
        if algorithm == "uniform_cost":
            return 0.0
        return remaining_cost(state, goals, actions)

    serial = count()
    frontier = [(estimate(start), estimate(start), next(serial), 0.0, start)]
    best_cost, parents, trace = {start: 0.0}, {}, []
    expanded = 0
    while frontier and expanded < max_expanded:
        _, h, _, cost, state = heapq.heappop(frontier)
        if cost != best_cost[state]:
            continue  # A cheaper route to this state replaced this queued entry.
        expanded += 1
        if len(trace) < 40:
            trace.append({"state": sorted(state), "g": cost, "h": h, "f": cost + h})
        if goals <= state:
            return {
                "status": "goal_reached",
                "algorithm": algorithm,
                "cost": cost,
                "steps": reconstruct(state, parents),
                "expanded": expanded,
                "initial_state": sorted(start),
                "goal_state": sorted(goals),
                "trace": trace,
            }
        for action in actions:
            if not action.requires <= state:
                continue
            next_state = state | (action.covers & goals)
            if next_state == state:
                continue
            next_cost = cost + action.cost
            if next_cost < best_cost.get(next_state, math.inf):
                best_cost[next_state] = next_cost
                parents[next_state] = state, action
                next_h = estimate(next_state)
                heapq.heappush(
                    frontier, (next_cost + next_h, next_h, next(serial), next_cost, next_state)
                )
    return {
        "status": "limit_reached" if frontier else "no_plan",
        "algorithm": algorithm,
        "cost": None,
        "steps": [],
        "expanded": expanded,
        "initial_state": sorted(start),
        "goal_state": sorted(goals),
        "trace": trace,
    }
