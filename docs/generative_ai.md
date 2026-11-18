# Generative AI explanations in CropNova

## Provider setup: Google Gemini

CropNova now supports Google Gemini as well as OpenAI. The local configuration selects **Gemini**, using `gemini-3.5-flash-lite`. At the earlier account setup, Google AI Studio showed the connected project on its **Free tier**. No billing upgrade was enabled. That observation is historical; provider eligibility, model access and quotas may change.

Google publishes a free input/output tier for this model, with usage limits and eligibility conditions. Free-tier content may be used to improve Google's products. Use example profiles rather than personal farm records for classroom testing. See [Google's pricing](https://ai.google.dev/gemini-api/docs/pricing) and [API key documentation](https://ai.google.dev/gemini-api/docs/api-key).

The app never switches automatically to OpenAI when Gemini fails or reaches a limit. An API key does not guarantee quota or model access. Live verification completed for all three cases: supported match, water shortfall and missing pH. Each returned a generated explanation that passed the status/reference checks. The dated results are recorded in `ai_verification.json`.

## What the AI does

The rule engine and CSP run first. The language model receives the recorded crop checks, supporting facts and limitations. It writes a short explanation for each crop in easy English.

We use a pretrained model through an API. We have not trained a new language model. It does not add facts to the knowledge base or choose the crop independently.

On the website, select **Add a plain-language explanation**, then run the assessment. The written report appears directly on the result page, followed by the recorded crop checks. Without an available service, the original assessment still works.

## Private local settings

The server loads `.env` when it starts. Git ignores this file, and it has owner-only permissions. Existing environment variables take priority.

The selected provider uses these settings:

```text
AI_PROVIDER=gemini
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_API_KEY=your-private-key
```

Never commit your real key or paste it into a chat. If you need to configure a replacement key privately, run:

```zsh
python3 scripts/configure_ai.py --provider gemini
```

The setup command preserves existing keys. If a Gemini key already exists, edit the local file privately to replace it. Restart the website to load changed settings:

```zsh
python3 app.py
```

Use Python 3.10 or later; Python 3.13 is the tested runtime. Provider calls use the Python standard library. Install `requirements.txt` for PDF reports, the deployment server and local transformer retrieval. Stop the existing server before starting another on port 8000.

OpenAI support remains available through `AI_PROVIDER=openai`, `OPENAI_API_KEY` and `OPENAI_MODEL`. That provider requires its own API quota or credits. It is not used as a fallback.

## Read the code in this order

| Code | What it does |
|---|---|
| `web_views.py`: `farm_form()` | Lets the user request an explanation and names the selected provider. |
| `agent.py`: `run_assessment()` | Runs input validation, knowledge retrieval, rules and CSP. |
| `genai_explainer.py`: `prepare_context()` | Collects results and evidence without the user's district or town inputs. |
| `response_schema()` | Describes the fields the model must return. |
| `gemini_provider.py`: `call_gemini()` | Sends one bounded request to Google's Generate Content API and reads only model text. |
| `genai_explainer.py`: `call_openai()` | Provides the separate OpenAI adapter. |
| `validate_answer()` | Checks candidate IDs, statuses, text length and evidence references. |
| `generate_explanation()` | Chooses the configured provider and handles unavailable services. |
| `local_settings.py` | Reads allowed local settings without running shell commands. |
| `web_views.py`: `inline_report()` | Escapes generated text and displays it beside the original results. |

An API lets one program request a service from another. JSON is a structured text format. A schema describes the expected shape of that text. An environment variable supplies a setting to a running program.

## What is checked

The model must preserve the assessment status. Every crop must appear once, with its original status. Cited fact IDs must come from that crop's recorded checks. Empty, malformed and incomplete replies are not shown. Provider errors and API keys are not displayed in the assessment.

These checks do not prove every sentence is correct. The model can misrepresent a fact while using a valid reference ID. Generated wording is labelled, and the original trace remains available for comparison. Published-reference screening still needs independent local agronomic validation before real farming use.

The Gemini request does not start a persistent chat or create a file store. Google's free-tier data terms still apply. The OpenAI adapter requests `store: false`; that setting does not promise zero provider retention.

## Test it

Choose **Published reference: Wheat**, tick **Add a plain-language explanation**, and run the assessment. The example uses Haryana, Rabi, loamy soil, pH 7 and a 650 mm seasonal crop-water budget.

To test all three website cases—match, water shortfall and missing pH—run:

```zsh
python3 scripts/verify_ai.py --live
```

The command saves dated results to `docs/ai_verification.json`. It reports missing keys, rate limits or failed generation honestly. Without `--live`, it only checks the local assessment paths.

Automated tests use controlled replies rather than paid or quota-consuming API requests. Run `python3 -m pytest -q` after installing the development requirements.

The implementation follows [Google's structured-output guide](https://ai.google.dev/gemini-api/docs/structured-output), [Generate Content API reference](https://ai.google.dev/api/generate-content) and [OpenAI's Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs).

## Explain it to the teacher

“Our rule engine and CSP produce the crop assessment. A generative AI explanation layer receives those results and their evidence. It explains them in easy language. Our code checks that the crop statuses and evidence references remain consistent, and the standard assessment still works if the AI service is unavailable.”

## Personalised report feature

The public website now saves a completed assessment behind a random, one-hour link. Its PDF contains field inputs, results, measured-versus-reference comparisons, reasons, sources and unresolved questions. A successful optional generated explanation is included and labelled. Downloading the report does not call the model or rerun the checks. PDF layout and recorded results are generated by application code, not by the language model.

## Review verification on 14 November 2026

A fresh live report explanation and one evidence-grounded follow-up answer succeeded with the existing Gemini configuration. The local encoder was also checked on six example questions. See `http_review.json` and `transformer_checks.json`. These checks do not establish agricultural accuracy or guarantee future provider quota.
