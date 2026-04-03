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

# Kill every MiMi process across all versions, not just the lockfile PID
kill_all() {
    # Kill lockfile PID if present
    if [[ -f "$LOCKFILE" ]]; then
        kill "$(cat "$LOCKFILE")" 2>/dev/null || true
        rm -f "$LOCKFILE"
    fi
    # Sweep for any remaining python processes running mimi's main.py or camera_app.py
    pkill -9 -f "mimi-assistant.*main\.py" 2>/dev/null || true
    pkill -9 -f "mimi-assistant.*camera_app\.py" 2>/dev/null || true
    pkill -9 -f "Cellar/mimi-assistant" 2>/dev/null || true
}

_progress_stamp() { date +%s; }

_print_milestone() {
    local icon="$1" msg="$2" start="$3"
    local now elapsed
    now=$(_progress_stamp)
    elapsed=$(( now - start ))
    printf '  %s  %-42s %s\n' "$icon" "$msg" "${elapsed}s"
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

    local start_ts
    start_ts=$(_progress_stamp)

    printf '\n'
    printf '  %-48s\n' "Starting MiMi Assistant..."
    printf '  %s\n' "──────────────────────────────────────────────────"

    # ── Milestone flags ───────────────────────────────────────────────────
    local m_oww_loading=false m_models_dl=false m_oww_loaded=false
    local m_mic_start=false m_mic_ok=false m_mimi_running=false
    local m_cam_loading=false m_cam_ready=false m_ready=false

    local timeout=120 elapsed=0

    while [[ $elapsed -lt $timeout ]]; do
        if [[ -f "$LOG_OUT" ]]; then

            if ! $m_oww_loading && grep -q "Loading openWakeWord models" "$LOG_OUT" 2>/dev/null; then
                m_oww_loading=true
                _print_milestone "⏳" "Loading wake-word models..." "$start_ts"
            fi

            if ! $m_models_dl && grep -q "Models may already exist\|download_models" "$LOG_OUT" 2>/dev/null; then
                m_models_dl=true
                _print_milestone "✅" "Wake-word models check done" "$start_ts"
            fi

            if ! $m_oww_loaded && grep -q "openWakeWord loaded" "$LOG_OUT" 2>/dev/null; then
                m_oww_loaded=true
                _print_milestone "✅" "Wake-word model loaded" "$start_ts"
            fi

            if ! $m_mic_start && grep -q "Microphone test\b\|Testing microphone" "$LOG_OUT" 2>/dev/null; then
                m_mic_start=true
                _print_milestone "⏳" "Testing microphone..." "$start_ts"
            fi

            if ! $m_mic_ok && grep -q "Microphone test successful" "$LOG_OUT" 2>/dev/null; then
                m_mic_ok=true
                _print_milestone "✅" "Microphone OK" "$start_ts"
            fi

            if ! $m_mimi_running && grep -q "MiMi Assistant is running" "$LOG_OUT" 2>/dev/null; then
                m_mimi_running=true
                _print_milestone "⏳" "Pre-warming gesture model (TFLite)..." "$start_ts"
            fi

            if ! $m_cam_loading && grep -q "\[camera\] Loading gesture model" "$LOG_OUT" 2>/dev/null; then
                m_cam_loading=true
                _print_milestone "⏳" "Loading TFLite gesture model..." "$start_ts"
            fi

            if ! $m_cam_ready && grep -q "\[camera\] Camera ready" "$LOG_OUT" 2>/dev/null; then
                m_cam_ready=true
                _print_milestone "✅" "Gesture model ready" "$start_ts"
                m_ready=true
                break
            fi
        fi

        if ! is_running; then
            break
        fi

        sleep 1
        elapsed=$(( elapsed + 1 ))
    done

    local total_s=$(( $(_progress_stamp) - start_ts ))
    printf '  %s\n' "──────────────────────────────────────────────────"

    if $m_ready; then
        printf '  \033[0;32m%-48s %s\033[0m\n' "Ready! Say 'Hey Mycroft' to activate." "${total_s}s total"
    elif is_running; then
        yellow "  Running but slow — check: mimi-ctl logs"
    else
        red "  Failed to start — check: mimi-ctl logs"
        if [[ -s "$LOG_ERR" ]]; then
            echo ""
            dim "  Last error:"
            tail -n 5 "$LOG_ERR" | while IFS= read -r line; do dim "    $line"; done
        fi
    fi
    printf '\n'
}

cmd_stop() {
    kill_all
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

    kill_all

    dim "  Uninstalling current version..."
    brew uninstall --force mimi-assistant 2>/dev/null || true

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

    kill_all

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
