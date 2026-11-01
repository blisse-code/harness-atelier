# Contributing

1. **Start from a failure.** Open an issue that describes a real setup where the skill did the wrong thing: the prompt, what it did, and what it should have done.
2. **Add a fixture or a rubric row first**, then change the skill. A fix without a test regresses.
3. **Keep the skill lean.** `SKILL.md` stays under 500 lines. Detail goes in `references/`. Explain *why* rather than adding capital-letter MUSTs.
4. **Visuals are generated.** Edit `docs/visuals/build_visuals.py`, run it, and commit the SVGs. Motion must stay CSS-only and reduced-motion safe.
5. **Run `python3 evals/run_evals.py`** before opening a pull request. CI runs the same checks.
6. **No copied content.** Learn from other harnesses and skills, cite them in the README credits, and write in your own words.
