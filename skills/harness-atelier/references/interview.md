# Interview: getting the real process

The interview has one job: fill `harness.config.json` with how this designer or team *actually* works, plus the failures they want never to repeat. Everything generated rests on it.

## How to run it

- **Real before ideal.** Ask about a specific past project, never "what's your process?". People answer the abstract question with the process they wish they had. The harness has to survive the real one.
- **One question at a time**, biggest impact first. Give 2–4 concrete options and mark your recommendation; the person can always type their own. Use AskUserQuestion where available (up to 4 questions per call, but only batch questions that don't depend on each other).
- **Don't ask what you can read.** If a brief, a reference harness, a Figma file or a project folder answers something, read it and confirm in one line instead of asking.
- **Write answers into the config as they arrive.** Don't hold them in your head across turns.
- **Stop when answers stop changing the build.** Four rounds is typical; two can be enough for a solo designer. Unanswered fields stay empty and become `[[ASK]]` markers.
- **Listen for failures.** Every "that's where it went wrong" goes into `known_failures` verbatim. Each becomes a concrete fix in Phase 4.

## Round 1: context and people

| Ask | Why it matters | Config field |
|---|---|---|
| Agency/studio, solo/freelance, or in-house product? | Chooses the context rules and which parts get emphasis | `context` |
| Who works in it, and what does each role own? | Owners per stage, routing, whether the reconciler is needed | `team`, `roles` |
| Who owns the harness and approves rule changes? | Without an owner, rules drift and nobody can settle a dispute | `owner` |
| Which tools are in play (design file, shared drive, notes, git, hosting, tracker)? | Skills must use the real tools and stop when one isn't connected | `tools` |
| Research, design, or both? | Decides which files and skills exist | `tracks` |
| Is this a master you'll copy per client/project, or one project? | A master keeps per-project files seeded on purpose | `role` |

## Round 2: walk a real project

Opening: *"Pick one recent project that went reasonably well. Walk me from the first message about it to the moment you delivered. What happened first, then what?"*

Probe each step for:
- **Who did it**, and what came out (a file, a deck, a Figma page, a decision).
- **What "done" meant**, and who said so.
- **What came back**: feedback, its route, whether it arrived in order.
- **Handoffs**: to other teams, to engineering, to the client; who owned what was on the other side.
- **Re-scopes**: did the brief change mid-way, and how was it recorded?

Then: *"Now one that went badly. Where exactly did it go wrong?"* Ask for the concrete moment ("round-1 feedback arrived in round 3 and got lost"), not a lesson ("communication").

Fills: `stages` (id, name, owner, input, output, done_when, method), `approval_chain`, `deliverable_kinds`, `known_failures`.

If they have two reference projects (one research-only, one research plus design), walk both: the differences show which steps are standard and which were project-specific. Ask which is which rather than guessing.

## Round 3: rails

| Ask | Why | Config field |
|---|---|---|
| Where does the design system live: a design file, code, a base kit, nothing yet? | Source of truth for `system/`; tokens are mirrored, never invented | `design_system.source` |
| A new client or product with nothing to inherit, or an established one? | New: building the rails is the first deliverable. Established: iterate against them, and treat drift as a finding | `design_system.speed` |
| What must never leak (rates, other clients' names, unreleased product names)? | Seeds the guard and the commit hook. Split: this project's own terms are committed; anything that must not travel with the repo (other clients, your rates) stays machine-local. Let them type real terms into the files themselves if they prefer | `confidential_terms`, `confidential_terms_local` |
| Any non-negotiable standards: accessibility level, brand rules, regulatory constraints? | These become gate criteria | `standards` |

## Round 4: checks and gates

| Ask | Why | Config field |
|---|---|---|
| Who signs off, in what order? Can a later gate's feedback skip back? | The approval chain and the loop-back rule | `approval_chain` |
| What do reviewers catch again and again? | Each repeat becomes a gate criterion or a sensor | `known_failures`, then the rubric |
| How do you know a deliverable is ready to show? | Done-criteria per deliverable kind | `stages[].done_when` |
| How much autonomy do you want the AI to have: propose only, apply after per-item approval, or act and report? | Sets how skills like `feedback-to-changes` apply changes; lands in `CLAUDE.md` and decision D4 | `autonomy` |

## Answer → file map

| Answer | Lands in |
|---|---|
| Stages, owners, outputs, done-criteria | `CLAUDE.md` pipeline table, `docs/process.md`, `context/timeline.md` |
| How each stage really ran | `docs/process.md` stage sections |
| Approval chain | `CLAUDE.md`, `records/approvals.md`, ship-without-sign-off sensor |
| Known failures | `docs/evolution.md` register, plus the fix you build for each |
| Design system source and speed | `CLAUDE.md` rails, `system/*`, `system/system-log.md` |
| Confidential terms | `.harness/confidential.txt` (committed) and `.harness/confidential.local.txt` (machine-only); never `harness.config.json` |
| Standards, autonomy | `docs/gate-rubric.md`; `CLAUDE.md` and `docs/decisions.md` |
| Team and roles | `docs/onboarding.md`, routing in `next-steps` |
| Repeated reviewer catches, standards | `docs/gate-rubric.md` project-specific criteria |

## Quick mode (no interview possible)

Fill what you can from the materials given, leave the rest empty, generate, and say clearly: "This is a scaffold. N questions are open (listed); it becomes your harness once they're answered and one real project has run through it."
