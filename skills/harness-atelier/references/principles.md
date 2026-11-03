# Principles: why each part exists

Each principle says what to do, why, and where this skill puts it into practice. Source tags are at the end of each line and listed at the bottom. Where sources disagree, the disagreement is noted rather than smoothed over.

## Contents
1. What a harness is for
2. Memory and context
3. Rails
4. Moves: workflow, skills, agents, hooks
5. Checks
6. Loop
7. Fitting it to designers
8. Anti-patterns

## 1. What a harness is for

1. **The harness is the lever you control.** The same model can score very differently depending on what surrounds it, because the harness decides what context arrives at each step. Spend effort here before switching models. *[MER, LC, ANT, VO]*
2. **Build narrow, for a recurring workflow.** A custom harness pays off when the same work repeats with the same context, tools and outputs, and mixes fixed steps with judgement. A design studio's brief → research → design → delivery pipeline is exactly that. *[VO, LC]*
3. **A harness directs power; it doesn't take it away.** Frame rails as what lets people move fast safely, so a team doesn't experience them as bureaucracy. *[DH, KG]*
4. **Judge the whole experience, not one screen.** Models already produce a tidy single screen. What breaks is coherence across a flow and across sessions. The harness exists for the flow. *[DH, KG]*
5. **Every part is a bet about what the model can't do alone.** Those bets go stale as models improve. Re-test by removing one part at a time on a small task; keep what carries weight. → `docs/evolution.md`, "When the model changes". *[ANT, MER]*

## 2. Memory and context

6. **The instruction file is a map, not an encyclopedia.** A huge `CLAUDE.md` crowds out the task, rots, and stops being read. Keep it near 100 lines of pointers and non-negotiables; put method in `docs/`. → map size sensor. *[Lopopolo/OpenAI via AH, VER]*
7. **Load knowledge progressively.** One-line skill descriptions are always visible; the full skill loads only when relevant. Write descriptions as routing rules: when to use, when not, with the alternative named. *[VER, LC]*
8. **Stable first, volatile last.** Brief, rules and decisions are the stable spine; today's task goes on top. A stable spine also makes caching work. Changing the spine should be a deliberate act. *[MER, PFD]*
9. **State lives in files, not sessions.** Handover entries, decisions, records and logs outlive any session and any person's memory. Read the newest handover first and mirror it back. → `handover` skill, SessionStart hook. *[MER, ANT, PFD, AH]*
10. **Govern what gets written.** Memory the agent writes can mislead its future self. Keep records append-mostly, dated and attributed; mark superseded decisions instead of deleting them. *[MER, RAM]*
11. **Sketching vs Committed.** Keep tentative options visibly separate from decisions, so a sketch never hardens into a constraint by accident. *[PFD]*
12. **Adjustment vs reframe.** Executing differently against the same problem is fine; changing the problem or breaking a Committed decision means stop and let a person choose. *[PFD]*
13. **Re-explaining context is a harness bug.** If someone keeps telling the AI the same thing, that thing belongs in a file. *[PFD]*

## 3. Rails

14. **Make the design system readable by agents.** Tokens, components with states, and patterns in a form the AI can look up, mirrored from the real source of truth and never invented. → `system/`. *[KG, DH, RAM]*
15. **Encode intent, not just usage.** Each component says what it must never become, and each pattern records its intentional exceptions with reasons, so the AI doesn't "tidy up" a deliberate choice. → `system/components.md`, `patterns.md`. *[DH, SK, AH]*
16. **Research becomes constraints.** A finding steers generation only if it's written where the AI reads before generating, as a rule ("users abandon X when Y"), with its source. → `context/ux-context.md`. *[NN/g via AH]*
17. **Enforce rules in code, not prose.** Anything that must hold every time (confidentiality, blocked actions) goes in a hook or a check, because written rules fail the first time someone is in a hurry. → `confidential_guard.py`, pre-commit hook. *[MER, LC, VO, VER, AH]*
18. **Tier risk.** Read-only, reversible and destructive actions need different treatment. Evaluators and reconcilers are read-only by design. *[MER, VO, VER]*

## 4. Moves: workflow, skills, agents, hooks

19. **Model before structure, structure before screens.** Mental model and intent paths → IA → flows → screens. *[user practice, HCI]*
20. **Agree "done" before starting.** Write what will be checked and how before work begins; the gate then checks against that. *[ANT sprint contracts, VO, VER]*
21. **Small batches through the gate.** One flow or one research question at a time; large batches hide fails. *[ANT, VER]*
22. **Delegate only work with a clean handoff shape.** Subagents get a clear brief and return the answer, not the journey; decisions stay with the main session. *[VER, MER, LC]*
23. **Hooks put policy outside the model.** Session start (mirror state, run sensors), before writes (guard), at stop (rebuild dashboard, nudge a handover). *[MER, LC]*
24. **Interview sparingly, and only for what changes the plan.** A few questions, ranked by impact, one at a time, with options and a recommendation. *[PFD, DIY]*
25. **Look before building; combine, don't rebuild.** Inventory what exists, map it onto harness roles, and let the person choose when two pieces overlap. Never build a parallel system next to a working one. *[DIY, RAM]*

