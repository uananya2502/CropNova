# Current implementation and review checklist

- [x] Published knowledge loads through `load_knowledge` and passes structural validation.
- [x] Source review and regional applicability control usable evidence.
- [x] Three IF-THEN rules provide evidence/season traces.
- [x] One-variable CSP checks season, water, soil texture and pH.
- [x] Missing input, missing knowledge, conflicts and violations have separate outcomes.
- [x] Public pages use plain language and show entered values, references and reasons.
- [x] Saved report pages and PDFs reuse the same recorded assessment.
- [x] Gemini provides optional explanations with schema, status and citation validation.
- [x] Local MiniLM retrieves scoped assessment findings for follow-up questions.
- [x] Request limits, bounded caches and explicit provider-failure states are implemented.
- [x] Tests cover engine behavior, private storage, web routes and provider failures.
- [ ] Independent agronomic review and labelled field evaluation.
- [ ] Broader region-specific evidence and representative retrieval evaluation.
- [ ] Public hosting with resource, quota and abuse controls verified on the chosen host.

See `project_review.json` for measured review results and `learning_guide.md` for the code map. Earlier pending-module and synthetic-website instructions are obsolete.
