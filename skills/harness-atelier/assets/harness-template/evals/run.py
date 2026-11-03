#!/usr/bin/env python3
"""Layer B runner: behaviour evals as headless Claude sessions in throwaway copies of this harness.

  python3 evals/run.py                 # every case, 3 runs each
  python3 evals/run.py B2 B7 --runs 1  # chosen cases, one run each
  python3 evals/run.py --list

Safety (evals/README.md): each run is a fresh copy with its own new git history (no remote); `claude -p --restricted`
(the harness's own hooks loaded explicitly; no other settings; file tools confined to the clone), shell commands sandboxed so they
can write only inside the clone, no MCP connectors, and a spending cap per run.
Results: evals/results/<date>-B.md (detail) and a line in evals/runs.md (with --log).
"""
import argparse
import concurrent.futures as cf
import fnmatch
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))
LOGIN = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True).stdout.strip() or os.environ.get("USER", "eval")
TOOLS = "Read,Edit,Write,Glob,Grep,Bash,Skill,Agent"
ALLOWED = ["Read", "Edit", "Write", "Glob", "Grep", "Skill", "Bash", "Agent"]
# The shell runs in Claude Code's sandbox: commands can write only inside the clone (and temp), never the real repo.
SANDBOX = json.dumps({"sandbox": {"enabled": True, "autoAllowBashIfSandboxed": True, "allowUnsandboxedCommands": False}})
BUDGET = os.environ.get("EVAL_MAX_USD", "4")


def sh(cmd, cwd, **kw):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, **kw)


def slug(path):
    return re.sub(r"[^A-Za-z0-9]", "-", path)


# ---------- fixture ----------

def make_clone(case):
    tmp = tempfile.mkdtemp(prefix="harness-evalB-")
    root = os.path.join(tmp, "repo")
    shutil.copytree(REPO, root, ignore=shutil.ignore_patterns(".git", "__pycache__", "results"))
    sh(["git", "init", "-q"], root)
    for k, v in (("user.email", "eval@example.invalid"), ("user.name", "eval")):
        sh(["git", "config", k, v], root)
    for step in case.get("setup", []):
        apply_setup(root, step)
    sh(["git", "add", "-A"], root)
    sh(["git", "commit", "-qm", "eval fixture", "--allow-empty"], root)
    base = sh(["git", "rev-parse", "HEAD"], root).stdout.strip()
    return tmp, root, base, ""


def apply_setup(root, step):
    p = os.path.join(root, step.get("replace") or step.get("append") or step.get("append_table_row") or step.get("write"))
    if "write" in step:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w", encoding="utf-8").write(step["text"])
        return
    text = open(p, encoding="utf-8").read()
    if "replace" in step:
        assert step["old"] in text, "setup: %r not in %s" % (step["old"], p)
        text = text.replace(step["old"], step["new"], step.get("count", -1))
    elif "append" in step:
        text = text.rstrip("\n") + step["text"]
    else:  # a new row under the table whose header contains header_hint, in that header's column order
        lines = text.split("\n")
        hi = next(i for i, l in enumerate(lines) if l.startswith("|") and step["header_hint"] in l)
        header = [c.strip() for c in lines[hi].strip().strip("|").split("|")]
        end = hi + 2
        while end < len(lines) and lines[end].startswith("|"):
            end += 1
        lines.insert(end, "| " + " | ".join(step["cells"].get(h, "") for h in header) + " |")
        text = "\n".join(lines)
    open(p, "w", encoding="utf-8").write(text)


# ---------- the session ----------

def run_claude(root, prompt):
    # The harness's own hooks (confidentiality guard, handover nudge) are part of what's being tested,
    # so the copy's settings are loaded explicitly (restricted mode ignores settings files), plus the sandbox.
    settings = {}
    sp = os.path.join(root, ".claude", "settings.json")
    if os.path.exists(sp):
        settings = json.load(open(sp))
    settings.update(json.loads(SANDBOX))
    cmd = ["claude", "-p", prompt, "--restricted", "--strict-mcp-config", "--tools", TOOLS,
           "--allowedTools", *ALLOWED, "--permission-mode", "dontAsk", "--output-format", "stream-json",
           "--verbose", "--no-session-persistence", "--max-budget-usd", BUDGET, "--settings", json.dumps(settings)]
    r = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=1800, stdin=subprocess.DEVNULL,  # claude -p reads piped stdin as prompt
                       env=dict(os.environ, HARNESS_USER=LOGIN))
    tools, texts, result, cost = [], [], "", 0.0
    for line in r.stdout.splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("type") == "assistant":
            for c in ev.get("message", {}).get("content", []):
                if c.get("type") == "tool_use":
                    tools.append({"name": c["name"], "input": c.get("input", {})})
                elif c.get("type") == "text":
                    texts.append(c["text"])
        elif ev.get("type") == "result":
            result, cost = ev.get("result") or "", ev.get("total_cost_usd") or 0.0
    return {"tools": tools, "texts": texts, "final": result or (texts[-1] if texts else ""), "cost": cost,
            "error": r.stderr[-800:] if r.returncode else ""}


