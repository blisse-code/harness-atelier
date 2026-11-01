#!/usr/bin/env python3
"""Package skills/harness-atelier into dist/harness-atelier.skill (a zip with the skill folder at its root).

    python3 tools/package_skill.py
"""
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "skills" / "harness-atelier"
OUT = REPO / "dist" / "harness-atelier.skill"
SKIP = {"__pycache__", ".DS_Store"}


def main() -> int:
    if len(list(SRC.rglob("SKILL.md"))) != 1:
        print("Refusing: the skill folder must contain exactly one SKILL.md.", file=sys.stderr)
        return 1
    OUT.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(SRC.rglob("*")):
            if p.is_file() and not (SKIP & set(p.parts)) and p.suffix != ".pyc":
                info = zipfile.ZipInfo(str(Path("harness-atelier") / p.relative_to(SRC)))
                info.external_attr = (0o755 if p.suffix in {".py", ".sh"} else 0o644) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, p.read_bytes())
    print(f"wrote {OUT.relative_to(REPO)} ({OUT.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
