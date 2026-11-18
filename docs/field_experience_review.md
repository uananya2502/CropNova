# Field experience review — 15 November 2026

## Crop and state choices

The assessment crop menu contains crop names only. The state menu contains state names only. Locations on published example profiles describe those example inputs, not where a crop can grow. Applicability still comes from source scope: removing a menu label does not invent local agronomic evidence.

## Practical next steps

`farm_next_steps.py` now turns the recorded season, water, soil and pH findings into four practical action cards. Each card includes the entered value, its reference, an explanation of the relevant finding, and source links where recorded. Water shortfalls, missing measurements and incompatible measurement bases produce different instructions.

New assessments preserve reviewed, applicable sowing-window and indicative growing-period records in a separate `field_guidance` snapshot. These records help explain planning; they do not satisfy a crop constraint, change the result or enter the LLM's crop-decision evidence. Historical ECOCROP entries remain excluded.

Old saved reports still render meaningful actions using their original recorded checks. They do not silently acquire new sources. Reassessing creates a new snapshot with the current published background guidance.

The A* information-task sequence remains available in an optional disclosure when there are open tasks. Artificial effort points have been removed from farmer-facing wording. A task sequence is not a crop-care calendar or an irrigation schedule.

## Visual identity and motion

The theme uses forest and sage greens, with restrained wheat-gold, olive and terracotta accents. Three generated decorative assets are stored locally as compressed WebP files:

- `static/field-morning.webp`: landing-page field illustration.
- `static/botanical-paper.webp`: faint page texture, under a readability overlay.
- `static/harvest-banner.webp`: landing-page closing banner.

Cards use rounded leaf-like corners, restrained colour panels and larger reading spaces. Transitions cover hover/press feedback, rain selection, disclosure opening and short page/card entrances. All motion is disabled for `prefers-reduced-motion: reduce`; content remains visible without JavaScript. The generated artwork is decorative and is not evidence about a real farm.

## Verification

The full suite passes 415 tests. New checks cover plain crop labels, wheat in Punjab, field-specific next-step instructions, source review and location gates, sowing-window snapshots, missing or mismatched water measurements, old saved reports and immutable decisions. JavaScript and CSS syntax checks pass. Live HTTP verification covers page assets, forms, saved results, editing, reports, next steps and readiness. Browser visual review remains unavailable because the browser policy blocked localhost; no screenshot-based layout verification is claimed.
