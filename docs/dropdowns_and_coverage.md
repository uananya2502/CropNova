# Dropdown controls and available reference examples

The current knowledge base supports these complete worked examples. They are example inputs, not collected farm observations or guaranteed planting recommendations.

| Crop | State | Season | Texture | pH | Water depth | Water basis | Drainage |
|---|---|---|---|---|---|---|---|
| Wheat | Haryana | Rabi | Loamy | 7 | 650 mm | Seasonal crop-water supply | Well drained |
| Rice | Haryana | Kharif | Clayey | 6 | 700 mm | Seasonal crop-water supply | Well drained |
| Chickpea | Haryana | Rabi | Loamy | 7 | 150 mm | Supplemental irrigation | Well drained |
| Maize | Rajasthan | Kharif | Loamy | 7 | 800 mm | Seasonal crop-water supply | Well drained |

Choose one crop, or load its profile from the menu at `/assess`. District is optional; these reference examples do not establish district-specific recommendations. The reference ranges and their limits are explained in `knowledge_requirements.md`.

## What changed

- All visible assessment choices are native dropdowns; only the internal objective remains a hidden field.
- Crop selection defaults to an explicit required choice, avoiding accidental comparison of all four crops across incompatible regional scopes. Comparing all four is still an explicit option.
- Soil pH uses 0.1 increments from 0 to 14. Water depth uses 25 mm increments through 2,000 mm plus selected larger values. Unknown remains an option. Exact values already stored in a report are preserved when editing rather than rounded.
- Changing state updates the district menu. Saved unlisted labels remain visible on edit; unknown district choices do not invent crop knowledge.
- A live preview compares the same inputs with the same reference checks. It shows matched checks and names the specific remaining condition. It does not save an assessment, request generation or use provider quota.
- A reference-profile picker and coverage table are visible before submission. No knowledge fact or regional scope was altered to make an example pass.

## Scope and geography

State/territory labels are taken from the Government of India directory. District choices currently cover Haryana (23, including Hansi), Rajasthan (41), and Punjab (23). For other states the district may be left unspecified. These geographic lists are UI metadata, not agricultural source evidence.

Sources checked on 15 November 2026:

- [State and territory directory](https://igod.gov.in/sg/states)
- [Haryana district directory](https://igod.gov.in/sg/HR/E042/organizations)
- [Hansi district administration](https://hansi.haryana.gov.in/)
- [Rajasthan district directory](https://igod.gov.in/sg/RJ/E042/organizations)
- [Punjab district directory](https://igod.gov.in/sg/PB/E042/organizations)

The older Haryana state district page still lists 22 districts; the current directory and Hansi administration confirm the additional district. The menu uses the newer list.

Punjab and other states still lack the same complete local crop records. A blank water value, an unsupported location, an incompatible water basis, or a condition outside a documented preference can remain unresolved. The preview makes these reasons visible before generating a result; it does not suppress them.

## Code and verification

- `form_choices.py`: state/district lists, numeric options and crop submission compatibility.
- `assessment_form.py`: dropdown rendering, profile picker and worked coverage table.
- `coverage_preview.py`: read-only reasoning preview.
- `app.py`: `/form-options`, `/coverage-preview` and submission parsing.
- `static/app.js`: dependent district options and debounced preview requests.
- `tests/test_dropdown_form.py`: checks controls, complete profile submissions, exact-value preservation, missing inputs, Punjab gaps and no provider/storage calls from previews.

Validation: 340 automated tests pass. All four covered profiles were submitted using defaults parsed from the rendered dropdowns, and each matched all four implemented reference checks. This does not measure agricultural accuracy. Browser visual automation is unavailable for localhost in this session; endpoint and native HTML behavior are checked without claiming visual browser QA.
