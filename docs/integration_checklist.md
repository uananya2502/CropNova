# CropNova integration and demonstration checklist

## Module contract checklist

- [x] Knowledge is loaded through `knowledge_base.loader.load_knowledge()`.
- [x] Knowledge is structurally checked through `knowledge_base.validator.validate_knowledge()`.
- [x] Pending/unverified facts cannot satisfy hard constraints.
- [x] `rule_engine.evaluate_rules` is used automatically when that teammate module becomes available.
- [x] Missing rule engine is explicit and does not produce a fake rule result.
- [x] Candidate records flow into `solve_constraints()` as the `selected_crop` domain.
- [x] CSP output remains structured; the agent does not parse console text.
- [x] Constraint, fact, source, and candidate IDs remain present in the trace.
- [x] Agent emits only agreed top-level status strings.
- [x] Unknown, invalid input, no knowledge, no solution, and module failure are distinct.
- [x] Deterministic explanations preserve solver status.
- [x] Evidence package is ready for a future approved GenAI provider adapter.

## UI checklist

- [x] Introduction and limitations are visible.
- [x] Region, season, soil, water, objective, priority, and candidate inputs are available.
- [x] Unknown values are explicit.
- [x] pH is range-validated.
- [x] Feasible, rejected, and unknown candidates are separate.
- [x] Constraint IDs, reasons, and evidence IDs are visible.
- [x] Warnings, follow-up questions, diagnostics, and limitations are displayed.
- [x] Submitted values are preserved for refinement.
- [x] No personal contact data is collected.

## Demonstration sequence

1. Run `python app.py` and open `http://127.0.0.1:8000`.
2. Submit a complete profile against the current pending knowledge base.
3. Show `NO_SUPPORTED_KNOWLEDGE`, unresolved candidates, constraint reasons, and `Unknown treated as satisfied: No`.
4. Change the season to `I don't know` and rerun.
5. Show `MORE_INFORMATION_NEEDED` and the targeted season question.
6. Run `python -m unittest discover -v`.
7. Point out the feasible and unsatisfiable synthetic fixtures in `tests/test_csp_solver.py`.
8. After the knowledge owner adds sourced verified facts, rerun the same form to demonstrate feasible/rejected outcomes without changing solver code.

## Remaining team-owned integration inputs

- [ ] Knowledge owner adds source-backed facts and source metadata for the agreed region/crops.
- [ ] Rule-engine owner provides `evaluate_rules()` and stable rule traces.
- [ ] Team chooses an approved GenAI provider and course-compliant API policy before a real model adapter is added.
- [ ] Highest-risk GenAI grounding and response-validation tests are added only when a real provider integration is claimed.
