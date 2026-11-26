#!/usr/bin/env bash
# DAY 3 classroom: historical G07 evidence cards only. NEVER launches ROS/Gazebo/Goal.
set -Eeuo pipefail
umask 077
readonly REPO='https://github.com/silverbjin/axia-robot-safety-student.git'
readonly BRANCH='feat/day02-g07-scenario-demo-20261126'
readonly PIN='f43df3132c8c1dac29f7c980274cd85bcdda02fc'
readonly RUNNER_BLOB='7c40f7a51b1ff6504be7bd4f16acbead185ebf55'
readonly DATA_BLOB='4a6212555ba58d93e06a165477ad1f973dc8992d'
CACHE="${AXIA_DAY3_SCENARIO_CACHE_DIR:-$HOME/axia_day3_scenario_history_pinned}"
MODE="${1:---doctor}"
if (( $# > 0 ));then shift;fi
case "$MODE" in
  --doctor|--success|--failed|--compare) ;;
  *) echo 'DAY3_SCENARIO_USAGE=--doctor|--success|--failed|--compare [--json-out NEW_PATH]' >&2;exit 2;;
esac
for exe in git python3;do
  command -v "$exe" >/dev/null || { echo "DAY3_SCENARIO_MISSING=$exe" >&2;exit 2; }
done
bash -n "${BASH_SOURCE[0]}"
if [[ "$MODE" == --doctor ]];then
  (( $# == 0 )) || { echo DAY3_SCENARIO_DOCTOR_BAD_ARGUMENTS >&2;exit 2; }
  echo 'DAY3_SCENARIO_DOCTOR_L0_PASS NO_NETWORK_NO_ROS_NO_GAZEBO_NO_GOAL'
  echo "DAY3_SCENARIO_PIN=$PIN"
  exit 0
fi
JSON_ARGS=()
if (( $# == 2 )) && [[ "$1" == --json-out && -n "$2" ]];then
  JSON_ARGS=(--json-out "$2")
elif (( $# != 0 ));then
  echo 'DAY3_SCENARIO_BAD_ARGUMENTS' >&2
  exit 2
fi
[[ -n "$CACHE" && "$CACHE" != / ]] || { echo 'DAY3_SCENARIO_BAD_CACHE_PATH' >&2;exit 2; }
if [[ ! -e "$CACHE" ]];then
  # A single pinned upstream checkout; never overwrite an existing directory.
  git clone --quiet --depth 1 --single-branch --branch "$BRANCH" -- "$REPO" "$CACHE" || {
    echo 'DAY3_SCENARIO_CLONE_FAILED_HOLD' >&2;exit 3;
  }
fi
[[ -d "$CACHE/.git" ]] || { echo 'DAY3_SCENARIO_CACHE_NOT_GIT_HOLD' >&2;exit 3; }
ACTUAL="$(git -C "$CACHE" rev-parse HEAD)" || exit 3
ORIGIN="$(git -C "$CACHE" remote get-url origin)" || exit 3
[[ "$ACTUAL" == "$PIN" && "$ORIGIN" == "$REPO" ]] || {
  echo "DAY3_SCENARIO_SHA_OR_ORIGIN_DRIFT_HOLD actual=$ACTUAL" >&2;exit 3;
}
[[ -z "$(git -C "$CACHE" status --porcelain --untracked-files=all)" ]] || {
  echo 'DAY3_SCENARIO_CACHE_DIRTY_HOLD' >&2;exit 3;
}
RUNNER="$CACHE/special_lecture/day02/scripts/g07_scenario_replay.py"
DATA="$CACHE/special_lecture/day02/scenarios/PROVEN_G07_SCENARIO_SNAPSHOT_20261122.json"
[[ -f "$RUNNER" && -f "$DATA" ]] || { echo 'DAY3_SCENARIO_SOURCE_MISSING_HOLD' >&2;exit 3; }
[[ "$(git -C "$CACHE" hash-object "$RUNNER")" == "$RUNNER_BLOB"
   && "$(git -C "$CACHE" hash-object "$DATA")" == "$DATA_BLOB" ]] || {
  echo 'DAY3_SCENARIO_SOURCE_BLOB_DRIFT_HOLD' >&2;exit 3;
}
CASE="${MODE#--}"
echo "DAY3_SCENARIO_UPSTREAM_PIN_OK=$ACTUAL case=$CASE"
echo 'DAY3_SCENARIO_SCOPE=HISTORIC_EVIDENCE_REPLAY_L0_ONLY NEW_L2_L3=NOT_RUN'
python3 "$RUNNER" --case "$CASE" "${JSON_ARGS[@]}"
