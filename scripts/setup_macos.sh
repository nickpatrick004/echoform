#!/usr/bin/env bash
set -euo pipefail

# Echoform macOS/Linux setup script.
# Run from the repository root:
#   ./scripts/setup_macos.sh

cd "$(dirname "$0")/.."

echo "== Echoform setup =="

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ERROR: ffmpeg was not found on PATH."
  echo "Install on macOS with: brew install ffmpeg"
  exit 1
fi

PYTHON_BIN=""
for candidate in python3.12 python3.11 python3.10 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then
    if "$candidate" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
    then
      PYTHON_BIN="$candidate"
      break
    fi
  fi
done

if [[ -z "$PYTHON_BIN" ]]; then
  echo "ERROR: Python 3.10+ was not found."
  echo "Recommended macOS install: brew install python@3.12"
  exit 1
fi

echo "Using Python: $($PYTHON_BIN --version)"
echo "Using FFmpeg: $(ffmpeg -version | head -n 1)"

if [[ -d .venv ]]; then
  echo "Removing old .venv"
  rm -rf .venv
fi

echo "Creating virtual environment"
"$PYTHON_BIN" -m venv .venv

# shellcheck disable=SC1091
source .venv/bin/activate

echo "Installing Echoform in editable mode"
python -m pip install --upgrade pip
python -m pip install -e .

echo "Verifying install"
python -c "import echoform; print('echoform package:', echoform.__file__)"
echoform --help >/dev/null
echoform-queue --help >/dev/null

echo ""
echo "Setup complete."
echo "Activate later with: source .venv/bin/activate"
echo "Run a preview with: echoform-queue --folder batch --preview"
echo "Run full batch with: echoform-queue --folder batch"
