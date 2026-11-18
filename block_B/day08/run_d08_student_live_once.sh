#!/usr/bin/env bash
# D08 classroom live observer: D04/D05 official Gazebo Waffle RGB-D + YOLO
# plus D08 read-only RViz. No Goal, cmd_vel, private observer or safety claims.
set -Eeuo pipefail
umask 077
MODE="${1:---run}"
case "$MODE" in
  --self-check|--doctor|--run) ;;
  *) echo "D08_STUDENT_LIVE_USAGE=--self-check|--doctor|--run" >&2; exit 2 ;;
esac
[[ "$#" -le 1 ]] || { echo "D08_STUDENT_LIVE_TOO_MANY_ARGS" >&2; exit 2; }
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BASE="$(cd -- "$HERE/.." && pwd)"
SOURCE="$BASE/day04/run_student_gazebo_yolo_once.sh"
RVIZ="$HERE/live/d08_student_rgbd_monitor.rviz"
[[ -s "$SOURCE" && -s "$RVIZ" ]] || {
  echo "D08_STUDENT_LIVE_SOURCE_MISSING" >&2; exit 2;
}
bash -n "$SOURCE"
grep -Fq '/axia/d05/rgbd/image' "$RVIZ"
grep -Fq '/axia/d05/rgbd/depth_image' "$RVIZ"
grep -Fq '/yolo/cam0/debug_image' "$RVIZ"

# Reuse the proven D04/D05 launcher with NO private D05 distance observer.
# D08 RViz selection changes only the read-only view.
export AXIA_D05_LIVE=1
export AXIA_D05_SENSOR_ONLY=1
# D08 RViz already subscribes /yolo/cam0/debug_image.
# Avoid a duplicate GUI renderer; upstream YOLO detections remain unchanged.
export AXIA_D04_STUDENT_IMAGE_VIEW=0
export AXIA_D04_STUDENT_RVIZ=1
export AXIA_D04_STUDENT_RVIZ_CONFIG="$RVIZ"
export AXIA_D08_STAGED_GUI=1
# Same D07-H01 staged GUI pattern. Xvfb CI uses software-only,
# actual WSLg uses a scoped D3D12/NVIDIA GUI child (no global GPU settings).
if [[ "${GITHUB_ACTIONS:-false}" == true ]]; then
  export AXIA_D08_GUI_BACKEND="${AXIA_D08_GUI_BACKEND:-software}"
else
  export AXIA_D08_GUI_BACKEND="${AXIA_D08_GUI_BACKEND:-d3d12}"
fi
export AXIA_D04_STUDENT_GUI=1
export AXIA_D04_STUDENT_DOMAIN_ID="${AXIA_D08_DOMAIN_ID:-49}"
export AXIA_D04_STUDENT_GUI_HOLD_S="${AXIA_D08_HOLD_S:-300}"

if [[ "$MODE" == --self-check ]]; then
  bash "$SOURCE" --self-check
  echo "D08_LIVE_RVIZ_STATIC_PASS GAZEBO_NOT_RUN RVIZ_NOT_RUN YOLO_NOT_RUN NO_GOAL"
  exit 0
fi

ROS_SETUP="${AXIA_D04_STUDENT_ROS_SETUP:-/opt/ros/jazzy/setup.bash}"
[[ -r "$ROS_SETUP" ]] || {
  echo "D08_STUDENT_JAZZY_SETUP_MISSING=$ROS_SETUP" >&2; exit 2;
}
# ROS setup files reference optional unset environment variables.
set +u
source "$ROS_SETUP"
set -u
if ! command -v rviz2 >/dev/null 2>&1; then
  echo "D08_RVIZ2_NOT_INSTALLED: sudo apt-get install ros-jazzy-rviz2" >&2
  exit 2
fi
if [[ "$MODE" == --doctor ]]; then
  echo "D08_STUDENT_RVIZ2_FOUND=1"
  exec bash "$SOURCE" --doctor
fi

# Real WSL2 RViz logs show the installed Jazzy /robot_description has
# upstream package://.../models/*.dae missing-path references (Nav2 issue #19).
# Generate a PRIVATE read-only RViz file + official URDF mesh-path overlay.
# Do not modify official URDF, Gazebo SDF, ROS robot_state_publisher or TF.
MODEL_TOOL="$HERE/live/prepare_rviz_mesh_view.py"
[[ -r "$MODEL_TOOL" ]] || {
  echo "D08_RVIZ_OFFICIAL_MESH_TOOL_MISSING" >&2; exit 2;
}
NAV_PREFIX="$(ros2 pkg prefix nav2_minimal_tb3_sim)" || {
  echo "D08_RVIZ_OFFICIAL_NAV2_PACKAGE_MISSING" >&2; exit 2;
}
URDF="$NAV_PREFIX/share/nav2_minimal_tb3_sim/urdf/turtlebot3_waffle.urdf"
MODEL_CACHE="$HOME/.cache/axia/d08/rviz"
mkdir -p "$MODEL_CACHE"
MODEL_DIR="$(mktemp -d "$MODEL_CACHE/waffle-XXXXXXXX")"
python3 "$MODEL_TOOL" --prefix "$NAV_PREFIX" --urdf "$URDF" \
  --rviz "$RVIZ" --out "$MODEL_DIR" || {
  echo "D08_RVIZ_OFFICIAL_MESH_FIX_BLOCKED" >&2; exit 2;
}
export AXIA_D04_STUDENT_RVIZ_CONFIG="$MODEL_DIR/d08_render_view.rviz"
echo "D08_RVIZ_OFFICIAL_MESH_VIEW_READY config=$AXIA_D04_STUDENT_RVIZ_CONFIG"

echo "D08_STUDENT_LIVE_LAUNCH_REQUESTED: Gazebo + moving visual-only person + RGB-D + YOLO + RViz2"
echo "D08_STUDENT_LIVE_READONLY: NO_GOAL NO_CMD_VEL NO_PRIVATE_D05_RANGE NO_SAFETY_TTL"
echo "D08_GUI_WINDOWS=GAZEBO_RVIZ2_ONLY YOLO_DEBUG_IN_RVIZ NO_IMAGE_VIEW"
echo "D08_STUDENT_RVIZ_CONFIG=$RVIZ"
echo "D08_STUDENT_DOMAIN_ID=$AXIA_D04_STUDENT_DOMAIN_ID"
echo "D08_STUDENT_LIVE_NOT_YET_VERIFIED: check D05_PUBLIC_SENSOR_ONLY_PASS and actual GUI"
# Existing D04 runner owns ROS/Gazebo/RViz process groups and cleans on Ctrl+C.
exec bash "$SOURCE" --run
