# CropNova Knowledge Base Starter v0.1.0

## Files
- `data/knowledge_facts.json`: main KB containing crop profiles, facts, sources and pending research.
- `data/facts.csv`: spreadsheet-friendly fact table.
- `data/sources.csv`: source catalog.
- `data/rule_candidates.json`: draft guardrail rules for Annu.
- `data/csp_starter.json`: initial CSP variables and guardrails for Abhinav.
- `docs/knowledge_policy.md`: rules for adding and approving facts.

## Important
This is a source-traceable starter, not a complete agronomic advisory. It has source-backed general principles and explicit research tasks. Do not invent local sowing dates, fertilizer doses, pesticide instructions, disease treatments or regionally suitable varieties.

## Integration
This JSON is richer than the original minimal file described during setup. Back up your current `knowledge_base/data/knowledge_facts.json` and inspect `loader.py`, `validator.py` and `query.py` before replacing or adapting it.
