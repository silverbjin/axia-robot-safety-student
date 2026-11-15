#!/usr/bin/env bash
# Student Block C one-shot: education only, never invokes Nav2/Goal/cmd_vel.
set -Eeuo pipefail
MODE="${1:---doctor}"
[[ $# -eq 1 ]] || { echo BLOCK_C_USAGE_ERROR >&2; exit 2; }
case "$MODE" in --doctor|--unit|--ros-l1|--all) ;; *) echo BLOCK_C_USAGE_ERROR >&2; exit 2 ;; esac
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT="${AXIA_BLOCK_C_EVIDENCE_DIR:-${HOME:-/tmp}/axia_block_c_evidence/$(date -u +%Y%m%dT%H%M%SZ)-$$}"
export PYTHONDONTWRITEBYTECODE=1
function doctor() {
    command -v python3 >/dev/null || { echo BLOCK_C_ENV_BLOCKED_NO_PYTHON >&2; return 2; }
    PYVER="$(python3 -c 'import sys;print(".".join(map(str,sys.version_info[:3])))')"
    python3 - <<'PY'
import sys
raise SystemExit(0 if sys.version_info[:2] == (3,12) else 2)
PY
    [[ $? -eq 0 ]] || { echo "BLOCK_C_ENV_DIFF_BLOCKED expected=3.12 actual=$PYVER" >&2; return 2; }
    echo "BLOCK_C_STUDENT_DOCTOR python=$PYVER role=student ros_required_for_unit=false gazebo_required=false"
    echo "BLOCK_C_NO_GOAL_NO_CMD_VEL_NO_CERTIFIED_ESTOP"
}
function unit() {
    doctor
    mkdir -p "$REPORT"
    python3 "$ROOT/fixtures/generator.py" --check --fixture-dir "$ROOT/fixtures" >"$REPORT/fixture.log" 2>&1
    PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q "$ROOT/tests/test_block_c_scaffold_contract.py" --junitxml="$REPORT/pytest.xml" >"$REPORT/pytest.log" 2>&1
    cat "$REPORT/fixture.log" "$REPORT/pytest.log"
    echo "BLOCK_C_STUDENT_SCAFFOLD_PUBLIC_L0_PASS evidence=$REPORT todo_completed=false"
}
function rosl1() {
    doctor
    [[ -f /opt/ros/jazzy/setup.bash ]] || { echo BLOCK_C_ROS_L1_BLOCKED_JAZZY_NOT_INSTALLED >&2; return 2; }
    mkdir -p "$REPORT"
    set +u
    # ROS setup reads optional AMENT_* variables; no global cleanup or cmd_vel.
    source /opt/ros/jazzy/setup.bash
    set -u
    export PYTHONPATH="$ROOT/day12/ros_transport${PYTHONPATH:+:$PYTHONPATH}"
    python3 "$ROOT/day12/ros_transport/ros_l1_probe.py" --events "$ROOT/day12/ros_transport/sample_events.jsonl" --out "$REPORT/ros_l1" --messages 8
    echo "BLOCK_C_STUDENT_JAZZY_ROS_L1_ONLY_PASS owner_wsl2_verified=false"
}
case "$MODE" in --doctor) doctor;; --unit) unit;; --ros-l1) rosl1;; --all) unit;rosl1;; esac
