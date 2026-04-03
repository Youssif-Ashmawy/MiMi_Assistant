#!/usr/bin/env bash
# mimi-ctl.sh — control MiMi Assistant
#
# Usage:
#   mimi-ctl start    — start in background (shows live progress until ready)
#   mimi-ctl stop     — stop
#   mimi-ctl restart  — restart
#   mimi-ctl status   — show PID + last log lines
#   mimi-ctl logs     — live tail of logs (Ctrl-C to exit)
#   mimi-ctl logs-clear — clear log files
#   mimi-ctl upgrade  — stop → untap → tap → install latest
#   mimi-ctl uninstall — stop → remove .zprofile entry → brew uninstall

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MIMI_HOME="${MIMI_HOME:-$SCRIPT_DIR}"
MIMI_LOGS="${MIMI_LOGS:-$MIMI_HOME/logs}"
PYTHON="$MIMI_HOME/venv/bin/python"
MAIN="$MIMI_HOME/src/main.py"
LOG_OUT="$MIMI_LOGS/mimi.out.log"
LOG_ERR="$MIMI_LOGS/mimi.err.log"
LOCKFILE="/tmp/mimi-assistant.lock"
PROFILE="$HOME/.zprofile"
MARKER="# >>> mimi-assistant >>>"
MARKER_END="# <<< mimi-assistant <<<"
TAP_URL="https://github.com/Youssif-Ashmawy/MiMi_Assistant"

green()  { printf '\033[0;32m%s\033[0m\n' "$*"; }
yellow() { printf '\033[0;33m%s\033[0m\n' "$*"; }
red()    { printf '\033[0;31m%s\033[0m\n' "$*"; }
dim()    { printf '\033[2m%s\033[0m\n' "$*"; }

is_running() {
    [[ -f "$LOCKFILE" ]] && kill -0 "$(cat "$LOCKFILE")" 2>/dev/null
}

cmd_start() {
    if is_running; then
        yellow "MiMi is already running (PID $(cat "$LOCKFILE"))."
        return
    fi

    mkdir -p "$MIMI_LOGS"
    # Clear logs so progress tail only shows current startup
    : > "$LOG_OUT"
    : > "$LOG_ERR"

    nohup "$PYTHON" "$MAIN" \
        >> "$LOG_OUT" \
        2>> "$LOG_ERR" &
    echo $! > "$LOCKFILE"
    disown

    echo ""
    echo "  Starting MiMi Assistant..."
    echo ""

    # ── Live startup progress ─────────────────────────────────────────────
    # Watch log for known milestones and print them as they appear.
    # Exit once we see the "running" line or a fatal error.
    local timeout=60
    local elapsed=0
    local ready=false

    while [[ $elapsed -lt $timeout ]]; do
        if [[ -f "$LOG_OUT" ]]; then
            # Check for key progress lines in order
            if grep -q "Loading openWakeWord models" "$LOG_OUT" 2>/dev/null && \
               ! grep -q "_oww_loading_printed" /tmp/mimi-progress 2>/dev/null; then
                dim "  ⏳ Loading wake word models..."
                touch /tmp/mimi-progress-oww 2>/dev/null || true
            fi

            if grep -q "Microphone test" "$LOG_OUT" 2>/dev/null && \
               [[ ! -f /tmp/mimi-progress-mic ]]; then
                dim "  ⏳ Testing microphone..."
                touch /tmp/mimi-progress-mic 2>/dev/null || true
            fi

            if grep -q "Microphone test successful" "$LOG_OUT" 2>/dev/null && \
               [[ ! -f /tmp/mimi-progress-mic-ok ]]; then
                dim "  ✅ Microphone ready"
                touch /tmp/mimi-progress-mic-ok 2>/dev/null || true
            fi

            if grep -q "openWakeWord loaded" "$LOG_OUT" 2>/dev/null && \
               [[ ! -f /tmp/mimi-progress-oww-ok ]]; then
                dim "  ✅ Wake word model loaded"
                touch /tmp/mimi-progress-oww-ok 2>/dev/null || true
            fi

            if grep -q "MiMi Assistant is running" "$LOG_OUT" 2>/dev/null; then
                ready=true
                break
            fi
        fi

        # Check for crash
        if ! is_running; then
            break
        fi

        sleep 1
        elapsed=$((elapsed + 1))
    done

    rm -f /tmp/mimi-progress-oww /tmp/mimi-progress-mic \
          /tmp/mimi-progress-mic-ok /tmp/mimi-progress-oww-ok 2>/dev/null || true

    echo ""
    if $ready; then
        green "  MiMi Assistant is ready! Say 'Hey Mycroft' to activate."
    elif is_running; then
        yellow "  MiMi is running but took longer than expected — check: mimi-ctl logs"
    else
        red "  MiMi failed to start — check: mimi-ctl logs"
    fi
    echo ""
}

