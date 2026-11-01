#!/usr/bin/env python3
"""Deterministic evals for harness-atelier: the parts that can be tested without a model.

For every fixture config in evals/fixtures/ it generates a harness in a temp folder, verifies it,
then plants known problems and checks the right sensor catches each one. It also checks the
scaffold's safety promises (never overwrite, refuse protected paths) and the repo's own hygiene
(one SKILL.md, visuals rebuilt from source, reduced-motion support).

Behavioural evals (does the skill interview well, does it stop at the map?) need a model and a
person; they are described in docs/EVALS.md.

    python3 evals/run_evals.py          # exit 1 if anything fails
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILL = REPO / "skills" / "harness-atelier"
SCAFFOLD = SKILL / "scripts" / "scaffold.py"
VERIFY = SKILL / "scripts" / "verify_harness.py"
RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))


def run(cmd, cwd=None, stdin=None):
    p = subprocess.run([str(c) for c in cmd], cwd=cwd, input=stdin, capture_output=True, text=True, timeout=120)
    return p.returncode, p.stdout + p.stderr


def sensors(root: Path) -> list[dict]:
    _, out = run([sys.executable, "scripts/harness_check.py", "--json"], cwd=root)
    return json.loads(out)["findings"]


def fired(root: Path, check_name: str, severity: str | None = None) -> bool:
    return any(f["check"] == check_name and (severity is None or f["severity"] == severity) for f in sensors(root))


def fixture_suite(cfg_path: Path, tmp: Path) -> None:
    tag = cfg_path.stem
    cfg = json.loads(cfg_path.read_text())
    out = tmp / tag
    code, txt = run([sys.executable, SCAFFOLD, "--config", cfg_path, "--out", out])
    report = json.loads(txt) if code in (0, 1) else {}
    check(f"{tag}: scaffold runs", code == 0, txt[-300:] if code else "")
    check(f"{tag}: no unrendered template variables", not report.get("unrendered_variables"), str(report.get("unrendered_variables")))

    code, txt = run([sys.executable, VERIFY, out])
    check(f"{tag}: verify passes with no PROBLEM lines", code == 0 and "PROBLEM" not in txt, txt[-400:])
    check(f"{tag}: fresh harness has zero sensor fails", "0 fail(s)" in txt, txt[-300:])

    code, txt = run([sys.executable, SCAFFOLD, "--config", cfg_path, "--out", out])
    check(f"{tag}: re-running never overwrites", json.loads(txt)["written"] == 0)

    code, _ = run([sys.executable, SCAFFOLD, "--config", cfg_path, "--out", out / "inside", "--protect", out])
    check(f"{tag}: refuses to write inside a protected path", code == 2)

    # Planted problems -> the right sensor fires.
    term = (cfg.get("confidential_terms") or cfg.get("confidential_terms_local") or [None])[0]
    if term:
        word = term.split(":", 1)[1] if term.startswith(("CS:", "RE:")) else term
        leak = out / "work" / "leak.md"
        leak.parent.mkdir(parents=True, exist_ok=True)
        leak.write_text(f"notes about {word}\n")
        check(f"{tag}: leaked term is a Confidentiality fail", fired(out, "Confidentiality", "fail"))
        event = json.dumps({"tool_name": "Write", "tool_input": {"file_path": "x.md", "content": word}})
        code, _ = run([sys.executable, ".claude/hooks/confidential_guard.py"], cwd=out, stdin=event)
        check(f"{tag}: write guard blocks the term", code == 2)
        leak.unlink()

    ships = out / "records" / "ships.md"
    ships.write_text(ships.read_text() + "| 2026-01-10 | Deck | v1 | Client | link | R9 |\n")
    check(f"{tag}: ship without final approval fails", fired(out, "Shipped without sign-off", "fail"))

    tasks = out / "records" / "tasks.md"
    tasks.write_text(tasks.read_text() + "| T1 | a | x | s | todo | 2099-01-01 | y |\n| T1 | b | x | s | todo | 2099-01-01 | y |\n")
    check(f"{tag}: duplicate IDs warn", fired(out, "Duplicate IDs", "warn"))

    fb = out / "records" / "feedback.md"
    fb.write_text(fb.read_text().replace("| ID | Date | From |", "| Ref | Date | From |"))
    check(f"{tag}: renamed record column fails", fired(out, "Record schema", "fail"))

    if "design" in (cfg.get("tracks") or []):
        (out / "system" / "tokens.md").write_text(
            "# Tokens\n\n## Colour\n\n| Token | Value | Use |\n|---|---|---|\n| ink | #111111 | text |\n\n"
            "## Spacing scale\n\n| Token | Value |\n|---|---|\n| s1 | 4px |\n| s2 | 8px |\n| s3 | 16px |\n\n## Type scale\n")
        proto = out / "work" / "prototypes" / "p"
        proto.mkdir(parents=True, exist_ok=True)
        (proto / "index.html").write_text('<div style="padding:8px 13px;color:#ff0000"></div>')
        check(f"{tag}: off-scale spacing warns", fired(out, "Spacing compliance", "warn"))
        check(f"{tag}: off-system colour warns", fired(out, "Token compliance", "warn"))

    if cfg.get("role") == "master":
        check(f"{tag}: project rows in a master warn", fired(out, "Work in the master", "warn"))


def repo_hygiene(tmp: Path) -> None:
    skill_mds = [p for p in SKILL.rglob("SKILL.md")]
    check("package holds exactly one SKILL.md", len(skill_mds) == 1, ", ".join(map(str, skill_mds)))
    head = (SKILL / "SKILL.md").read_text().split("---")[1]
    desc = re.search(r"description:\s*(.+)", head).group(1)
    check("description is under 1024 characters", len(desc) < 1024, str(len(desc)))
    check("SKILL.md stays under 500 lines", (SKILL / "SKILL.md").read_text().count("\n") < 500)

    vis = REPO / "docs" / "visuals"
    copy = tmp / "visuals"
    shutil.copytree(vis, copy)
    run([sys.executable, copy / "build_visuals.py"])
    same = all((copy / f.name).read_text() == f.read_text() for f in vis.glob("*.svg"))
    check("visuals match their generator (no hand edits)", same)
    for f in vis.glob("*.svg"):
        t = f.read_text()
        check(f"{f.name}: honours reduced motion", "prefers-reduced-motion: reduce" in t)
        check(f"{f.name}: has title and description", "<title" in t and "<desc" in t)
        check(f"{f.name}: no SMIL (CSS-only motion)", "<animate" not in t)

    plugin = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text())
    paths = [s for p in plugin["plugins"] for s in p.get("skills", [])]
    check("marketplace skill paths exist", all((REPO / s).exists() for s in paths), str(paths))


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for cfg in sorted((REPO / "evals" / "fixtures").glob("*.json")):
            fixture_suite(cfg, tmp)
        repo_hygiene(tmp)
    width = max(len(n) for n, _, _ in RESULTS)
    for name, ok, detail in RESULTS:
        print(f"{'PASS' if ok else 'FAIL'}  {name.ljust(width)}" + (f"   {detail.strip()[:200]}" if not ok and detail else ""))
    fails = sum(1 for _, ok, _ in RESULTS if not ok)
    print(f"\n{len(RESULTS) - fails}/{len(RESULTS)} passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
