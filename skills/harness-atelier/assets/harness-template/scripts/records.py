"""Shared reader for the harness's Markdown records.

Records are plain Markdown tables so people can edit them by hand and git can
merge them. The price of that freedom is drift: a renamed column silently
blinds every tool that reads the table. So every reader goes through here, and
every table is checked against `.harness/schema.json`, the single place that
says which columns and which status words each record uses.

Standard library only. Python 3.8+.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / ".harness" / "schema.json"

SEED_MARKER = re.compile(r"<!--\s*status:\s*seed", re.IGNORECASE)
ASK_MARKER = re.compile(r"\[\[ASK:([^\]]*)\]\]")


def load_schema() -> dict:
    with SCHEMA_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def _cells(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def _is_separator(line: str) -> bool:
    return bool(re.fullmatch(r"\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*", line))


def read_table(path: Path) -> tuple[list[str], list[dict]]:
    """Return (header, rows) for the first Markdown table in `path`.

    Rows appended after the table with blank lines in between are still read,
    as long as they have the same number of cells: hand-appended rows (for
    example `echo "| ... |" >> file`) are common and must not vanish.
    """
    if not path.exists():
        return [], []
    lines = path.read_text(encoding="utf-8").splitlines()
    header: list[str] = []
    rows: list[dict] = []
    i = 0
    while i < len(lines) - 1:
        if lines[i].strip().startswith("|") and _is_separator(lines[i + 1]):
            header = _cells(lines[i])
            i += 2
            break
        i += 1
    if not header:
        return [], []
    for line in lines[i:]:
        if not line.strip().startswith("|") or _is_separator(line):
            continue
        cells = _cells(line)
        if len(cells) != len(header):
            continue
        if all(not c for c in cells):
            continue
        rows.append(dict(zip(header, cells)))
    return header, rows


def read_record(name: str, schema: dict | None = None) -> dict:
    """Read a record by its schema name. Returns header, rows and drift warnings."""
    schema = schema or load_schema()
    spec = schema["records"][name]
    path = ROOT / spec["path"]
    header, rows = read_table(path)
    warnings: list[str] = []
    if not path.exists():
        warnings.append(f"{spec['path']} is missing")
    elif not header:
        warnings.append(f"{spec['path']} has no table; tools cannot read it")
    else:
        missing = [c for c in spec["columns"] if c not in header]
        if missing:
            warnings.append(f"{spec['path']}: column(s) renamed or missing: {', '.join(missing)}")
    status_col = spec.get("status_column")
    allowed = spec.get("statuses")
    if status_col and allowed:
        for r in rows:
            value = r.get(status_col, "")
            if value and not any(value.lower().startswith(a.lower()) for a in allowed):
                warnings.append(
                    f"{spec['path']}: '{value}' in {status_col} is not one of: {', '.join(allowed)}"
                )
    return {"name": name, "path": spec["path"], "header": header, "rows": rows, "warnings": warnings}


def text_files(root: Path = ROOT):
    """Yield the harness's own text files, skipping git internals and caches."""
    skip_dirs = {".git", "node_modules", ".cache", "__pycache__", ".venv"}
    exts = {".md", ".txt", ".json", ".html", ".css", ".js", ".py", ".sh", ".yml", ".yaml", ".csv"}
    for p in root.rglob("*"):
        if any(part in skip_dirs for part in p.parts):
            continue
        if p.is_file() and p.suffix.lower() in exts:
            yield p
