#!/usr/bin/env python3
"""Build dashboard/data.js from the records, so dashboard/index.html opens
straight from disk (no server, no install, works offline).

The dashboard only ever shows what is already written in the repo's records.
It never invents a figure: an empty record shows as "no data yet", not zero.

Usage: python3 scripts/build_dashboard.py [--quiet]
"""
from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import records as R  # noqa: E402


def last_session() -> dict | None:
    path = R.ROOT / "records" / "handovers.md"
    if not path.exists():
        return None
    blocks = re.split(r"\n(?=### )", path.read_text(encoding="utf-8"))
    entries = [b for b in blocks if b.startswith("### ")]
    if not entries:
        return None
    last = entries[-1].strip().splitlines()
    return {"title": last[0][4:].strip(), "body": "\n".join(last[1:]).strip()}


def sensors() -> dict:
    try:
        out = subprocess.run([sys.executable, str(R.ROOT / "scripts" / "harness_check.py"), "--json"],
                             capture_output=True, text=True, timeout=60).stdout
        return json.loads(out)
    except Exception as exc:
        return {"findings": [{"check": "Sensors", "severity": "warn",
                              "evidence": f"could not run harness_check.py: {exc}", "fix": "Run it by hand."}],
                "fails": 0, "warns": 1}


def evals() -> dict:
    """Eval runs from evals/runs.md (the harness checking itself): the latest few, newest last."""
    path = R.ROOT / "evals" / "runs.md"
    if not path.exists():
        return {"runs": []}
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.startswith("|") and len(cells) >= 4 and re.match(r"\d{4}-\d{2}-\d{2}$", cells[0]):
            rows.append({"date": cells[0], "layer": cells[1], "rows": cells[2], "result": cells[3]})
    return {"runs": rows[-6:]}


def main() -> int:
    quiet = "--quiet" in sys.argv
    schema = R.load_schema()
    cfg_path = R.ROOT / "harness.config.json"
    config = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
    data = {name: R.read_record(name, schema) for name in schema["records"]}

    def count(name: str, col: str, prefix: str) -> int:
        return sum(1 for r in data.get(name, {}).get("rows", []) if r.get(col, "").lower().startswith(prefix))

    payload = {
        "built_at": dt.datetime.now().isoformat(timespec="minutes"),
        "harness": config.get("harness_name", "Harness"),
        "owner": config.get("owner"),
        "context": config.get("context"),
        "stages": config.get("stages", []),
        "approval_chain": config.get("approval_chain", []),
        "summary": {
            "tasks_open": sum(1 for r in data["tasks"]["rows"] if not r.get("Status", "").lower().startswith("done")),
            "tasks_blocked": count("tasks", "Status", "blocked"),
            "feedback_open": count("feedback", "Status", "open"),
            "changes_pending": count("changes", "Decision", "pending"),
            "ships": len(data["ships"]["rows"]),
        },
        "records": {k: {"path": v["path"], "rows": v["rows"]} for k, v in data.items()},
        "last_session": last_session(),
        "sensors": sensors(),
        "evals": evals(),
    }
    out = R.ROOT / "dashboard" / "data.js"
    out.write_text("window.HARNESS = " + json.dumps(payload, indent=1) + ";\n", encoding="utf-8")
    if not quiet:
        print(f"Dashboard data written: {out.relative_to(R.ROOT)} (open dashboard/index.html)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
