#!/usr/bin/env bash
# D07 exact-commit student bootstrap: one WSL2 command, no private repository.
# Does NOT source ROS in outer shell (protects AMENT_TRACE_SETUP_FILES).
# Does NOT overwrite an existing student's D07 worktree or local changes.
set -Eeuo pipefail
umask 077

MODE="${1:---run}"
case "$MODE" in
  --self-check|--doctor|--run) ;;
  *) echo "D07_BOOTSTRAP_USAGE=--self-check|--doctor|--run" >&2;exit 2 ;;
esac
[[ "$#" -le 1 ]] || { echo "D07_BOOTSTRAP_TOO_MANY_ARGS" >&2;exit 2; }
if [[ "$MODE" == '--self-check' ]];then
  bash -n "${BASH_SOURCE[0]}"
  echo "D07_BOOTSTRAP_STATIC_PASS GAZEBO_NOT_RUN RVIZ_NOT_RUN NO_GOAL"
  exit 0
fi

SOURCE_SHA="${AXIA_D07_PUBLIC_SHA:-}"
[[ "$SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]] || {
  echo "D07_SOURCE_SHA_REQUIRED: pin a publicly CI-verified commit" >&2
  exit 2
}
REPO_URL='https://github.com/silverbjin/axia-robot-safety-student.git'
DIR="${AXIA_D07_DEMO_DIR:-$HOME/axia_d07_live_demo}"
LAUNCH_REL='block_B/day07/run_d07_student_gazebo_rviz_once.sh'
command -v git >/dev/null || { echo 'D07_GIT_MISSING' >&2; exit 2; }

if [[ ! -e "$DIR" ]];then
  mkdir -p "$DIR"
  git -C "$DIR" init -q
  git -C "$DIR" remote add origin "$REPO_URL"
  git -C "$DIR" fetch -q --no-tags --depth 1 origin "$SOURCE_SHA"
  git -C "$DIR" checkout --detach -q FETCH_HEAD
elif [[ -d "$DIR/.git" ]];then
  ORIGIN="$(git -C "$DIR" remote get-url origin)"
  [[ "$ORIGIN" == "$REPO_URL" ]] || {
    echo "D07_ORIGIN_MISMATCH: existing work preserved" >&2;exit 2;
  }
  [[ -z "$(git -C "$DIR" status --porcelain)" ]] || {
    echo "D07_LOCAL_CHANGES_PRESERVED: commit/stash manually, no reset" >&2
    exit 2
  }
else
  echo "D07_DEMO_DIR_OCCUPIED: existing work preserved" >&2;exit 2
fi
HEAD="$(git -C "$DIR" rev-parse HEAD 2>/dev/null || true)"
[[ "$HEAD" == "$SOURCE_SHA" ]] || {
  echo "D07_SOURCE_SHA_MISMATCH expected=$SOURCE_SHA actual=$HEAD" >&2
  exit 2
}
RUNNER="$DIR/$LAUNCH_REL"
[[ -s "$RUNNER" ]] || {
  echo "D07_RUNNER_MISSING_IN_PINNED_SOURCE=$RUNNER" >&2;exit 2
}
echo "D07_STUDENT_SOURCE_SHA=$HEAD"
bash -n "$RUNNER"
bash "$RUNNER" --self-check

if [[ "$MODE" == '--doctor' ]];then
  exec bash "$RUNNER" --doctor
fi
echo "D07_STUDENT_NO_GOAL: live Gazebo/RViz sensor-only, H01 actual physical Planner not connected"
exec bash "$RUNNER" --run
