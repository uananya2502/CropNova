# Reliability improvements on 29 October 2026

## Implemented

- Shared scope matching enforces country, state, district, season, soil and irrigation restrictions. Unsupported restrictions cannot silently become global evidence.
- Contradictory season, soil, water or pH facts produce an unknown result with fact and source IDs. Duplicate equivalent pH evidence is accepted.
- The solver filters facts belonging to another crop, rejects malformed ranges, and never accepts nonfinite pH measurements.
- Rules evaluate the crops actually selected. A seasonal-candidate rule complements evidence-availability rules; the CSP still independently evaluates all four hard requirements.
- False AND unknown evaluates false. A rule that does not fire cannot claim its positive conclusion. Enabled rules are evaluated in priority order.
- The agent rejects unknown crop selections, invalid nested profiles and malformed labels instead of ignoring them. Follow-up questions are deduplicated.
- Water-conservation preferences order feasible crops by supported categorical water demand. Rejected or unresolved crops cannot enter this list. There are no success percentages.
- Evidence packages include the actual fact and source records. The website supports JSON export, source links and an evidence-readiness table.
- The research profile is separate from the synthetic presentation profiles.

## Knowledge additions

The active dataset now contains 41 facts and 17 source records. Source extraction does not mean independent agronomic approval. Four new published-reference profiles cover all four screens within their documented contexts. See [knowledge_requirements.md](knowledge_requirements.md) for source details and exact example inputs.

Numeric water screening keeps seasonal crop-water supply separate from supplemental irrigation. Water budgets within a published envelope remain unresolved until a local requirement is known. Soil and pH preferences are not treated as universal exclusion limits. Maize soil/season/pH guidance remains scoped to Rajasthan; Haryana catalogue references preserve their original crop and variety limits.

## Verification

Run `/opt/anaconda3/bin/python3.13 -m pytest -q`: 161 tests passed at this revision. New regressions exercise contradictory evidence, district/season restrictions, nonfinite pH, pH endpoints, false-plus-unknown rules, invalid selections, dataset separation, JSON export and malformed submissions.

Run `/opt/anaconda3/bin/python3.13 scripts/audit_knowledge.py` to reproduce research coverage. The saved audit is `docs/knowledge_audit.json`. It is a readiness check, not an independent agronomic benchmark.

## Remaining requirements

The research dataset still needs independent team review, local validation, wider regional coverage, local crop-water estimates and independently checked agricultural cases. A published general reference is not automatically sufficient for a local recommendation.

No ML training has been added. An optional OpenAI Responses API explanation adapter is now implemented, including structured outputs, result/reference validation and provider-failure tests. The server key is configured; live generation is blocked by exhausted API credits. Deterministic explanations still work without network access. See `generative_ai.md`.

The current user interface could not be visually rechecked because browser inspection was blocked by the browser URL security policy. Automated WSGI tests verify the application paths.

## GitHub update merged

Pulled main through `a9a50a2` (two commits after `21bac50`). Preserved local improvements and incorporated the HAU source record, dated wheat-season fact, pending chickpea historical evidence, soil evidence register, backup files and upstream regressions. Updated overlapping tests to preserve the dated source restriction and account for the new numeric inputs and published soil references. Historical evidence remains inactive. A pre-pull Git stash is retained as a recovery copy.

## Free-provider support

Added a small Google Gemini Generate Content API adapter alongside OpenAI. Google AI Studio confirmed the connected project is Free tier. Local settings explicitly select Gemini. Missing keys, quota errors and failed responses never cause a paid-provider fallback. The same decision/reference validator is used by both providers. See `generative_ai.md` and `ai_verification.json` for setup and actual verification status.

Live Gemini verification succeeded for the match, water-shortfall and missing-pH cases using `gemini-3.5-flash-lite`. All generated replies passed structural decision/reference validation. The server was restarted with the Gemini settings.

## Local website connection repair

Changed startup from a single-request WSGI server to a threaded WSGI server. A slow AI call or a browser connection that has not sent a request no longer blocks the home page. Idle request sockets have a timeout. Added form progress feedback and protection against repeated assessment submissions.

Two real-HTTP regression tests cover a home-page request during a blocked AI call and an idle browser connection. After restarting, the home and assessment routes returned HTTP 200, a published wheat assessment returned FEASIBLE_OPTIONS_FOUND, and a live Gemini explanation completed through the running server. The home page remained responsive during that request.

The user reported ERR_SOCKET_NOT_CONNECTED in existing in-app browser tabs. Automated reload was blocked by the browser URL security policy, so the error-tab recovery requires a manual reopen. No browser-policy workaround was used.

## Public interface and personalised reports

Replaced the classroom-facing interface with a responsive field-assessment design using native HTML, CSS, JavaScript and an SVG field illustration. The public flow always uses published knowledge; synthetic fixtures remain restricted to tests. Technical status codes, rule traces and internal constraint labels are omitted from the website and PDF.

Added a shared plain-language evidence summary: entered value, published reference, explanation, source links and actions for unresolved conditions. Missing input is distinguished from missing knowledge. Generated wording uses everyday equivalents for internal technical labels without changing measurements, decisions or qualifications.

Added personalised PDF reports, visually checked at two pages for a one-crop assessment with live Gemini wording. Reports reuse the saved assessment rather than making another provider request. Random access links expire after one hour; SQLite stores up to 100 reports in a Git-ignored private directory. Refreshes use a saved-result URL.

