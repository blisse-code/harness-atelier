---
name: harness-atelier
description: Build a complete, working AI harness for a designer or design team from scratch. It interviews them about how they actually work, maps the harness, then generates and verifies the whole system - CLAUDE.md map, workflow skills, an independent evaluator agent, hooks, structured records, deterministic checks, a confidentiality guard and a status dashboard. Use whenever a design lead, studio or agency, freelancer or in-house product designer wants Claude set up around their design or research process, asks for a "harness", "AI workflow", "agent setup", "CLAUDE.md for my team", "design ops with AI", "a project template for design work", or wants every session to follow their process and leave reusable output behind, even if they never say "harness".
---

# Harness Atelier

A harness is everything around the model that makes it reliable for one kind of work: what it reads first, what it may and may not do, where it writes, how its output is checked, and how the setup improves after each mistake. Most of the quality gap between a good AI session and a bad one comes from the harness, not the model. Designers feel this as "it was great yesterday and forgot everything today", "it invents spacing values", "feedback got lost between the meeting and the file".

This skill builds that harness for one designer or team, fitted to how they really work, and leaves a system that runs: files, hooks, checks and a dashboard, verified before you call it done.

## What gets built: five parts

| Part | Job | Generated as |
|---|---|---|
| **Rails** | Keep output inside what's allowed: tokens, components, patterns, user constraints, confidentiality | `system/`, `context/ux-context.md`, `.harness/confidential.txt`, a write-time guard hook |
| **Memory** | Hold the truth between sessions and people | `CLAUDE.md` (a short map), `context/`, `docs/decisions.md`, `records/handovers.md` |
| **Moves** | The workflow itself | stage table in `CLAUDE.md`, 8 workflow skills, evaluator and reconciler agents, hooks |
| **Checks** | Catch problems before a person reviews, and prove the harness itself still works | deterministic sensors (`scripts/harness_check.py`), a gate run by a separate evaluator, and evals of the harness (`evals/`, the `evals` skill): script tests, behaviour cases run in a throwaway copy, seeded-gate and flow checks |
| **Loop** | Turn every miss into a permanent fix | `docs/evolution.md` (failure register, rituals), decisions log, past-work index; every logged miss also becomes an eval case |

Read `references/principles.md` once before your first build: it explains why each part exists, which is what lets you tailor it well instead of filling in a template.

## Ground rules

- **Reference material is read-only.** When the person points you at an existing harness, repo or folder "to learn from", read it, never write to it, and pass it to the scaffold as `--protect`. If you're working through a device bridge, use read-only commands only (`cat`, `ls`, `find`, `grep`).
- **Learn, don't copy.** Take principles from references; build the harness from this skill's templates and the interview. Never copy another repo's files, wording or structure wholesale, and never install third-party skills or plugins into the harness without the person reviewing them.
- **Never guess what a person must answer.** Unknowns become `[[ASK: ...]]` markers in the generated files. A confident wrong value in a harness is worse than a visible gap, because every future session obeys it.
- **Never create secrets, keys, passwords or rate figures**, and never ask for them.
- **Don't claim it works until you've run it.** `scripts/verify_harness.py` and a dry run are the evidence; report exactly what they showed.
- **Keep chat short; put detail in files.** The person reviews the map and the generated files, not a wall of chat.

## Workflow

Use a task list; this takes several turns. Tell the person what you're about to do in one sentence, then start.

### Phase 0: Look before building

1. Find out where the harness should live (a new folder, or an existing project), whether it's a **master** they'll copy per client/project or a single **project** harness, and which folders are reference-only. Ask if it isn't clear; never pick a location inside a reference folder.
2. Inventory what already exists there and in anything they point to: an existing `CLAUDE.md` or `AGENTS.md`, skills, a design-system file (Figma, tokens in code), research repositories, project templates. Note what each existing piece already does. You'll merge with it, not replace it: the scaffold never overwrites a file, and when something overlaps, the person picks which survives.
3. If a reference harness exists, read its docs on *why* it was built the way it was (decision logs are gold). Write down the lessons as principles in your own words.

### Phase 1: Interview (how they actually work)

Follow `references/interview.md`. The essentials:

