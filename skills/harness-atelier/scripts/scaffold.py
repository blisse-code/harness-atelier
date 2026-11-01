#!/usr/bin/env python3
"""Generate a designer's harness from a filled harness.config.json.

    python3 scaffold.py --config harness.config.json --out ./my-harness \
        [--protect /path/that/must/never/be/written] [--dry-run]

What it guarantees, because these are the mistakes worth never making:
  * It never overwrites a file that already exists. Existing files are listed
    as "kept"; the skill then merges by hand, with the designer choosing.
  * It refuses to write inside any --protect path (reference repos, the
    designer's originals) and inside the skill's own folder.
  * Anything the config leaves empty becomes a visible [[ASK: ...]] marker in
    the generated files, never a guessed value.
  * It writes .harness/schema.json, the one place that defines every record's
    columns and status words, so the checker and dashboard can't drift apart.

Standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE = SKILL_DIR / "assets" / "harness-template"

CONTEXT_LABEL = {
    "agency": "Agency / studio (many clients, a team, a client approval gate)",
    "solo": "Solo / freelance (one person, several clients)",
    "inhouse": "In-house product team (one product, PMs and engineers)",
}

SPEED_GUIDANCE = {
    "new": ("New system. Building the rails (system/tokens.md, system/components.md, "
            "context/ux-context.md) is the first deliverable, so the timeline shows it. Do not rush to "
            "screens before the rails exist."),
    "returning": ("Established system. Do not rebuild the rails: iterate against them. Any departure "
                  "from system/ is a Gate finding, not a fresh debate."),
}


def ask(what: str) -> str:
    return f"[[ASK: {what}]]"


def md_table(header: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(out)


def build_schema(tracks: list[str]) -> dict:
    recs = {
        "tasks": {"path": "records/tasks.md", "id_column": "ID",
                  "columns": ["ID", "Task", "Owner", "Stage", "Status", "Due", "Source"],
                  "status_column": "Status", "statuses": ["todo", "doing", "blocked", "done"]},
        "feedback": {"path": "records/feedback.md", "id_column": "ID",
                     "columns": ["ID", "Date", "From", "Feedback", "Applies to", "Status", "Resolution"],
                     "status_column": "Status", "statuses": ["open", "planned", "resolved", "declined"]},
        "changes": {"path": "records/changes.md", "id_column": "ID",
                    "columns": ["ID", "Date", "Requested by", "Change", "Scope impact", "Decision", "Decided by"],
                    "status_column": "Decision", "statuses": ["pending", "accepted", "rejected"]},
        "approvals": {"path": "records/approvals.md", "id_column": None,
                      "columns": ["Round", "Date", "Deliverable", "Gate", "Reviewer", "Verdict", "Notes"],
                      "status_column": "Verdict", "statuses": ["approved", "changes requested", "pending"]},
        "ships": {"path": "records/ships.md", "id_column": None,
                  "columns": ["Date", "Deliverable", "Version", "Shipped to", "Link", "Approval round"]},
        "gates": {"path": "records/gate-log.md", "id_column": None,
                  "columns": ["Date", "Deliverable", "Sensors", "Evaluator", "Fails", "Warns", "Verdict"],
                  "status_column": "Verdict", "statuses": ["ready", "not ready", "waived"]},
        "timeline": {"path": "context/timeline.md", "id_column": None,
                     "columns": ["Stage", "Start", "End", "Owner", "Status"],
                     "status_column": "Status", "statuses": ["not started", "in progress", "at risk", "done"]},
    }
    if "research" in tracks:
        recs["insights"] = {"path": "records/insights.md", "id_column": "ID",
                            "columns": ["ID", "Insight", "Evidence", "Confidence", "In ux-context"],
                            "status_column": "Confidence", "statuses": ["high", "medium", "low"]}
    return {"version": 1, "records": recs}


def variables(cfg: dict) -> dict:
    tracks = cfg.get("tracks") or []
    team = cfg.get("team") or []
    roles = cfg.get("roles") or {}
    stages = cfg.get("stages") or []
    chain = cfg.get("approval_chain") or []
    tools = cfg.get("tools") or {}
    ds = cfg.get("design_system") or {}
    failures = cfg.get("known_failures") or []
    ctx = cfg.get("context") or ""

    later = "_open: see docs/process.md_"  # the question is asked once, in process.md, not in every copy
    stage_rows = [[str(i + 1), s.get("name") or later, s.get("owner") or later,
                   s.get("output") or later, s.get("done_when") or later]
                  for i, s in enumerate(stages)]
    timeline_rows = [[s.get("name", "?"), "", "", s.get("owner", ""), "not started"] for s in stages]
    if "design" in tracks and (ds.get("speed") or "new") == "new":
        timeline_rows.insert(0, ["Rails: tokens, components, ux-context", "", "", (team[0].get("name") if team else ""),
                                 "not started"])
    skill_for = {"intake": "intake", "brief": "intake", "handoff": "handoff", "deliver": "handoff",
                 "synth": "synthesise", "feedback": "feedback-to-changes"}
    sections = []
    for i, s in enumerate(stages):
        sid = (s.get("id") or "").lower()
        skill = next((f"`{sk}`" for key, sk in skill_for.items() if key in sid),
                     "none dedicated yet (write one if this stage repeats); run `gate` before review")
        sections.append(
            f"### {i + 1}. {s.get('name') or ask('stage name')}\n\n"
            f"- **Owner:** {s.get('owner') or ask('owner')}\n"
            f"- **Takes in:** {s.get('input') or ask('what this stage starts from')}\n"
            f"- **Writes to:** {s.get('output') or ask('output file')}\n"
            f"- **Done when:** {s.get('done_when') or ask('what done means')}\n"
            f"- **Skill:** {skill}\n"
            f"- **How it actually runs:** {s.get('method') or ask('how this stage ran on the real reference project, step by step')}\n")
    design = "design" in tracks
    rails = []
    if design:
        rails.append("- **Design system:** `system/tokens.md`, `system/components.md`, `system/patterns.md`. Use what is "
                     "registered; never invent a value or a one-off component. A new value goes through the `system-update` "
                     f"skill after it is approved. Source of truth: {ds.get('source') or ask('where the design system lives')}.")
    rails.append("- **Users and context:** `context/ux-context.md`. Read it before generating any flow, screen, copy or "
                 "recommendation. Research findings live there as constraints (\"users abandon X when Y\"), not as narrative.")
    rails.append("- **Confidentiality:** `.harness/confidential.txt`. A hook blocks writes containing a listed term; a git "
                 "hook blocks commits. Never work around either. If a term is wrong, the owner edits the list.")
    if design:
        rails.append("- **System speed:** " + SPEED_GUIDANCE.get(ds.get("speed") or "new"))
    moves = [("A new brief, request or project arrives", "`intake`"),
             ("Feedback arrives (meeting, email, comments)", "`feedback-to-changes`"),
             ("Work is ready for someone to review", "`gate` (runs the sensors, then the `evaluator` agent)")]
    if design:
        moves.append(("A component or token is approved", "`system-update`"))
    if "research" in tracks:
        moves.append(("Research data needs turning into insights", "`synthesise`"))
    moves += [("\"What should I do next?\" / after any review round", "`next-steps`"),
              ("A deliverable leaves the building", "`handoff`"),
              ("The session is ending after real work", "`handover`")]
    if parallel_team(cfg):
        moves.append(("Several people worked in parallel (after a pull)", "`reconciler` agent: reports gaps, fixes nothing"))
    v = {
        "RAILS": "\n".join(rails),
        "MOVES_TABLE": md_table(["When", "Use"], [list(m) for m in moves]),
        "STAGE_SECTIONS": "\n".join(sections) or ask("stage-by-stage method"),
        "TOOLS_LIST_INLINE": ", ".join(k for k, val in tools.items() if val) or ask("tools in use"),
        "HARNESS_NAME": cfg.get("harness_name") or "Design Harness",
        "OWNER": cfg.get("owner") or ask("who owns this harness and approves rule changes"),
        "CREATED": cfg.get("created") or "",
        "CONTEXT": ctx,
        "CONTEXT_LABEL": CONTEXT_LABEL.get(ctx, ask("working context: agency, solo or in-house")),
        "TRACKS": ", ".join(tracks) if tracks else ask("tracks: research, design or both"),
        "PIPELINE_LINE": " → ".join(s.get("name", "?") for s in stages) if stages else ask("the real stages, in order"),
        "STAGES_TABLE": md_table(["#", "Stage", "Owner", "Writes to", "Done when"], stage_rows)
        if stage_rows else ask("walk through one real past project to get the stages"),
        "TIMELINE_ROWS": "\n".join("| " + " | ".join(r) + " |" for r in timeline_rows),
        "TEAM_TABLE": md_table(["Name", "Role", "Owns"],
                               [[t.get("name", "?"), t.get("role", "?"), roles.get(t.get("role", ""), ask("what this role owns"))]
                                for t in team]) if team else ask("who is on the team and what each role owns"),
        "APPROVAL_CHAIN": " → ".join(chain) if chain else ask("who signs off, in what order"),
        "FINAL_GATE": chain[-1] if chain else ask("final approver"),
        "TOOLS_LIST": "\n".join(f"- {k}: {'yes' if v is True else v}" for k, v in tools.items() if v) or ask("tools in use"),
        "DS_SOURCE": ds.get("source") or ask("where the design system lives: figma, code or none yet"),
        "DS_SPEED": ds.get("speed") or "new",
        "DS_SPEED_GUIDANCE": SPEED_GUIDANCE.get(ds.get("speed") or "new"),
        "DELIVERABLES": ", ".join(cfg.get("deliverable_kinds") or []) or ask("deliverable types"),
        "FAILURE_ROWS": "\n".join(f"| F{i + 1} | {f} | {ask('guide, sensor or record that prevents it')} | open |"
                                  for i, f in enumerate(failures)),
        "CONTEXT_RULES": context_rules(ctx, design),
        "AUTONOMY": {"propose": "Propose only: the AI drafts, a person applies.",
                     "per-item": "Apply after per-item approval: each proposed change is approved individually.",
                     "act-and-report": "Act and report: the AI applies routine changes and reports them; anything that "
                                       "touches scope, a Committed decision or a client-facing file still needs approval."
                     }.get(cfg.get("autonomy") or "", ask("how much the AI may apply on its own: propose, per-item or act-and-report")),
        "STANDARDS_ROWS": "\n".join(f"| {s} | Output breaches it | The element and the standard's clause |"
                                     for s in (cfg.get("standards") or [])) or
                          "| " + ask("non-negotiable standards: accessibility level, brand rules, regulation") + " | | |",
        "ROLE": "master" if cfg.get("role") == "master" else "project",
        "ROLE_LINE": ("**This is a master harness.** Don't do client work here: start each project from a fresh copy. "
                      "Seed files are meant to stay seeded in the master." if cfg.get("role") == "master"
                      else "This is a project harness: one client or product."),
    }
    return v


def context_rules(ctx: str, design: bool) -> str:
    """Context-specific rules; lines tagged <!-- design --> only appear when there is a design track."""
    path = SKILL_DIR / "references" / "contexts" / f"{ctx}.rules.md"
    if not path.exists():
        return ask("context-specific rules (agency, solo or in-house)")
    keep = []
    for line in path.read_text(encoding="utf-8").strip().splitlines():
        if line.rstrip().endswith("<!-- design -->"):
            if not design:
                continue
            line = line.rstrip()[: -len("<!-- design -->")].rstrip()
        keep.append(line)
    return "\n".join(keep)


def parallel_team(cfg: dict) -> bool:
    """Several people working in the same repo at the same time. Solo setups with an occasional
    contractor don't qualify unless the config says so with "parallel_work": true."""
    if "parallel_work" in cfg:
        return bool(cfg["parallel_work"])
    return len(cfg.get("team") or []) > 1 and cfg.get("context") != "solo"


