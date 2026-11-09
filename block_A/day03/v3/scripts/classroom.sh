#!/usr/bin/env bash
# D03 v3 student-only entrypoint. Always run as child Bash, never source in terminal.
# Simulation-only approval prompts: YES-D3-SIM / YES-D3-FAULT.
# Marker: AXIA_D3_V3_SIM_ONLY. Do not publish Goal/Reset/Rearm/cmd_vel.
set -Eeuo pipefail
HERE="$(cd "$(dirname "$0")" && pwd -P)"
exec python3 "$HERE/classroom.py" "$@"
