#!/usr/bin/env bash
# AXIA DAY02: real ROS 2 ament_python colcon build. No ROS nodes, Gazebo or Goals.
set -Eeuo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd -P)"
MODE="--both"
OUT="$HOME/axia-day02-colcon-builds"
while (( $# ));do
  case "$1" in
    --both|--accepted|--failed|--verify|--doctor)
      MODE="$1";shift ;;
    --out)
      (( $#>=2 )) || { echo "AXIA_DAY02_OUT_VALUE_MISSING" >&2;exit 2; }
      OUT="$2";shift 2 ;;
    *) echo "AXIA_DAY02_BAD_ARGUMENT=$1" >&2;exit 2 ;;
  esac
done
# Verify the two Git tree hashes and ensure no student edits were silently substituted.
python3 "$DIR/scripts/verify_dual_source.py"
if [[ "$MODE" == --verify ]];then
  echo "AXIA_DAY02_DUAL_SOURCE_VERIFY_L0_PASS_NO_ROS_NO_GAZEBO_NO_GOAL"
  exit 0
fi

preflight() {
  [[ -r /opt/ros/jazzy/setup.bash ]] || {
    echo "AXIA_DAY02_BUILD_HOLD=ROS_JAZZY_MISSING" >&2;return 2;
  }
  local osversion
  osversion="$(. /etc/os-release; printf '%s' "$VERSION_ID")"
  [[ "$osversion" == 24.04 ]] || {
    echo "AXIA_DAY02_BUILD_HOLD=UBUNTU_24_04_REQUIRED actual=$osversion" >&2;return 2;
  }
  for exe in git python3 colcon;do
    command -v "$exe" >/dev/null || {
      echo "AXIA_DAY02_BUILD_HOLD=MISSING_$exe" >&2;return 2;
    }
  done
  set +u
  source /opt/ros/jazzy/setup.bash
  set -u
  command -v ros2 >/dev/null || { echo "AXIA_DAY02_BUILD_HOLD=MISSING_ros2_AFTER_SOURCE" >&2;return 2; }
  [[ "$ROS_DISTRO" == jazzy ]] || {
    echo "AXIA_DAY02_BUILD_HOLD=ROS_DISTRO_NOT_JAZZY" >&2;return 2;
  }
  python3 -c 'import setuptools, ament_package' || {
    echo "AXIA_DAY02_BUILD_HOLD=AMENT_PYTHON_DEPENDENCY_MISSING" >&2;return 2;
  }
  echo "AXIA_DAY02_JAZZY_COLCON_PREFLIGHT_PASS"
}
preflight
if [[ "$MODE" == --doctor ]];then
  echo "AXIA_DAY02_BUILD_DOCTOR_PASS_NO_COLCON_EXECUTED"
  exit 0
fi

# Output is always isolated. Do not delete, overwrite, or alter original sources.
[[ ! -e "$OUT" ]] || {
  echo "AXIA_DAY02_REFUSE_EXISTING_OUTPUT=$OUT" >&2;exit 3;
}
umask 077
mkdir -p "$OUT"
case "$MODE" in
  --accepted) CASES="accepted" ;;
  --failed) CASES="failed" ;;
  --both) CASES="accepted failed" ;;
  *) echo "AXIA_DAY02_INVALID_BUILD_MODE" >&2;exit 3 ;;
esac
for label in $CASES;do
  (
    set -Eeuo pipefail
    SRC="$DIR/$label/runtime"
    DEST="$OUT/$label"
    mkdir -p "$DEST/logs"
    cp -a "$SRC" "$DEST/runtime"
    cd "$DEST/runtime/ros2_ws"
    set +u
    source /opt/ros/jazzy/setup.bash
    set -u
    python3 -m compileall -q "$DEST/runtime/ros2_ws/src"
    echo "AXIA_DAY02_PYTHON_SYNTAX_PASS case=$label"
    # Actual colcon build for four ament_python packages; not a C++ compiler benchmark.
    colcon build \
      --base-paths "$DEST/runtime/ros2_ws/src" \
      --build-base "$DEST/build" \
      --install-base "$DEST/install" \
      --event-handlers console_direct+ \
      --packages-select \
        axia_fault_injector axia_safety_bringup axia_safety_supervisor axia_scenario_verifier \
      2>&1 | tee "$DEST/logs/colcon_build.log"
    set +u
    source "$DEST/install/local_setup.bash"
    set -u
    for pkg in axia_fault_injector axia_safety_bringup axia_safety_supervisor axia_scenario_verifier;do
      ros2 pkg prefix "$pkg" >/dev/null
    done
    python3 - "$DEST" "$label" <<'PY'
import json,sys
from pathlib import Path
dest=Path(sys.argv[1]);label=sys.argv[2]
result={"case":label,"colcon_build":"PASS","ament_python_packages":4,
        "new_gazebo_run":False,"new_goal_sent":False,
        "new_native_moving_l2":"NOT_RUN","new_owner_l3":"NOT_RUN"}
(dest/"BUILD_RESULT.json").write_text(json.dumps(result,indent=2)+"\n")
PY
    echo "AXIA_DAY02_COLCON_BUILD_PASS case=$label packages=4 NO_GAZEBO_NO_GOAL"
  )
done
echo "AXIA_DAY02_BOTH_SOURCE_BUILD_FINISHED cases=$CASES result_dir=$OUT"
