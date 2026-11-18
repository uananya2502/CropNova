# 01. Start here: what CropNova actually does

This is your personal learning handbook, separate from the final submission report. It explains the implemented project and helps you practise the viva.

CropNova is a crop decision-support website. A user enters a location, growing season, soil texture, measured pH and water budget. The program compares these inputs with applicable published crop references. It explains which checked conditions match, which need attention, and which remain unresolved.

The current knowledge base covers wheat, rice, maize and chickpea. It contains 41 facts and 17 source records. The retrieval policy currently accepts 36 facts as source-reviewed agricultural knowledge; that does not mean every fact can satisfy every constraint. Applicability and the constraint-eligible flag still matter. Coverage varies by crop and region.

## A simple answer for your teacher

"We built a crop assessment system that combines source-backed knowledge, IF-THEN rules and constraint checking. It records the reason behind each result. We also integrated a local sentence transformer to retrieve relevant findings and Gemini to explain them in ordinary language."

## Different jobs in the pipeline

- The reasoning code calculates the recorded result.
- A separate fuzzy index describes gradual numeric alignment, and A* plans follow-up tasks.
- The local MiniLM encoder finds findings related to a question.
- Gemini writes an explanation using those findings.

We integrated pretrained models. We did not train a crop classifier or a new language model. A reference match is preliminary; it does not prove crop success in a real field.

## How to use this handbook

First read chapters 1-5 for the overall idea. Then study the rules, CSP, agent and worked examples. Open the files while reading the code walkthroughs. Finally practise the viva answers aloud, using your own words. If a line number changes after editing, search for the function name given beside it.

# 02. Planning the project and choosing its scope

The problem is that crop guidance is scattered across references, and a user may not understand why an option was selected. Our project goal is to make a limited, traceable comparison rather than return an unexplained crop name.

## Requirements we implemented

- Accept farm-condition inputs and allow missing measurements.
- Retrieve knowledge with recorded sources and applicability.
- Evaluate each crop against season, water, soil texture and pH.
- Keep a failed check separate from an unknown check.
- Show inputs, references, reasons, sources and unresolved questions.
- Save the assessment briefly so the webpage and downloaded PDF use the same result.
- Offer optional generated explanations and questions grounded in recorded evidence.

## Development phases

1. Define the input fields, four checks and expected result categories.
2. Structure crop facts and source records in JSON.
3. Implement the rule engine, CSP search and agent coordination.
4. Add traceable explanations, forms, saved results and PDF export.
5. Integrate Gemini and local transformer retrieval.
6. Test positive, negative, missing-input and failure cases; improve readability.

These are development phases, not a claim about exact historical dates or who authored every line.

## What 'planning' means here

The agent coordinates assessment steps. A separate A* planner now searches a sequence of information-gathering and evidence-review tasks, using explicit states, preconditions and relative effort costs. It plans follow-up work, not a planting calendar, a sequence of crop treatments or a guarantee of suitability. STRIPS, PDDL and reinforcement-learning planning are not implemented.

A good viva answer is: "We use A* to organise the missing-information and review tasks. Its goal is to cover the follow-up tasks in our model, not to make a crop feasible."

# 03. The AI concepts: what is used and why

AI is a broad field. It includes explicit reasoning as well as systems that learn patterns from data. Machine learning is part of AI, and transformers are neural-network models within machine learning.

| Concept | Role in CropNova |
|---|---|
| Knowledge representation | JSON facts store crop properties, sources and scope. |
| Rule-based reasoning | IF-THEN rules identify available knowledge and seasonal evidence. |
| Constraint satisfaction | All implemented conditions must pass for a recorded feasible crop. |
| Intelligent agent | Coordinates inputs, evidence, checks and follow-up questions. |
| Fuzzy logic | Describes gradual alignment of supported pH and water measurements. |
| A* search | Plans a minimum-relative-effort sequence of follow-up information tasks. |
| Explainability | Preserves the inputs, reasons, fact IDs and source IDs behind checks. |
| Transformer encoder | Produces text embeddings for semantic evidence retrieval. |
| Generative AI / LLM | Gemini writes an explanation from recorded evidence. |
| RAG | Retrieve relevant evidence before asking Gemini to write an answer. |

## Why we combined these techniques

Explicit rules and constraints let us inspect why a result was produced. Semantic retrieval lets the user phrase a question naturally. Generated wording makes a detailed trace easier to read. Each part has a limited responsibility.

Do not say "our project uses no ML" now that pretrained neural models are included. Say: "The crop decision layer is symbolic. The language and retrieval features use pretrained neural models."

## What is not implemented

There is no locally trained crop recommendation classifier, image disease detector, live weather integration, profit predictor, independent expert validation or automatic learning from user questions. The website does not become more knowledgeable simply because people use it.

# 04. Python you need before reading the code

A function groups a task. A parameter is an input to that task; a return value is its output. Imports allow one file to reuse a function from another file.

A dictionary stores named values, such as a crop's ID and status. A list stores ordered items, such as selected crops. A set stores unique values, useful when checking whether a cited ID is allowed. A tuple is an ordered container commonly used for fixed definitions.

```python
profile = {"season": "rabi", "soil": {"ph": 7.0}}
season = profile.get("season", "unknown")
ph = profile["soil"]["ph"]
```

The first access can return a default when a key is missing. The second assumes those keys exist. Nested dictionaries group related soil and water fields.

## Important patterns in this project

- `None` means a measurement is not supplied; it is not zero.
- `if`, `elif` and `else` choose a branch based on a condition.
- A `for` loop visits each crop, fact or constraint.
- A list comprehension builds a filtered list. Read it as "keep each item if...".
- `try` and `except` turn expected failures into a useful response.
- A dataclass stores related result fields. Frozen result dataclasses resist accidental reassignment.
- An Enum gives a named set of statuses such as satisfied, violated and unknown.
- A context manager, written with `with`, closes resources such as database connections.

## Readability rule

Read the function name and docstring first. Identify its inputs and output next. Only then inspect branches. Do not memorise every line before understanding the data flowing through it.

# 05. The complete architecture

[FIGURE:workflow]

The browser sends the submitted fields to the Python website. The website calls the agent. The agent normalises inputs, validates knowledge, scopes evidence, evaluates rules and runs the CSP solver. The recorded result includes decisions and evidence IDs.

The result page also shows separate fuzzy alignment and A* follow-up panels. These do not rewrite the crop findings. The webpage and farm PDF use the same core summary-building code. SQLite stores a snapshot of the completed assessment. Refreshing a result or downloading its PDF does not rerun the reasoning engine or call Gemini again.

## Main boundaries

- `profile_validation.py`: input meaning and validity.
- `agent.py`: order of the assessment steps.
- `rule_engine/`: explicit IF-THEN evaluations.
- `constraint_definitions.py`: meaning of each crop condition.
- `csp_solver.py`: candidate search and classification.
- `web_views.py` and `static/`: presentation and interaction.
- `assessment_summary.py`: shared, plain-language findings.
- `semantic_search.py` and `assessment_questions.py`: evidence retrieval and follow-up answers.