- **Anchor on a real past project**, start to finish, and then one that went badly. People describe their ideal process when asked in the abstract; the harness has to fit the real one, including the messy parts (out-of-order feedback, mid-project re-scopes, the approval nobody logged).
- Ask **one question at a time**, with concrete options and your recommendation (use AskUserQuestion when available). Skip anything you can learn from files.
- **Four rounds, roughly:** context and people → walk the real project → rails (design system, confidentiality, standards) → checks and gates (who signs off, what reviewers keep catching).
- Write answers into a copy of `assets/harness.config.example.json` as you go (save it in your working folder, not in a reference folder). Every bad experience they mention goes into `known_failures`: each one will become a concrete fix.

If the person can't or won't do an interview ("just give me the scaffold"), fill the config from whatever you have (a brief, their description, a reference project), leave every unknown empty, and say plainly that the result is a scaffold with open questions, not a fitted harness.

### Phase 2: Show the harness map before generating files

This is information architecture before screens: the cheapest moment to correct the structure. Show one compact view (an artifact page or a table in chat, whichever the person will read):

- the pipeline: stage → owner → output → what "done" means;
- for each stage, its **guide** (what steers it beforehand: skill, rule, rail) and its **sensor** (what catches problems afterwards: check, gate criterion, record);
- the approval chain, and where approval ends and shipping starts;
- each known failure → the fix you'll build for it;
- what is deliberately left out, and why.

Get a yes or corrections. Corrections here are worth more than anything after generation. If nobody is there to answer (a scheduled or unattended run), save the map beside the config, say in one line that you proceeded without sign-off, and carry on.

### Phase 3: Generate

```bash
python3 <skill>/scripts/scaffold.py --config <config.json> --out <target> \
  --protect <each reference folder> [--dry-run]
```

The scaffold writes the full system, skips track-specific files the config doesn't need (no `system/` for research-only work, no reconciler unless several people work in parallel), keeps any existing file untouched (reported as `kept_existing`), and turns every empty config field into an `[[ASK]]` marker. A non-empty `unrendered_variables` list means a template bug: fix it before continuing. For files listed as kept, show the person how the generated version differs and let them choose; merge by hand.

If the target is on the person's computer and you only have a bridge, generate in your workspace, verify there, then copy the result across (and still never into a protected folder).

### Phase 4: Tailor (this is what makes it theirs)

The scaffold gives structure; this phase gives it their substance. Detail for each file: `references/components.md`.

1. **Stage method:** fill each stage section in `docs/process.md` from the interview walk-through: inputs, steps as they really ran, outputs, done-criteria. Replace its `[[ASK]]` markers wherever the interview answered them.
2. **Decisions:** one row in `docs/decisions.md` per rule you're encoding, with who decided and the basis (which interview answer, which project). A rule with no source can't be safely challenged later.
3. **Known failures → fixes.** For each `known_failures` entry, build the actual fix and name it in the failure register: a sensor (a function in `scripts/harness_check.py`), a gate criterion (`docs/gate-rubric.md`), a rule in `CLAUDE.md` or `ux-context.md`, or a new record field. "Remember to…" is not a fix. Check the built-in sensors first (`references/components.md` lists them) so you extend rather than duplicate. Plant each failure in a throwaway copy and confirm the sensor fires. Expect this to be the longest step: it is real engineering, and the part that makes the harness worth having.
4. **Stages without a skill:** if a stage is distinctive (a workshop, a mystery-shopping audit, a design-QA pass), write a small skill for it using the pattern in `references/components.md`. Keep each one short: steps, the files it writes, what done means.
5. **Tools:** adapt the skills to the person's real tools (Figma via MCP, Drive, Notion, a code repo) and list the connections each role needs in `docs/onboarding.md`. If a tool isn't connected in their setup, the skill should stop and say so, never fake the step.
6. **Confidentiality:** confirm what must never leak is listed. This project's own terms go in `.harness/confidential.txt` (committed, so every teammate's guard checks them). Terms that must not travel with the repo (other clients' names, the person's rates) go in `.harness/confidential.local.txt` (gitignored; it must be recreated on each machine, so say so in onboarding). An empty list is a gap to raise, not a default. Keep regex patterns narrow: a currency pattern in a fintech project would block every price in a prototype.
7. **Mould the evals.** Turn each known failure and each rule the person stressed into an eval case (`evals/cases.project.json`, see `references/components.md` §7), both sides for scope edges. This is what lets the harness prove, after every later change, that it still does what they asked.
8. **Clear seeds you filled; delete seed files for steps they don't use.** In a **master**, leave the per-project seeds in `context/` and `system/` in place: they are meant to be filled in each copy, and the checker and verifier know that. Keep `CLAUDE.md` under ~120 lines; move detail into `docs/`.

