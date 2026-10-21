# CropNova CSP problem definition

## Version 1 formulation

- Variable: `selected_crop`
- Domain: candidate crops supplied by the rule engine or, while that module is absent, crop records from the knowledge base
- Hard constraints: season compatibility, water availability, soil texture, and soil pH
- Search: deterministic backtracking over the candidate domain in input order
- Consistency: a complete assignment is feasible only when every implemented hard constraint is `satisfied`

Each hard check is three-valued: `satisfied`, `violated`, or `unknown`. Unknown is never converted to satisfied. A candidate with one violated constraint is rejected. A candidate with no violation but at least one unknown check stays unknown and needs more information or verified knowledge.

Facts may satisfy a constraint only when they are marked `verified` and their regional applicability matches the user profile. Pending, missing, conflicting, malformed, or out-of-scope facts produce an unknown result.

## Worked viva example

This is a synthetic solver example, not an agricultural claim.

1. Variable: `selected_crop`
2. Domain: `[Candidate A, Candidate B]`
3. User profile: Rabi, loamy soil, pH 7, moderate water
4. Candidate A's verified test facts: Rabi, loamy, pH 6-8, low water requirement
5. Candidate B's verified test facts: Kharif, loamy, pH 6-8, low water requirement
6. Search examines Candidate A first; all four checks pass, so the assignment is feasible.
7. Search examines Candidate B; `CONSTRAINT001` fails because the verified season does not match, so it is rejected.

The domain order and output are deterministic. Diagnostics report two assignments examined. If every candidate fails, status is `unsatisfiable` and the conflict report lists the exact constraint IDs and reasons. If a required fact or input is unknown, status is `incomplete` rather than satisfiable.

## Public result shape

`solve_constraints()` returns:

- `status`: `satisfiable`, `incomplete`, or `unsatisfiable`
- `variables` and `domains`
- `feasible_candidates`
- `rejected_candidates`
- `unknown_candidates`
- `conflicts`
- `diagnostics`, including search algorithm and assignments examined

Every candidate trace separates satisfied, failed, and unknown constraints and preserves fact/source IDs for the result page.