Gemini is an external service. The encoder, crop reasoning, webpage rendering and report storage run in the application environment. An unavailable language service should not erase the original findings.

# 06. Input validation: prevent a wrong question before answering

Normalisation gives flat form values and nested API values a consistent shape. A text input such as "7" becomes a numeric pH value. A blank pH stays `None`. Labels such as the growing season are normalised for comparison.

Validation checks whether the resulting values make sense for the program. Examples include a pH between 0 and 14, a finite water budget between 0 and 10,000 mm, supported field labels, and a selected crop that exists in the knowledge base. The water budget limit is an input policy, not a crop requirement.

## What the review improved

Numbers represented by booleans, objects or overflowing integers are rejected. Long labels are bounded. Missing values stay missing rather than becoming guessed defaults. The website separately limits body size, field count and incomplete submissions.

[CODE:profile_validation.py:_number]

## What to say in a viva

"Validation checks whether an input is acceptable. Normalisation changes its representation into the shape our functions expect. Neither step decides whether a crop is suitable."

A missing required measurement leads to a targeted question. Missing agricultural knowledge leads to a different message: the system cannot invent a reference merely because all input boxes were filled.

# 07. The knowledge base: facts with provenance

The active data file is `knowledge_base/data/knowledge_facts.json`. It is a structured collection of crop records, fact records, sources and research metadata. It is not a training table where each row labels a farm with the correct crop.

A fact has an identifier, a crop, a property or category, a statement or value, source IDs and a verification status. It can also declare applicability, units, a preferred range or an eligibility flag.

```json
{
  "fact_id": "EXAMPLE_ONLY",
  "crop_id": "wheat",
  "property": "soil_ph_range",
  "value": [6.5, 7.5],
  "source_ids": ["EXAMPLE_SOURCE"],
  "verification_status": "verified_general"
}
```

This is an abbreviated illustration, not a complete record to paste into the data file. Actual records also carry a category, statement and other required metadata.

## Two different kinds of checking

`validate_knowledge()` checks the structure: IDs, references, types, ranges and unsupported nesting. `get_usable_facts()` checks the retrieval policy, including review status of the linked source records.

"Verified" is a repository label for reviewed source extraction. It is not proof that a local agricultural expert independently validated every recommendation. Source review and field validation are different tasks.

## Adding knowledge correctly

Read the source, record the relevant section and value, preserve its scope and units, add the fact and source IDs, run validation, and test how the new fact changes assessments. Adding more crop names without complete supporting evidence is not enough.

# 08. Applicability, conflicts and honest uncertainty

A source can be correct but irrelevant to the user's context. A Rajasthan-specific maize reference must not silently become a Haryana reference. A fact restricted to one district, season or irrigation context needs a matching profile.

`scope_matches()` checks those restrictions. During this review we fixed an edge case: if both `state` and the older `region` alias are present, both restrictions must match. One cannot be ignored just because the other exists.

## Four reasons a check may remain open

1. A required measurement was not supplied.
2. No eligible fact is available for that crop and context.
3. Applicable facts disagree or contain an unsupported value.
4. The reference is a preference or an indicative range that cannot establish a definite decision.

The constraints preserve fact and source IDs even for many unresolved findings. This helps a user see what needs review.

## Shared source does not mean shared support

Two facts may cite the same document. The fact supporting soil texture must not automatically support pH. The question retriever now verifies the exact fact IDs behind each finding, in addition to checking its sources and applicability.

## A useful viva distinction

"Unknown" means the evidence cannot establish an answer. "Violated" means a supported check failed. We keep these separate because absence of evidence is not automatically evidence of incompatibility.

# 09. The rule engine: what 'a rule fires' means

A rule is an explicit IF-THEN statement. The engine evaluates its conditions. If all conditions are true, the rule fires and its conclusion is established. A known false condition means not fired. Missing information or evidence can produce unknown.

The current definitions contain three rules:

| Rule | What it establishes |
|---|---|
| RULE_KB_001 | Usable crop knowledge exists for evaluation. |
| RULE_WATER_001 | Verified water-related reference evidence is available. |
| RULE_SEASON_001 | The entered season matches applicable seasonal evidence. |

The water-availability rule checks the existence of evidence. It does not calculate the user's water sufficiency. The water constraint performs that separate comparison.

## Yes, no and unknown example

For a controlled season fact documenting Rabi, an entered Rabi season fires the seasonal rule. Kharif makes it not fire if the documented set is exhaustive. An unknown season leaves the rule unknown. If a source is explicitly non-exhaustive, an unlisted season can also remain unknown.

The combined-rule evaluator gives a known false condition precedence over an unknown one. For an AND rule, one false condition is enough to prevent the conclusion.

## Important limitation

This engine evaluates registered conditions once. It is a small deterministic rule evaluator, not a general production-rule system repeatedly chaining newly inferred facts until no more rules apply.

# 10. CSP: finding a crop that meets all implemented conditions

CSP means constraint satisfaction problem. A CSP describes variables, possible values for them, and conditions that valid assignments must satisfy.

In CropNova there is one variable, `selected_crop`. Its domain is the selected crop records, or all four crops when the user leaves the selection empty. The four condition classes check growing season, water, soil texture and pH. Drainage can be a prerequisite inside the soil-texture check; it is not a fifth top-level CSP constraint.

## Classification of one candidate

- At least one violated check: rejected.
- No violation, but at least one unknown: unresolved.
- Every implemented check satisfied: feasible for this limited comparison.

[CODE:csp_solver.py:define_problem]

## How it differs from a rule

A rule establishes a specific conclusion, such as seasonal evidence matching. CSP classification requires the full conjunction of implemented conditions. A season rule firing is therefore not enough to recommend a crop.

The CSP does not optimise yield, profit or crop ranking. Several crops can satisfy the checks. The website's number of matched conditions is a count, not a calibrated confidence score.

The direct solver has a generic custom-constraint interface. The public agent uses the four default checks and the published knowledge retrieval policy.

# 11. Backtracking: follow one small example

The solver assigns a crop value, evaluates a complete assignment, records the result, and returns to try the next value. This is deterministic backtracking in input order. Because there is only one variable, the search is effectively a sequential visit to each crop in the domain.

```python
for crop in candidate_domain:
    checks = evaluate_all_four_checks(crop)
    if any_check_is_violated(checks):
        rejected.append(crop)
    elif any_check_is_unknown(checks):
        unresolved.append(crop)
    else:
        feasible.append(crop)
```

This is teaching pseudocode. The implemented recursive function and its trace-building code are inside `solve_constraints()`.

## Controlled dry run

Suppose Candidate A has matching season, water, soil and pH test facts. It is feasible. Candidate B has a supported season mismatch. It is rejected even if another check is unknown. Candidate C has three matches and no pH evidence. It remains unresolved.

The diagnostic count reports how many complete candidate assignments were examined. It does not measure agronomic accuracy or how many AI model calls occurred.

## Complexity

