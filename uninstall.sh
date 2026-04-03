#!/usr/bin/env bash
# MiMi Assistant — uninstall script
# Stops MiMi and removes it from ~/.zprofile.

set -euo pipefail

PROFILE="$HOME/.zprofile"
MARKER="# >>> mimi-assistant >>>"
MARKER_END="# <<< mimi-assistant <<<"

green()  { printf '\033[0;32m%s\033[0m\n' "$*"; }
yellow() { printf '\033[0;33m%s\033[0m\n' "$*"; }

# Stop running instance
if pgrep -f "python.*main\.py" >/dev/null 2>&1; then
    pkill -f "python.*main\.py" && green "MiMi stopped."
else
    yellow "MiMi is not running."
fi

# Remove .zprofile block
if grep -q "$MARKER" "$PROFILE" 2>/dev/null; then
    # Use sed to remove everything between the markers (inclusive)
    sed -i '' "/$MARKER/,/$MARKER_END/d" "$PROFILE"
    # Remove the blank line left before the block
    sed -i '' '/^$/N;/^\n$/d' "$PROFILE"
    green "Removed MiMi from $PROFILE."
else
    yellow "MiMi was not found in $PROFILE."
fi

green "Uninstall complete."
