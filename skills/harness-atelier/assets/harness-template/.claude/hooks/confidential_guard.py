#!/usr/bin/env python3
"""PreToolUse guard for Write/Edit. Blocks a write that would put a listed
confidential term into a file, at the moment of writing, not at commit time.

A written rule ("never mention X") fails the first time someone is
in a hurry. A guard does not. Exit code 2 blocks the tool call and shows the
reason to Claude, who can then rephrase.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TERM_FILES = [ROOT / ".harness" / "confidential.txt", ROOT / ".harness" / "confidential.local.txt"]

try:
    event = json.load(sys.stdin)
except Exception:
    sys.exit(0)

tool_input = event.get("tool_input", {}) or {}
target = str(tool_input.get("file_path", ""))
if target.endswith((".harness/confidential.txt", ".harness/confidential.local.txt")):
    sys.exit(0)
lines = []
for f in TERM_FILES:
    if f.exists():
        lines += f.read_text(encoding="utf-8").splitlines()

chunks = [tool_input.get("content", ""), tool_input.get("new_string", "")]
for e in tool_input.get("edits", []) or []:
    chunks.append(e.get("new_string", ""))
text = "\n".join(c for c in chunks if isinstance(c, str))

for raw in lines:
    line = raw.strip()
    if not line or line.startswith("#"):
        continue
    if line.startswith("RE:"):
        pat = re.compile(line[3:])
    elif line.startswith("CS:"):
        pat = re.compile(r"\b" + re.escape(line[3:]) + r"\b")
    else:
        pat = re.compile(r"\b" + re.escape(line) + r"\b", re.IGNORECASE)
    if pat.search(text):
        print(f"Blocked: this write contains a term listed as confidential ('{line}'). "
              "Remove or anonymise it. If the term should not be listed, ask the owner to edit that file.",
              file=sys.stderr)
        sys.exit(2)
sys.exit(0)
