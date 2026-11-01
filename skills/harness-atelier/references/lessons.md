# Lessons: what broke in real harnesses, and the fix each needed

These come from studying (read-only) how a studio harness was built and changed over two months of live projects. Each one cost a real incident or a wasted day. The scaffold already builds in the fixes. They're here so you recognise the same failure when tailoring a harness, or when someone asks "why is it built like this?".

## Rules and enforcement

- **A written rule failed the first time it mattered.** "Never name the client" sat in the instruction file and a client name still reached a published release note. *Fix:* enforcement in code, at two points: write time (guard hook) and commit time (git hook). Write a rule in prose only when it can't be checked.
- **The term list itself was the leak, then it wasn't, then it could be again.** Keeping confidential terms out of git meant they never reached a teammate's machine, so their hooks checked nothing. *Fix:* commit the project's own terms (the project already names its own client), but keep terms that must not travel with this repo (other clients' names, rates) in a gitignored local file that the guard reads too. A freelancer's committed list naming their other clients would itself be the leak, especially once prototypes are hosted. Checks exclude both term files from their own scan, or the commit that adds a term blocks itself.
- **A short term matched inside unrelated words.** A two-letter abbreviation blocked commits on filenames. *Fix:* whole-word matching by default, a case-sensitive prefix for names that are also ordinary words, and a regex form for patterns like currency figures.
- **A derived file re-triggered its own alarm.** Anything built from the records (dashboard data) contains whatever the records contain. *Fix:* scan sources, not build products.

## Checks that silently checked nothing

- **An exact-string match missed the common variant.** The placeholder check matched one spelling of the marker and skipped most real placeholders for weeks. *Fix:* match the marker's prefix, and test every check by planting the problem it should catch.
- **Root-level files were outside the checked folders.** *Fix:* define the scan by file type across the whole tree, with explicit skips, rather than an include-list of folders.
- **Rows appended under a table were invisible.** Rows added with a shell append landed after the table and parsers ignored them. *Fix:* read every row with the right cell count anywhere after the header, and flag it.
- **A renamed column blinded the dashboard without an error.** *Fix:* one schema file defines every record's columns and status words; the checker reports drift as a fail.

## Memory and continuity

- **Sessions started cold and re-decided settled things.** *Fix:* a handover entry at the end of each substantive session, read and mirrored back at the start of the next; a contradiction with a Committed decision is raised, never silently followed.
- **Juniors didn't create files a README told them to create.** *Fix:* pre-seed every expected file with a marker that says when it's used and who fills it, plus a standing rule to fill or delete seeds, plus a sensor that lists what's still seeded.
- **A stale cached copy was trusted over the live source.** A sync reported "no changes" an hour after the source was restructured. *Fix:* fetch live, then use the cache only as a hand-off file. Store timestamps in UTC and show local time.
- **A test run found the skill's own headline problem unguarded.** Invented spacing values were the motivating pain, but only colours were checked. *Fix:* a spacing sensor that reads the scale from `system/tokens.md`. Lesson: every pain named in the interview needs a named sensor, including the obvious ones.
- **Parallel sessions took the same new IDs.** *Fix:* pull right before allocating an ID; on a clash, renumber your own rows and every reference to them; a sensor flags duplicate IDs.

## Structure

- **The instruction file grew into an encyclopedia.** At about twice the target length it was crowding out the task. *Fix:* split into a short map plus `docs/`, keeping every section name so existing pointers still resolved; a sensor warns on size and on dead pointers.
- **One design system for the whole studio was wrong.** Each client has its own. *Fix:* rails are per project, with a bootstrap order (previous project for this client → client's system → base kit → fresh) logged each time.
- **Approval and shipping were conflated.** Approved work sat unshipped and nobody could tell. *Fix:* separate records, and a sensor that fails a ship row with no final-gate approval.
- **Feedback arrived out of order.** Client comments on round 1 landed while the team was on round 4. *Fix:* map old feedback onto the current version as individually approvable changes; never revert later rounds wholesale.
- **Out-of-scope work had no owner.** *Fix:* scope records not just what's out, but who owns it and what happens at the handoff.

## Honesty

- **"Planned" infrastructure sat unbuilt for a day while being described as if it existed.** *Fix:* only describe what has been run; label everything else as not built.
- **A check was substituted with a human step and the gap went unmentioned.** *Fix:* when a capability is deferred, say so in the decisions log with what would activate it.
- **Some limits are permanent.** Hooks can't run before a person trusts the folder; a sync script can't force a team's daily habit. State these plainly in the handover rather than implying the harness covers them.
