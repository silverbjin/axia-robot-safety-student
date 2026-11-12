#!/usr/bin/env bash
# D04 STUDENT: independent public official Nav2/TB3 Waffle Pi RGB in Gazebo
# + upstream C++ yolo_ros ONNX, real GUI debug video and read-only RViz.
# No instructor repo, no P1 code, no Goal, cmd_vel, fault or SW Stop/E-Stop.
set -Eeuo pipefail
umask 077

MODE="${1:---run}"
case "$MODE" in --run|--doctor|--self-check) ;; *) echo "D04_STUDENT_USAGE=--doctor|--run|--self-check"; exit 2;; esac
[[ $# -le 1 ]] || { echo "D04_STUDENT_USAGE=--run"; exit 2; }
BASE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$BASE/gazebo_yolo"
SCENE="$ROOT/prepare_scene.py"
MONITOR="$ROOT/verify_live.py"
RVIZ="$ROOT/axia_d04_student.rviz"
YOLO_SHA='94d2dd500cb26027ee9c019f4d3a02029ac615cc'
ONNX_SHA='4f44c33cea12d4b5785e5e7c0a20c13d0c62a77de607ce96a40d6036c7d7bbcf'
ACTOR_SHA='49af0df3a319d1cb8ca2cebf02dbd00f625e5d5bec820bc5e109925b18b65c6e'
CACHE="$HOME/.cache/axia/d04_student_gazebo"
ASSET_CACHE="$HOME/.cache/axia/d04/assets"
YOLO_WS="$HOME/.cache/axia/d04/yolo_ws_$YOLO_SHA"
MODEL="$ASSET_CACHE/yolo26n.onnx"
ACTOR="$ASSET_CACHE/walk.dae"
ROS_SETUP="${AXIA_D04_STUDENT_ROS_SETUP:-/opt/ros/jazzy/setup.bash}"
CI_HEADLESS="${AXIA_D04_STUDENT_CI_HEADLESS:-0}"
GUI="${AXIA_D04_STUDENT_GUI:-1}"
SHOW_RVIZ="${AXIA_D04_STUDENT_RVIZ:-0}"
HOLD="${AXIA_D04_STUDENT_GUI_HOLD_S:-180}"
export ROS_DOMAIN_ID="${AXIA_D04_STUDENT_DOMAIN_ID:-40}"
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export GZ_PARTITION="axia_d04_student_$$_${ROS_DOMAIN_ID}"

if [[ "$MODE" == --self-check ]]; then
  for p in "$SCENE" "$MONITOR" "$RVIZ"; do
    [[ -s "$p" ]] || { echo "D04_STUDENT_GAZEBO_SOURCE_MISSING=$p"; exit 2; }
  done
  bash -n "${BASH_SOURCE[0]}"
  python3 -m py_compile "$SCENE" "$MONITOR"
  echo "D04_STUDENT_GAZEBO_STATIC_PASS GAZEBO_NOT_RUN YOLO_NOT_RUN"
  echo "D04_STUDENT_GAZEBO_SOURCE=PUBLIC_OFFICIAL_NAV2_YOLO_ROS NO_PRIVATE_P1"
  exit 0
fi

if [[ ! -r "$ROS_SETUP" ]]; then
  echo "D04_STUDENT_ROS_JAZZY_MISSING=$ROS_SETUP"; exit 2
fi
if [[ "$CI_HEADLESS" != 1 ]]; then
  if ! grep -qiE 'microsoft|wsl' /proc/sys/kernel/osrelease ||
     ! grep -q '24.04' /etc/os-release; then
    echo "D04_STUDENT_WSL2_UBUNTU_24_04_REQUIRED"; exit 2
  fi
fi
# First check only OS-level tools. ros2 can be absent from PATH until
# after sourcing /opt/ros/jazzy/setup.bash (observed in public CI RED).
for tool in bash curl git python3 sha256sum setsid timeout; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "D04_STUDENT_MISSING_TOOL=$tool"; exit 2
  fi
done
if [[ "$GUI" == 1 && -z "${DISPLAY:-}" ]]; then
  echo "D04_STUDENT_WSLG_DISPLAY_MISSING: Gazebo GUI requires WSLg DISPLAY"; exit 2
fi
[[ "$GUI" == 0 || "$GUI" == 1 ]] || { echo "D04_STUDENT_GUI_INVALID"; exit 2; }
[[ "$SHOW_RVIZ" == 0 || "$SHOW_RVIZ" == 1 ]] || { echo "D04_STUDENT_RVIZ_INVALID"; exit 2; }
[[ "$HOLD" =~ ^[0-9]{1,4}$ ]] || { echo "D04_STUDENT_HOLD_INVALID"; exit 2; }

set +u
source "$ROS_SETUP"
set -u
for tool in ros2 gz xacro colcon; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    if [[ "$MODE" == --doctor ]]; then
      echo "D04_STUDENT_ROS_TOOL_MISSING_AFTER_SOURCE=$tool"; exit 2
    fi
    echo "D04_STUDENT_INSTALL_OFFICIAL_TOOLS_AFTER_ROS_SOURCE missing=$tool"
    sudo apt-get update -qq
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
      python3-colcon-common-extensions ros-jazzy-ros-gz ros-jazzy-xacro
    break
  fi
done
for tool in ros2 gz xacro colcon; do
  command -v "$tool" >/dev/null || { echo "D04_STUDENT_TOOL_BLOCKED=$tool"; exit 2; }
done

for p in nav2_bringup nav2_minimal_tb3_sim turtlebot3_gazebo ros_gz_image image_view; do
  if ! ros2 pkg prefix "$p" >/dev/null 2>&1; then
    if [[ "$MODE" == --doctor ]]; then
      echo "D04_STUDENT_OFFICIAL_PACKAGE_MISSING=$p"; exit 2
    fi
    echo "D04_STUDENT_INSTALLING_OFFICIAL_ROS_DEPENDENCIES"
    sudo apt-get update -qq
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
      ros-jazzy-nav2-bringup ros-jazzy-nav2-minimal-tb3-sim \
      ros-jazzy-turtlebot3-gazebo ros-jazzy-ros-gz \
      ros-jazzy-image-view ros-jazzy-xacro ros-jazzy-rviz2
    break
  fi
done
for p in nav2_bringup nav2_minimal_tb3_sim turtlebot3_gazebo ros_gz_image image_view; do
  ros2 pkg prefix "$p" >/dev/null || { echo "D04_STUDENT_PACKAGE_BLOCKED=$p"; exit 2; }
done
if [[ "$MODE" == --doctor ]]; then
  if [[ -s "$YOLO_WS/install/setup.bash" ]]; then
    echo "D04_STUDENT_YOLO_OVERLAY_CACHED=$YOLO_WS"
  else
    echo "D04_STUDENT_YOLO_BUILD_REQUIRED=$YOLO_WS"
  fi
  echo "D04_STUDENT_PREFLIGHT_PASS GAZEBO_NOT_RUN GUI_NOT_RUN"
  exit 0
fi

mkdir -p "$ASSET_CACHE" "$CACHE" "$HOME/axia_d04_student_evidence"
OUT="$(mktemp -d "$HOME/axia_d04_student_evidence/d04-gazebo-XXXXXXXX")"
SCENE_DIR="$OUT/scene"
PIDS=()
cleanup() {
  local rc=$?
  trap - EXIT INT TERM
  set +e
  echo "D04_STUDENT_SHUTDOWN: stopping only child process groups" | tee -a "$OUT/session.log"
  for (( i=${#PIDS[@]}-1; i>=0; i-- )); do
    kill -TERM -- "-${PIDS[i]}" 2>/dev/null || true
  done
  sleep 2
  for pid in "${PIDS[@]}"; do
    if kill -0 "$pid" 2>/dev/null; then kill -KILL -- "-$pid" 2>/dev/null || true; fi
    wait "$pid" 2>/dev/null || true
  done
  printf '%s\n' "D04_STUDENT_EVIDENCE=$OUT" "D04_STUDENT_EXIT_CODE=$rc"
  exit "$rc"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

if [[ ! -s "$YOLO_WS/install/setup.bash" ]]; then
  mkdir -p "$YOLO_WS/src"
  if [[ ! -d "$YOLO_WS/src/yolo_ros/.git" ]]; then
    git clone -q https://github.com/mgonzs13/yolo_ros.git "$YOLO_WS/src/yolo_ros"
  fi
  git -C "$YOLO_WS/src/yolo_ros" checkout -q --detach "$YOLO_SHA"
  [[ "$(git -C "$YOLO_WS/src/yolo_ros" rev-parse HEAD)" == "$YOLO_SHA" ]] || exit 2
  echo "D04_STUDENT_BUILDING_PUBLIC_YOLO_ROS SHA=$YOLO_SHA"
  (
    cd "$YOLO_WS"
    colcon build --merge-install --executor sequential --packages-up-to yolo_bringup \
      --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF \
      --event-handlers console_direct+
  ) >"$OUT/yolo_build.log" 2>&1 || {
    echo "D04_STUDENT_YOLO_BUILD_BLOCKED"; tail -n 35 "$OUT/yolo_build.log"; exit 2;
  }
fi
set +u
source "$YOLO_WS/install/setup.bash"
set -u
ros2 pkg prefix yolo_msgs >/dev/null || { echo "D04_STUDENT_YOLO_MESSAGES_UNAVAILABLE"; exit 2; }

download_pinned() {
  local target="$1" hash="$2" url="$3"
  if ! (echo "$hash  $target" | sha256sum -c - >/dev/null 2>&1); then
    curl -fL --retry 3 --max-time 180 "$url" -o "$target.tmp"
    echo "$hash  $target.tmp" | sha256sum -c -
    mv "$target.tmp" "$target"
  fi
  echo "$hash  $target" | sha256sum -c -
}
download_pinned "$MODEL" "$ONNX_SHA" \
  'https://huggingface.co/unileon-robotics/YOLO26-ONNX/resolve/main/yolo26n.onnx'
download_pinned "$ACTOR" "$ACTOR_SHA" \
  'https://fuel.gazebosim.org/1.0/Mingfei/models/actor/tip/files/meshes/walk.dae'

NAV_DIR="$(ros2 pkg prefix nav2_minimal_tb3_sim)/share/nav2_minimal_tb3_sim"
PI_DIR="$(ros2 pkg prefix turtlebot3_gazebo)/share/turtlebot3_gazebo"
test -r "$NAV_DIR/urdf/gz_waffle.sdf.xacro"
test -r "$PI_DIR/models/turtlebot3_waffle_pi/model.sdf"
test -r "$NAV_DIR/worlds/tb3_sandbox.sdf.xacro"
python3 "$SCENE" \
  --waffle "$NAV_DIR/urdf/gz_waffle.sdf.xacro" \
  --pi "$PI_DIR/models/turtlebot3_waffle_pi/model.sdf" \
  --world "$NAV_DIR/worlds/tb3_sandbox.sdf.xacro" \
  --actor "$ACTOR" --model "$MODEL" --out "$SCENE_DIR" \
  > "$OUT/scene.log"
echo "D04_STUDENT_SCENE_READY: public Waffle Pi RGB + visual-only person"

start_group() {
  local name="$1"; shift
  setsid "$@" > "$OUT/${name}.log" 2>&1 &
  local pid=$!
  PIDS+=("$pid")
  echo "D04_STUDENT_PROCESS_STARTED name=$name pid=$pid"
}
if [[ "$GUI" == 1 ]]; then
  HEADLESS="headless:=False"
else
  HEADLESS="headless:=True"
fi
echo "D04_STUDENT_GUI=${GUI} GZ_PARTITION=$GZ_PARTITION ROS_DOMAIN_ID=$ROS_DOMAIN_ID"
# The official Nav2 simulation launch supplies Gazebo, robot_state_publisher,
# Gazebo bridge and Waffle spawn. No navigation goal is sent by this demo.
start_group gazebo_nav2 ros2 launch nav2_bringup tb3_simulation_launch.py \
  "robot_sdf:=$SCENE_DIR/student_waffle_rgb.sdf.xacro" \
  "world:=$SCENE_DIR/student_human_world.sdf.xacro" \
  "$HEADLESS" use_rviz:=False use_composition:=False autostart:=False \
  x_pose:=-0.5 y_pose:=-0.5 yaw:=0.0
start_group camera_bridge ros2 run ros_gz_image image_bridge /camera/image_raw
start_group yolo_ros ros2 launch yolo_bringup yolo.launch.py \
  "params_file:=$SCENE_DIR/student_yolo.yaml" namespace:=yolo
if [[ "$GUI" == 1 ]]; then
  start_group image_view ros2 run image_view image_view \
    --ros-args -r image:=/yolo/cam0/debug_image
  if [[ "$SHOW_RVIZ" == 1 ]]; then
    if command -v rviz2 >/dev/null; then
      start_group rviz2 rviz2 -d "$RVIZ" --ros-args -p use_sim_time:=true
    else
      echo "D04_STUDENT_RVIZ_UNAVAILABLE: optional; Gazebo+YOLO still launched"
    fi
  fi
fi
echo "D04_STUDENT_GAZEBO_LAUNCHED: GUI startup requested; NOT yet verified"
echo "D04_STUDENT_GUI_NOTICE: Gazebo and yolo image_view windows may open after ROS startup"

set +e
python3 "$MONITOR" --timeout "${AXIA_D04_STUDENT_MONITOR_TIMEOUT_S:-160}" \
  --out "$OUT/live_verdict.json" | tee "$OUT/live_monitor.log"
LIVE_RC=${PIPESTATUS[0]}
set -e
if [[ "$LIVE_RC" -ne 0 ]]; then
  echo "D04_STUDENT_LIVE_BLOCKED rc=$LIVE_RC"
  echo "D04_STUDENT_FIRST_LOGS=$OUT/gazebo_nav2.log,$OUT/camera_bridge.log,$OUT/yolo_ros.log"
  exit 3
fi
if [[ "$GUI" == 1 ]]; then
  echo "D04_STUDENT_GUI_HOLD_STARTED seconds=$HOLD; press Ctrl+C when finished"
  sleep "$HOLD"
fi
echo "D04_STUDENT_DEMO_COMPLETE: live RGB+YOLO checked; GUI render on WSL2 remains user-observed"
echo "D04_STUDENT_SCOPE=VISUAL_ONLY NO_GOAL NO_CMD_VEL NO_SAFETY_TTL NO_ESTOP"
