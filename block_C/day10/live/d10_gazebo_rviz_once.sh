#!/usr/bin/env bash
# D10 owner classroom demo: D08 Gazebo/RViz sensor session and D12 synthetic
# Isolation Forest diagnostic replay. No robot control, Goal, or Safety TTL.
set -Eeuo pipefail
umask 077
MODE="${1:---run}"
[[ $# -le 1 ]] || { echo D10_LIVE_USAGE_ERROR >&2; exit 2; }
case "$MODE" in --self-check|--doctor|--run) ;; *) echo D10_LIVE_USAGE_ERROR >&2; exit 2 ;; esac
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STUDENT="$(cd "$HERE/../../.." && pwd)"
D08="$STUDENT/block_B/day08/run_d08_student_live_once.sh"
MARKER="$HERE/d10_if_rviz_marker.py"
BUILDER="$HERE/build_d10_rviz_overlay.py"
RVIZ="$STUDENT/block_B/day08/live/d08_student_rgbd_monitor.rviz"
D08_PID=""
MARKER_PID=""
OUT=""
[[ -s "$D08" && -s "$MARKER" && -s "$BUILDER" && -s "$RVIZ" ]] || {
  echo D10_LIVE_STUDENT_ASSET_MISSING >&2; exit 2;
}
bash -n "$D08"
python3 "$MARKER" --self-check
if [[ "$MODE" == --self-check ]]; then
  echo D10_LIVE_STATIC_PASS NO_ROS_NO_GAZEBO_NO_CONTROL
  exit 0
fi
INSTRUCTOR="${AXIA_D10_INSTRUCTOR_ROOT:-}"
[[ -d "$INSTRUCTOR/.git" ]] || {
  echo D10_LIVE_INSTRUCTOR_LOCAL_CLONE_REQUIRED >&2; exit 2;
}
BLOCK_C="$INSTRUCTOR/training/block_C"
SCORES="$BLOCK_C/day10/reference_outputs/if_scores_test.csv"
GENERATOR="$BLOCK_C/day12/events.py"
BRIDGE="$BLOCK_C/day12/shared/ros_diagnostic_bridge.py"
[[ -s "$SCORES" && -s "$GENERATOR" && -s "$BRIDGE" ]] || {
  echo D10_LIVE_INSTRUCTOR_REFERENCES_MISSING >&2; exit 2;
}
if [[ "$MODE" == --doctor ]]; then
  echo "D10_LIVE_DOCTOR_STATIC_PASS student=$(git -C "$STUDENT" rev-parse HEAD)"
  echo D10_LIVE_ROS_GAZEBO_NOT_RUN
  exit 0