With N candidates, C checks and roughly F facts scanned per check, reasoning work is approximately O(N x C x F). Here C is four. General multi-variable CSP search can grow exponentially, but it would be misleading to claim that CropNova currently solves a large combinatorial farm-planning problem. It does not implement arc consistency, MRV or branch-and-bound.

# 12. The intelligent agent and its result statuses

The agent is the coordinator. It accepts observations, consults knowledge, runs reasoning steps and returns an assessment with follow-up questions. It has no independent physical sensors or machinery; observations come from the submitted fields.

## A PEAS description for discussion

| PEAS part | CropNova interpretation |
|---|---|
| Performance | Useful, traceable findings; honest uncertainty; correct handling of inputs. |
| Environment | User-reported field conditions and a limited reference knowledge base. |
| Actuators | Webpage findings, questions, explanations and report output. |
| Sensors | Form/API values supplied by the user. |

This is a conceptual description of the software agent. We do not currently measure a single numeric performance objective or deploy autonomous farm actuators.

## Internal assessment statuses

| Status | Meaning |
|---|---|
| FEASIBLE_OPTIONS_FOUND | At least one crop passes every implemented check. |
| MORE_INFORMATION_NEEDED | Unresolved candidates need a required user input. |
| NO_SUPPORTED_KNOWLEDGE | Unresolved candidates need suitable evidence or review. |
| NO_FEASIBLE_OPTION | Every assessed crop has at least one supported violation. |
| INVALID_INPUT | The supplied values are invalid. |
| SYSTEM_ERROR | A module or configuration failure prevented completion. |

If at least one feasible crop exists, the overall result can show matches while other crops remain unresolved. Read the per-crop findings too.

The agent is not a learning agent that retrains from interactions. It follows programmed logic over the supplied profile and reference records.

# 13. Explainable AI: show the path to the result

Explainability in CropNova begins before any language-model call. Each constraint produces a structured outcome: a status, reason code, human-readable reason, fact IDs, source IDs and, where relevant, missing fields.

[FIGURE:evidence]

The summary builder translates these outcomes into the user's entry, published reference, finding and next step. The original trace remains available in structured assessment data. Public pages use ordinary labels instead of CSP or internal IDs.

## Two layers of explanation

The deterministic explanation is assembled from recorded values and known result codes. It works without Gemini. The generated explanation is optional wording created from the assessment evidence. Both should preserve the same recorded decisions.

Showing sources helps a user inspect a claim. It does not prove that every source was interpreted correctly, that a source applies to every field, or that generated prose is free of mistakes.

## What this project does not use

We do not apply SHAP or LIME. Those techniques are commonly used to explain statistical models; our main decision layer already exposes its explicit conditions. We also do not display a language model's hidden chain of thought. We show the application's own recorded checks and evidence instead.

A strong viva answer is: "Our explanations are traceable to the input, comparison, reason and source. The generated text is a convenience layer over that trace."

# 14. Water and pH: understand the careful parts

The numeric water check compares a user budget with a documented reference range and a measurement basis. Seasonal crop-water supply and supplemental irrigation are different measurements and are not automatically interchangeable.

For the current wheat reference, the recorded range is 450-650 mm of seasonal crop-water use:

| Example input | Result of this limited comparison |
|---|---|
| 300 mm | Below the reference envelope: a shortfall. |
| 500 mm | Inside the envelope: local demand is still uncertain. |
| 650 mm | Covers the upper reference value: this check passes. |
| 650 mm supplemental only | Different basis: cannot make that comparison. |

These are examples of program behavior, not irrigation prescriptions. Effective rainfall, timing, usable soil moisture, conveyance losses and field conditions still matter. Paddy preparation and seepage are not established by the simple seasonal reference.

## Why pH outside a preferred range can remain unknown

A preferred range describes favorable documented conditions. It does not necessarily state a hard biological survival boundary. If the recorded fact is marked preferred, an outside value requests review rather than proving that the crop cannot grow.

The same caution applies to non-exhaustive soil and season lists. Do not tell the teacher "anything outside the table is impossible". Explain the distinction between a documented preference and a supported exclusion.

# 15. Fuzzy logic: gradual alignment, not a new crop verdict

A crisp check has a discrete outcome such as satisfied, violated or unknown. Fuzzy logic allows partial membership in descriptive sets. A value can be partly in two overlapping sets; membership is a degree of fit, not a probability that the value is true.

CropNova uses a zero-order Sugeno system to describe pH/water alignment with recorded references. It does not replace the CSP result. Season and soil checks must already be established. A known failed check blocks the index; missing, conflicting, unreviewed or incompatible numeric evidence cannot receive a score.

## Inputs and fuzzy sets

- pH distance: distance outside the documented pH band divided by max(band width, 1). Sets: aligned, nearby and distant.
- Water ratio: entered budget divided by the upper reference value, on the same water basis. Sets: low, partial and covered.

[FIGURE:fuzzy]

For water, low membership falls from 1 to 0 between ratios 0.5 and 0.8. Partial is triangular at (0.5, 0.8, 1.0). Covered rises from 0 to 1 between 0.8 and 1.0. pH uses overlapping aligned, nearby and distant shapes.

These membership settings are engineering assumptions for a reference-alignment index. They are not sourced biological limits, expert-calibrated crop thresholds or a probability of crop success. The underlying reference ranges still need valid sources and applicability.

# 16. Fuzzy rules and a worked Sugeno calculation

The nine rules combine three pH sets with three water sets. AND uses the minimum membership strength. Each rule has a constant consequent, making this zero-order Sugeno inference [T8].

| pH / water | Low | Partial | Covered |
|---|---|---|---|
| Aligned | 20 points | 55 points | 85 points |
| Nearby | 20 points | 20 points | 55 points |
| Distant | 20 points | 20 points | 20 points |

```text
strength = min(pH membership, water membership)
index = sum(strength * rule output) / sum(strength)
```

## Example: pH 7 and 600 mm for the wheat reference

The supported wheat pH range is 6.5-7.5, so normalised pH distance is 0 and aligned membership is 1. The water ratio is 600 / 650 = 0.9231.

| Fired rule | Strength | Constant output |
|---|---|---|
| Aligned pH AND partial water | 0.3846 | 55 |
| Aligned pH AND covered water | 0.6154 | 85 |

The weighted result is approximately 73.5 index points. The CSP water check still stays unresolved: 600 mm lies inside the 450-650 mm reference envelope, and exact local demand is unknown. A soft score does not convert that unknown into a pass.

Open `infer_alignment()` for inference, `memberships()` for the shapes, and `analyze_crop()` for evidence gating. The result retains memberships, fired rule IDs, strengths, constants and source IDs. Outputs use a weighted average, not Mamdani centroid defuzzification.

# 17. A*: the exact state-space problem in this project

A* is informed search. It chooses the frontier state with the lowest f = g + h, combining the known cost so far with an estimate of remaining cost [T9]. A* is not restricted to map navigation; CropNova searches a small task-planning state space.

