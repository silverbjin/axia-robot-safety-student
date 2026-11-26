#!/usr/bin/env bash
# PRIVATE Instructor H01: real physics, no-moving-Goal Gazebo + RViz2
set -Eeuo pipefail
umask 077
MODE="${1:---run}"
case "$MODE" in --self-check|--doctor|--run) ;; *)
  echo 'D07_H01_GUI_USAGE=--self-check|--doctor|--run' >&2;exit 2;;
esac
[[ $# -le 1 ]] || { echo D07_H01_GUI_TOO_MANY_ARGS >&2;exit 2; }
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SMOKE="$ROOT/scripts/p2_no_goal_smoke_ci.sh"
RVIZ="$ROOT/training/block_B/instructor/rviz/d07_h01_physical_replan.rviz"
GEOMETRY="$ROOT/tools/d07_h01_geometry_l2.py"
for file in "$SMOKE" "$RVIZ" "$GEOMETRY";do
  [[ -s "$file" ]] || { echo "D07_H01_GUI_SOURCE_MISSING=$file" >&2;exit 2; }
done
bash -n "$SMOKE"
bash -n "${BASH_SOURCE[0]}"
grep -Fq 'Fixed Frame: map' "$RVIZ"
grep -Fq '/axia/d07/h01/path_visual' "$RVIZ"
grep -Fq 'AXIA_D07_H01_GUI_NO_GOAL' "$SMOKE"
if [[ "$MODE" == --self-check ]];then
  echo 'D07_H01_GUI_STATIC_NO_GOAL_PASS GAZEBO_NOT_RUN RVIZ_NOT_RUN'
  echo 'D07_H01_GUI_SOURCE_PINNED_AND_NO_GOAL_STATIC_ONLY'
  exit 0
fi
[[ -r /opt/ros/jazzy/setup.bash ]] || { echo D07_GUI_JAZZY_MISSING >&2;exit 2; }
set +u
source /opt/ros/jazzy/setup.bash
set -u
for exe in ros2 gz rviz2 colcon setsid git python3 timeout;do
  command -v "$exe" >/dev/null || {
    echo "D07_GUI_MISSING_EXECUTABLE=$exe" >&2;exit 2;
  }
done
for pkg in nav2_bringup nav2_minimal_tb3_sim ros_gz_sim;do
  ros2 pkg prefix "$pkg" >/dev/null || {
    echo "D07_GUI_MISSING_OFFICIAL_PACKAGE=$pkg" >&2;exit 2;
  }
done
SHA="$(git -C "$ROOT" rev-parse HEAD)"
[[ "$SHA" =~ ^[0-9a-f]{40}$ ]] || { echo D07_GUI_SHA_INVALID >&2;exit 2; }
[[ -z "$(git -C "$ROOT" status --porcelain --untracked-files=no)" ]] || {
  echo D07_GUI_TREE_DIRTY >&2;exit 2;
}
if [[ "$MODE" == --doctor ]];then
  echo "D07_H01_GUI_DOCTOR_PASS_NO_ROS_NODES SHA=$SHA"
  exit 0
fi
[[ -n "${DISPLAY:-}" ]] || { echo D07_GUI_DISPLAY_MISSING >&2;exit 2; }
if [[ "${GITHUB_ACTIONS:-}" != true ]];then
  grep -qiE 'microsoft|wsl' /proc/sys/kernel/osrelease || {
    echo D07_GUI_OWNER_WSL2_REQUIRED >&2;exit 2;
  }
fi
# User GUI never borrows public CI moving-Goal permission.
for flag in AXIA_G07_CI_SIM_GOAL_ALLOWED AXIA_P3_S01_CI_GOAL_ALLOWED \
            AXIA_P3_S03_CI_COMPOUND_ALLOWED AXIA_P3_S04_CI_PNU_ALLOWED \
            AXIA_P3_S05_CI_GOAL_ALLOWED;do
  [[ "${!flag:-0}" != 1 ]] || {
    echo "D07_GUI_MOVING_OR_FAULT_FLAG_DENIED=$flag" >&2;exit 2;
  }
done
HOLD="${AXIA_D07_GUI_HOLD_S:-10}"
[[ "$HOLD" =~ ^[0-9]+$ && "$HOLD" -ge 5 && "$HOLD" -le 15 ]] || {
  echo D07_GUI_HOLD_INVALID >&2;exit 2;
}
export AXIA_D07_GUI_HOLD_S="$HOLD"
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-57}"
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export GZ_PARTITION="${GZ_PARTITION:-axia_p2_d07_gui_${ROS_DOMAIN_ID}_$$_$(date +%s)}"
[[ "$GZ_PARTITION" == axia_p2_* ]] || {
  echo D07_GUI_GZ_PARTITION_INVALID >&2;exit 2;
}
export AXIA_D07_H01_GUI_NO_GOAL=1
export AXIA_P2_G07_PHYSICAL_PREFLIGHT=1
export AXIA_G07_OWNER_STARTUP_PARITY=1
export AXIA_P0_SIM_ONLY=1
export AXIA_G07_CI_SIM_GOAL_ALLOWED=0
export AXIA_G07_CI_OWNER_BAG_PARITY=0
export AXIA_D07_H01_GEOMETRY_ONLY=0
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
OUT="${AXIA_D07_GUI_EVIDENCE_DIR:-$HOME/axia_d07_gui_research}"
mkdir -p "$OUT";chmod 700 "$OUT"
# The same smoke process is the single owner of Gazebo, Gazebo -g and
# read-only RViz2; its cleanup trap terminates only its process groups.
echo "D07_H01_GUI_SHA=$SHA GZ_PARTITION=$GZ_PARTITION ROS_DOMAIN_ID=$ROS_DOMAIN_ID"
echo 'D07_H01_GUI_NO_GOAL: Ctrl+C closes only this run-owned simulation and GUI'
bash "$SMOKE"
