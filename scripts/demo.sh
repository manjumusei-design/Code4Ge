#!/usr/bin/env bash
# CommitForge automated demo — creates a temp repo, runs scan, cleans up.
set -euo pipefail

DEMO_DIR=$(mktemp -d)
trap 'rm -rf "$DEMO_DIR"' EXIT

echo "Creating demo repo in $DEMO_DIR"
cd "$DEMO_DIR"
git init -q

cat > app.py << 'PY'
def greet(name: str) -> str:
    return f"Hello, {name}!"

# TODO: add farewell function
# TODO: add error handling
# TODO: add logging
# TODO: add validation
# TODO: add tests
PY

git add . && git commit -q -m "initial commit"
echo "def main(): greet('world')" >> app.py

echo ""
echo "Running commitforge scan..."
python -m commitforge --repo "$DEMO_DIR" scan 2>/dev/null || {
    # Fallback: run from project directory
    PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
    PYTHONPATH="$PROJECT_DIR" python -m commitforge --repo "$DEMO_DIR" scan 2>/dev/null || true
}

echo ""
echo "Demo complete"