| Element | CropNova definition |
|---|---|
| State | A frozenset of follow-up requirement IDs covered so far. |
| Initial state | Empty set: no follow-up task has been covered. |
| Goal | Cover all needs currently identified by the saved assessment. |
| Actions | Gather measurements, combine soil results, or review evidence. |
| Preconditions | Missing measurements must precede relevant review actions. |
| Transition | Add the requirements covered by the selected action. |
| Cost g | Sum of positive relative effort points. |
| Heuristic h | Maximum of the cheapest covering cost for each unmet need. |

`astar_search.py` implements the search; `preparation_planner.py` supplies task definitions and costs. The goal means covering planned information work. It does not guarantee that a measurement will be favorable, a reference will be found, or a crop will become feasible. Real observations require a new assessment.

The code uses a heap priority queue, best known cost per state, stale-entry checks, parent links for reconstruction and a 4,096-expansion limit. The goal is accepted when popped from the queue, not merely when first generated. An unreachable goal or expansion limit is reported explicitly.

# 18. A* dry run: costs, heuristic and a baseline

Use the wheat example with unknown season and texture and blank pH/water. The identified needs are season, texture, pH and water information.

| Available task | Relative effort |
|---|---|
| Confirm season | 1 |
| Obtain pH | 3 |
| Identify texture | 2 |
| Estimate water budget | 2 |
| Obtain pH and texture together | 4 |

Separate tasks cost 8. The combined-soil alternative gives a three-step plan costing 7: confirm season (1), estimate water (2), obtain both soil results (4). Equivalent-cost orderings can exist. These are declared task-model points, not measured hours or money.

## Why the heuristic is safe

At the empty state, the cheapest covering costs are 1, 3, 2 and 2, so h = max(...) = 3. Every complete plan must cover every unmet need. Its total cost cannot be lower than the cheapest cost needed to cover any one of them. Taking the maximum gives a lower bound. Summing could count a shared action twice.

[CODE:astar_search.py:remaining_cost]

The heuristic ignores prerequisites, which is optimistic. It is also consistent: an action either leaves a need uncovered or covers it at a cost at least as large as its cheapest covering cost.

A* and uniform-cost search agreed on minimum cost in 32 controlled scenarios. For this example, A* expanded 10 states and uniform-cost 16. This small comparison demonstrates implementation behavior, not universal superiority or agricultural accuracy. With h = 0, A* becomes uniform-cost search.

# 19. The local transformer: text into comparable vectors

A transformer processes relationships between tokens using attention. A token is a piece of text, not always a whole word. The original Transformer paper describes an attention-based architecture; our application uses pretrained models built on this family of ideas [T1].

MiniLM is used as a sentence encoder. In CropNova, `all-MiniLM-L6-v2` converts short questions and assessment notes into 384-number vectors, also called embeddings [T2]. Related meanings can produce vectors pointing in similar directions. It is not a crop-classification model.

The model is downloaded once by `scripts/prepare_transformer.py`, pinned to a specific revision, and loaded on CPU. Browser requests do not start a model download. The application disables remote model code and requests safetensors weights.

## How this differs from keyword search

A keyword search looks for matching words. Semantic search can connect "Is there enough water?" with a finding labelled "Water supply" even when wording differs. Semantic similarity can still be wrong, especially for unrelated questions or context not covered by the saved assessment.

## What we contributed

We integrated the encoder, built assessment-specific evidence notes, filtered their applicability, cached their vectors and connected retrieval to the question interface. The encoder's original pretraining was done by its authors; our project does not claim that work.

Read `load_encoder()`, `assessment_documents()` and `search_assessment()` in that order. Model details and its Apache-2.0 license are in the model card [T2].

# 20. Similarity and retrieval: a small mathematical view

A vector is an ordered list of numbers. For search, the project normalises embeddings to length one. The dot product then gives their cosine similarity [T3].

```text
score(query, note) = sum(query[i] * note[i])
                         over all vector dimensions
```

A larger score means a stronger match according to this encoder. It does not mean a crop is more suitable, that an answer is true, or that the model has that probability of being correct.

[CODE:semantic_search.py:document_vectors]

`search_assessment()` encodes the question, compares it with the saved notes, sorts scores and keeps up to three above the configured minimum similarity of 0.28. That threshold is an implementation choice; it is not a calibrated agricultural or safety threshold.

## Evidence filtering happens before ranking

Only selected assessment crops are searched. Fact status, constraint eligibility, applicable scope, source review and the exact supporting fact IDs are checked. An attractive wording match cannot make an out-of-scope source eligible.

The code uses a direct NumPy comparison over a very small collection of notes. There is no separate vector database. Adding one would not automatically make the answers more accurate.

Sentence-BERT is useful background reading for sentence embeddings and similarity search [T4]. We use the ready-made encoder interface rather than reimplementing its training procedure.

# 21. Attention, inference and training: useful viva depth

Self-attention lets a token's representation depend on other tokens in the same input. Queries and keys determine attention weights; values carry the information being combined. The standard scaled dot-product formula is background theory [T1]:

```text
Attention(Q, K, V) = softmax(Q K-transpose / sqrt(d_k)) V
```

Here Q, K and V are matrices of token representations after learned transformations. The scale keeps dot products controlled; softmax converts a row of scores into weights. Multiple attention heads can capture different relationships. Position information helps represent order.

## Do not confuse two different comparisons

Attention is inside the pretrained network. CropNova's cosine-similarity calculation compares the final embeddings of separate texts. We did not write the attention calculation in `semantic_search.py`; the installed model implements its own network. Our code calls its encoding interface and ranks the resulting vectors.

## Training versus inference

Training adjusts model weights from data using an optimisation procedure. Inference uses already learned weights to produce an embedding or answer. Our application performs inference. It has no local training loop, backpropagation, optimiser, epoch count or training learning rate to report.

The top-three retrieval limit and 0.28 similarity threshold are application settings. They are not learned crop thresholds and should not be confused with the neural model's trained parameters.

The integrated encoder is useful for sentence meaning. The generative API is useful for composing text. Neither replaces the need for good agricultural evidence, and neither should be presented as a model trained by this team.

# 22. Gemini and the generative explanation

An LLM is a large language model that generates text from its context. CropNova calls Gemini through a server-side HTTP API. The configured model name is read from environment settings; availability and quota are controlled by the provider.

The report feature first calculates the crop checks. `prepare_context()` selects the recorded candidates, checks, facts and limitations. The model is instructed to explain those decisions, preserve crop IDs and statuses, and avoid inventing treatments or new evidence.

## Structured output and application validation

A JSON schema describes the expected answer fields [T5]. The Python validator independently checks the returned structure, complete candidate coverage, unchanged statuses, bounded text and allowed fact references.

A well-shaped JSON answer can still contain an incorrect sentence. Schema validation and citation checks reduce some risks; they do not establish factual correctness. The user should inspect the recorded findings and sources.

## When the provider cannot answer

Missing keys, network errors, quota errors, incomplete responses or failed validation lead to an explicit fallback. Crop checks and deterministic explanations remain available. There is no automatic switch to a paid provider.

The Gemini key belongs in private server settings, not frontend JavaScript, a public repository or a PDF. Local `.env` settings are loaded when starting the development server. Hosted deployments use environment settings configured on the host.

