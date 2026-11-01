#!/usr/bin/env python3
"""SessionStart hook. Whatever this prints is put in front of Claude before the
first message, so it is the cheapest way to stop a session starting cold.

It mirrors three things: where the last session left off, what the sensors see
right now, and how many questions are still waiting on a person. It never
fails the session: a broken hook should not stop anyone working.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

try:
    import records as R
    cfg = json.loads((ROOT / "harness.config.json").read_text(encoding="utf-8"))
    print(f"[{cfg.get('harness_name', 'Harness')}] owner: {cfg.get('owner') or 'not set'}"
          + (" · MASTER harness: start client work in a copy, not here" if cfg.get("role") == "master" else ""))

    sessions = (ROOT / "records" / "handovers.md").read_text(encoding="utf-8")
    entries = [b for b in sessions.split("\n### ")[1:]]
    if entries:
        print("Last handover (mirror this back in 2-3 lines before working):")
        print("### " + entries[-1].strip()[:1200])
    else:
        print("No handover entries yet: this is the first session, or the last one did not hand over.")

    out = subprocess.run([sys.executable, str(ROOT / "scripts" / "harness_check.py"), "--quick", "--json"],
                         capture_output=True, text=True, timeout=45).stdout
    res = json.loads(out)
    if res["findings"]:
        print(f"Sensors: {res['fails']} fail(s), {res['warns']} warn(s). Top items:")
        for f in sorted(res["findings"], key=lambda f: f["severity"] != "fail")[:5]:
            print(f"  - [{f['severity']}] {f['check']}: {f['evidence']}")
    else:
        print("Sensors: clean.")

    asks = 0
    for p in R.text_files():
        if p.suffix == ".md":
            asks += len(R.ASK_MARKER.findall(p.read_text(encoding="utf-8")))
    if asks:
        print(f"{asks} open [[ASK]] question(s) wait on a person. Ask; never infer them.")
except Exception as exc:  # never block a session on the hook itself
    print(f"(session_start hook could not finish: {exc})")
