#!/usr/bin/env bash
# mimi-ctl.sh — control MiMi Assistant
#
# Usage:
#   ./scripts/mimi-ctl.sh start    — start in background
#   ./scripts/mimi-ctl.sh stop     — stop
#   ./scripts/mimi-ctl.sh restart  — restart
#   ./scripts/mimi-ctl.sh status   — show PID + last log lines
#   ./scripts/mimi-ctl.sh logs     — live tail of logs (Ctrl-C to exit)
#   ./scripts/mimi-ctl.sh logs-clear — clear log files

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MIMI_HOME="${MIMI_HOME:-$SCRIPT_DIR}"
MIMI_LOGS="${MIMI_LOGS:-$MIMI_HOME/logs}"
PYTHON="$MIMI_HOME/venv/bin/python"
MAIN="$MIMI_HOME/src/main.py"
LOG_OUT="$MIMI_LOGS/mimi.out.log"
LOG_ERR="$MIMI_LOGS/mimi.err.log"
LOCKFILE="/tmp/mimi-assistant.lock"

green()  { printf '\033[0;32m%s\033[0m\n' "$*"; }
yellow() { printf '\033[0;33m%s\033[0m\n' "$*"; }
red()    { printf '\033[0;31m%s\033[0m\n' "$*"; }

is_running() {
    [[ -f "$LOCKFILE" ]] && kill -0 "$(cat "$LOCKFILE")" 2>/dev/null
}

cmd_start() {
    if is_running; then
        yellow "MiMi is already running (PID $(pgrep -f "$PGREP_PAT"))."
        return
    fi
    mkdir -p "$MIMI_LOGS"
    nohup "$PYTHON" "$MAIN" \
        >> "$LOG_OUT" \
        2>> "$LOG_ERR" &
    echo $! > "$LOCKFILE"
    disown
    green "MiMi launched — use 'status' or 'logs' to confirm it started."
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

case "${1:-}" in
    start)      cmd_start      ;;
    stop)       cmd_stop       ;;
    restart)    cmd_restart    ;;
    status)     cmd_status     ;;
    logs)       cmd_logs       ;;
    logs-clear) cmd_logs_clear ;;
    *) echo "Usage: $(basename "$0") {start|stop|restart|status|logs|logs-clear}"; exit 1 ;;
esac
