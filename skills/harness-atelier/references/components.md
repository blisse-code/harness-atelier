# Components: tailoring what the scaffold generates

## Contents
1. Generated tree
2. Tailoring each file
3. Writing a stage skill
4. Adding a sensor
5. Adding a record
6. Hooks
7. Evals (the harness checking itself)
8. Keeping it small

## 1. Generated tree

```
<harness>/
├── CLAUDE.md                 map: pipeline, rails, memory, moves, checks, chain, hard lines (≤ ~120 lines)
├── AGENTS.md                 pointer for other agents
├── README.md                 the five parts, for people
├── harness.config.json       interview answers (no confidential terms)
├── docs/                     process.md · decisions.md · evolution.md · gate-rubric.md · onboarding.md
├── context/                  brief.md · scope.md · timeline.md · ux-context.md
├── system/                   tokens.md · components.md · patterns.md · system-log.md     (design track)
├── records/                  tasks · feedback · changes · approvals · ships · gate-log · insights (research) · past-work · handovers
├── work/                     research/ · design/ · prototypes/
├── dashboard/index.html      opens from disk; data.js is built by scripts/build_dashboard.py
├── scripts/                  records.py · harness_check.py · build_dashboard.py · install_git_hooks.sh
├── .harness/                 schema.json (record columns + status words) · confidential.txt
└── .claude/                  settings.json (hooks) · hooks/ · skills/ (8) · agents/ (evaluator, reconciler)
```

In the skill, the generated skills are stored as `SKILL.md.tmpl` so the skill package holds exactly one SKILL.md; the scaffold writes them out as `SKILL.md`. The reconciler is only generated for teams that work in parallel (not solo, unless `"parallel_work": true`). `.harness/confidential.local.txt` is gitignored.

## 2. Tailoring each file

| File | Tailor by | Don't |
|---|---|---|
| `CLAUDE.md` | Checking the stage table reads right; adding at most a few project-wide non-negotiables they named | Paste method detail in; move it to `docs/process.md` |
| `docs/process.md` | One section per stage, from the walk-through: steps as they actually ran, inputs, outputs, done | Write an idealised method nobody follows |
| `docs/decisions.md` | A row per encoded rule, with who decided and the basis | Leave rules without a source |
| `docs/evolution.md` | Filling the Fix column for each known failure with the actual file that fixes it | Write "be careful" as a fix |
| `docs/gate-rubric.md` | Adding project-specific criteria (their accessibility level, brand rules, repeated reviewer catches) | Remove the default criteria; mark them n/a with a reason instead |
| `context/ux-context.md` | Seeding with any known user constraints (from existing research), each with its source | Write narrative; write rules a generator can obey |
| `system/*` | Mirroring real values from the source (Figma variables via MCP, or the code tokens file) | Type values from screenshots or memory |
| Skills | Naming the real tools (e.g. "read the Figma frame with the Figma MCP"), the approval style they chose | Add steps the tool can't do in their setup |
| `.harness/confidential.txt` | Real terms; `CS:` for names that are also common words, `RE:` for patterns like currency figures | Put the terms anywhere else |

## 3. Writing a stage skill

Add one when a stage is distinctive and repeats: a co-creation workshop, a comparative audit, a design-QA pass, a usability test cycle. Keep it under ~40 lines.

```markdown
---
name: <verb-noun>
description: <what it does>. Use when <the phrases and moments people actually say>, or <the stage> starts.
---

# <Name>

<One or two sentences: why this stage exists and the mistake it prevents.>

1. **Read first:** <the files this stage starts from>.
2. <Step as it really runs, with the decision points.>
3. **Write** <the output files, same turn>.
4. **Done when** <the agreed criterion>. Then run `gate`.
```

Also add the stage to the Moves table in `CLAUDE.md` and to its section in `docs/process.md`.

## 4. Adding a sensor

A sensor belongs in `scripts/harness_check.py` when a miss can be detected without judgement: a missing field, a stale file, a value outside the system, a record pointing at nothing. The pattern:

```python
def check_<name>(data: dict) -> None:
    for row in data.get("<record>", {}).get("rows", []):
        if <condition>:
            add("<Check name>", "fail" | "warn", f"<file>: <what, with the row ID>", "<the fix, in one line>")
```

Call it from `main()` (inside the non-`--quick` branch if it's slow). Choose **fail** only when the problem should block review; a check that fails something the next review is meant to resolve (an unconfirmed brief, say) should warn until that review is approved. Then plant the problem in a scratch copy, run the check, and confirm it fires before you call the sensor done.

Built-in sensors: confidentiality, map size and dead pointers, record schema drift and duplicate IDs, unplanned feedback, blocked and overdue tasks, ship without final approval, insight evidence, handover missing or stale (date-based, works without git), work in a master, unfilled seeds, open questions, colour and spacing values off the system. Budget real time for the project-specific ones: in testing, turning a person's own failures into plant-tested sensors was the longest part of tailoring, and the most valuable.

## 5. Adding a record

1. Add its columns, ID column and status words to `.harness/schema.json` in this harness; that is all the checker and dashboard need. (If you maintain a writable copy of this skill and want every future harness to have the record, also add it to `build_schema()` in `scaffold.py`; never edit a read-only installed skill.)
2. Create the Markdown file with the exact header and a one-paragraph "what goes here".
3. Point to it from `CLAUDE.md` → Records.
4. If the dashboard should show it, add a section in `dashboard/index.html` (data is already in `HARNESS.records.<name>`).

## 6. Hooks

| Hook | Script | Does | Never |
|---|---|---|---|
| SessionStart | `session_start.py` (+ git hook install) | Prints the last handover, a quick sensor summary and open-question count into context | Fails the session; it swallows its own errors |
| PreToolUse (Write/Edit) | `confidential_guard.py` | Blocks a write containing a listed term (exit 2, reason shown) | Inspects files outside the write |
| Stop | `on_stop.py` | Rebuilds the dashboard; once per stop, asks for a handover if project files changed without one | Loops: it respects `stop_hook_active`; `"handover_nudge": false` in the config turns the nudge off |

Hooks run only after the person accepts the folder's trust prompt. Say so in the handover.

## 7. Evals (the harness checking itself)

The scaffold writes `evals/` and the `evals` skill. Tailor them in Phase 4:
- **Cases from the interview:** each `known_failures` entry and each rule the person stressed becomes a case in `evals/cases.project.json` (same shape as `evals/cases.json`: id `P-…`, rule, optional setup, prompt, code checks on the end state, optional yes/no judge question), plus a row in `evals/EVALS.md` section D. Prefer a code check (a file changed, a row added, a term absent) over a judge.
- **Both sides:** for a scope edge, one case where the request must stop and one where an in-scope request must go ahead.
- **Run once before hand-over:** `python3 -m unittest discover -s evals/tests -v` (free) and `python3 evals/run.py --runs 1` (tokens; ask first). Report failures honestly and triage them: eval wrong, harness wrong, or gate wrong.
- **Schedule and owner** go in `evals/README.md`; failures become tasks in `records/tasks.md`.

## 8. Keeping it small

- If a record hasn't been written to in a month of real use, ask whether to delete it.
- If two skills are always used together, merge them.
- `CLAUDE.md` over ~120 lines: move detail out. The sensor warns at 150.
- Each new part needs a named failure it prevents. "Might be useful" is not enough.
