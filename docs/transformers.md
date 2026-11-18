# Transformers and follow-up questions, in easy words

CropNova now uses two pretrained AI models for different jobs. We have integrated these models; we have not trained a new foundation model.

## 1. The local transformer finds the useful findings

The sentence transformer is `sentence-transformers/all-MiniLM-L6-v2`. It turns a question and the saved assessment findings into lists of numbers called embeddings. Text with related meaning usually has similar embeddings. CropNova compares these lists to retrieve up to three relevant findings.

For example, “Is there enough water for wheat?” should find the recorded water check even though the question does not use the exact field label “water budget”. This is semantic search.

This encoder does not write answers and does not decide which crop matches. It runs locally on the CPU. Its similarity score is a retrieval aid, not a percentage of suitability, confidence or agricultural accuracy.

We pin the model to revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, load safetensors, and disable remote model code. The model is pretrained and Apache-2.0 licensed. Model details: [Hugging Face model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2). Search method: [Sentence Transformers documentation](https://www.sbert.net/examples/sentence_transformer/applications/semantic-search/README.html).

## 2. Gemini writes the answer

Gemini was already connected for the optional written assessment explanation. The new question feature also uses Gemini: it receives the question, recorded crop decisions and retrieved findings, then writes a short answer. This retrieve-then-generate pattern is called retrieval-augmented generation, or RAG.

The answer includes references to retrieved finding IDs. CropNova resolves these IDs into evidence cards and the original source links. A response that changes a structured crop decision or cites an unknown finding is rejected. This validation does not prove every sentence is correct; users should still inspect the evidence.

The model does not update the knowledge base or saved crop result. It cannot reassess a hypothetical input change: users update the field form for that. With a missing key, exhausted quota or provider failure, the feature displays retrieved findings without pretending that a written answer was generated. There is no automatic paid fallback.

## 3. The original reasoning still decides the result

The rule engine and constraint checks compare the entered season, soil texture, pH and water supply with applicable references. The local encoder finds relevant explanations of those checks. Gemini puts those explanations into everyday language.

A simple explanation for a presentation:

> Our reasoning system checks the farm conditions. A local transformer finds the most relevant evidence for the user's question. Gemini explains that evidence in simple words, with source links. The explanation does not change the recorded decision.

## Try it

```sh
python3 -m pip install -r requirements.txt
python3 scripts/prepare_transformer.py
python3 app.py
```

Preparing the model needs an internet connection once. Requests never initiate a download. The cache defaults to `instance/models`; set `CROPNOVA_MODEL_CACHE` in the process environment to use another location. The Gemini key remains a private server environment variable.

Run an assessment, then use **Ask about your assessment**. Example questions:

- “Is my water supply enough for wheat?”
- “Why does this crop match my field?”
- “What information is still missing?”

Questions about unsupported crops, treatments, yield predictions or prices are declined. Questions and relevant evidence are sent to Google when a written answer is requested; town/district fields are not included in the Q&A context. Do not enter personal information in questions. The question box states this before submission.

## Code map

| File | Purpose |
|---|---|
| `semantic_search.py` | Loads the encoder, builds scoped evidence records and ranks their embeddings |
| `assessment_questions.py` | Validates questions, retrieves findings, calls Gemini and validates citations and decisions |
| `app.py` | Accepts a question only for a valid, unexpired private assessment link |
| `web_views.py`, `static/app.js` | Displays the question form, answer and source cards |
| `scripts/prepare_transformer.py` | Downloads and prepares the pinned local model |
| `scripts/check_transformer.py` | Runs six actual-model retrieval smoke checks |

The code keeps search, generation, validation and page rendering in separate small functions. Comments explain the purpose of each stage. The first question can take longer while the encoder loads; later questions reuse it. Repeating the same question uses a ten-minute cache. Requests are limited to six new questions per minute per report, with two simultaneous Gemini Q&A calls per server process.

## What was checked

The actual encoder retrieved the expected finding within its top three results for six example questions covering water, pH, season and soil across the four supported crops. Results are saved in `docs/transformer_checks.json`. This is a small smoke check, not an accuracy benchmark or field validation. Run it again with `python3 scripts/check_transformer.py`.

Automated tests cover source review and regional filtering, retrieval ranking, invalid citations, changed crop statuses, provider failure, private report access, input limits, repeated questions, rate limits and unchanged saved assessments. These tests use controlled model responses and consume no API quota.

## Hosting considerations

The transformer needs more memory and installation space than the earlier standard-library crop engine. Use one Gunicorn worker with threads to share one loaded model. Choose a host with enough RAM for Python, PyTorch and the encoder, and measure usage on that host. A free Gemini quota does not make application hosting free. An unprepared model or an undersized host leaves normal assessment findings available but cannot provide semantic search.

Search is currently English and limited to the saved assessment. It does not search the whole internet, learn from questions, diagnose crop images or guarantee that every unrelated question is rejected by the similarity threshold. Broader evaluation with locally reviewed questions remains future work.
