#!/usr/bin/env bash
# Same build for macOS/Linux — produces a native binary of that OS (NOT a Windows .exe;
# PyInstaller cannot cross-compile). Mainly useful to verify the packaging.
set -euo pipefail
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"
"$PY" -m venv .venv-build
. .venv-build/bin/activate
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements-build.txt
[ "${1:-}" = "onedir" ] && export SLIDELIB_ONEDIR=1
pyinstaller --clean --noconfirm slide_library.spec
echo "Built: $(pwd)/dist/"