# 23. RAG: answering a question about a saved assessment

RAG stands for retrieval-augmented generation. In this implementation, it means finding relevant recorded assessment notes first, then giving those notes to Gemini to help write an answer.

[FIGURE:rag]

## The request sequence

1. Check that the private assessment link is valid and unexpired.
2. Validate a question of 3-400 characters and an optional assessed crop.
3. Decline explicitly unsupported topics and unassessed crop requests.
4. Retrieve relevant eligible notes with the local encoder.
5. Send the question, recorded statuses and retrieved notes to Gemini, if configured.
6. Reject changed structured statuses and citations outside the retrieved set.
7. Display the answer, cited findings and original source links.

When search is unavailable, the interface says so. When retrieval works but generation fails, it can still display the retrieved findings. An insufficient-evidence answer should not become an invented recommendation.

## Cached answers and limits

Successful answers are cached for ten minutes. Temporary failure results are cached for only fifteen seconds so recovery is not hidden for a long time. Up to six new questions per minute are allowed per report link, and up to two Gemini Q&A calls run concurrently per process. These are basic application controls, not a complete defence for a high-traffic public service.

The result is a small, source-grounded assessment assistant. It is not an unrestricted agricultural chatbot or an internet research agent.

# 24. The website and HTTP: where the browser meets Python

HTML describes page structure. CSS controls layout and appearance. JavaScript handles interactive behavior, such as submitting a question without reloading the whole page. The Python WSGI application receives requests and returns responses.

| Route | Purpose |
|---|---|
| GET / | Show the blank assessment form. |
| POST /assess | Evaluate submitted fields and redirect to a saved result. |
| GET /assessment/{token} | Display the recorded assessment and report. |
| POST /assessment/{token}/ask | Answer a follow-up question for that report. |
| GET /reports/{token}.pdf | Export the same saved assessment. |
| POST /report | Return structured assessment JSON for integration. |
| GET /health | Check that the server responds. |

GET reads a page. POST submits data. The assessment route returns HTTP 303 after saving, so refreshing the result page does not repeat the original submission. Invalid form values return 422; malformed bodies return 400; oversized bodies return 413; missing report links return 404.

## Safer and clearer presentation

The server escapes text inserted into HTML. The question interface creates elements with `textContent`, rather than interpreting generated text as HTML. The server only exposes a small whitelist of static files. Request-body and field-count limits keep malformed submissions bounded.

The threaded development server allows another page to respond while an AI request is waiting. A production deployment uses Gunicorn; the development server is for local work.

# 25. Storage, privacy and report consistency

Each saved result receives a random bearer token. Anyone holding a valid link can read that report, so the link should be treated as private. It is not an account login or a permission system for named users.

The store uses SQLite, included with Python. Queries use parameters rather than concatenating token text into SQL. Each operation uses its own connection, with a context manager for commit and close.

[CODE:report_store.py:load_report]

Saved links are available for one hour. Storage keeps at most 100 reports. Expired rows are cleaned when a new report is saved, so physical removal is not guaranteed at the exact expiry second. The application rejects an expired link even before that cleanup occurs.

## What leaves the application

Crop reasoning and the encoder run locally. Optional generated explanations send selected evidence to the configured provider. Follow-up questions send the question and relevant findings. Town and district input fields are omitted from the Q&A context, but a user could still type personal information in the question.

Private keys and the local database are Git-ignored. Hosting needs appropriate HTTPS, storage permissions, resource limits and provider settings. An ephemeral filesystem can lose saved links after restart; multiple machines need shared storage.

The farm PDF is assembled by ReportLab. Downloading a report is not itself a model-generation event: it formats the previously saved findings and any saved generated wording.

# 26. A complete worked assessment

Open `http://127.0.0.1:8000/?preset=reference-wheat`. This explicitly fills example inputs; the normal home page starts blank.

| Input | Example value |
|---|---|
| State | Haryana |
| Season | Rabi |
| Soil texture | Loamy |
| Measured pH | 7 |
| Water budget | 650 mm |
| Water basis | Seasonal crop-water supply |
| Crop | Wheat |

These values are a presentation example, not measurements collected from a farm.

## Follow the data

The form submits strings. Normalisation produces a nested profile. Crop knowledge is loaded and validated. Eligible wheat facts are selected for the location. The rule engine records evidence and season conclusions. The CSP examines one crop assignment and evaluates four checks.

The current example matches all four limited reference checks. The agent records FEASIBLE_OPTIONS_FOUND. The website translates this into plain language, displays the input/reference comparisons and saves a copy with a private token.

## Explain one result instead of reading the whole screen

"The water input is 650 mm. The recorded wheat reference is 450-650 mm on the same seasonal basis. Our comparison therefore marks this check as covered. The explanation still asks us to confirm timing, losses and local conditions."

Ask "Is my water supply enough for wheat?" to show retrieval and the optional generated answer. If the provider is unavailable, explain the fallback honestly rather than claiming the deterministic text came from an LLM.

# 27. Show improvements by changing one input

A convincing demonstration includes cases that do not produce a match. Start with the wheat example, change only one field, and explain the resulting trace.

| Change from the example | Expected behavior |
|---|---|
| Water = 300 mm | Water shortfall; crop needs attention. |
| Water = 500 mm | Within the reference envelope; local estimate required. |
| pH blank | More information needed; a pH follow-up appears. |
| Water basis = supplemental only | Measurements are incompatible; check stays unresolved. |
| State = unsupported region | Region-specific evidence may be missing. |
| pH = 20 | Invalid input; correct the form before assessment. |

A different valid example can show each supported crop:

| Crop | State / season | Soil / pH | Budget / basis |
|---|---|---|---|
| Rice | Haryana / Kharif | Clayey / 6 | 700 mm seasonal |
| Maize | Rajasthan / Kharif | Loamy / 7 | 800 mm seasonal |
| Chickpea | Haryana / Rabi | Loamy / 7 | 150 mm supplemental |

Use well-drained soil for the maize and chickpea examples. Their documented soil guidance includes drainage prerequisites.

Do not adjust inputs until a desired crop appears and present that as an independent test. Explain why each input was chosen and what source supports its comparison. A controlled example demonstrates behavior; a representative, independently labelled evaluation would measure performance.

# 28. Why the app says 'more information needed'

The message has several possible causes. A required user measurement can be missing, the knowledge base can lack a local reference, or a documented preference may not establish a definite decision. The per-condition reason tells you which problem occurred.

## The Ludhiana example

With Punjab, Rabi, clayey soil, pH 7 and no water budget, the application lacks a required water value. Its current seasonal/soil references also do not cover every Punjab crop case. A pH match alone cannot establish an entire crop match.

Adding an actual measured water estimate resolves only the missing input. It does not manufacture Punjab-specific guidance. For an actual Ludhiana field, keep the correct location; improving the knowledge base requires applicable sources.

## Fully covered worked examples