183 automated tests pass. A two-worker Gunicorn smoke test verified health, static assets, result redirects, cross-worker report access and repeated PDF downloads. The public app startup was prepared for deployment with dependencies, a Procfile and hosting/storage instructions. No hosting publication was performed. Browser preview remains unavailable under the earlier browser URL policy; verification used HTTP tests, structured content checks and direct PDF rendering.

## Report displayed on the website

The personalised report now appears directly on the saved assessment page, including the supplied field details, crop narratives and unresolved questions. Main actions scroll to this report. A PDF export remains under an optional secondary control. Generated wording is shown inline when available; the report also works without a provider request. 184 tests pass.

## Visual polish

Added hand-drawn crop SVG icons, softer surfaces, rounded cards, larger form and report text, stronger comparison spacing, and warmer colour accents. The personalised report reads directly on the results page and precedes the sidebar on mobile. Asset URLs were versioned again so the updated styles are requested on refresh. Styling is formatted with readable rules and section comments. The assessment logic is unchanged.

## Transformer evidence search and follow-up questions

Added a pinned, CPU sentence transformer for semantic retrieval within a saved assessment and a Gemini-backed question box with visible evidence and source links. Questions cannot update recorded crop decisions. Source review and regional scope are checked before retrieval. Missing models or provider failures produce explicit unavailable/evidence-only states. Added question input limits, per-report rate limits, a bounded answer cache, and structural validation of citations and crop decisions. The frontend inserts generated text using textContent.

Validation: 210 automated tests passed. Six actual-encoder example queries retrieved the expected finding in the top three; this is a smoke check, not agricultural accuracy. Details and reproducible commands are in `docs/transformers.md`.

## Review on 14 November 2026

Split input normalisation and validation into `profile_validation.py`. Simplified `agent.py` from 1,342 lines to 454 while keeping the existing entry points, and compared complete reports for 24 normal assessment scenarios. The rule helpers now share the registered evaluator instead of maintaining duplicate implementations. Reformatted the changed Python modules and added comments at workflow boundaries.

Fixed conflicting region aliases, overflowing or malformed numeric inputs, long profile labels, truncated/oversized requests, excessive form fields, malformed report-token types and stale caching of temporary AI failures. Semantic retrieval now checks the exact fact IDs behind a finding, so another fact sharing the source cannot make it eligible. Raw internal exception messages are not returned to public API users. Added a same-origin content security policy. Updated the CLI example and stale presentation notes.

Validation: 244 automated tests passed; 24 normal-scenario reports matched the pre-refactor implementation; six real-encoder smoke questions found the expected finding within the top three. None of these is an agricultural accuracy percentage. The learning PDF includes a source-derived code map and viva questions.

Live verification on 14 November: the current server returned all four reference assessment pages and PDFs; one actual Gemini report explanation and one MiniLM/Gemini follow-up answer succeeded. See `http_review.json`. Browser automation was unavailable for localhost, so this does not claim a new browser-level visual interaction check.

## Fuzzy alignment and A* added after the guideline review

Implemented zero-order Sugeno inference for supported pH/water alignment and an explicit A* state-space planner for follow-up information tasks. Neither changes the recorded CSP result. Exact reviewed fact eligibility is shared with semantic retrieval. Public result pages show an ordinary-language alignment panel and ordered follow-up steps, with visible limitations.

Added 47 tests for membership boundaries, inference traces, evidence gating, hard-result preservation, admissible/consistent heuristic behavior, optimal cost agreement, prerequisites, unreachable goals and search limits. All 291 tests pass. A* and uniform-cost search agree on minimum cost in 32 controlled scenarios; the missing-measurement wheat example uses a 7-point combined-task plan, with 10 versus 16 expansions. These are software comparisons, not agricultural accuracy or a claim that A* always expands fewer states.

The supplied guideline allows CSP or fuzzy logic; both are present. Full report and PPT remain pending; current literature candidates still need full review and the final comparison table. Final-report authoring is paused at the user's request.

## Multi-page website and production packaging

Separated the home, field form, saved findings, personalised report, next steps and edit screens. Added how-it-works, sources and privacy pages, shared active navigation, private-page noindex headers and a brand favicon. Legacy preset links redirect to the dedicated form. Editing starts a new snapshot; the old result remains unchanged. New page modules reuse the existing assessment and explanation components.

Added a shared provider concurrency limit, core readiness endpoint, HEAD handling, Gunicorn configuration, Docker/Compose definitions, CPU wheel selection, private persistent data path and a preflight script. No public deployment was made. Docker is unavailable here, so the image build is unverified; browser visual automation is blocked for localhost.

Validation: 318 tests passed; Gunicorn configuration and the real production HTTP flow passed, including public pages, POST redirect, saved report/plan/edit, immutable previous results, PDF export, HEAD readiness and old example redirects. The prepared encoder loaded successfully, and the pinned CPython 3.13 Linux CPU torch wheel metadata was checked. Details are in `multipage_checks.json`.

A macOS-only worker reload failure appeared while testing Gunicorn HUP with a threaded master. Preloading the lightweight application before worker forks resolved the observed failure; the encoder is still lazy. Production readiness and two graceful reloads then passed. The local user-facing site remains served by `python app.py`.
