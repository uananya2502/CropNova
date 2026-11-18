# CropNova

CropNova compares crop options with a field's location, season, soil and water, then explains the findings with published sources. The public interface uses plain language and supports personalised PDF reports.

The knowledge base has 41 facts and 17 source records for wheat, rice, maize and chickpea. Regional coverage varies. These are preliminary reference checks, not field-validated recommendations or guarantees of crop success.

## Run

Python 3.13 is the tested runtime.

```sh
python3 -m pip install -r requirements.txt
python3 scripts/prepare_transformer.py
python3 app.py
```

Open `http://127.0.0.1:8000/`. See [deployment instructions](docs/deployment.md) for the Gunicorn start command, private environment variables, storage and hosting limits. No hosting deployment is performed automatically.

## What users can do

- Enter a field profile and compare four crop options against applicable published references.
- See their entered values beside the references, with a plain explanation of each finding.
- Review missing measurements, uncertain guidance and next steps.
- Request an optional Gemini-generated explanation grounded in the recorded assessment.
- Download a personalised PDF with inputs, findings, explanations, source links and unresolved questions.
- Reopen the result or download it without another provider request. Result links are private bearer links and expire after an hour.

Synthetic fixtures are reserved for tests. A public request cannot activate them. The website and PDF do not show internal engine codes or diagnostic traces.

## Read the code

| Module | Responsibility |
|---|---|
| `app.py` | HTTP routes, published-data assessment flow, redirects and downloads |
| `web_views.py`, `static/` | Public pages, responsive styling, illustration and form feedback |
| `agent.py` | Coordinates source retrieval, rule evaluation and crop checks |
| `profile_validation.py` | Normalises inputs and validates labels and measurements |
| `constraint_definitions.py`, `csp_solver.py` | Evidence-based constraint checks and candidate search |
| `assessment_summary.py` | Shared plain-language explanations for the website and PDF |
| `assessment_pdf.py` | PDF layout using the saved assessment |
| `report_store.py` | Private, short-lived SQLite report storage |
| `genai_explainer.py`, `gemini_provider.py` | Provider requests, structured replies, validation and fallback |
| `semantic_search.py` | Local MiniLM transformer retrieves relevant saved-assessment evidence |
| `assessment_questions.py` | Source-grounded follow-up questions, citations, validation and fallback |
| `knowledge_base/` | Published facts, applicability, source records and validation |

The rule engine and CSP determine recorded outcomes. Separate fuzzy alignment and A* follow-up planning do not overwrite those outcomes. The language model explains them; it cannot update those outcomes or the knowledge base. Structural response validation does not prove generated prose is factually correct.

The user interface offers supported crop comparison, not unimplemented objectives such as yield optimisation or a soil-improvement ranking. Internal integration endpoints and engine interfaces remain available for development.

## Tests

```sh
python3 -m pip install -r requirements-dev.txt
python3 -m pytest -q
```

Current checks cover engine correctness, evidence scope, provider failures, public-data separation, private report downloads, PDF content, saved-result integrity, and concurrent HTTP requests.

Run `python3 scripts/verify_ai.py --live` for three actual provider requests, subject to the account's quota. Automated tests use controlled responses and do not consume provider quota.

## More detail

- [Beginner explanation of generative AI](docs/generative_ai.md)
- [Published crop requirements and example inputs](docs/knowledge_requirements.md)
- [Deployment and report storage](docs/deployment.md)
- [Implementation notes](docs/improvements.md)

## Ask about an assessment

A pretrained local sentence transformer now retrieves relevant findings for follow-up questions. Gemini, the existing LLM, writes a short answer citing those findings. Crop decisions remain with the reasoning engine. Prepare the model once with `python3 scripts/prepare_transformer.py` before starting the server. See [the beginner transformer guide](docs/transformers.md) for setup, examples, limitations and verification.

## Learning and viva preparation

Start with [the beginner learning guide](docs/learning_guide.md). A printable version is generated at `output/pdf/CropNova-Learning-and-Viva-Guide.pdf` using `python3 scripts/build_learning_guide.py`. Code locations in the guide are generated from the current Python source. The latest review results are in `docs/project_review.json`.

## Fuzzy logic and A*

New assessment pages show a gradual pH/water reference-alignment index and a minimum-relative-effort plan for follow-up information tasks. The index is not a crop-success probability; the plan does not guarantee that measurements or reviewed evidence will make a crop feasible.

- `fuzzy_logic.py`: membership functions, nine zero-order Sugeno rules, and weighted output.
- `astar_search.py`: priority-queue A* and uniform-cost baseline.
- `preparation_planner.py`: the assessment-specific states, goals, tasks, prerequisites and relative costs.
- `docs/fuzzy_and_search.md`: beginner implementation notes and examples.
- `docs/guidelines_check.json`: status against the supplied course guidelines.

Run `python3 scripts/check_fuzzy_search.py` to repeat the 32 controlled scenario comparisons. The final academic report is deferred until its template arrives. The personal learning handbook now covers these additions and includes refreshed code locations. It is separate from the deferred submission report.

## Multi-page website and production packaging

The home page now leads to a separate field form. Generated results, the online report, next steps and editing each have their own route. Sources, how-it-works and privacy also have dedicated pages. Submitting an edit creates a new snapshot instead of overwriting an old result.

`public_pages.py` contains public screens; `assessment_pages.py` contains saved-assessment screens. Production runs through `gunicorn.conf.py` and the Procfile. A Dockerfile, Compose definition, readiness endpoint and `scripts/check_deployment.py` are included. See [deployment instructions](docs/deployment.md). Docker image execution requires Docker and has not been verified in this workspace.

## Dropdown form and visible coverage

The assessment form now uses menus for state, district, season, soil texture, pH, drainage, water budget, water basis, crop and optional explanation. A profile selector loads each of the four complete worked reference examples. The coverage preview runs the same four checks without saving a report or calling an AI provider.

`form_choices.py` holds the input catalogues; `assessment_form.py` renders controls and the coverage table; `coverage_preview.py` builds the preview. District menus cover Haryana, Rajasthan and Punjab. Location choices do not add agricultural evidence. Other states are labelled as having limited local crop coverage. See `docs/dropdowns_and_coverage.md`.

### Farmer-focused input and multilingual explanations

The existing app now includes illustrated seasonal rain observations, optional exact rainfall, simple water-access choices, and English/Hindi/Punjabi explanations. Crops that match the four checks appear first; other options use a compact comparison. See [the implementation and data-scope notes](docs/farmer_experience.md).

The library contains **640 records**: **112 core records plus 528 historical FAO attributes** for the assessed crops. Historical attributes are visible for reference but excluded from decisions and LLM evidence. This count is not a farm dataset or an accuracy claim.

### Mandi prices and weekly forecasting

Open **Mandi prices** on a saved assessment to compare dated wholesale prices for a crop, mandi, variety and grade. An optional weekly estimate appears when the model beats the previous-week baseline on later test weeks and the imported reports are recent. The market advice uses the recorded field result and keeps all crop findings intact. See [data import and forecast validation](docs/mandi_prices.md).
