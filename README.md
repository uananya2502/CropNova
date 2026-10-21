# CropNova

CropNova is an explainable agricultural decision-support prototype. It combines a source-aware knowledge base, an optional IF-THEN rule-engine adapter, a genuine constraint-satisfaction search, and an intelligent agent with a browser interface.

> CropNova is an educational prototype. It does not guarantee crop success and does not replace advice from local agricultural professionals.

## What is implemented

- `csp_solver.py` defines the `selected_crop` variable, candidate domain, deterministic backtracking search, conflict output, and diagnostics.
- `constraint_definitions.py` checks season, water, soil texture, and pH using only user input and applicable facts marked `verified`.
- `agent.py` validates and normalizes input, loads and validates knowledge, invokes a rule-engine adapter, runs the CSP, asks targeted follow-ups, and assembles one of the six agreed result statuses.
- `explanations.py` creates deterministic candidate explanations and a compact evidence package that a future grounded GenAI adapter can consume without changing decisions.
- `app.py` provides a responsive browser form and report using only the Python standard library.
- `tests/` covers satisfiable, rejected, multiple-solution, unsatisfiable, unknown, unverified-fact, invalid-input, follow-up, and end-to-end browser cases.

The current knowledge records are marked `pending_research` and contain no verified agricultural facts. The integrated app therefore correctly returns `NO_SUPPORTED_KNOWLEDGE` or `MORE_INFORMATION_NEEDED` instead of inventing a recommendation. Add verified, sourced facts through the knowledge-base module to enable feasible outcomes.

## Run the browser prototype

Python 3.10 or newer is required; there are no third-party runtime dependencies.

```powershell
python app.py
```

Open `http://127.0.0.1:8000`.

## Run the demonstration and tests

```powershell
python main.py
python -m unittest discover -v
python -m unittest discover -s knowledge_base/tests -v
```

## Public interfaces

```python
from csp_solver import solve_constraints
from agent import run_assessment

csp_result = solve_constraints(candidates, user_profile, constraints=None)
final_report = run_assessment(user_profile)
```

Candidate facts use the knowledge contract:

```json
{
  "fact_id": "FACT001",
  "property": "growing_season",
  "value": ["rabi"],
  "applicability": {"region": "Example State"},
  "source_ids": ["SRC001"],
  "verification_status": "verified"
}
```

Supported constraint properties are `growing_season`, `water_requirement`, `soil_texture`, and `soil_ph_range`. Aliases are documented in `constraint_definitions.py`.

If a teammate later adds `rule_engine.evaluate_rules(profile, facts)`, the agent imports and uses it automatically. Until then, knowledge-base crops seed the CSP domain only and are never labelled recommendations.

## Result statuses

- `FEASIBLE_OPTIONS_FOUND`
- `MORE_INFORMATION_NEEDED`
- `NO_FEASIBLE_OPTION`
- `NO_SUPPORTED_KNOWLEDGE`
- `INVALID_INPUT`
- `SYSTEM_ERROR`

See `docs/csp_problem.md` and `docs/integration_checklist.md` for the worked CSP example, contracts, demonstration path, and team hand-off checklist.
