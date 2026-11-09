#!/usr/bin/env bash
# AXIA D03 v3 student P1 environment helper.
# No Start/Goal/Fault/Reset/Rearm/velocity publication; never deletes student work.
# Run as a CHILD shell: bash scripts/p1_d03_v3_student_setup.sh --prepare
set -Eeuo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(cd "$HERE/.." && pwd -P)"
MODE="${1:---help}"

usage() {
  cat <<'EOF'
AXIA P1+D03 v3 student environment (Ubuntu 24.04 / ROS 2 Jazzy / Gazebo Harmonic)
Usage: bash scripts/p1_d03_v3_student_setup.sh COMMAND

  --install-deps  Install required official Ubuntu/ROS packages via apt
                  (ROS apt repository must be configured first)
  --prepare       Create/reuse isolated classroom session, build five local P1/D3
                  ROS 2 packages and run basic preflight (no Gazebo launched)
  --check         Check prepared ROS 2 / Nav2 / Gazebo / P1/D3 package indexes
  --help          Print this message; makes no changes

Requires a standalone student D03_v3 checkout. Does not run a Nav2 Goal,
Safety Start, Fault Injection, Reset/Rearm, /cmd_vel or actual robot hardware.
EOF
}

blocked() { printf '[BLOCKED] %s\n' "$*" >&2; exit 2; }

if [[ "$MODE" == --help || "$MODE" == -h || "$MODE" == help ]]; then
  usage
  exit 0
fi
[[ "$#" == 1 ]] || blocked 'Use one command option; see --help'
case "$MODE" in
  --install-deps|--prepare|--check) ;;
  *) blocked "Unknown mode: $MODE. See --help" ;;
esac

[[ "$(uname -s)" == Linux && -f /etc/os-release ]] ||
  blocked 'Linux Ubuntu 24.04 required'
# shellcheck disable=SC1091
source /etc/os-release
[[ "${ID:-}" == ubuntu && "${VERSION_ID:-}" == 24.04 ]] ||
  blocked 'Ubuntu 24.04 Noble required (not ROS Humble/Fortress)'

if [[ "$MODE" == --install-deps ]]; then
  command -v apt-get >/dev/null || blocked 'apt-get not available'
  if (( EUID == 0 )); then
    APT=(apt-get)
  else
    command -v sudo >/dev/null || blocked 'sudo required for package installation'
    APT=(sudo apt-get)
  fi
  # This does NOT create or overwrite apt sources. Set up ROS 2 Jazzy apt sources
  # using https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html
  "${APT[@]}" update
  apt-cache show ros-jazzy-ros-base >/dev/null 2>&1 ||
    blocked 'Official ROS Jazzy apt source missing; follow ROS installation link'
  "${APT[@]}" install -y --no-install-recommends \
    git procps python3-pip python3-venv python3-pytest python3-yaml \
    python3-colcon-common-extensions \
    ros-jazzy-ros-base ros-jazzy-nav2-bringup \
    ros-jazzy-nav2-minimal-tb3-sim ros-jazzy-ros-gz \
    ros-jazzy-ros2cli ros-jazzy-nav2-msgs ros-jazzy-diagnostic-msgs
  printf '[INSTALLED] ROS 2 Jazzy / Nav2 / Gazebo Harmonic / Waffle dependencies\n'
  printf '[NEXT] bash scripts/p1_d03_v3_student_setup.sh --prepare\n'
  exit 0
fi

[[ -f /opt/ros/jazzy/setup.bash ]] ||
  blocked 'ROS Jazzy not found; configure ROS apt source and run --install-deps'
[[ -f "$ROOT/ros2_ws/src/axia_safety_bringup/package.xml" ]] ||
  blocked 'Shared P1 source absent. Check repository and D03_v3 branch'
[[ -f "$ROOT/ros2_ws/src/axia_d3_demo/package.xml" ]] ||
  blocked 'D03 demo source absent'
[[ -f "$ROOT/block_A/day03/v3/P1_RUNTIME_SOURCE_MANIFEST.json" ]] ||
  blocked 'P1 source provenance manifest absent'

# ROS environment is only sourced in this child shell. Does not modify
# ~/.bashrc or interactive-terminal flags.
set +u
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
set -u

for name in ros2 colcon gz python3; do
  command -v "$name" >/dev/null || blocked "Missing executable: $name"
done
ENTRY="$ROOT/block_A/day03/v3/scripts/classroom.sh"
[[ -f "$ENTRY" ]] || blocked 'Classroom entrypoint not found'

if [[ "$MODE" == --prepare ]]; then
  bash "$ENTRY" session
  bash "$ENTRY" prepare
fi

[[ -f "$ROOT/install/setup.bash" ]] ||
  blocked 'Missing built install/setup.bash. Run --prepare'
set +u
# shellcheck disable=SC1091
source "$ROOT/install/setup.bash"
set -u

bash "$ENTRY" preflight
for pkg in axia_safety_bringup axia_safety_supervisor axia_fault_injector axia_scenario_verifier axia_d3_demo; do
  ros2 pkg prefix "$pkg" >/dev/null || blocked "P1/D3 package missing: $pkg"
done
printf '[READY] P1_D03_V3_STUDENT_BUILD_BASIC_PREFLIGHT\n'
printf '[SCOPE] Gazebo GUI NOT_RUN; Nav2 Goal NOT_RUN; Fault NOT_RUN; E-Stop NOT_CERTIFIED\n'
printf '[NEXT] In a NEW terminal: cd %q; bash block_A/day03/v3/scripts/classroom.sh launch\n' "$ROOT"
