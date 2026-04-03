#!/usr/bin/env bash
# MiMi Assistant — install script (git clone users)
# Usage: ./install.sh

set -euo pipefail

MIMI_HOME="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

green()  { printf '\033[0;32m%s\033[0m\n' "$*"; }

# ── Python venv ───────────────────────────────────────────────────────────────
if [[ ! -d "$MIMI_HOME/venv" ]]; then
    echo "Creating virtual environment..."
    python3 -m venv "$MIMI_HOME/venv"
    "$MIMI_HOME/venv/bin/pip" install --upgrade pip -q
    "$MIMI_HOME/venv/bin/pip" install -r "$MIMI_HOME/requirements.txt" -q
    green "Virtual environment created."
else
    green "Virtual environment already exists."
fi

# ── shell profile setup ───────────────────────────────────────────────────────
export MIMI_HOME
bash "$MIMI_HOME/scripts/mimi-setup.sh"
