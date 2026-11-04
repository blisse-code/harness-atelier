# Changelog

## 0.2.0

- Generated harnesses check themselves: an `evals/` kit (script tests, a behaviour runner with 8 cases run in a sandboxed throwaway copy, a rubric with a row per known failure, a run log) and an `evals` skill that runs them, triages failures and keeps cases fitted to the project.
- Scaffold adds `evals` to the moves table and a row per interview failure to `evals/EVALS.md`; `verify_harness.py` runs the script evals; the interview asks which mistakes would hurt most and who fixes eval findings.
- Template fixes found by those evals: intake writes the brief with `[[ASK]]` markers instead of waiting for answers; handover triggers on a stated decision or "I'm stopping"; owner-stated rules are recorded the same turn.
- Generated dashboard: animated "How this harness works" section (pipeline and check loop, live numbers, Replay, reduced-motion safe).
- Repo: new animated diagram `evals.svg`; the learning loop gains "a rule stops holding → an eval case"; 83 deterministic evals (was 64).

## 0.1.0

First public release.

- Skill: interview (anchored on a real project and a failed one), harness map before files, generation, tailoring, verification, handover.
- Generated harness: CLAUDE.md map, 8 workflow skills, evaluator and reconciler agents, SessionStart / PreToolUse / Stop hooks, structured records with one schema, deterministic sensors (confidentiality, schema drift, duplicate IDs, unplanned feedback, blocked and overdue work, ship without sign-off, insight evidence, stale handover, work in a master, unfilled seeds, open questions, off-system colour and spacing), committed and machine-local confidentiality lists, master and project roles, a status dashboard with reduced-motion-safe motion.
- Scaffold never overwrites and refuses protected paths; verifier plant-tests the write guard and scores each part.
- Typography: Atkinson Hyperlegible (OFL) in the diagrams (embedded subset) and the generated dashboard (bundled, offline).
- Repo: Claude Code marketplace manifest, animated SVG diagrams from a generator, 64 deterministic evals in CI, release workflow that attaches the .skill file when a release is published.
