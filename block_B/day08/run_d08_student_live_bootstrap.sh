#!/usr/bin/env bash
# AXIA D08 WSL2 single-entry bootstrap: NO outer ROS source under set -u.
# Preserve student's existing checkout, .venv, caches, logs, local edits.
set -Eeuo pipefail
umask 077

MODE="${1:---run}"
case "$MODE" in
  --self-check|--doctor|--run) ;;
  *) echo "D08_STUDENT_BOOTSTRAP_USAGE=--self-check|--doctor|--run" >&2; exit 2 ;;
esac
[[ "$#" -le 1 ]] || { echo "D08_STUDENT_BOOTSTRAP_INVALID_ARGUMENTS" >&2; exit 2; }

BRANCH="feat/d08-live-gazebo-rviz-no-goal-20261115"
REPO_URL="https://github.com/silverbjin/axia-robot-safety-student.git"
DIR="${AXIA_D08_DEMO_DIR:-$HOME/axia_d08_student_live}"
LAUNCH_REL="block_B/day08/run_d08_student_live_once.sh"

if [[ "$MODE" == --self-check ]]; then
  bash -n "${BASH_SOURCE[0]}"
  echo "D08_STUDENT_BOOTSTRAP_STATIC_PASS ROS_NOT_SOURCED GAZEBO_NOT_RUN RVIZ_NOT_RUN NO_GOAL"
  exit 0
fi

# Never source /opt/ros/jazzy/setup.bash in this outer shell.
# The exact same inner runner used by public L2 handles ROS setup with
# set +u/source/set -u, shielding ROS-generated AMENT_TRACE_SETUP_FILES.
if [[ ! -e "$DIR" ]]; then
  git clone --single-branch --branch "$BRANCH" "$REPO_URL" "$DIR"
elif [[ -d "$DIR" ]] && git -C "$DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  CURRENT="$(git -C "$DIR" branch --show-current)"
  if [[ "$CURRENT" != "$BRANCH" ]]; then
    echo "D08_STUDENT_EXISTING_BRANCH_PRESERVED current=$CURRENT expected=$BRANCH" >&2
    exit 2
  fi
  if [[ -n "$(git -C "$DIR" status --porcelain --untracked-files=no)" ]]; then
    echo "D08_STUDENT_LOCAL_CHANGES_PRESERVED: commit or stash manually; no reset" >&2
    exit 2
  fi
  ORIGIN="$(git -C "$DIR" remote get-url origin)"
  if [[ "$ORIGIN" != "$REPO_URL" &&
        "$ORIGIN" != "https://github.com/silverbjin/axia-robot-safety-student" ]]; then
    echo "D08_STUDENT_UNEXPECTED_ORIGIN=$ORIGIN" >&2
    exit 2
  fi
  git -C "$DIR" fetch --no-tags origin "$BRANCH"
  git -C "$DIR" merge --ff-only FETCH_HEAD
else
  echo "D08_STUDENT_DIRECTORY_NOT_GIT_PRESERVED=$DIR" >&2
  exit 2
fi

[[ -s "$DIR/$LAUNCH_REL" ]] || {
  echo "D08_STUDENT_LIVE_RUNNER_MISSING=$DIR/$LAUNCH_REL" >&2; exit 2;
}
echo "D08_STUDENT_RELEASE_SOURCE_SHA=$(git -C "$DIR" rev-parse HEAD)"
bash "$DIR/$LAUNCH_REL" --self-check

if [[ "$MODE" == --doctor ]]; then
  exec bash "$DIR/$LAUNCH_REL" --doctor
fi

# rviz2 is mandatory for D08, unlike optional D04/D05. Provision only
# the missing official RViz package; do not alter ROS, Nav2, private sources.
if ! command -v rviz2 >/dev/null 2>&1; then
  if [[ -r /opt/ros/jazzy/setup.bash ]]; then
    echo "D08_RVIZ2_OFFICIAL_PACKAGE_CHECK: runner will source ROS safely"
    # Basic binary path check, avoiding an outer 'source'.
    if [[ ! -x /opt/ros/jazzy/bin/rviz2 ]]; then
      command -v sudo >/dev/null || { echo "D08_SUDO_MISSING" >&2; exit 2; }
      sudo apt-get update
      sudo DEBIAN_FRONTEND=noninteractive apt-get install -y ros-jazzy-rviz2
    fi
  fi
fi

# Public CI calls this script too, then the identical D04/D05 ROS launcher.
# AXIA_D08_HOLD_S=300 means GUI stays available without repeated logs.
exec bash "$DIR/$LAUNCH_REL" --run
