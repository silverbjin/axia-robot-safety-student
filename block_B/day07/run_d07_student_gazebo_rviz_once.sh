#!/usr/bin/env bash
# D07 sensor-first REAL Gazebo + read-only RViz2. Reuse existing D04/D05
# official Waffle Gazebo+YOLO launcher; NO Nav2 moving Goal or Twist.
# H01 planner overlays remain DISABLED until separate physical L2 admission.
set -Eeuo pipefail
umask 077

MODE="${1:---run}"
case "$MODE" in
  --self-check|--doctor|--run) ;;
  *) echo "D07_STUDENT_USAGE=--self-check|--doctor|--run" >&2; exit 2 ;;
esac
[[ "$#" -le 1 ]] || { echo "D07_TOO_MANY_ARGS" >&2; exit 2; }

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SOURCE="$HERE/../day04/run_student_gazebo_yolo_once.sh"
RVIZ="$HERE/live/d07_student_nav2_observer.rviz"
[[ -s "$SOURCE" && -s "$RVIZ" ]] || {
  echo "D07_GAZEBO_RVIZ_SOURCE_MISSING" >&2; exit 2;
}
bash -n "$SOURCE"
grep -Fq 'Fixed Frame: odom' "$RVIZ"
grep -Fq 'Value: /scan' "$RVIZ"
grep -Fq 'Value: /odom' "$RVIZ"
grep -Fq 'Value: /global_costmap/costmap' "$RVIZ"
grep -Fq 'Enabled: false' "$RVIZ"

# All runtime/process shutdown responsibility remains with the already
# verified D04/D05 student launcher (including its native Ctrl+C cleanup).
export AXIA_D05_LIVE=1
export AXIA_D05_SENSOR_ONLY=1
export AXIA_D04_STUDENT_GUI=1
export AXIA_D04_STUDENT_RVIZ=1
export AXIA_D04_STUDENT_RVIZ_CONFIG="$RVIZ"
export AXIA_D04_STUDENT_DOMAIN_ID="${AXIA_D07_DOMAIN_ID:-51}"
export AXIA_D04_STUDENT_GUI_HOLD_S="${AXIA_D07_HOLD_S:-300}"

if [[ "$MODE" == '--self-check' ]]; then
  bash "$SOURCE" --self-check
  echo "D07_RVIZ_STATIC_PASS GAZEBO_NOT_RUN RVIZ_NOT_RUN NO_GOAL"
  echo "D07_STUDENT_NO_GOAL NO_CMD_VEL CERTIFIED_ESTOP_FALSE"
  exit 0
fi

ROS_SETUP="${AXIA_D04_STUDENT_ROS_SETUP:-/opt/ros/jazzy/setup.bash}"
[[ -r "$ROS_SETUP" ]] || {
  echo "D07_JAZZY_SETUP_MISSING=$ROS_SETUP" >&2;exit 2;
}
# ROS-generated setup files sometimes reference unset AMENT_TRACE_SETUP_FILES.
set +u
source "$ROS_SETUP"
set -u
command -v rviz2 >/dev/null 2>&1 || {
  echo "D07_RVIZ2_REQUIRED: sudo apt-get install ros-jazzy-rviz2" >&2
  exit 2
}

if [[ "$MODE" == '--doctor' ]]; then
  echo "D07_RVIZ2_FOUND=1"
  exec bash "$SOURCE" --doctor
fi
[[ -n "${DISPLAY:-}" ]] || {
  echo "D07_WSLG_DISPLAY_MISSING" >&2;exit 2;
}
echo "D07_STUDENT_GAZEBO_RVIZ_LAUNCH_REQUESTED Waffle+visual-only Actor+actual Scan+TF+Odom"
echo "D07_STUDENT_NO_GOAL NO_CMD_VEL NO_H01_PHYSICAL_REPLAN NO_CONTACT_OR_TTL_CLAIM"
echo "D07_RVIZ_CONFIG=$RVIZ"
echo "D07_ROS_DOMAIN_ID=$AXIA_D04_STUDENT_DOMAIN_ID"
echo "D07_SENSOR_ONLY_LIVE_EXPECT_VERDICT_FROM_D04_D05_NOT_YET_VERIFIED"
exec bash "$SOURCE" --run
