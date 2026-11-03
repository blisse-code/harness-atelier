# Evals

Two kinds of test keep this skill honest. Deterministic evals run in CI on every push. Behavioural evals need a model and a person, and are run before each release and after any change to `SKILL.md` or `references/`.

## 1. Deterministic (automated)

`python3 evals/run_evals.py` generates a harness from each fixture in `evals/fixtures/`, then:

| Area | What is checked |
|---|---|
| Generation | Scaffold runs, no template variable left unrendered, `verify_harness.py` reports no PROBLEM lines and zero sensor fails on a fresh harness |
| Safety | Re-running never overwrites; writing inside a `--protect` path is refused |
| Sensors | Planted problems are caught by the right check: leaked term (fail), write guard (blocks), ship without final approval (fail), duplicate IDs (warn), renamed column (fail), off-scale spacing and off-system colour (warn), project rows in a master (warn) |
| Generated evals | Each generated harness has its eval kit (`evals/`, the `evals` skill), its script evals pass, its behaviour cases parse, the dashboard has the animated "How this harness works" section, and the script evals fail when the write guard is disabled |
| Repo hygiene | Exactly one `SKILL.md` in the package, description under 1024 characters, SKILL.md under 500 lines, visuals identical to their generator output, every SVG has title, description, reduced-motion support and no SMIL, marketplace paths exist |

| Fixture | Exercises |
|---|---|
| `agency-full` | Three-person team, both tracks, three-gate approval chain, committed and machine-local terms, standards, autonomy |
| `solo-master` | Solo master harness (seeds expected), two-gate chain, no reconciler despite a contractor |
| `inhouse-research` | Research-only, one person: no `system/`, no design skills, map pointers still valid |
| `minimal` | Almost nothing answered: everything missing becomes an `[[ASK]]`, nothing crashes |

Add a fixture whenever a real setup breaks the skill. The fixture is the regression test.

## 2. Behavioural (model + person)

Run each prompt in a fresh session with the skill installed, playing the person. Score each line pass or fail; a release needs every line to pass on all three prompts.

**Prompts**

1. Agency lead: *"I lead a small design team at an agency. Set up Claude so every project follows our process: brief, research, design, client sign-off."* Answer as a three-person studio with a reference repo you name as read-only.
2. Freelancer: *"I'm a freelance product designer, Claude keeps losing context and inventing spacing values, build me a harness."* Answer as solo, with one past failure involving lost client feedback.
3. In-house, impatient: *"Just give me the scaffold for our product design team, no interview."*

**Rubric**

| # | The skill… |
|---|---|
| B1 | Opens with one sentence saying what it will do, then starts (no plan waiting for approval) |
| B2 | Takes stock of existing files before asking anything it could have read |
| B3 | Asks about a **real** past project, and one that went badly, not "what's your process?" |
| B4 | Asks one question at a time, with options and a recommendation |
| B5 | Shows the harness map **before** generating any file, and waits (or says it proceeded unattended) |
| B6 | Passes every reference folder as `--protect`, and never writes into it |
| B7 | Turns each named failure into a concrete check, rubric line or rule, plant-tests sensors, and names the fixing file in the failure register |
| B8 | Leaves unknowns as `[[ASK]]` markers instead of inventing values |
| B9 | Runs `verify_harness.py` and reports its maturity label and what it could not test |
| B10 | Puts other clients' names in the machine-local terms file, never the committed one |
| B11 | Keeps chat short; detail is in files |
| B12 | For prompt 3: produces the scaffold, and says plainly that it is a scaffold with N open questions, not a fitted harness |
| B13 | Turns each known failure and each rule the person stressed into an eval case (both sides for scope edges), runs the script evals before hand-over, and asks before running token-spending behaviour evals |

Record each run as a dated row: prompt, model, B1 to B12, notes. A failure becomes a change to `SKILL.md` or `references/` and a new row, never a one-off prompt tweak.

| Date | Prompt | Model | Fails | Notes |
|---|---|---|---|---|

## 3. The generated harness's own behaviour evals

Each generated harness carries behaviour cases (`evals/cases.json`) run by `evals/run.py`: headless Claude sessions in a throwaway copy, restricted mode, the copy's own hooks loaded, a shell sandboxed to the copy, a spend cap. Before a release, scaffold the `agency-full` fixture and run them 3 times (`python3 evals/run.py --runs 3`); every case must pass 3 of 3. They found two template gaps when first run: intake deferred writing the brief when no one could answer (now writes `[[ASK]]` markers), and "we agreed X; I'm stopping" left no handover (the handover skill now triggers on it).

