"""Layer A evals: this harness's scripts give the right result (evals/EVALS.md, rows A1-A5).

Run from the harness root:  python3 -m unittest discover -s evals/tests -v
Each test works in a throwaway copy of this folder, so nothing here touches the real records.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TERM = "zzqevalconfidentialzz"  # synthetic: never print a real listed term


def run(cmd, cwd, stdin=None):
    return subprocess.run(cmd, cwd=cwd, input=stdin, capture_output=True, text=True)


class Copy(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="harness-evalA-")
        self.root = os.path.join(self.tmp, "h")
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns(".git", "__pycache__"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def py(self, *args, stdin=None):
        return run([sys.executable, *args], self.root, stdin)

    def add_term(self):
        with open(os.path.join(self.root, ".harness", "confidential.local.txt"), "a", encoding="utf-8") as f:
            f.write("\n" + TERM + "\n")


class A1Sensors(Copy):
    def test_sensors_run_and_json_parses(self):
        r = self.py("scripts/harness_check.py")
        self.assertIn(r.returncode, (0, 1), r.stderr)
        j = self.py("scripts/harness_check.py", "--json")
        json.loads(j.stdout)


class A2Records(Copy):
    def test_every_record_parses(self):
        code = ("import json, sys; sys.path.insert(0, 'scripts'); import records as R; "
                "s = json.load(open('.harness/schema.json')); [R.read_record(n, s) for n in s['records']]; print('ok')")
        r = self.py("-c", code)
        self.assertEqual(r.stdout.strip(), "ok", r.stderr)


class A3GuardBlocksTerm(Copy):
    def event(self, text):
        return json.dumps({"tool_name": "Write", "tool_input": {"file_path": os.path.join(self.root, "context", "brief.md"),
                                                                "content": text}})

    def test_planted_term_blocked_clean_text_allowed(self):
        self.add_term()
        blocked = self.py(".claude/hooks/confidential_guard.py", stdin=self.event("this names %s" % TERM))
        self.assertEqual(blocked.returncode, 2, blocked.stdout + blocked.stderr)
        clean = self.py(".claude/hooks/confidential_guard.py", stdin=self.event("nothing secret here"))
        self.assertEqual(clean.returncode, 0, clean.stdout + clean.stderr)


class A4StagedTermFails(Copy):
    def test_staged_term_fails_the_commit_check(self):
        self.add_term()
        run(["git", "init", "-q"], self.root)
        with open(os.path.join(self.root, "evals-tmp.md"), "w") as f:
            f.write("names %s\n" % TERM)
        run(["git", "add", "evals-tmp.md"], self.root)
        r = self.py("scripts/harness_check.py", "--staged")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)


class A5DashboardBuilds(Copy):
    def test_dashboard_data_written(self):
        r = self.py("scripts/build_dashboard.py", "--quiet")
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(os.path.join(self.root, "dashboard", "data.js"), encoding="utf-8") as f:
            self.assertIn("window.HARNESS", f.read())


if __name__ == "__main__":
    unittest.main()