### Phase 5: Verify

1. `python3 <skill>/scripts/verify_harness.py <target>`: it checks every part, parses every record, runs the sensors, plants a throwaway confidential term to prove the guard blocks it, checks hook paths, builds the dashboard, and runs the harness's script evals. Fix every PROBLEM line before going further.
2. **Dry run:** walk one realistic brief (ideally the real reference project) through the generated harness's `intake` skill and the first stage, reading its `CLAUDE.md` as a fresh session would. Note anywhere the instructions were ambiguous or a file was missing, and fix the harness, not the run.
3. **Behaviour evals:** with the person's OK (they spend tokens), run `python3 evals/run.py --runs 1` in the target. Triage every failure before changing anything: is the case wrong, or the harness? Fix the harness when it's the harness; that's the point.
4. If git is available, run `git init` in the target and test that the pre-commit hook blocks a staged file containing a listed term (then remove the test file).
5. Report the maturity label verify prints (sketch, wireframe, prototype, production) honestly. A freshly generated harness is normally "prototype" at best: seeded files and open questions only fill through real use. Any sensor fail caps it at "wireframe".
6. Say what you could **not** test: live design-tool and notes connections, the evaluator running through `gate`, hooks behind a real trust prompt. Those are verified in the person's first real session.

### Phase 6: Hand over

Keep it short:
- what was built (the five parts, one line each) and where; point them to the dashboard's animated **How this harness works** section, which shows the pipeline and the check loop with live numbers;
- how to start: open the folder in Claude Code or the desktop app, accept the trust prompt (this lets the hooks run), say who you are;
- the open `[[ASK]]` questions, grouped by who can answer them;
- a time-boxed first week: run one real piece of work through it, run the evals before the first internal review, do the weekly 20-minute check on Friday, log every miss in the failure register (and give it an eval case);
- what this harness does not solve (state it plainly).

Publish the harness map as an artifact if they'll share it with their team.

## Fitting the context

| Context | Emphasise | Watch for |
|---|---|---|
| **Agency / studio** | Per-client rails, client gate, cross-team scope edges, out-of-order feedback, several people per repo (reconciler), confidentiality | Studio-wide design systems (wrong: each client has its own); approval logged nowhere |
| **Solo / freelance** | The evaluator (you review your own work), handovers to your future self, one master copied per client, other clients' names kept machine-local, upkeep time-boxed to an hour a week | Over-building: cut records before cutting checks; no reconciler for an occasional contractor |
| **In-house product** | Design system shared with engineering (code may be the source of truth), decisions that outlive projects, engineering handoff specs, post-launch evidence | A harness that duplicates the team's existing tracker; link to it instead |

Context rules land in the generated `CLAUDE.md` automatically from `references/contexts/`. Edit them there if a context needs a better default.

## Files in this skill

- `scripts/scaffold.py`: generates the harness from a config (never overwrites, honours `--protect`).
- `scripts/verify_harness.py`: tests a generated harness and scores each part.
- `assets/harness.config.example.json`: the config shape, filled with an example.
- `assets/harness-template/`: everything the scaffold writes (`.tmpl` files are filled from the config), including `evals/` (script tests, behaviour runner and cases, rubric, run log) and the `evals` skill.
- `references/principles.md`: why each part exists, with sources. Read before the first build.
- `references/interview.md`: the question bank and how answers map to files.
- `references/components.md`: how to tailor each generated file, write a stage skill, add a sensor or a record.
- `references/lessons.md`: failure modes found while building and running real harnesses, and the fix each needed.
- `references/contexts/*.rules.md`: per-context rules inserted into `CLAUDE.md`.
