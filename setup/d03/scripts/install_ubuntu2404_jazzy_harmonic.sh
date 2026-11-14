#!/usr/bin/env bash
# Ubuntu 24.04 amd64 only; ROS 2 Jazzy and compatible Gazebo Harmonic via ros_gz vendor deps.
# Run as regular user: bash scripts/install_ubuntu2404_jazzy_harmonic.sh
set -Eeuo pipefail
export DEBIAN_FRONTEND=noninteractive
LOG_DIR="${HOME}/axia-env-logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/install_$(date +%Y%m%d_%H%M%S).log"
exec > >(tee -a "$LOG_FILE") 2>&1
fail(){ echo "[BLOCKED] $*" >&2; exit 2; }
trap 'rc=$?; if [[ "$rc" -ne 0 ]]; then echo "[FAIL] exit=$rc (inspect: $LOG_FILE)"; fi' EXIT
[[ "${EUID}" -ne 0 ]] || fail 'Run as a normal sudo-capable user, not root.'
[[ -r /etc/os-release ]] || fail 'Cannot read /etc/os-release'
# shellcheck disable=SC1091
source /etc/os-release
[[ "${ID:-}" == ubuntu && "${VERSION_ID:-}" == 24.04 && "${VERSION_CODENAME:-}" == noble ]] || fail "Ubuntu 24.04 noble required, found ${PRETTY_NAME:-unknown}"
[[ "$(dpkg --print-architecture)" == amd64 ]] || fail 'AXIA standardized image/runtime requires amd64; arm64 needs separate review.'
command -v sudo >/dev/null || fail 'sudo missing'
sudo -v
printf '[INFO] OS=%s arch=%s log=%s\n' "$PRETTY_NAME" "$(dpkg --print-architecture)" "$LOG_FILE"
if grep -qi microsoft /proc/version; then echo '[INFO] WSL detected'; fi
sudo apt-get update
sudo apt-get install -y --no-install-recommends \
  ca-certificates curl gnupg lsb-release locales software-properties-common \
  git build-essential cmake python3 python3-pip python3-venv python3-pytest \
  python3-colcon-common-extensions python3-rosdep2 unzip jq
sudo locale-gen en_US.UTF-8 ko_KR.UTF-8
export LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8
sudo add-apt-repository -y universe
if ! dpkg-query -W -f='${Status}' ros2-apt-source 2>/dev/null | grep -q 'install ok installed'; then
  echo '[STEP] Acquiring official ros2-apt-source release manifest'
  ROS_APT_VERSION="$(curl -fsSL --retry 3 --max-time 30 https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | python3 -c 'import json,sys;print(json.load(sys.stdin)["tag_name"])')"
  [[ "$ROS_APT_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || fail "Unexpected ROS apt source version: $ROS_APT_VERSION"
  ROS_APT_DEB="/tmp/ros2-apt-source_${ROS_APT_VERSION}.noble_all.deb"
  curl -fL --retry 3 -o "$ROS_APT_DEB" "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_VERSION}/ros2-apt-source_${ROS_APT_VERSION}.noble_all.deb"
  sudo apt-get install -y "$ROS_APT_DEB"
else
  echo '[SKIP] ros2-apt-source is installed'
fi
sudo apt-get update
# Gazebo Harmonic is the Jazzy-recommended Gazebo; do not mix OSRF and ROS vendor apt sources automatically.
sudo apt-get install -y \
  ros-jazzy-desktop ros-jazzy-ros-gz ros-jazzy-navigation2 ros-jazzy-nav2-bringup \
  ros-jazzy-nav2-minimal-tb3-sim ros-jazzy-diagnostic-msgs \
  ros-jazzy-diagnostic-updater ros-jazzy-diagnostic-aggregator \
  ros-jazzy-diagnostic-common-diagnostics ros-dev-tools
SOURCE_LINE='source /opt/ros/jazzy/setup.bash'
if ! grep -Fxq "$SOURCE_LINE" "$HOME/.bashrc" 2>/dev/null; then
  printf '\n# AXIA D03 ROS 2 Jazzy\n%s\n' "$SOURCE_LINE" >> "$HOME/.bashrc"
fi
mkdir -p "$HOME/axia_d03_ws/src"
if [[ ! -f /opt/ros/jazzy/setup.bash ]]; then fail 'ROS environment setup file missing'; fi
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
[[ "${ROS_DISTRO:-}" == jazzy ]] || fail 'ROS_DISTRO != jazzy'
command -v ros2 >/dev/null || fail 'ros2 CLI not found'
command -v gz >/dev/null || fail 'Gazebo gz CLI not found: inspect apt and avoid mixing distro sources.'
ros2 interface show diagnostic_msgs/msg/DiagnosticStatus >/dev/null
ros2 pkg prefix diagnostic_aggregator >/dev/null
ros2 pkg prefix nav2_bringup >/dev/null
ros2 pkg prefix ros_gz_bridge >/dev/null
GZ_VERSIONS="$(gz sim --versions 2>&1 || true)"
echo "[CHECK] gz sim versions: $GZ_VERSIONS"
echo "$GZ_VERSIONS" | grep -Eq '(^|[^0-9])8\.[0-9]' || fail 'Gazebo Sim major 8 (Harmonic) was not found. Inspect package versions.'
python3 -m pytest --version
printf '[PASS] INSTALLATION_CLI_READY (not Gazebo execution/ROS integration test)\n'
printf '[NEXT] source /opt/ros/jazzy/setup.bash; bash scripts/verify_environment.sh\n'