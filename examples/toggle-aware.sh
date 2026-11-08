#!/usr/bin/env bash
# Toggle between Aware and Quiet mode, optionally pausing/resuming music.
#
# Usage: toggle-aware.sh [pause]
#
#   pause   Also control playback via playerctl: pause music when switching
#           to Aware, resume it when switching back to Quiet.
#
# Environment:
#   PLAYER  playerctl player to control (default: spotify)
#
# Uses `bosectl` from PATH if installed, otherwise falls back to the bosectl
# script in this repository. Handy to bind to a global keyboard shortcut.
set -euo pipefail

if command -v bosectl >/dev/null 2>&1; then
    bosectl=(bosectl)
else
    repo_dir="$(cd "$(dirname "$(realpath "${BASH_SOURCE[0]}")")/.." && pwd)"
    if [[ ! -f "$repo_dir/bosectl" ]]; then
        echo "error: bosectl not found on PATH or in $repo_dir" >&2
        exit 1
    fi
    bosectl=(python3 "$repo_dir/bosectl")
fi

control_music="${1:-}"
player="${PLAYER:-spotify}"

music() {
    if [[ "$control_music" == "pause" ]]; then
        playerctl --player="$player" "$1" || true
    fi
}

if [[ "$("${bosectl[@]}" current)" == "aware" ]]; then
    music play
    "${bosectl[@]}" quiet
else
    music pause
    "${bosectl[@]}" aware
fi
