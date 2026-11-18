# Farmer-focused CropNova changes

The existing Python application, saved assessment pages and crop-checking pipeline remain in place. This update adds a simpler input experience and explains the recorded findings in everyday language.

## What the farmer sees

- Four illustrated choices: No Rain, Low Rain, Medium Rain and High Rain. These describe observed rain this growing season, not a weather forecast.
- An optional exact seasonal rainfall field. Rainfall observations never become a guessed water budget.
- Simple choices for rain-only fields and access to irrigation. A measured usable-water estimate is available under an optional advanced section.
- Crop matches first, with entered values and the corresponding published references. Equal matches are labelled jointly; no yield or profit ranking is invented.
- A compact comparison of the other crops. If no crop matches all four checks, crops with at least three matches may be shown as worth checking first, explicitly pending confirmation.
- English, Hindi and Punjabi explanations, with an optional three-column view. The main native-language explanation comes before the other-crop comparison.

## Generative explanations

The existing Gemini and OpenAI integrations are reused. Both are Transformer-based LLM services. No LLM is trained by this project.

The writer receives the actual entered values, recorded outcomes, matching reference ranges and only the facts cited by those checks. Town and district input fields are omitted. Rain observations are explicitly separate from usable crop-water supply. Archived ecological entries are excluded.

A multilingual response has one translation per requested language, an unchanged crop status, valid evidence IDs, the selected primary text, and a separate precaution in each language. Validation rejects missing or duplicate languages, missing native scripts, changed decisions, unsupported numbers, invented evidence IDs and mislabelling published data as synthetic. These checks do not establish perfect translation or sentence-level factual correctness. Farmer and agricultural-expert review is still needed.

If the provider is unavailable or its answer fails validation, deterministic explanations in the requested languages still show the crop-check results. The farmer does not need an API key or an account.

The saved website report uses the selected primary language. The optional PDF export keeps English findings; native explanations remain available on the website, avoiding missing Indic glyphs in the current PDF font setup.

## What the 640 knowledge records mean

The library has ten assessment crops: wheat, rice, maize, chickpea, barley, cotton, groundnut, sorghum, pearl millet and soybean.

There are 112 core records, including reviewed screening references, background guidance and a small number of previously pending records. The expansion adds 528 non-empty, original ECOCROP attributes for 13 species corresponding to those crops. Cotton has four species; this does not add extra assessment crop options.

The 528 historical attributes are deliberately marked `needs_review`, `historical_reference: true` and `constraint_eligible: false`. They appear in the sources library for study, with original units and species, but never satisfy crop checks or enter LLM explanation evidence. This avoids silently replacing newer local guidance with conflicting global ranges. FAO says ECOCROP was discontinued around 2015. Its annual rainfall fields are not seasonal crop-water estimates.

This is a knowledge library, not 640 measured farms or a model-training dataset. Increasing its record count does not establish agricultural accuracy.

Reproduce the source-reviewed additions with `scripts/expand_crop_knowledge.py`, followed by `scripts/import_ecocrop_background.py`. The historical importer pins its source CSV commit, records a SHA-256 hash, omits missing fields and preserves original field codes. It does not invent entries to reach a target count.

Sources:

- [FAO ECOCROP overview and historical status](https://www.fao.org/land-water/resources/tools/databases/ecocrop/en)
- [Pinned FAO snapshot distributed with the OpenCLIM project](https://github.com/OpenCLIM/ecocrop/blob/ea43ecd418fd1a1ea08d32c7dce64b7fae02dec4/EcoCrop_DB.csv)
- [PAU Kharif 2026 package](https://pau.edu/content/ccil/pf/pp_kharif.pdf)
- [PAU Rabi 2025–26 package](https://pau.edu/content/ccil/pf/pp_rabi.pdf)
- [FAO indicative seasonal crop-water guidance](https://www.fao.org/4/s2022e/s2022e07.htm)

## How to make it useful beyond a classroom

The useful first audience is farmers and extension workers comparing a small set of crops in a covered region. A credible next step is to have a local agronomist verify Punjab/Haryana crop records and test the workflow with a small group of farmers. Record whether they understand the input questions, whether the open questions are actionable, and how the shortlist compares with the adviser’s assessment.

Later priorities are local weather with a clear date and forecast horizon, easier water estimation using field area and known irrigation measurements, voice input/read-aloud support, and locally approved sowing guidance. Each should be added with an appropriate source and evaluated separately. More LLM prose alone will not make recommendations reliable.