| Crop | State / season | Soil / pH | Water budget / basis |
|---|---|---|---|
| Wheat | Haryana / Rabi | Loamy / 7 | 650 mm seasonal |
| Rice | Haryana / Kharif | Clayey / 6 | 700 mm seasonal |
| Maize | Rajasthan / Kharif | Loamy / 7 | 800 mm seasonal |
| Chickpea | Haryana / Rabi | Loamy / 7 | 150 mm supplemental |

Choose only the crop in that row, and use well-drained soil for the maize/chickpea examples. The district can be blank. These are example inputs, not collected farm measurements or values to substitute for real observations.

Open `/?preset=reference-wheat` to fill the wheat example. The ordinary home page starts blank. All four implemented checks should match that example, while the report retains the wider limitations about local conditions and crop success.

# 29. Testing: evidence that software behavior is checked

The latest review ran 291 automated tests successfully. The suite covers the agent, constraints, rule outcomes, knowledge validation, region scope, provider failures, HTML escaping, saved reports, PDFs, question validation and server responsiveness.

[FIGURE:checks]

Before adding the separate fuzzy/planning result fields, we compared complete reports for 24 ordinary scenarios before and after the agent refactor. All matched. These include four reference profiles with changed pH, water, state, season or drainage. New tests separately cover the intentional edge-case fixes.

A* and uniform-cost search returned the same minimum cost in 32 controlled scenarios. In the missing-measurement wheat example, A* expanded 10 states and uniform-cost expanded 16; this does not mean A* is always faster.

The actual local encoder was run on six example questions. Each retrieved the expected finding within its top three results. This is a small retrieval smoke check, not an agricultural accuracy benchmark or evidence of broad chatbot reliability.

## Test types in easy language

- Unit test: checks a small function or condition.
- Integration test: checks modules working together.
- Regression test: ensures a previously found bug stays fixed.
- Mock: supplies a controlled external response without calling the actual provider.
- Smoke check: checks that a real component works on a few basic examples.

## Why we do not claim '100% accurate'

Passing tests means the tested software behaviors match their assertions. Tests can share the same assumptions as the code. Independent agronomic cases, representative questions, expert labels and evaluation measures are still required before an agricultural accuracy claim.

Run `python3 -m pytest -q`. For real local-model retrieval, run `python3 scripts/check_transformer.py`. Real Gemini calls consume provider quota and can fail independently of the core reasoning tests. On 14 November 2026, one live report explanation and one live follow-up answer also succeeded; all four reference pages and PDF exports passed HTTP checks.

# 30. Evaluation: what to measure next, without inventing accuracy

A test fixture checks specified program behavior. An independent evaluation asks whether the system's results agree with trustworthy external judgements. CropNova has software tests and a small retrieval smoke check; it does not yet have a representative labelled farm-evaluation set.

## Evaluate the symbolic crop checks

Prepare cases with measured inputs, stated location, relevant sources and expert-reviewed expected outcomes for each condition. Include matches, supported violations, missing measurements, scope gaps, conflicts and incompatible units. Record unresolved cases separately rather than forcing them into a positive or negative class.

Compare expected and recorded condition outcomes. Report how many cases were decided and how many remained unresolved. If a carefully defined binary classification task is appropriate, precision and recall can be measured, but they must use clear labels and denominators. A reported number must say exactly what was evaluated.

## Evaluate retrieval and generated answers separately

For retrieval, label which notes answer each question, then measure whether a relevant note appears in the top K. A larger, varied question set should include paraphrases and questions that have no supported answer. The present six-question check is too small to establish broad reliability.

For generated wording, review whether every claim follows from the cited evidence, whether statuses and measurements are preserved, and whether the model appropriately declines unsupported questions. Passing the JSON validator is only one part of this review.

## Avoid evaluation leakage

Do not use the same handpicked examples to tune behavior and then call them an unbiased test set. Reserve independent cases. Training/validation/test splits become relevant if the team later trains a model; the current symbolic knowledge base is not split into those sets simply to create the appearance of ML training.

# 31. Code walkthrough A: input, status and orchestration

Start with the public entry point, `app.assess()`, then move to `agent.run_assessment()`. Do not start by reading the whole stylesheet or every stored fact.

The main agent function is organised into five commented stages: validate inputs, load knowledge, scope candidates and rules, solve constraints, and build the traceable report. Smaller helpers handle candidate resolution, missing information and source lookup.

[CODE:agent.py:_select_candidates]

This function resolves names and IDs once, preserves user order and avoids duplicate assessments. Leaving the selection empty returns the available domain.

[CODE:agent.py:_status]

This function uses actual constraint results. It does not request unrelated optional fields simply because they are blank. A missing required input and a knowledge gap lead to different internal statuses.

## How to demonstrate code understanding

Set a breakpoint or add a temporary print in a local copy immediately after `solve_constraints()`. Inspect `feasible_candidates`, `unknown_candidates` and `rejected_candidates`. Remove the print afterward, particularly if it contains a private farm profile. You should be able to explain why the example moves into one list rather than another.

# 32. Code walkthrough B: constraints and rule results

Open `constraint_definitions.py`. The result dataclass records what a check established and why. `HardConstraint` provides shared helpers. Season and soil texture reuse a set-based comparison. Water and pH have their own numeric handling.

[CODE:constraint_definitions.py:ConstraintOutcome.to_dict]

The method converts an Enum status and tuple fields into JSON-friendly strings and lists. It changes representation, not the decision.

## Read the water function in this order

1. Is a numeric reference available for this crop and scope?
2. Did the user provide a numeric budget?
3. Do source and input use the same supported basis and units?
4. Are the numeric ranges finite and consistent?
5. Is the budget below, inside, or at/above the reference envelope?

Next open `rule_engine/engine.py`. Each registered rule's conditions produce small result objects. The evaluator combines condition statuses, gathers evidence IDs and establishes a conclusion only when the rule fires.

Rule definitions and constraint definitions are intentionally separate. One can record that season evidence matches while the other checks still need water or pH information. Read their traces together rather than claiming a rule fire guarantees suitability.

# 33. Code walkthrough C: retrieval, generation and display

Open `semantic_search.py` first. `assessment_documents()` builds the small note collection and filters exact supporting facts. `document_vectors()` caches normalised note embeddings. `search_assessment()` ranks notes for a question.

Then open `assessment_questions.py`. It validates question length and selected crops, calls retrieval, prepares the limited context, and validates the written response. `cached_answer()` handles reuse and per-report question limits.

For report wording, open `genai_explainer.py`. The equivalent sequence is context preparation, provider call and answer validation. `gemini_provider.py` handles the bounded HTTP request and reads completed answer text rather than thought parts.

## The final presentation step

`web_views.py` returns HTML bytes for the webpage. `static/app.js` submits the question with `fetch`, creates answer elements and assigns their text using `textContent`. Links are built from recorded source metadata and restricted to HTTP(S).

`assessment_summary.py` gives the webpage and PDF the same everyday explanation of a recorded check. `assessment_pdf.py` formats the saved summary and any saved generated wording. It does not recalculate or call the model.

## A useful debugging question

