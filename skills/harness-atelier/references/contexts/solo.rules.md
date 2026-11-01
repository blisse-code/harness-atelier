### Solo rules

- **One master, one copy per client.** Keep a master harness (`"role": "master"`) and start each client project from a fresh copy (`"role": "project"`) so briefs, rails and records never mix. Improvements found on a project go back into the master deliberately, logged in `docs/decisions.md`.
- **Other clients' names never travel.** Put them in `.harness/confidential.local.txt` (machine-only); the committed list holds only this project's own terms, so a pushed repo or hosted prototype can't reveal who else you work for.
- **You are every gate but the last.** Because you review your own work, the `evaluator` agent matters more here than anywhere: run `gate` before you send anything, and never skip it on "small" changes.
- **Time-box the harness itself.** Spend no more than about an hour a week on harness upkeep (the weekly check in `docs/evolution.md`). If upkeep grows past that, cut a record, not a check.
- **Your future self is the teammate.** Handovers are not optional: in two weeks you will remember the design, not the reasons.