def include(rel: str, cfg: dict) -> bool:
    tracks = cfg.get("tracks") or []
    team = cfg.get("team") or []
    if rel.startswith(("work/research/", "records/insights.md", ".claude/skills/synthesise/")):
        return "research" in tracks
    if rel.startswith(("work/design/", "work/prototypes/", "system/", ".claude/skills/system-update/")):
        return "design" in tracks
    if rel.startswith(".claude/agents/reconciler.md"):
        return parallel_team(cfg)
    return True


def render(text: str, v: dict) -> str:
    def sub(m):
        key = m.group(1)
        return str(v[key]) if key in v and v[key] is not None else m.group(0)
    return re.sub(r"\{\{([A-Z_]+)\}\}", sub, text)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--protect", action="append", default=[])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    cfg = json.loads(Path(a.config).read_text(encoding="utf-8"))
    out = Path(a.out).expanduser().resolve()
    for p in a.protect + [str(SKILL_DIR)]:
        pr = Path(p).expanduser().resolve()
        if out == pr or pr in out.parents:
            print(f"Refusing: {out} is inside protected path {pr}.", file=sys.stderr)
            return 2

    v = variables(cfg)
    written, kept, skipped = [], [], []
    for src in sorted(TEMPLATE.rglob("*")):
        if src.is_dir() or "__pycache__" in src.parts:
            continue
        rel = str(src.relative_to(TEMPLATE))
        if rel.endswith(".tmpl"):
            rel = rel[:-5]
        if not include(rel, cfg):
            skipped.append(rel)
            continue
        dst = out / rel
        if dst.exists():
            kept.append(rel)
            continue
        written.append(rel)
        if a.dry_run:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.name.endswith(".tmpl"):
            dst.write_text(render(src.read_text(encoding="utf-8"), v), encoding="utf-8")
        else:
            shutil.copy2(src, dst)

    generated = {
        ".harness/schema.json": json.dumps(build_schema(cfg.get("tracks") or []), indent=2) + "\n",
        "harness.config.json": json.dumps({k: val for k, val in cfg.items()
                                           if k not in ("confidential_terms", "confidential_terms_local")}, indent=2) + "\n",
        ".harness/confidential.txt": (
            "# Terms that must never appear in this harness's files. One per line, matched as whole words,\n"
            "# case-insensitive. CS:Term = case-sensitive (names that are also ordinary words).\n"
            "# RE:regex = a pattern, e.g. RE:\\bPROJ-[A-Z]{3}\\b for internal codenames. Keep patterns narrow:\n"
            "# a currency pattern in a fintech project would block every price in a prototype.\n"
            "# This file is committed so every teammate's guard checks the same list. Put terms that must not\n"
            "# travel with this repo (OTHER clients' names, your own rates) in .harness/confidential.local.txt,\n"
            "# which is gitignored and read the same way, and recreate it on each machine.\n"
            + "".join(t + "\n" for t in (cfg.get("confidential_terms") or []))),
        ".harness/confidential.local.txt": (
            "# Machine-local terms (gitignored): other clients' names, your own rates. Same syntax as confidential.txt.\n"
            + "".join(t + "\n" for t in (cfg.get("confidential_terms_local") or []))),
    }
    for rel, text in generated.items():
        dst = out / rel
        if dst.exists():
            kept.append(rel)
            continue
        written.append(rel)
        if not a.dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(text, encoding="utf-8")

    if not a.dry_run:
        for p in list((out / "scripts").glob("*")) + list((out / ".claude" / "hooks").glob("*")):
            if p.suffix in {".py", ".sh"}:
                p.chmod(0o755)

    leftover = []
    if not a.dry_run:
        for rel in written:
            p = out / rel
            if p.suffix in {".md", ".json", ".html"}:
                leftover += [f"{rel}: {m}" for m in re.findall(r"\{\{[A-Z_]+\}\}", p.read_text(encoding="utf-8"))]
    print(json.dumps({"out": str(out), "written": len(written), "kept_existing": kept,
                      "skipped_by_config": skipped, "unrendered_variables": leftover,
                      "dry_run": a.dry_run}, indent=2))
    return 1 if leftover else 0


if __name__ == "__main__":
    sys.exit(main())
