#!/usr/bin/env python3
"""Verify a generated harness actually works before calling it done.

    python3 verify_harness.py /path/to/harness

Runs real tests, not a file listing:
  1. Every part (Rails, Memory, Moves, Checks, Loop) has its files.
  2. Every record parses against .harness/schema.json.
  3. The sensors run and return a verdict.
  4. The write-time guard blocks a planted confidential term (uses a throwaway
     term, never one of the real ones, and changes nothing on disk).
  5. Hooks in .claude/settings.json point at files that exist.
  6. The dashboard builds.
Then prints a scorecard per part (working / thin / absent) and a maturity
label (sketch, wireframe, prototype, production), with the evidence for each.

It never writes into the harness except dashboard/data.js (a build product).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

PARTS = {
    "Rails": ["system/tokens.md", "system/components.md", "context/ux-context.md", ".harness/confidential.txt",
              ".claude/hooks/confidential_guard.py"],
    "Memory": ["CLAUDE.md", "context/brief.md", "context/scope.md", "context/timeline.md", "docs/decisions.md",
               "records/handovers.md"],
    "Moves": [".claude/settings.json", ".claude/skills/intake/SKILL.md", ".claude/skills/gate/SKILL.md",
              ".claude/skills/handover/SKILL.md", ".claude/skills/next-steps/SKILL.md", ".claude/agents/evaluator.md"],
    "Checks": ["scripts/harness_check.py", "scripts/records.py", ".harness/schema.json", "docs/gate-rubric.md",
               "records/gate-log.md"],
    "Loop": ["docs/evolution.md", "docs/decisions.md", "records/past-work.md"],
}
SEED = re.compile(r"<!--\s*status:\s*seed", re.I)
ASK = re.compile(r"\[\[ASK:")


def run(cmd, cwd, stdin=None):
    p = subprocess.run(cmd, cwd=cwd, input=stdin, capture_output=True, text=True, timeout=90)
    return p.returncode, p.stdout + p.stderr


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    root = Path(sys.argv[1]).resolve()
    results, problems = {}, []

    try:
        cfg = json.loads((root / "harness.config.json").read_text(encoding="utf-8"))
    except Exception:
        cfg = {}
    tracks = cfg.get("tracks") or []
    master = cfg.get("role") == "master"
    if "design" not in tracks:
        PARTS["Rails"] = [f for f in PARTS["Rails"] if not f.startswith("system/")]
    for part, files in PARTS.items():
        missing = [f for f in files if not (root / f).exists()]
        seeded = [f for f in files if (root / f).exists() and (root / f).suffix == ".md"
                  and SEED.search((root / f).read_text(encoding="utf-8"))
                  and not (master and f.startswith(("context/", "system/")))]  # a master keeps these seeded
        state = "absent" if len(missing) == len(files) else ("thin" if missing or seeded else "working")
        results[part] = {"state": state, "missing": missing, "seeded": seeded}

    code, out = run([sys.executable, "-c",
                     "import sys; sys.path.insert(0,'scripts'); import records as R, json; s=R.load_schema();"
                     "print(json.dumps({n: R.read_record(n, s)['warnings'] for n in s['records']}))"], root)
    try:
        drift = {k: v for k, v in json.loads(out.strip().splitlines()[-1]).items() if v}
    except Exception:
        drift = {"_parser": [out.strip()[:300]]}
    if drift:
        problems.append(f"record drift: {drift}")

    code, out = run([sys.executable, "scripts/harness_check.py", "--json"], root)
    sens = {"fails": 0}
    try:
        sens = json.loads(out)
        sensor_line = f"sensors ran: {sens['fails']} fail(s), {sens['warns']} warn(s)"
    except Exception:
        sensor_line = "sensors did not run"
        problems.append(f"harness_check.py failed: {out[:300]}")

    planted = "zq-verify-term-7731"
    terms = root / ".harness" / "confidential.txt"
    guard_line = "guard not tested"
    if terms.exists():
        original = terms.read_text(encoding="utf-8")
        try:
            terms.write_text(original + planted + "\n", encoding="utf-8")
            event = json.dumps({"tool_name": "Write", "tool_input": {"file_path": "x.md", "content": f"note {planted}"}})
            gcode, gout = run([sys.executable, ".claude/hooks/confidential_guard.py"], root, stdin=event)
            clean = json.dumps({"tool_name": "Write", "tool_input": {"file_path": "x.md", "content": "harmless"}})
            ccode, _ = run([sys.executable, ".claude/hooks/confidential_guard.py"], root, stdin=clean)
        finally:
            terms.write_text(original, encoding="utf-8")
        if gcode == 2 and ccode == 0:
            guard_line = "guard blocks a planted term and allows clean text"
        else:
            guard_line = f"guard FAILED (planted exit {gcode}, clean exit {ccode})"
            problems.append(guard_line)

    hook_line = "no settings.json"
    sp = root / ".claude" / "settings.json"
    if sp.exists():
        settings = json.loads(sp.read_text(encoding="utf-8"))
        refs = re.findall(r"\$CLAUDE_PROJECT_DIR/([^\"\s]+)", json.dumps(settings).replace('\\"', '"'))
        dead = [r for r in refs if not (root / r).exists()]
        hook_line = f"{len(refs)} hook command(s), {len(dead)} dead"
        if dead:
            problems.append(f"hooks point to missing files: {dead}")

    code, out = run([sys.executable, "scripts/build_dashboard.py", "--quiet"], root)
    dash_line = "dashboard builds" if code == 0 and (root / "dashboard" / "data.js").exists() else f"dashboard FAILED: {out[:200]}"
    if "FAILED" in dash_line:
        problems.append(dash_line)

    asks = sum(len(ASK.findall(p.read_text(encoding="utf-8"))) for p in root.rglob("*.md")
               if ".git" not in p.parts)

    states = [r["state"] for r in results.values()]
    if problems or "absent" in states:
        maturity = "sketch"
    elif states.count("working") <= 2 or sens.get("fails", 0):
        maturity = "wireframe"
    elif states.count("working") < 5 or asks:
        maturity = "prototype"
    else:
        maturity = "production"

    print("| Part | State | Evidence |\n|---|---|---|")
    for part, r in results.items():
        ev = []
        if r["missing"]:
            ev.append("missing: " + ", ".join(r["missing"]))
        if r["seeded"]:
            ev.append("still seeded: " + ", ".join(r["seeded"]))
        print(f"| {part} | {r['state']} | {'; '.join(ev) or 'all files present and filled'} |")
    print(f"\nTests: {sensor_line}; {guard_line}; {hook_line}; {dash_line}; "
          f"records parse {'cleanly' if not drift else 'WITH DRIFT'}; {asks} open [[ASK]] marker(s).")
    if master:
        print("Role: master (per-project seeds in context/ and system/ are expected to stay seeded).")
    print(f"Maturity: {maturity}. " + {
        "sketch": "Something structural is missing or broken; fix the problems listed before anyone uses it.",
        "wireframe": "The structure works but most parts are still empty, or the sensors report fails.",
        "prototype": "Works end to end; seeded files and open questions remain to be filled from real use.",
        "production": "All parts working and filled; keep it honest with the weekly check.",
    }[maturity])
    for p in problems:
        print(f"PROBLEM: {p}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