cmd_stop() {
    if ! is_running; then
        yellow "MiMi is not running."
        rm -f "$LOCKFILE"
        return
    fi
    kill "$(cat "$LOCKFILE")" 2>/dev/null || true
    rm -f "$LOCKFILE"
    green "MiMi stopped."
}

cmd_restart() {
    cmd_stop
    sleep 0.5
    cmd_start
}

cmd_status() {
    echo ""
    if is_running; then
        green "Status: RUNNING  (PID $(cat "$LOCKFILE"))"
    else
        yellow "Status: STOPPED"
    fi
    echo ""
    echo "--- stdout (last 10) ---"
    [[ -f "$LOG_OUT" ]] && tail -n 10 "$LOG_OUT" || echo "(no log yet)"
    echo ""
    echo "--- stderr (last 10) ---"
    [[ -f "$LOG_ERR" ]] && tail -n 10 "$LOG_ERR" || echo "(no log yet)"
    echo ""
}

cmd_logs() {
    echo "Tailing logs — Ctrl-C to stop"
    tail -f "$LOG_OUT" "$LOG_ERR" 2>/dev/null || { red "No logs yet — run 'start' first."; exit 1; }
}

cmd_logs_clear() {
    : > "$LOG_OUT" && green "Cleared stdout log."
    : > "$LOG_ERR" && green "Cleared stderr log."
}

cmd_upgrade() {
    echo ""
    echo "  Upgrading MiMi Assistant..."
    echo ""

    cmd_stop 2>/dev/null || true

    dim "  Uninstalling current version..."
    brew uninstall mimi-assistant 2>/dev/null || true

    dim "  Removing tap..."
    brew untap youssif/mimi 2>/dev/null || true

    dim "  Re-adding tap..."
    brew tap youssif/mimi "$TAP_URL"

    dim "  Installing latest version..."
    brew install mimi-assistant

    green "  Upgrade complete!"
    echo ""
    echo "  Run 'mimi-ctl start' to launch the new version."
    echo ""
}

cmd_uninstall() {
    echo ""
    echo "  Uninstalling MiMi Assistant..."
    echo ""

    cmd_stop 2>/dev/null || true

    # Remove .zprofile block
    if grep -q "$MARKER" "$PROFILE" 2>/dev/null; then
        sed -i '' "/$MARKER/,/$MARKER_END/d" "$PROFILE"
        green "  Removed auto-start from $PROFILE."
    fi

    rm -f "$LOCKFILE"

    dim "  Removing brew package..."
    brew uninstall mimi-assistant 2>/dev/null || true

    dim "  Removing tap..."
    brew untap youssif/mimi 2>/dev/null || true

    green "  MiMi Assistant uninstalled."
    echo ""
}

case "${1:-}" in
    start)      cmd_start      ;;
    stop)       cmd_stop       ;;
    restart)    cmd_restart    ;;
    status)     cmd_status     ;;
    logs)       cmd_logs       ;;
    logs-clear) cmd_logs_clear ;;
    upgrade)    cmd_upgrade    ;;
    uninstall)  cmd_uninstall  ;;
    *) echo "Usage: mimi-ctl {start|stop|restart|status|logs|logs-clear|upgrade|uninstall}"; exit 1 ;;
esac
