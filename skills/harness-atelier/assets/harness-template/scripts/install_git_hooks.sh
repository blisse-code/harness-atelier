#!/usr/bin/env bash
# Installs the pre-commit confidentiality check. .git/hooks is not part of a
# clone, so every new machine needs this once; the SessionStart hook runs it.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[ -d "$ROOT/.git" ] || exit 0
HOOK="$ROOT/.git/hooks/pre-commit"
cat > "$HOOK" <<'HOOK'
#!/usr/bin/env bash
python3 "$(git rev-parse --show-toplevel)/scripts/harness_check.py" --staged || {
  echo "Commit blocked by the confidentiality check above." >&2; exit 1; }
HOOK
chmod +x "$HOOK"