If a result looks wrong, determine which layer is responsible: input conversion, evidence scope, condition logic, retrieval ranking, generated wording, or presentation. Fixing the explanation text must not hide a wrong underlying check.

# 34. Run, debug and prepare for presentation

Use Python 3.13, the runtime used for the recorded checks. A virtual environment keeps project packages separate from unrelated projects.

```sh
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements-dev.txt
python3 scripts/prepare_transformer.py
python3 -m pytest -q
python3 app.py
```

The model preparation needs an internet connection once. Model files are cached locally. Gemini needs a private key and available provider quota; the normal crop checks do not.

## Useful commands

- `python3 main.py --crop wheat`: print a structured example assessment without a website.
- `python3 scripts/check_transformer.py`: run actual-encoder smoke questions.
- `python3 scripts/audit_knowledge.py`: inspect example coverage and knowledge counts.
- `python3 scripts/build_learning_guide.py`: regenerate this handbook and its source-derived code index.

## Common symptoms

If the browser says the site cannot be reached, confirm the Python process is running on the expected port. If the port is already in use, identify the existing project server before stopping it. If changes are not visible, restart the backend after Python edits and refresh the page.

If crop checks work but the written explanation does not, inspect configuration, quota and fallback status. If semantic search is unavailable, confirm the pinned local model was prepared in the same runtime/cache location. Do not publish keys or paste raw provider error bodies while debugging.

# 35. Review improvements and remaining work

The refactor reduced `agent.py` from 1,342 lines. It is now 459 lines including the fuzzy/planning integration, with input handling separated into a 183-line module. The combined pair is also smaller than the old agent. Shorter code is helpful only if its meaning remains clear; other modules were formatted across more readable lines rather than compressed.

## Concrete changes

- Added numbered workflow comments and clearer module responsibilities.
- Removed duplicate rule-helper implementations by using the registered evaluator.
- Rejected overflowing numbers, malformed objects and excessively long labels.
- Required all declared location restrictions to match.
- Checked the exact eligible fact IDs behind retrieved notes.
- Rejected truncated, oversized and excessive-field submissions.
- Kept temporary AI failures cached briefly so recovery is visible.
- Hid raw internal errors from public JSON and added a same-origin browser policy.
- Updated the CLI examples and obsolete presentation instructions.

## Remaining limitations

Knowledge still covers four crops with limited regional scope. Sources need independent local review and field validation. The encoder needs broader labelled retrieval tests, including irrelevant questions. Citation validation cannot prove every generated sentence. Formal crop scheduling, live weather, multilingual evaluation and economic prediction are not implemented.

Public deployment also needs host-specific memory, persistence, HTTPS, quota and abuse checks. One local SQLite file and process-level limits do not automatically scale across machines. No public hosting deployment is claimed by this review.

# 36. Viva practice: the basic project questions

## 1. What is your project?
CropNova compares a user's farm conditions with published crop guidance and explains the matches, shortfalls and unresolved checks.

## 2. What problem does it solve?
It makes a limited crop comparison traceable, so users can inspect the reason and source instead of receiving an unexplained crop name.

## 3. What are the inputs and outputs?
Inputs include location, season, soil texture, pH, drainage, water budget and basis. Outputs include per-crop findings, reasons, sources, questions and a report.

## 4. Why is it AI?
It uses symbolic knowledge, rules, constraint reasoning and agent coordination. Its optional language features use pretrained neural models.

## 5. Is AI the same as ML?
No. AI is broader. Our main decision layer uses explicit reasoning; the encoder and Gemini are pretrained ML-based components.

## 6. Did you train a model?
We did not train a new crop classifier or LLM. We integrated pretrained models and implemented the evidence and reasoning pipeline around them.

## 7. Is a dataset required?
The symbolic layer needs a knowledge base of facts and sources. Training a new ML predictor would require a suitable labelled dataset. Evaluation still needs independent test cases.

## 8. Are these real farm observations?
The presentation presets are example input values. The knowledge references are published sources. Example inputs must not be presented as collected farm data.

## 9. What makes the system explainable?
Each check retains the entered value, comparison, reason, status, fact IDs and sources. Generated wording sits on top of this trace.

## 10. What makes it different from a generic chatbot?
Its recorded crop result comes from explicit checks. Follow-up answers retrieve evidence from that saved result rather than freely recommending crops from model memory.

# 37. Viva practice: rules, CSP and the agent

## 11. What does 'rule fires' mean?
All conditions required by that IF-THEN rule were satisfied, so its defined conclusion is established.

## 12. Does a fired rule mean a crop is suitable?
No. A rule may establish only that evidence exists or a season matches. The full crop result still requires all four checks.

## 13. What is the difference between rules and CSP?
Rules establish specific conclusions. CSP searches candidate assignments and requires all implemented conditions to hold.

## 14. State your CSP formulation.
Variable: selected_crop. Domain: chosen crop records, or all four. Constraints: season, water, soil texture and pH.

## 15. Why backtracking with only one variable?
It provides a generic assignment-search structure and deterministic traces. With one variable, it is essentially a visit to each domain value; it is not a large combinatorial search.

## 16. What if one check is unknown?
Without any violation, the candidate remains unresolved. Unknown never becomes a pass. A known violation still makes that candidate rejected.

## 17. What does the intelligent agent do?
It normalises inputs, retrieves applicable evidence, evaluates rules and constraints, classifies the result and prepares questions and explanations.

## 18. Is it a learning agent?
It does not retrain from user interaction. It coordinates programmed reasoning and pretrained model inference.

## 19. Have you implemented AI planning?
Yes, for follow-up information tasks: A* searches action sequences with preconditions, positive costs and a goal. It does not plan physical crop treatments or optimise a planting calendar.

## 20. What happens if all candidates fail?
The overall result is no feasible option when each candidate has a supported violation. The report lists the failed checks and their reasons.

# 38. Viva practice: transformers, LLMs and RAG

## 21. What is a transformer?
A neural architecture that uses attention to model relationships between tokens. We use pretrained transformer-based components rather than training the architecture ourselves.

## 22. Why use MiniLM?
It supplies sentence embeddings for local semantic retrieval. Our code can find related assessment notes when the user's wording differs.

## 23. What is an embedding?
A numeric representation of text. Similarity between embeddings helps rank relevant notes; it does not prove the notes or answers are true.

## 24. Is MiniLM generating the answer?
No. The local encoder retrieves notes. Gemini generates the written explanation from the supplied context.

## 25. What is RAG here?
We retrieve relevant saved-assessment evidence, then give it to Gemini to ground a short answer with citations.

## 26. What is cosine similarity?
It compares vector directions. For normalised embeddings, our code calculates it with a dot product. It is a retrieval score, not crop confidence.

## 27. How do you reduce hallucinations?
We limit the context, instruct the model to use it, require citations, preserve statuses and reject malformed responses. These checks do not eliminate every factual error.

## 28. Is RAG the same as fine-tuning?
No. Retrieval supplies evidence at request time. Fine-tuning changes a model's parameters through training. We have not fine-tuned these models.

## 29. Can Gemini change the saved crop decision?
The application does not use its answer to update the solver result or knowledge base. Structured status changes cause validation failure.

