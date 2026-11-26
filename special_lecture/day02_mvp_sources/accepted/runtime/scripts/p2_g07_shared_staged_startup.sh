#!/usr/bin/env bash
# Exact same G07 staged Nav2 readiness launcher on PUBLIC CI and WSL2 Owner.
# Only the surrounding ROS/Gazebo display backend differs (WSLg vs offscreen).
# NO Goal, NO Crash, NO E-Stop. Always preserve the gate-specific first failure.
set -Eeuo pipefail
[[ $# == 2 && -n "$1" && -n "$2" ]] || {
  echo 'G07_SHARED_STARTUP_BLOCKED: expected verdict and initialpose output' >&2
  exit 2
}
[[ "${AXIA_P0_SIM_ONLY:-0}" == 1
  && "${ROS_DISTRO:-}" == jazzy
  && "${GZ_PARTITION:-}" == axia_p2_* ]] || {
  echo 'G07_SHARED_STARTUP_BLOCKED: ROS Jazzy isolated simulation only' >&2
  exit 2
}
echo 'AXIA_G07_SHARED_STAGED_RUNNER_BEGIN NO_GOAL'
timeout --signal=TERM --kill-after=10s 480s   python3 tools/p2_staged_no_goal.py     --output "$1" --initialpose-output "$2" --allow-sim-initialpose
echo 'AXIA_G07_SHARED_STAGED_RUNNER_READY NO_GOAL'
