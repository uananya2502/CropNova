# Showing the current project

This replaces the earlier synthetic website instructions. The public website uses published references; synthetic fixtures remain in tests only.

1. Run `python3 app.py`, then open `http://127.0.0.1:8000/?preset=reference-wheat`.
2. Explain the example values: Haryana, Rabi, loamy soil, pH 7, 650 mm seasonal crop-water budget, Wheat. These are example inputs, not collected farm measurements.
3. Submit and open the crop findings. Show the input, reference, reason and source for each of the four checks.
4. Change only water to 300 mm and reassess. The water check reports a reference shortfall.
5. Restore 650 mm and clear pH. The result needs more information, with a targeted follow-up.
6. Restore pH and change water to 500 mm. It falls within the reference range and remains unresolved pending a local estimate.
7. Ask “Is my water supply enough for wheat?” in the saved assessment. Explain local semantic retrieval and the optional Gemini-written answer. Provider availability and quota can affect the written answer.
8. Open `agent.run_assessment`, the four classes in `constraint_definitions.py`, and `csp_solver.solve_constraints`. Show `python3 -m pytest -q` and explain one regression test.

Read the full code map, explanations and viva questions in `learning_guide.md`. Do not claim field validation, a trained crop classifier, a classical farm-planning algorithm, or a guaranteed crop recommendation.