# ---------- grading ----------

def changed_files(root, base):
    diff = sh(["git", "diff", "--name-only", base], root).stdout.split()
    new = sh(["git", "ls-files", "--others", "--exclude-standard"], root).stdout.split()
    return set(diff) | set(new), set(new) | set(sh(["git", "diff", "--name-only", "--diff-filter=A", base], root).stdout.split())


def grade(check, root, base, session):
    changed, added = changed_files(root, base)
    read = lambda rel: open(os.path.join(root, rel), encoding="utf-8", errors="replace").read() if os.path.exists(os.path.join(root, rel)) else ""
    if "new_files" in check:
        n = len([f for f in added if fnmatch.fnmatch(f, check["new_files"])])
        ok = n >= check.get("min", 0) and n <= check.get("max", 10 ** 6)
        return ok, "%d new file(s) matching %s" % (n, check["new_files"])
    if "not_contains" in check:
        ok = not re.search(check["regex"], read(check["not_contains"]))
        return ok, "%s %s %r" % (check["not_contains"], "no longer has" if ok else "still has", check["regex"])
    if "changed_contains" in check:
        pats = check["changed_contains"].split("|")
        hits = [f for f in changed if any(fnmatch.fnmatch(f, p) for p in pats)]
        added_lines = sh(["git", "diff", base, "--", *hits], root).stdout if hits else ""
        for f in hits:
            if f in added:
                added_lines += read(f)
        ok = bool(re.search(check["regex"], added_lines))
        return ok, "changed %s; new text %s %r" % (hits or "nothing", "has" if ok else "lacks", check["regex"])
    if "unchanged" in check:
        ok = check["unchanged"] not in changed
        return ok, "%s %s" % (check["unchanged"], "unchanged" if ok else "was edited")
    if "committed" in check:
        n = int(sh(["git", "rev-list", "--count", base + "..HEAD"], root).stdout.strip() or 0)
        return n >= 1, "%d new commit(s)" % n
    if "count_at_least" in check:
        n = len(re.findall(check["regex"], read(check["count_at_least"])))
        return n >= check["min"], "%d match(es) of %r" % (n, check["regex"])
    if "not_in_repo" in check:  # only what the session wrote: the eval's own files hold the test string
        diff = sh(["git", "diff", base], root).stdout
        hit = [f for f in changed if check["not_in_repo"] in read(f)] if check["not_in_repo"] in diff or added else []
        hit = [f for f in hit if f in added or check["not_in_repo"] in diff]
        return not hit, "written to %s" % hit if hit else "not stored anywhere"
    return False, "unknown check %s" % check


def judge(case, session, root):
    ctx = ""
    if case.get("judge_context_file_tail"):
        t = open(os.path.join(root, case["judge_context_file_tail"]), encoding="utf-8").read()
        ctx = "\n\nNewest entry of %s:\n%s" % (case["judge_context_file_tail"], t[t.rfind("\n## "):][:2500])
    calls = "\n".join("- %s %s" % (t["name"], json.dumps(t["input"])[:200]) for t in session["tools"][:40])
    prompt = ("You grade one behaviour of an AI assistant. Rule: %s\nUser request: %s%s\n\nTool calls it made:\n%s\n\n"
              "Its final reply:\n%s\n\nQuestion: %s\nAnswer with YES or NO on the first line, then one sentence why."
              % (case["rule"], case["prompt"], ctx, calls or "(none)", session["final"][:6000], case["judge"]))
    r = subprocess.run(["claude", "-p", prompt, "--restricted", "--strict-mcp-config", "--tools", "",
                        "--output-format", "json", "--no-session-persistence", "--max-budget-usd", "1"],
                       cwd=tempfile.gettempdir(), capture_output=True, text=True, timeout=600, stdin=subprocess.DEVNULL)
    try:
        out = json.loads(r.stdout).get("result", "")
    except ValueError:
        out = r.stdout
    return out.strip().upper().startswith("YES"), out.strip().replace("\n", " ")[:300]