## 5. Checks

26. **Guides and sensors, both.** Guides steer before the work; sensors notice after. Guides alone never learn whether they worked; sensors alone keep catching the same mistake. *[Böckeler via AH]*
27. **Cheap and deterministic first, judgement second.** Grep-able problems (placeholders, schema drift, stray hex values, leaks) are caught by script before an evaluator spends judgement. Then visual and agent critique, then people. The aim is fewer problems reaching people, not thinner human review. *[KG, SK, Böckeler via AH]*
28. **Separate the maker from the judge.** Self-evaluation is lenient. A separate evaluator, briefed with a rubric and told to be skeptical, finds what the maker won't. Watch for the evaluator finding a real problem and then talking itself into approving. *[ANT]*
29. **Evidence, not confidence.** Every finding names its check, cites the element or file, and carries a severity. Fail is the default; only the owner waives it, in writing. *[SK design-lint, AH]*
30. **Weight taste explicitly.** Coherence and distinctiveness deserve as much weight as craft, because models deliver tidy craft by default. Output that would still work with a competitor's name swapped in is generic. *[ANT, DH]*
31. **Scoped, honest claims.** Say exactly what ran and what couldn't be checked. Never "all good" without a run behind it. *[VER, VO]*
32a. **Check the harness too, not just the work.** The gate checks a deliverable; evals check that the harness itself still behaves: its scripts give the right result, Claude follows its rules every time (several runs, not one), and the gate catches planted problems without inventing new ones. Start from real misses; grade the end state in the files, never what Claude says it did; run in a throwaway copy with no connectors. Every failure is triaged: is the eval wrong, the harness wrong, or the gate wrong? *[ANT evals guidance, AH]*
32. **Approval and shipping are different events.** A round can be approved and never shipped; record both. *[RAM, AH]*

## 6. Loop

33. **Every miss becomes a permanent fix.** A recurring comment becomes a rule, a recurring one-off UI a component, a recurring flag a sensor, and past failures go into context. → failure register. *[KG, DH, Hashimoto via AH]*
34. **Every rule has a source.** Who decided, when, on what basis. Without it nobody can safely change the rule later. → `docs/decisions.md`. *[AH]*
35. **Small, time-boxed rituals.** A weekly 20-minute check and a monthly review of Committed decisions; if the brief fails twice in a row, rewrite it rather than patching again. *[PFD, DIY]*
36. **Evaluate the harness itself.** Fixture projects and a short behaviour rubric catch regressions when the harness changes. A single instruction file plus many skills degrades without this. *[DIY, MD]*

## 7. Fitting it to designers

- Run outputs should be reviewable team artefacts (brief, insights, gate log, dashboard), not chat logs. *[VO, RAM]*
- No-code or Figma-first teams get checklists and records rather than fake code folders; the scripts still run, but nothing assumes a build pipeline. *[DIY]*
- Agency work is a gap in most sources: per-client rails, a client approval gate, cross-team scope edges and out-of-order feedback come from the studio harness studied for this skill. *[AH]*

## 8. Anti-patterns

- A tool zoo: dozens of narrow tools or skills nobody can route between. *[MER, MD]*
- An infinite context buffet: everything loaded every session. *[MER]*
- Permissions that rely on trusting the model. *[MER, VO]*
- Building before auditing; rebuilding an organised project; parallel systems. *[DIY]*
- Humans as the only quality gate, or faster output without a faster loop. *[KG]*
- Waiting for perfect documentation before starting; grow it from where agents deviate. *[KG]*
- Failures nobody records. *[KG]*
- Long chat reports instead of files. *[DIY, RAM]*

## Sources

- **[MER]** Alex Merced, "Designing your own AI harness" (dev.to).
- **[VO]** Claire Vo, *How I AI*: "What is an AI harness? I build one live". No transcript was available, so this is based on the show notes and the companion write-up only.
- **[ANT]** Anthropic, "Harness design for long-running application development".
- **[RAM]** Madhuri Maram, "Harness" (madhurimaram.com/harness).
- **[LC]** LangChain, "How to build a custom agent harness". Vendor post.
- **[VER]** Vercel Academy, "Build your own AI agent harness". Partly read (10 of 38 lessons). Vendor course.
- **[DH]** design-harness.com: the four-layer design harness model.
- **[KG]** Kogiso, "What is a Design Harness?" (note.com, in Japanese).
- **[DIY]** iruhdam1/skills, `diy-harness` skill. MIT.
- **[PFD]** iruhdam1/prefix-first-design. MIT.
- **[SK]** iruhdam1/skills pack (`design-lint`, `bake-the-brief` and others). MIT.
- **[MD]** Gao Dalie, "How to build Harness 2.0" (Medium). Members-only, so only the introduction was read.
- **[AH]** A studio's own agency harness, built and run on live projects and studied read-only. Its decision log cites Lopopolo/OpenAI and Böckeler/Thoughtworks on harness engineering, NN/g on UX context, and Hashimoto's "engineer the harness" practice.

Ideas are paraphrased throughout. No source's files or wording were copied into this skill or into the harnesses it generates.
