#!/usr/bin/env bash
# Toggle between Aware and Quiet mode, optionally pausing/resuming music.
#
# Usage: toggle-aware.sh [pause]
#
#   pause   Also control playback via playerctl: pause music when switching
#           to Aware, resume it when switching back to Quiet.
#
# Environment:
#   PLAYER               playerctl player to control (default: spotify)
#   BMAP_CONNECTED_ONLY  set to 1 to fail at once if the headphones are not
#                        connected (used by scripts that try several headsets)
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

# One connection: read the mode, switch, print the new mode.
mode="$("${bosectl[@]}" toggle aware quiet)"
echo "$mode"

if [[ "$control_music" == "pause" ]]; then
    case "$mode" in
        aware) playerctl --player="$player" pause || true ;;
        quiet) playerctl --player="$player" play || true ;;
    esac
fi
