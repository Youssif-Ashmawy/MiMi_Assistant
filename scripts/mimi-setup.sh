#!/usr/bin/env bash
# mimi-setup.sh — adds MiMi auto-start to ~/.zprofile
# Called by:  ./install.sh (git clone users)
#             mimi-setup   (brew install users)

set -euo pipefail

MIMI_HOME="${MIMI_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
MIMI_LOGS="${MIMI_LOGS:-$HOME/.mimi/logs}"
PROFILE="$HOME/.zprofile"
MARKER="# >>> mimi-assistant >>>"
MARKER_END="# <<< mimi-assistant <<<"

green()  { printf '\033[0;32m%s\033[0m\n' "$*"; }
yellow() { printf '\033[0;33m%s\033[0m\n' "$*"; }

if grep -q "$MARKER" "$PROFILE" 2>/dev/null; then
    yellow "MiMi is already in $PROFILE — run uninstall first to reconfigure."
    exit 0
fi

mkdir -p "$MIMI_LOGS"

cat >> "$PROFILE" <<EOF

$MARKER
export MIMI_HOME="$MIMI_HOME"
export MIMI_LOGS="$MIMI_LOGS"
if ! pgrep -f "python.*main\\.py" >/dev/null 2>&1; then
    mkdir -p "\$MIMI_LOGS"
    nohup "\$MIMI_HOME/venv/bin/python" "\$MIMI_HOME/src/main.py" \\
        >> "\$MIMI_LOGS/mimi.out.log" \\
        2>> "\$MIMI_LOGS/mimi.err.log" &
    disown
fi
$MARKER_END
EOF

green "Added MiMi auto-start to $PROFILE."
echo ""
echo "  MiMi starts automatically on every new Terminal session."
echo "  Start it now:   mimi-ctl start"
echo ""
yellow "  Ensure Terminal has Microphone permission:"
yellow "  System Settings → Privacy & Security → Microphone → Terminal ✓"
