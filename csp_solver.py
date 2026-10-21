"""Explainable constraint-satisfaction solver for CropNova.

Version 1 has one variable, ``selected_crop``.  Its domain is the candidate
list received from the rule engine.  Backtracking visits each domain value and
keeps only complete assignments for which every hard constraint is satisfied.
Unknown checks are deliberately not treated as satisfied.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from constraint_definitions import CheckStatus, DEFAULT_CONSTRAINTS, HardConstraint


@dataclass(frozen=True)
class CSPProblem:
    variables: tuple[str, ...]
    domains: Mapping[str, tuple[dict[str, Any], ...]]
    constraints: tuple[HardConstraint, ...]


def _candidate(candidate: Any, index: int) -> dict[str, Any]:
    if isinstance(candidate, str):
        return {"candidate_id": candidate, "name": candidate, "facts": []}
    if not isinstance(candidate, Mapping):
        raise TypeError(f"Candidate {index} must be a string or mapping.")
    result = dict(candidate)
    result.setdefault("candidate_id", result.get("crop_id") or f"CANDIDATE{index + 1:03d}")
    result.setdefault("name", result.get("candidate_id"))
    result.setdefault("facts", [])
    return result


def _facts_for(
    candidate: Mapping[str, Any],
    supplied: Mapping[str, Sequence[Mapping[str, Any]]] | None,
) -> list[Mapping[str, Any]]:
    own = candidate.get("facts", [])
    facts = list(own) if isinstance(own, Sequence) and not isinstance(own, str) else []
    if supplied:
        keys = (candidate.get("candidate_id"), candidate.get("crop_id"), candidate.get("name"))
        for key in keys:
            if key in supplied:
                facts.extend(supplied[key])
                break
    return facts


def define_problem(
    candidates: Iterable[Any],
    constraints: Sequence[HardConstraint] | None = None,
) -> CSPProblem:
    domain = tuple(_candidate(item, index) for index, item in enumerate(candidates))
    return CSPProblem(
        variables=("selected_crop",),
        domains={"selected_crop": domain},
        constraints=tuple(constraints or DEFAULT_CONSTRAINTS),
    )


def solve_constraints(
    candidates: Iterable[Any],
    user_profile: Mapping[str, Any],
    constraints: Sequence[HardConstraint] | None = None,
    *,
    facts: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Search the candidate domain and return a structured feasibility trace."""

    problem = define_problem(candidates, constraints)
    feasible: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    unknown: list[dict[str, Any]] = []
    examined = 0

    def backtrack(variable_index: int, assignment: dict[str, Any]) -> None:
        nonlocal examined
        if variable_index == len(problem.variables):
            examined += 1
            candidate = assignment["selected_crop"]
            outcomes = [
                constraint.check(candidate, user_profile, _facts_for(candidate, facts))
                for constraint in problem.constraints
            ]
            record = {
                "candidate_id": candidate["candidate_id"],
                "name": candidate["name"],
                "category": candidate.get("category"),
                "scientific_name": candidate.get("scientific_name"),
                "verification_status": candidate.get("verification_status", "unknown"),
                "assignment": {"selected_crop": candidate["candidate_id"]},
                "satisfied_constraints": [
                    item.to_dict() for item in outcomes if item.status is CheckStatus.SATISFIED
                ],
                "failed_constraints": [
                    item.to_dict() for item in outcomes if item.status is CheckStatus.VIOLATED
                ],
                "unknown_constraints": [
                    item.to_dict() for item in outcomes if item.status is CheckStatus.UNKNOWN
                ],
            }
            if record["failed_constraints"]:
                record["status"] = "rejected"
                rejected.append(record)
            elif record["unknown_constraints"]:
                record["status"] = "unknown"
                unknown.append(record)
            else:
                record["status"] = "feasible"
                feasible.append(record)
            return

        variable = problem.variables[variable_index]
        for value in problem.domains[variable]:
            assignment[variable] = value
            backtrack(variable_index + 1, assignment)
        assignment.pop(variable, None)

    backtrack(0, {})

    if feasible:
        status = "satisfiable"
    elif unknown:
        status = "incomplete"
    else:
        status = "unsatisfiable"

    conflicts = [
        {
            "candidate_id": item["candidate_id"],
            "constraint_ids": [row["constraint_id"] for row in item["failed_constraints"]],
            "reasons": [row["reason"] for row in item["failed_constraints"]],
        }
        for item in rejected
    ]
    return {
        "status": status,
        "variables": list(problem.variables),
        "domains": {
            key: [candidate["candidate_id"] for candidate in values]
            for key, values in problem.domains.items()
        },
        "feasible_candidates": feasible,
        "rejected_candidates": rejected,
        "unknown_candidates": unknown,
        "conflicts": conflicts,
        "diagnostics": {
            "algorithm": "deterministic backtracking domain search",
            "assignments_examined": examined,
            "unknown_is_satisfied": False,
        },
    }


__all__ = ["CSPProblem", "define_problem", "solve_constraints"]

