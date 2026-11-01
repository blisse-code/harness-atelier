#!/usr/bin/env python3
"""Sensors: the deterministic checks that run before any human or AI review.

Guides (CLAUDE.md, the skills, ux-context.md) steer work before it happens.
Sensors notice what went wrong afterwards. This file is the cheap, fast,
computational half of the sensors: greps and table reads that need no
judgement. The expensive, inferential half (does this screen fit the users?)
is the `gate` skill and the `evaluator` agent, and it runs *after* this passes,
so judgement is never spent on something a grep could have caught.

Usage:
  python3 scripts/harness_check.py            # full report, exit 1 on any fail
  python3 scripts/harness_check.py --quick    # session-start subset
  python3 scripts/harness_check.py --json     # machine-readable, for the dashboard
  python3 scripts/harness_check.py --staged   # confidentiality only, on staged git changes
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import records as R  # noqa: E402

FINDINGS: list[dict] = []


def add(check: str, severity: str, evidence: str, fix: str) -> None:
    FINDINGS.append({"check": check, "severity": severity, "evidence": evidence, "fix": fix})


# ---------------------------------------------------------------- confidentiality
TERM_FILES = [R.ROOT / ".harness" / "confidential.txt", R.ROOT / ".harness" / "confidential.local.txt"]


def load_terms() -> list[tuple[str, re.Pattern]]:
    lines = []
    for path in TERM_FILES:
        if path.exists():
            lines += path.read_text(encoding="utf-8").splitlines()
    terms = []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("RE:"):
            terms.append((line, re.compile(line[3:])))
        elif line.startswith("CS:"):
            terms.append((line, re.compile(r"\b" + re.escape(line[3:]) + r"\b")))
        else:
            terms.append((line, re.compile(r"\b" + re.escape(line) + r"\b", re.IGNORECASE)))
    return terms


def scan_text(label: str, text: str, terms) -> None:
    for name, pat in terms:
        m = pat.search(text)
        if m:
            line_no = text[: m.start()].count("\n") + 1
            add("Confidentiality", "fail", f"{label}:{line_no} matches listed term '{name}'",
                "Remove or anonymise it. If the term is wrong, edit .harness/confidential.txt.")


def check_confidential(staged: bool = False) -> None:
    terms = load_terms()
    if not terms:
        add("Confidentiality", "warn", ".harness/confidential.txt (and .local.txt) list no terms",
            "Ask the owner what must never leak (rates, other clients' names) and list it.")
        return
    term_files = {f.resolve() for f in TERM_FILES}
    if staged:
        try:
            out = subprocess.run(
                ["git", "diff", "--cached", "--unified=0", "--", ".", ":(exclude).harness/confidential.txt",
                 ":(exclude).harness/confidential.local.txt"],
                cwd=R.ROOT, capture_output=True, text=True, timeout=20).stdout
        except Exception as exc:  # git missing or hung: say so, never pass silently
            add("Confidentiality", "fail", f"could not read staged changes: {exc}", "Check git is installed.")
            return
        added = "\n".join(l[1:] for l in out.splitlines() if l.startswith("+") and not l.startswith("+++"))
        scan_text("staged changes", added, terms)
        return
    derived = {(R.ROOT / "dashboard" / "data.js").resolve()}  # built from the records, which are scanned
    for p in R.text_files():
        if p.resolve() in term_files or p.resolve() in derived:
            continue
        try:
            scan_text(str(p.relative_to(R.ROOT)), p.read_text(encoding="utf-8"), terms)
        except UnicodeDecodeError:
            continue


# ---------------------------------------------------------------- structure
def check_seeds_and_asks(config: dict) -> None:
    seeds, asks = [], []
    master = config.get("role") == "master"
    for p in R.text_files():
        if p.suffix not in (".md", ".tmpl"):
            continue
        text = p.read_text(encoding="utf-8")
        rel = str(p.relative_to(R.ROOT))
        in_tooling = "skills" in p.parts or "agents" in p.parts
        # A master keeps per-project seeds on purpose; only harness-level files must be filled there.
        expected_seed = master and rel.startswith(("context/", "system/", "work/"))
        if R.SEED_MARKER.search(text) and not in_tooling and not expected_seed:
            seeds.append(rel)
        for m in R.ASK_MARKER.finditer(text):
            asks.append(f"{rel}: {m.group(1).strip()[:70]}")
    if seeds:
        add("Unfilled seed files", "warn", f"{len(seeds)} still seeded: " + ", ".join(seeds[:8]) +
            (" ..." if len(seeds) > 8 else ""),
            "Fill each when its stage starts, or delete it if this harness never uses that step.")
    if asks:
        add("Open questions", "warn", f"{len(asks)} [[ASK]] markers, e.g. " + "; ".join(asks[:3]),
            "Ask the named person. Never infer an [[ASK]] answer.")


def check_map() -> None:
    path = R.ROOT / "CLAUDE.md"
    if not path.exists():
        add("Map", "fail", "CLAUDE.md is missing", "Regenerate it from harness.config.json.")
        return
    text = path.read_text(encoding="utf-8")
    n = text.count("\n") + 1
    if n > 150:
        add("Map size", "warn", f"CLAUDE.md is {n} lines",
            "Move detail into docs/ and leave a pointer. A map past ~150 lines stops being read as a map.")
    for ref in sorted(set(re.findall(r"`((?:docs|context|system|records|work|scripts|dashboard|\.claude|\.harness)/[^`\s]*)`", text))):
        target = R.ROOT / ref.rstrip("/")
        if "<" in ref or "*" in ref:
            continue
        if not target.exists():
            add("Map pointers", "fail", f"CLAUDE.md points to `{ref}`, which does not exist",
                "Create it or fix the pointer; a dead pointer teaches the agent to ignore the map.")


def check_records(schema: dict) -> dict:
    data = {}
    for name in schema["records"]:
        rec = R.read_record(name, schema)
        data[name] = rec
        for w in rec["warnings"]:
            sev = "fail" if ("renamed" in w or "missing" in w or "no table" in w) else "warn"
            add("Record schema", sev, w, "Restore the exact header from .harness/schema.json.")
        id_col = schema["records"][name].get("id_column")
        if id_col:
            seen: dict[str, int] = {}
            for r in rec["rows"]:
                k = r.get(id_col, "")
                if k:
                    seen[k] = seen.get(k, 0) + 1
            dups = [k for k, c in seen.items() if c > 1]
            if dups:
                add("Duplicate IDs", "warn", f"{rec['path']}: {', '.join(dups)} used more than once",
                    "Two sessions allocated the same ID. Renumber your own rows and their references.")
    return data


def check_master(data: dict, config: dict) -> None:
    if config.get("role") != "master":
        return
    used = [d["path"] for name, d in data.items() if d["rows"] and name != "timeline"]
    if used:
        add("Work in the master", "warn", "the master has project rows in: " + ", ".join(used),
            "Move them to the project's own copy; the master should stay a clean starting point.")


def check_handover_freshness(data: dict) -> None:
    """Catches lost context even without git: records dated after the newest handover."""
    path = R.ROOT / "records" / "handovers.md"
    if not path.exists():
        return
    dates = re.findall(r"^### (\d{4}-\d{2}-\d{2})", path.read_text(encoding="utf-8"), re.M)
    last = max(dates) if dates else None
    newest, where = None, ""
    for name in ("feedback", "changes", "approvals", "gates"):
        for r in data.get(name, {}).get("rows", []):
            d = r.get("Date", "")
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d) and (newest is None or d > newest):
                newest, where = d, data[name]["path"]
    if last and newest and newest > last:
        add("Session handover", "warn", f"{where} has activity on {newest}, after the last handover ({last})",
            "Write a handover for that work so the next session doesn't start cold.")


def check_flow(data: dict, config: dict) -> None:
    tasks = data.get("tasks", {}).get("rows", [])
    feedback = data.get("feedback", {}).get("rows", [])
    task_text = " ".join(" ".join(t.values()) for t in tasks)
    for f in feedback:
        fid = f.get("ID", "")
        if f.get("Status", "").lower().startswith("open") and fid and not re.search(r"\b" + re.escape(fid) + r"\b", task_text):
            add("Unplanned feedback", "warn", f"{f['ID']} ({f.get('From','?')}) is open and no task cites it",
                "Run the next-steps skill so it gets an owner and a date.")
    today = dt.date.today().isoformat()
    for t in tasks:
        status = t.get("Status", "").lower()
        if status.startswith("blocked"):
            add("Blocked work", "warn", f"{t.get('ID')} {t.get('Task','')[:50]} is blocked ({t.get('Owner','?')})",
                "Name what unblocks it in the task's Source cell.")
        due = t.get("Due", "")
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", due) and due < today and not status.startswith("done"):
            add("Overdue", "warn", f"{t.get('ID')} was due {due} ({t.get('Owner','?')})",
                "Re-date it with a reason, or escalate in next-steps.")
    chain = config.get("approval_chain") or []
    final_gate = chain[-1].lower() if chain else None
    approvals = data.get("approvals", {}).get("rows", [])
    for s in data.get("ships", {}).get("rows", []):
        rnd = s.get("Approval round", "")
        ok = any(a.get("Round") == rnd and a.get("Verdict", "").lower().startswith("approved")
                 and (final_gate is None or a.get("Gate", "").lower() == final_gate) for a in approvals)
        if not ok:
            add("Shipped without sign-off", "fail",
                f"records/ships.md: '{s.get('Deliverable','?')}' cites round '{rnd}' with no Approved row at the "
                f"'{final_gate or 'final'}' gate",
                "Approval and shipping are separate events; log the approval round first.")
    for i in data.get("insights", {}).get("rows", []):
        ev = i.get("Evidence", "")
        if not ev:
            add("Insight evidence", "fail", f"{i.get('ID')} has no evidence", "Cite the work/research/ file it came from.")
        else:
            path = ev.split("#")[0].split(" ")[0].strip("`")
            if "/" in path and not (R.ROOT / path).exists():
                add("Insight evidence", "fail", f"{i.get('ID')} cites {path}, which does not exist", "Fix the citation.")
    sessions = R.ROOT / "records" / "handovers.md"
    if sessions.exists() and "### " not in sessions.read_text(encoding="utf-8"):
        add("Session handover", "warn", "records/handovers.md has no handover entries yet",
            "End each substantive session with the handover skill.")


SPACING_PROPS = re.compile(
    r"(?:margin|padding|gap|row-gap|column-gap|inset|top|right|bottom|left)(?:-[a-z]+)?\s*:\s*([^;\"'}{]+)", re.I)


def check_spacing() -> None:
    """The classic agent habit: a 13px gap that exists nowhere in the system."""
    tokens = R.ROOT / "system" / "tokens.md"
    if not tokens.exists():
        return
    text = tokens.read_text(encoding="utf-8")
    if R.SEED_MARKER.search(text):
        return
    m = re.search(r"##\s*Spacing[^\n]*\n(.*?)(?:\n##\s|\Z)", text, re.S | re.I)
    if not m:
        return
    scale = {float(v) for v in re.findall(r"(\d+(?:\.\d+)?)\s*px", m.group(1))} | {0.0}
    if len(scale) < 3:
        return
    stray: dict[str, str] = {}
    for p in (R.ROOT / "work").rglob("*"):
        if p.suffix.lower() in {".html", ".css", ".scss", ".jsx", ".tsx", ".vue"} and "node_modules" not in p.parts:
            for decl in SPACING_PROPS.findall(p.read_text(encoding="utf-8", errors="ignore")):
                for v in re.findall(r"(-?\d+(?:\.\d+)?)px", decl):
                    if abs(float(v)) not in scale:
                        stray.setdefault(v + "px", str(p.relative_to(R.ROOT)))
    if stray:
        sample = "; ".join(f"{v} in {f}" for v, f in list(stray.items())[:5])
        add("Spacing compliance", "warn", f"{len(stray)} spacing value(s) off the scale in system/tokens.md: {sample}",
            "Use the nearest scale step, or register the value through system-update if it was approved.")


def check_tokens() -> None:
    tokens = R.ROOT / "system" / "tokens.md"
    if not tokens.exists() or R.SEED_MARKER.search(tokens.read_text(encoding="utf-8")):
        return
    known = {h.lower() for h in re.findall(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b", tokens.read_text(encoding="utf-8"))}
    stray: dict[str, set] = {}
    for p in (R.ROOT / "work").rglob("*"):
        if p.suffix.lower() in {".html", ".css", ".svg", ".jsx", ".tsx", ".vue"} and "node_modules" not in p.parts:
            for h in re.findall(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b", p.read_text(encoding="utf-8", errors="ignore")):
                if h.lower() not in known:
                    stray.setdefault(h.lower(), set()).add(str(p.relative_to(R.ROOT)))
    if stray:
        sample = "; ".join(f"{h} in {sorted(f)[0]}" for h, f in list(stray.items())[:4])
        add("Token compliance", "warn", f"{len(stray)} colour value(s) not in system/tokens.md: {sample}",
            "Use the token, or register the new value through system-update if it was approved.")


# ---------------------------------------------------------------- report
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--staged", action="store_true")
    args = ap.parse_args()

    if args.staged:
        check_confidential(staged=True)
    else:
        schema = R.load_schema()
        cfg_path = R.ROOT / "harness.config.json"
        config = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
        check_confidential()
        check_map()
        data = check_records(schema)
        check_flow(data, config)
        check_master(data, config)
        check_handover_freshness(data)
        if not args.quick:
            check_seeds_and_asks(config)
            check_tokens()
            check_spacing()

    fails = [f for f in FINDINGS if f["severity"] == "fail"]
    if args.json:
        print(json.dumps({"findings": FINDINGS, "fails": len(fails),
                          "warns": len(FINDINGS) - len(fails),
                          "checked_at": dt.datetime.now().isoformat(timespec="seconds")}, indent=2))
    else:
        if not FINDINGS:
            print("Sensors: clean.")
        else:
            print("| Check | Severity | Evidence | Fix |\n|---|---|---|---|")
            for f in sorted(FINDINGS, key=lambda f: f["severity"] != "fail"):
                print(f"| {f['check']} | {f['severity']} | {f['evidence']} | {f['fix']} |")
            print(f"\nVerdict: {len(fails)} fail(s), {len(FINDINGS) - len(fails)} warn(s)."
                  + (" Not ready for review." if fails else " Ready for the gate."))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
