#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/macos/EchoformGUI/Sources/EchoformGUI/Resources/Runtime"
VENV_DIR="$RUNTIME_DIR/venv"

echo "Building bundled Echoform runtime at: $VENV_DIR"
mkdir -p "$RUNTIME_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
"$PYTHON_BIN" -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/pip" install -r "$ROOT_DIR/requirements.txt"
"$VENV_DIR/bin/python" -c "import numpy, PIL, tqdm; print('Bundled Python dependencies OK')"

cat > "$RUNTIME_DIR/README.md" <<'MARKER'
# Bundled Echoform Runtime

This directory contains the Python runtime copied into the Swift package resources for development packaging.

For a signed public release, build the runtime on the oldest supported macOS version/architecture target and test on a clean Mac.
MARKER

echo "Runtime complete."
echo "Next: cd macos/EchoformGUI && swift build"
