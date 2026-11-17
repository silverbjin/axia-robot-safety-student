#!/usr/bin/env bash
# D07 H01 STUDENT: ACTUAL public Harmonic physical Waffle and native obstacle
# -> LaserScan -> official Nav2 Costmap -> ComputePathToPose -> RViz2 Path.
# No NavigateToPose, no cmd_vel, no fault injection, no certified E-Stop.
# Reuses pinned Instructor-validated runtime, now published with explicit
# instructor permission in student public h01_runtime. No private login.
set -Eeuo pipefail
umask 077
MODE="${1:---run}"
[[ $# -le 1 ]] || { echo D07_H01_STUDENT_UNKNOWN_ARGS_NO_GOAL >&2;exit 2; }
case "$MODE" in --self-check|--doctor|--run) ;; *)
  echo D07_H01_STUDENT_USAGE=--self-check\|--doctor\|--run >&2;exit 2;; esac

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
RUNTIME="$HERE/h01_runtime"
# GitHub container checkout can be owned by a different UID. The original
# H01 runner does several git -C subdirectory source checks. Trust only this
# exact checkout for this ONE process tree, never mutate user's ~/.gitconfig.
REPO_ROOT="$(cd "$HERE/../.." && pwd -P)"
export GIT_CONFIG_COUNT=1
export GIT_CONFIG_KEY_0=safe.directory
export GIT_CONFIG_VALUE_0="$REPO_ROOT"
STUDENT_SOURCE_SHA="$(git -C "$REPO_ROOT" rev-parse HEAD)" || {
  echo D07_H01_STUDENT_GIT_SOURCE_PIN_BLOCKED_NO_GOAL >&2;exit 3;
}
[[ "$STUDENT_SOURCE_SHA" =~ ^[a-f0-9]{40}$ ]] || {
  echo D07_H01_STUDENT_GIT_SOURCE_SHA_INVALID_NO_GOAL >&2;exit 3;
}
SOURCE="$RUNTIME/scripts/d07_h01_gui_no_goal_once.sh"
SMOKE="$RUNTIME/scripts/p2_no_goal_smoke_ci.sh"
RVIZ="$RUNTIME/training/block_B/instructor/rviz/d07_h01_physical_replan.rviz"
[[ -s "$SOURCE" && -s "$SMOKE" && -s "$RVIZ" ]] || {
  echo D07_H01_STUDENT_PUBLIC_RUNTIME_MISSING_NO_GOAL >&2;exit 2;
}
bash -n "${BASH_SOURCE[0]}"
bash -n "$SOURCE"
bash -n "$SMOKE"
if [[ "$MODE" == --self-check ]]; then
  bash "$SOURCE" --self-check
  grep -Fq '/axia/d07/h01/path_visual' "$RVIZ"
  test ! -e "$RUNTIME/training/block_B/instructor/d07_route_reference.py"
  test ! -e "$RUNTIME/training/block_B/instructor/hidden_tests"
  echo 'D07_H01_STUDENT_PUBLIC_PHYSICAL_STATIC_PASS GAZEBO_NOT_RUN RVIZ_NOT_RUN NO_GOAL'
  exit 0
fi

# Source Jazzy with nounset OFF; do not rely on a pre-sourced user shell.
[[ -r /opt/ros/jazzy/setup.bash ]] || {
  echo D07_H01_STUDENT_MISSING_JAZZY_NO_GOAL >&2;exit 2;
}
set +u
source /opt/ros/jazzy/setup.bash
set -u
[[ "${ROS_DISTRO:-}" == jazzy ]] || {
  echo D07_H01_STUDENT_WRONG_ROS_DISTRO_NO_GOAL >&2;exit 2;
}
for bin in ros2 gz colcon rviz2 xacro python3 git setsid timeout;do
  command -v "$bin" >/dev/null || {
    echo "D07_H01_STUDENT_MISSING_TOOL=$bin NO_GOAL" >&2;exit 2;
  }
