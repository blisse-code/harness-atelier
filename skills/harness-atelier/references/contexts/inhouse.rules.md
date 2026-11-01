### In-house rules

- **The design system is shared with engineering.** If tokens live in code, the code is the source of truth and `system/tokens.md` mirrors it; never let the two disagree silently. A mismatch is a sensor finding. <!-- design -->
- **Decisions outlive projects.** One product means `docs/decisions.md` and `context/ux-context.md` keep growing across features; date every entry and mark superseded ones instead of deleting them.
- **Handoff is to engineers, not a client.** `handoff` produces a spec (states, edge cases, tokens, acceptance criteria) and links the ticket. The final gate is usually the PM or product trio, not leadership.
- **Measure after launch.** Each shipped feature names the metric or signal that would show it worked, so the learning loop has real evidence, not opinions.