## 30. What happens without internet or API quota?
Prepared local reasoning and encoder inference can still work. Gemini generation needs network access and available quota; otherwise the application shows findings or a clear fallback.

# 39. Viva practice: evidence, testing and deployment

## 31. Is 650 mm a wheat irrigation prescription?
No. In the example it covers a published seasonal reference envelope on the same basis. Timing, rainfall, losses and local demand remain unverified.

## 32. Why does 500 mm remain unresolved?
It is inside the reference range. The exact local requirement is not established, so we cannot claim sufficiency from that comparison alone.

## 33. Why not reject every pH outside the preferred range?
A preference is not necessarily a survival boundary. An outside value can require local review instead of proving incompatibility.

## 34. What accuracy did you achieve?
We do not claim agricultural accuracy. The review passed 291 software tests, 32 A*/uniform-cost comparisons and six basic retrieval checks. An earlier refactor also passed 24 full-report comparisons. These measure different limited things.

## 35. Why use mocks?
They test model-response handling and failure cases repeatably without spending provider quota. They do not prove the live provider is always available.

## 36. Where are reports stored?
In a private SQLite snapshot with a random link. Links expire after one hour, and the store is bounded to 100 reports.

## 37. Is the downloadable PDF generative AI?
Its layout and recorded findings are assembled by code. If generated wording was requested and saved, that wording is included. Downloading does not call the model again.

## 38. Is the project ready for real farming decisions?
It is a preliminary support tool. Broader regional evidence, independent agronomic review and field evaluation are still required.

## 39. What did you improve, with a concrete example?
We changed status logic to follow actual constraint results, separating missing inputs from knowledge gaps. This review also prevented one location restriction from overriding another.

## 40. Where should you show the implementation?
Show both the website behavior and the relevant function: the agent, a constraint, the solver, and the question retrieval/validation code. The final code index gives the locations to open.

# 40. Viva practice: fuzzy logic and A* in our code

## 41. Why add fuzzy logic when we already have CSP?
CSP gives a discrete result. Fuzzy logic separately describes gradual pH/water alignment without changing that result.

## 42. What does 0.6 membership mean?
The input fits a particular fuzzy set to degree 0.6 under our membership function. It is not 60% probability or crop accuracy.

## 43. Which inference method did you implement?
Zero-order Sugeno: min for antecedent AND, constant rule consequents, and a normalised weighted average for the index.

## 44. Where did membership thresholds come from?
They are explicit engineering settings for normalised reference alignment. They still need expert calibration before agricultural interpretation.

## 45. Can a high index overrule a failed constraint?
No. A known failed check blocks the index, and unresolved checks remain unresolved even when an index is available.

## 46. What does A* search for here?
A low-relative-effort sequence of follow-up information and evidence-review tasks. It does not search for a physical treatment that guarantees suitability.

## 47. What are g, h and f?
g is accumulated effort, h is an optimistic remaining-effort estimate, and f = g + h determines priority.

## 48. Why not use Manhattan distance?
Our states are sets of covered requirements, not grid coordinates. The heuristic must match this task space.

## 49. How did you check A* optimality?
We compared minimum costs against uniform-cost search on controlled cases and tested heuristic admissibility, consistency, prerequisites and limits.

## 50. Does A* always beat uniform-cost search?
No. Both can find the same minimum cost; expansion counts depend on the heuristic and task graph. Our small examples do not establish universal speed superiority.

# 41. Your five-minute presentation and study exercises

## A practical five-minute sequence

Minute 1: Explain the problem, inputs and the distinction between crop checks and language explanation. Minute 2: Run the wheat example and show a source-backed condition. Minute 3: Change water to 300 mm, then clear pH, explaining the different outcomes. Minute 4: Ask an assessment question and identify retrieval, generation and evidence cards. Minute 5: Open the key code functions and show the test command and honest limitations.

## A strong before-and-after explanation

"Earlier, an assessment could request unrelated optional information even when those fields did not affect our four checks. We changed classification to use the actual constraint outcomes. Now missing required input and missing applicable knowledge are reported differently."

Use this explanation only with the corresponding historical change and tests; do not claim every old behavior can still be reproduced in the current build.

## Exercises that prove you understand the code

1. Predict the result when pH is blank before submitting the form.
2. Find where an unknown check is prevented from becoming feasible.
3. Trace one source ID from a fact to a check to a webpage link.
4. Explain why the water basis changes the comparison.
5. Find the exact function that rejects an invented citation.
6. Show that downloading the same report does not call Gemini again.
7. Add a controlled test for an input edge case without changing agricultural thresholds.

Do not memorise unsupported claims to impress an examiner. A clear, accurate explanation of a small working system is stronger than claiming unimplemented algorithms or an invented accuracy percentage.

# 42. Further reading and code navigation

These sources explain background concepts and the APIs used. They do not constitute independent validation of CropNova's agricultural results.

- [T1] Vaswani et al., Attention Is All You Need (2017): https://arxiv.org/abs/1706.03762
- [T2] Sentence Transformers, all-MiniLM-L6-v2 model card: https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2
- [T3] Sentence Transformers, semantic search documentation: https://www.sbert.net/examples/sentence_transformer/applications/semantic-search/README.html
- [T4] Reimers and Gurevych, Sentence-BERT (2019): https://arxiv.org/abs/1908.10084
- [T5] Google Gemini, structured output documentation: https://ai.google.dev/gemini-api/docs/structured-output
- [T6] UC Berkeley CS188, CSP course notes: https://inst.eecs.berkeley.edu/~cs188/archive/fa22/assets/notes/cs188-fa22-note03.pdf
- [T7] Python documentation, sqlite3: https://docs.python.org/3/library/sqlite3.html
- [T8] MathWorks, Sugeno fuzzy inference: https://www.mathworks.com/help/fuzzy/types-of-fuzzy-inference-systems.html
- [T9] Carnegie Mellon University, search notes: https://www.cs.cmu.edu/~07280-f26/notes/search/index.html

Agricultural values in this handbook describe the current repository's source records. The table below lists the actual sources attached to the four reference examples. Open the recorded document and section before changing a value or expanding its scope.

[AGRICULTURAL_SOURCES]

# 43. Exact code locations: open these while studying

This index is generated from the current Python source rather than typed from memory. It identifies the main functions and classes and their starting line numbers. The source file and symbol name are authoritative if later edits shift the lines.

[CODE_INDEX]

## Files you do not need to study first

The active website starts at `app.py`; the CLI example starts at `main.py`. Older backup constraint files, the starter knowledge folder and historical report-building assets are not the active reasoning path. Keep them separate from your presentation of the current implementation.

## Find a symbol quickly

```sh
rg -n 'def run_assessment' agent.py
rg -n 'class WaterConstraint' constraint_definitions.py
rg -n 'def validate_written_answer' assessment_questions.py
```

The reproducible review snapshot is in `docs/project_review.json`. The actual encoder checks are in `docs/transformer_checks.json`. Historical provider checks are dated records, not a guarantee of current quota or availability.