done
for pkg in nav2_bringup nav2_minimal_tb3_sim nav2_planner ros_gz_sim rqt_graph;do
  ros2 pkg prefix "$pkg" >/dev/null 2>&1 || {
    echo "D07_H01_STUDENT_MISSING_OFFICIAL_PACKAGE=$pkg NO_GOAL" >&2;exit 2;
  }
done
if [[ "$MODE" == --doctor ]]; then
  echo 'D07_H01_STUDENT_DOCTOR_READY OFFICIAL_JAZZY_NAV2_HARMONIC_RVIZ2_GAZEBO_NOT_RUN_NO_GOAL'
  exit 0
fi
[[ -n "${DISPLAY:-}" ]] || {
  echo D07_H01_STUDENT_WSLG_DISPLAY_MISSING_NO_GOAL >&2;exit 2;
}
# The CI can use Xvfb, the student path must be real WSL2/WSLg.
if [[ "${GITHUB_ACTIONS:-}" != true ]];then
  grep -qiE 'microsoft|wsl' /proc/sys/kernel/osrelease || {
    echo D07_H01_STUDENT_WSL2_REQUIRED_NO_GOAL >&2;exit 2;
  }
fi
for flag in AXIA_G07_CI_SIM_GOAL_ALLOWED AXIA_P3_S01_CI_GOAL_ALLOWED \
            AXIA_P3_S03_CI_COMPOUND_ALLOWED AXIA_P3_S04_CI_PNU_ALLOWED \
            AXIA_P3_S05_CI_GOAL_ALLOWED;do
  [[ "${!flag:-0}" != 1 ]] || {
    echo "D07_H01_STUDENT_MOVING_FLAG_DENIED=$flag NO_GOAL" >&2;exit 3;
  }
done
export AXIA_G07_CI_SIM_GOAL_ALLOWED=0
export AXIA_P0_SIM_ONLY=1
export AXIA_D07_H01_GUI_NO_GOAL=1
# Classroom default: keep the live Gazebo/Nav2/RViz nodes after original
# 3-stage proof, repeat physical object positions until Ctrl+C.
export AXIA_D07_H01_TEACHING_LOOP=1
if [[ "${GITHUB_ACTIONS:-}" == true ]]; then
  [[ "${AXIA_D07_H01_TEACHING_MAX_CYCLES:-}" == 1 ]] || {
    echo D07_H01_TEACHING_CI_MUST_BOUND_ONE_CYCLE_NO_GOAL >&2; exit 3;
  }
else
  [[ "${AXIA_D07_H01_TEACHING_MAX_CYCLES:-0}" == 0 ]] || {
    echo D07_H01_TEACHING_WSL2_AUTOSTOP_DENIED_CTRL_C_ONLY >&2; exit 3;
  }
fi
export AXIA_D07_H01_GPU_GUI_TRIAL=1
export AXIA_D07_H01_GEOMETRY_ONLY=0
export AXIA_P2_G07_PHYSICAL_PREFLIGHT=1
export AXIA_G07_OWNER_STARTUP_PARITY=1
export AXIA_G07_CI_OWNER_BAG_PARITY=0
export AXIA_D07_GUI_HOLD_S="${AXIA_D07_STUDENT_PHASE_HOLD_S:-10}"
export ROS_DOMAIN_ID="${AXIA_D07_STUDENT_DOMAIN_ID:-95}"
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export GZ_PARTITION="${GZ_PARTITION:-axia_p2_d07_student_${ROS_DOMAIN_ID}_$$_$(date +%s)}"
[[ "$ROS_DOMAIN_ID" =~ ^[0-9]{1,3}$ &&
   "$ROS_DOMAIN_ID" -le 232 && "$GZ_PARTITION" == axia_p2_* ]] || {
  echo D07_H01_STUDENT_DOMAIN_OR_PARTITION_INVALID_NO_GOAL >&2;exit 3;
}
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
# No fake success marker; exact same launch/geometry subprocess must pass.
if [[ -n "${AXIA_D07_STUDENT_LIVE_EVIDENCE:-}" ]];then
  OUT="${AXIA_D07_STUDENT_LIVE_EVIDENCE}"
  [[ ! -L "$OUT" && ! -e "$OUT/evidence" ]] || {
    echo D07_H01_STUDENT_EVIDENCE_EXISTS_NO_OVERWRITE >&2;exit 3;
  }
  mkdir -p "$OUT"
