# CropNova Knowledge Governance Policy

Each fact needs a unique ID, crop, category, narrow statement, source IDs, verification status, applicability, confidence and review notes.

Statuses:
- `verified_general`: sourced general principle, not automatically farm-specific advice.
- `verified_context_specific`: valid only within the stated applicability.
- `pending_research`: never use in recommendations or rules.
- `needs_review`: incomplete, stale or conflicting evidence.

Research workflow:
1. Prefer official ICAR institutes, state agricultural universities, KVKs, government agriculture departments and FAO where appropriate.
2. Record source title, publisher, URL, date/version, page/section, region and conditions.
3. Keep one claim per fact.
4. Record variety, soil, season, irrigation system and growth stage whenever the source specifies them.
5. Ask a second team member to review.
6. Only approved facts can be used by the rule engine.
7. If evidence is missing, ask a question or return `undetermined`.

Safety:
- Never generalize fertilizer rates from another region/crop.
- Do not treat indicative water ranges as irrigation schedules.
- Do not assume a crop is suitable for a field without applicable evidence.
- GenAI explains supplied evidence; it must not invent facts, thresholds or citations.