def run_once(case, n):
    tmp, root, base, _ = make_clone(case)
    try:
        s = run_claude(root, case["prompt"])
        results = [grade(c, root, base, s) for c in case.get("checks", [])]
        if case.get("judge"):
            results.append(judge(case, s, root))
        limit = re.search(r"(?i)hit your .{0,20}limit|usage limit|rate limit", s["final"] + s["error"])
        if limit:  # the session never really ran: not a pass or a fail
            return {"case": case["id"], "run": n, "pass": None, "evidence": ["not run: " + limit.group(0)],
                    "cost": s["cost"], "final": "", "tools": [], "bash": []}
        ok = all(r[0] for r in results) and not s["error"]
        if s["error"]:
            results.append((False, "session ended with an error: " + s["error"][-300:]))
        return {"case": case["id"], "run": n, "pass": ok, "evidence": [r[1] for r in results] + ([s["error"]] if s["error"] else []),
                "cost": s["cost"], "final": s["final"][:1500], "tools": [t["name"] for t in s["tools"]],
                "bash": [t["input"].get("command", "")[:160] for t in s["tools"] if t["name"] == "Bash"]}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--parallel", type=int, default=4)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--log", action="store_true", help="append a line to evals/runs.md and write the results file")
    a = ap.parse_args()
    cases = json.load(open(os.path.join(HERE, "cases.json")))["cases"]
    local = os.path.join(HERE, "cases.project.json")  # this project's own cases, written by the evals skill
    if os.path.exists(local):
        cases += json.load(open(local))["cases"]
    if a.list:
        for c in cases:
            print("%-4s %s  %s" % (c["id"], c["kind"], c["rule"][:90]))
        return
    chosen = [c for c in cases if not a.ids or c["id"] in a.ids]
    jobs = [(c, n) for c in chosen for n in range(1, a.runs + 1)]
    with cf.ThreadPoolExecutor(a.parallel) as ex:
        out = list(ex.map(lambda j: run_once(*j), jobs))
    by = {}
    for r in out:
        by.setdefault(r["case"], []).append(r)
    total_cost = sum(r["cost"] for r in out)
    lines = []
    for c in chosen:
        rs = by[c["id"]]
        done = [r for r in rs if r["pass"] is not None]
        p = sum(bool(r["pass"]) for r in done)
        status = "NOT RUN" if not done else ("PASS" if p == len(rs) else ("INCOMPLETE" if len(done) < len(rs) and p == len(done) else "FAIL"))
        print("%-4s %d/%d  %s%s" % (c["id"], p, len(rs), status, "" if len(done) == len(rs) else " (%d not run)" % (len(rs) - len(done))))
        for r in rs:
            if r["pass"] is False:
                print("     run %d: %s" % (r["run"], " | ".join(r["evidence"])[:400]))
                print("     shell: %s" % r["bash"])
        lines.append((c, rs, p))
    print("cost about $%.2f" % total_cost)
    if a.log:
        write_results(lines, total_cost, a.runs)


def write_results(lines, cost, runs):
    day = datetime.now().strftime("%Y-%m-%d")
    os.makedirs(os.path.join(REPO, "evals", "results"), exist_ok=True)
    path = os.path.join(REPO, "evals", "results", "%s-B.md" % day)
    with open(path, "a", encoding="utf-8") as f:
        f.write("# Layer B run, %s %s\n\nRunner: `python3 evals/behaviour/run.py` (%d run(s) per case). Cost about $%.2f.\n\n"
                "| Case | Kind | Passed | Evidence (failed runs) |\n|---|---|---|---|\n" % (day, datetime.now().strftime("%H:%M"), runs, cost))
        for c, rs, p in lines:
            ev = "; ".join("run %d: %s" % (r["run"], " | ".join(r["evidence"])) for r in rs if r["pass"] is not True).replace("|", "/")
            f.write("| %s | %s | %d/%d | %s |\n" % (c["id"], c["kind"], p, len(rs), ev[:700] or "—"))
        f.write("\n### Final replies of failed runs\n\n")
        for c, rs, p in lines:
            for r in rs:
                if r["pass"] is False:
                    f.write("**%s run %d** (tools: %s)\n\nShell commands: %s\n\n> %s\n\n" % (
                        c["id"], r["run"], ", ".join(r["tools"]) or "none", "; ".join("`%s`" % x for x in r["bash"]) or "none",
                        r["final"].replace("\n", "\n> ")))
    passed = sum(p == len(rs) for _, rs, p in lines)
    notrun = sum(r["pass"] is None for _, rs, _ in lines for r in rs)
    row = "| %s | B | %s | %d of %d cases passed all runs%s | %s | %d run(s) each; detail evals/results/%s-B.md |\n" % (
        day, ", ".join(c["id"] for c, _, _ in lines), passed, len(lines), "; %d run(s) not run (usage limit)" % notrun if notrun else "", LOGIN, runs, day)
    with open(os.path.join(REPO, "evals", "runs.md"), "a", encoding="utf-8") as f:
        f.write(row)
    print("logged:", path)


if __name__ == "__main__":
    main()