fi
[[ -r /opt/ros/jazzy/setup.bash && -n "${DISPLAY:-}" ]] || {
  echo D10_LIVE_JAZZY_OR_WSLG_DISPLAY_MISSING >&2; exit 2;
}
source /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 24.04 ]] || {
  echo D10_LIVE_UBUNTU_2404_REQUIRED >&2; exit 2;
}
DOMAIN="${AXIA_D10_DOMAIN_ID:-49}"
[[ "$DOMAIN" =~ ^[0-9]{1,3}$ ]] && (( DOMAIN <= 232 )) || {
  echo D10_LIVE_INVALID_ROS_DOMAIN_ID >&2; exit 2;
}
OUT="${AXIA_D10_LIVE_EVIDENCE:-$HOME/axia_d10_live_evidence/d10-$(date -u +%Y%m%dT%H%M%SZ)-$$}"
[[ ! -e "$OUT" ]] || { echo D10_LIVE_OUTPUT_ALREADY_EXISTS >&2; exit 2; }
mkdir -p "$OUT"
finish() {
  local rc=$?
  trap - EXIT INT TERM
  set +e
  if [[ -n "$MARKER_PID" ]]; then kill -TERM "$MARKER_PID" 2>/dev/null; fi
  if [[ -n "$D08_PID" ]]; then kill -TERM "$D08_PID" 2>/dev/null; fi
  if [[ -n "$MARKER_PID" ]]; then wait "$MARKER_PID" 2>/dev/null; fi
  if [[ -n "$D08_PID" ]]; then wait "$D08_PID" 2>/dev/null; fi
  echo "D10_LIVE_EVIDENCE=$OUT rc=$rc VISUAL_OWNER_L3_NOT_AUTO_VERIFIED"
  exit "$rc"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
git -C "$STUDENT" rev-parse HEAD >"$OUT/student_sha.txt"
git -C "$INSTRUCTOR" rev-parse HEAD >"$OUT/instructor_sha.txt"
sha256sum "$SCORES" >"$OUT/if_scores_test.sha256"
python3 "$GENERATOR" --scores "$SCORES" --out "$OUT/events" \
  --model-id D10_ISOLATION_FOREST | tee "$OUT/event_generate.log"
python3 "$BUILDER" --source "$RVIZ" --out "$OUT/d10_rviz_overlay.rviz" \
  | tee "$OUT/rviz_profile.log"
# Existing D08 runner owns Gazebo/YOLO/RViz process groups.
# Keep parent unsourced: D08 itself sources Jazzy safely under WSL2.
AXIA_D08_DOMAIN_ID="$DOMAIN" \
AXIA_D08_MONITOR_RVIZ="$OUT/d10_rviz_overlay.rviz" \
AXIA_D08_HOLD_S="${AXIA_D10_GUI_HOLD_S:-900}" \
AXIA_D08_RGBD_RATE_HZ="${AXIA_D10_RGBD_RATE_HZ:-10}" \
AXIA_D08_GUI_RENDER_ENGINE="${AXIA_D10_GUI_ENGINE:-ogre}" \
bash "$D08" --run >"$OUT/d08_session.log" 2>&1 &
D08_PID=$!
READY=0
for ((i=0; i<180; i++)); do
  if grep -Fq D05_PUBLIC_SENSOR_ONLY_PASS "$OUT/d08_session.log"; then
    READY=1; break
  fi
  if ! kill -0 "$D08_PID" 2>/dev/null; then break; fi
  sleep 2
done
[[ "$READY" == 1 ]] || {
  echo "D10_LIVE_D08_SENSOR_GATE_BLOCKED log=$OUT/d08_session.log" >&2
  tail -n 45 "$OUT/d08_session.log" >&2
  exit 3
}
(
  set +u; source /opt/ros/jazzy/setup.bash; set -u
  export ROS_DOMAIN_ID="$DOMAIN"
  export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
  exec /usr/bin/python3 "$MARKER" --frame-id base_link
) >"$OUT/marker.log" 2>&1 &
MARKER_PID=$!
sleep 1
kill -0 "$MARKER_PID" || { echo D10_LIVE_MARKER_START_FAILED >&2; exit 3; }
{
  echo "D10_LIVE_REPLAY_STARTED source=SYNTHETIC_COURSE_FIXTURE domain=$DOMAIN"
  echo "D10_LIVE_RVIZ_MARKER_TOPIC=/axia/education/d10_if_marker"
  echo D10_LIVE_AI_SCORE_IS_NOT_GAZEBO_SENSOR_OR_ESTOP
  echo D10_LIVE_GAZEBO_RVIZ_OWNER_VISUAL_L3_NOT_RUN_BY_STATIC_CI
} | tee "$OUT/live_summary.log"
# 104 synthetic events are replayed in trace order; each replay runs an isolated
# D12 EventGate. Source trace-local nanoseconds are NEVER compared with /clock.
while kill -0 "$D08_PID" 2>/dev/null; do
  (
    set +u; source /opt/ros/jazzy/setup.bash; set -u
    export ROS_DOMAIN_ID="$DOMAIN"
    export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
    exec /usr/bin/python3 "$BRIDGE" --events "$OUT/events/anomaly_events.jsonl" \
      --period-sec 0.5 --max-messages 104
  ) >>"$OUT/ros_diagnostics.log" 2>&1 || {
    echo "D10_LIVE_D12_REPLAY_FAILED log=$OUT/ros_diagnostics.log" >&2
    exit 4
  }
  sleep 2
done
wait "$D08_PID"