else
  mkdir -p "$HOME/axia_d07_h01_student_evidence"
  OUT="$(mktemp -d "$HOME/axia_d07_h01_student_evidence/session-XXXXXXXX")"
fi
OUT="$(cd "$OUT" && pwd -P)"
chmod 700 "$OUT"
export AXIA_P2_SMOKE_RESULTS="$OUT/evidence"
export AXIA_D07_GUI_EVIDENCE_DIR="$OUT"
printf 'student_source_sha=%s\norigin_instructor_scope=%s\n' \
  "$STUDENT_SOURCE_SHA" \
  'H01_STATIONARY_PHYSICAL_GAZEBO_READONLY_NO_GOAL' > "$OUT/source.txt"
echo "D07_H01_STUDENT_GAZEBO_RVIZ_L2_BEGIN source=$STUDENT_SOURCE_SHA"
echo "D07_H01_STUDENT_EVIDENCE=$OUT"
echo 'D07_H01_STUDENT_SCOPE NO_GOAL NO_CMD_VEL NO_ESTOP_NO_MOTION'
# Smoke owns its own Gazebo/Nav2/RViz child groups; exit code is retained.
set +e
( cd "$RUNTIME" && bash scripts/d07_h01_gui_no_goal_once.sh --run ) \
  > "$OUT/student_live_stdout.log" 2>&1
RUN_RC=$?
set -e
tail -n 65 "$OUT/student_live_stdout.log" || true
if [[ "$RUN_RC" -ne 0 ]]; then
  echo "D07_H01_STUDENT_GAZEBO_RVIZ_L2_BLOCKED stage=RUNTIME rc=$RUN_RC"
  echo AXIA_MVP_DEMO_ACCEPTED=HOLD
  exit "$RUN_RC"
fi
python3 - "$OUT/evidence/d07_h01_geometry/d07_h01_geometry.json" \
           "$OUT/evidence/d07_h01_geometry/phase_evidence.jsonl" <<'PY'
import json,sys
from pathlib import Path
j=json.loads(Path(sys.argv[1]).read_text())
rows=[json.loads(s) for s in Path(sys.argv[2]).read_text().splitlines() if s.strip()]
assert j["goal_sent"] is False
assert j["real_nav2"] is True and j["real_laser_scan"] is True
assert j["actual_costmap_obstacle_observed"] is True
assert j["obstacle_restored_away"] is True
assert j["certified_estop"] is False
assert {r.get("stage") for r in rows} >= {"before","intrusion","restored"}
assert all(r.get("rviz_subscription_count",0)>=1 for r in rows)
print("D07_H01_STUDENT_PHYSICAL_SCAN_COSTMAP_PATH_RVIZ_PHASES_PASS")
PY
# Exclude only the OUTER CI redirect stdout: the parent shell is still
# appending to live_stdout.log while this child generates its manifest.
# rqt_graph.log is also written by an OUTER CI-owned X11 GUI process; it
# is not closed until CI signal+wait, AFTER this wrapper's manifest. Keep
# its raw logfile for diagnosis, but do not falsely custody an open writer.
# All CLOSED native Gazebo/Nav2/scene/raw ROS files remain SHA256-covered.
( cd "$OUT" && find . -type f ! -name SHA256SUMS ! -name live_stdout.log ! -name rqt_graph.log -print0 | sort -z | xargs -0 -r sha256sum > SHA256SUMS )
echo "D07_H01_STUDENT_GAZEBO_RVIZ_L2_PASS NO_GOAL NO_CMD_VEL SOURCE_PINNED"
echo 'D07_H01_STUDENT_WSLG_PIXELS_USER_OBSERVATION_REQUIRED'
echo 'AXIA_MVP_DEMO_ACCEPTED=HOLD'
