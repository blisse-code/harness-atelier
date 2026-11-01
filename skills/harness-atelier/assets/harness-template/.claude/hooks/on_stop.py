#!/usr/bin/env python3
"""Stop hook. Two jobs, both cheap:
1. Rebuild the dashboard so it never shows yesterday's state.
2. Nudge a handover once: if this session changed records or work files and
   records/handovers.md was not touched, ask Claude to write the handover entry.
   `stop_hook_active` guards against looping; set "handover_nudge": false in
   harness.config.json to turn the nudge off.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
try:
    event = json.load(sys.stdin)
except Exception:
    event = {}

subprocess.run([sys.executable, str(ROOT / "scripts" / "build_dashboard.py"), "--quiet"],
               capture_output=True, timeout=60)

try:
    cfg = json.loads((ROOT / "harness.config.json").read_text(encoding="utf-8"))
except Exception:
    cfg = {}
if event.get("stop_hook_active") or cfg.get("handover_nudge", True) is False:
    sys.exit(0)

try:
    changed = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True,
                             text=True, timeout=15).stdout.splitlines()
except Exception:
    sys.exit(0)
paths = [l[3:] for l in changed]
touched_work = any(p.startswith(("records/", "work/", "context/", "system/")) for p in paths
                   if not p.startswith("records/handovers.md"))
touched_sessions = any(p.startswith("records/handovers.md") for p in paths)
if touched_work and not touched_sessions:
    print(json.dumps({"decision": "block",
                      "reason": "Project files changed this session but records/handovers.md has no handover. "
                                "If this was substantive work, run the handover skill; if it was trivial, "
                                "say so in one line and stop."}))
sys.exit(0)
