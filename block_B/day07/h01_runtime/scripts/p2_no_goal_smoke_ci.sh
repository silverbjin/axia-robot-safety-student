#!/usr/bin/env bash
# Sim-only L2: P2 exact graph + clocks, scan, odom. NO GOAL, NO FAULT.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT"
OUT="${AXIA_P2_SMOKE_RESULTS:-$ROOT/results/p2-smoke-$(date -u +%Y%m%dT%H%M%SZ)-$$}"
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd -P)"
LAUNCH_PID=''
BAG_PID=''
GUI_WATCH_PID=''
MOVING_GAZEBO_GUI_PID=''
MOVING_RVIZ_PID=''
OWNER_MOVING="${AXIA_G07_TASK04_OWNER_MOVING_L3:-0}"
CI_MOVING_GUI="${AXIA_G07_TASK04_CI_GUI_MOVING:-0}"
SENSOR_NO_GOAL="${AXIA_G07_OWNER_SENSOR_TRUTH_NO_GOAL:-0}"
[[ "$SENSOR_NO_GOAL" == 0 || "$SENSOR_NO_GOAL" == 1 ]] || exit 2
if [[ "$SENSOR_NO_GOAL" == 1 ]];then
  # Actual WSL2 sensor only. Never borrow Owner Moving/CI Goal authorization
  # or D07's altered Gaussian-free Waffle noise profile.
  [[ "${GITHUB_ACTIONS:-}" != true
     && "$OWNER_MOVING" == 0 && "$CI_MOVING_GUI" == 0
     && "${AXIA_D07_H01_GUI_NO_GOAL:-0}" == 0
     && "${AXIA_G07_CI_SIM_GOAL_ALLOWED:-0}" == 0
     && "${AXIA_G07_CI_OWNER_BAG_PARITY:-0}" == 0
     && "${AXIA_P0_SIM_ONLY:-0}" == 1
     && "${AXIA_G07_OWNER_STARTUP_PARITY:-0}" == 1
     && "${AXIA_P2_G07_PHYSICAL_PREFLIGHT:-0}" == 1
     && "${AXIA_P2_G07_RELOCATED_OBSTACLE:-0}" == 1
     && "${AXIA_G07_TASK02_SIMPLE_TF_CANDIDATE:-0}" == 0
     && "${LIBGL_ALWAYS_SOFTWARE:-0}" != 1
     && "${ROS_DISTRO:-}" == jazzy ]] || {
    echo 'G07_WSLG_SENSOR_NO_GOAL_AUTHORITY_DENIED' >&2;exit 2;
  }
  grep -qiE 'microsoft|wsl' /proc/sys/kernel/osrelease || {
    echo 'G07_WSLG_SENSOR_REAL_WSL2_REQUIRED' >&2;exit 2;
  }
fi
[[ "$OWNER_MOVING" == 0 || "$OWNER_MOVING" == 1 ]] || exit 2
[[ "$CI_MOVING_GUI" == 0 || "$CI_MOVING_GUI" == 1 ]] || exit 2
if [[ "$OWNER_MOVING" == 1 ]];then
  [[ "${GITHUB_ACTIONS:-}" != true
     && "${AXIA_G07_CI_SIM_GOAL_ALLOWED:-0}" != 1
     && "$CI_MOVING_GUI" == 0
     && "${AXIA_P0_SIM_ONLY:-0}" == 1
     && "${AXIA_P2_G07_PHYSICAL_PREFLIGHT:-0}" == 1
     && "${AXIA_G07_OWNER_STARTUP_PARITY:-0}" == 1
     && "${AXIA_G07_CI_OWNER_BAG_PARITY:-0}" == 1
     && -n "${DISPLAY:-}" && -t 0 && -r /dev/tty ]] || {
    echo 'G07_TASK04_OWNER_TTY_ENV_PREGOAL_BLOCKED' >&2;exit 2;
  }
  unset AXIA_G07_OWNER_COMMON_RUNNER_AUTHORIZED AXIA_P2_OWNER_PINNED_SHA || true
fi
if [[ "$CI_MOVING_GUI" == 1 ]];then
  [[ "${GITHUB_ACTIONS:-}" == true
     && "${AXIA_G07_CI_SIM_GOAL_ALLOWED:-0}" == 1
     && "$OWNER_MOVING" == 0 && -n "${DISPLAY:-}" ]] || {
    echo 'G07_TASK04_CI_GUI_SCOPE_BLOCKED_NO_GOAL' >&2;exit 2;
  }
fi
# Process clean-exit budget only; never a 150ms CM/300ms scan TTL change.
G07_MANAGED_LAUNCH_EXIT_GRACE_SEC=26
launch_active() {
  [[ -n "$LAUNCH_PID" && -r "/proc/$LAUNCH_PID/stat" ]] || return 1
  local pid comm state other
  read -r pid comm state other < "/proc/$LAUNCH_PID/stat" || return 1
  [[ "$state" != Z && "$state" != X ]]
}
bag_active() {
  [[ -n "$BAG_PID" && -r "/proc/$BAG_PID/stat" ]] || return 1
  local pid comm state other
  read -r pid comm state other < "/proc/$BAG_PID/stat" || return 1
  [[ "$state" != Z && "$state" != X ]]
}
stop_owner_parity_bag() {
  [[ -n "$BAG_PID" ]] || return 0
  kill -INT -- "-$BAG_PID" 2>/dev/null || true
  for i in {1..50}; do bag_active || break; sleep .1; done
  if bag_active; then
    kill -TERM -- "-$BAG_PID" 2>/dev/null || true
    for i in {1..20}; do bag_active || break; sleep .1; done
  fi
  if bag_active; then
    kill -KILL -- "-$BAG_PID" 2>/dev/null || true
    echo 'G07_CI_OWNER_BAG_FORCED_TEARDOWN' >&2
    return 3
  fi
  wait "$BAG_PID" 2>/dev/null || true
  BAG_PID=''
  echo 'G07_CI_OWNER_BAG_STOP_COMPLETED'
}
cleanup() {
 local rc=$?
 local gui_pid
 # Clean only GUI clients owned by this run, never every Gazebo instance.
 for gui_pid in "$MOVING_RVIZ_PID" "$MOVING_GAZEBO_GUI_PID";do
   if [[ -n "$gui_pid" ]] && kill -0 "$gui_pid" 2>/dev/null;then
     kill -INT -- "-$gui_pid" 2>/dev/null || true
     wait "$gui_pid" 2>/dev/null || true
   fi
 done
 trap - EXIT INT TERM
 set +e
 # Exactly ONE isolated read-only GUI process group is owned by this smoke.
 # A watcher sleeps until the verified free baseline; NO GUI renders before.
 if [[ -n "$GUI_WATCH_PID" ]]; then
   kill -INT -- "-$GUI_WATCH_PID" 2>/dev/null || true
   for i in 1 2 3 4 5; do
     kill -0 "$GUI_WATCH_PID" 2>/dev/null || break
     sleep .3
   done
   kill -TERM -- "-$GUI_WATCH_PID" 2>/dev/null || true
   wait "$GUI_WATCH_PID" 2>/dev/null || true
 fi
 if [[ -n "$LAUNCH_PID" ]]; then
   # Identical to G07 WSL2 Owner: Nav2 lifecycle before launch SIGINT.
   # Only after the already-successful CI simulation Goal and odom dwell.
   # Task03 disposable native sensor-only positive control has NOT sent
   # any Goal: skip unrelated managed Nav2 lifecycle shutdown. This avoids
   # a race in a world that is about to be discarded. Actual Moving Goal
   # still MUST obtain both lifecycle ACKs and CM child clean exit.
   if [[ "${AXIA_G07_TASK03_POSITIVE_ONLY:-0}" == 1
      && "${GITHUB_ACTIONS:-}" == true
      && "${AXIA_P0_SIM_ONLY:-0}" == 1
      && "${AXIA_G07_TASK03_ECM_WITNESS:-0}" == 1
      && "${AXIA_G07_CI_SIM_GOAL_ALLOWED:-0}" == 1
      && "${AXIA_G07_OWNER_STARTUP_PARITY:-0}" == 1
      && "$rc" == 0 ]]; then
     printf 'DISPOSABLE_NO_GOAL_DIRECT_SIGINT_CONFIRMED\n' \
       > "$OUT/task03_disposable_shutdown.marker"
     echo 'AXIA_G07_TASK03_NO_GOAL_DISPOSABLE_NATIVE_POSITIVE_SIGINT'
   elif [[ ( "${AXIA_G07_CI_SIM_GOAL_ALLOWED:-0}" == 1 || "$OWNER_MOVING" == 1 )
      && "${AXIA_G07_OWNER_STARTUP_PARITY:-0}" == 1
      && "$rc" == 0 ]]; then
     echo 'AXIA_G07_CI_MOVING_GOAL_ORDERED_SHUTDOWN_REQUIRED'
     if ! timeout --signal=TERM --kill-after=3s 82s \
          python3 tools/p2_g07_ordered_shutdown.py \
            --output "$OUT/g07_ordered_shutdown.json" --timeout-sec 60 \
            > "$OUT/g07_ordered_shutdown.log" 2>&1; then
       echo 'G07_MOVING_GOAL_ORDERED_SHUTDOWN_BLOCKED' >&2
       cat "$OUT/g07_ordered_shutdown.log" >&2 || true
       rc=3
     else
       cat "$OUT/g07_ordered_shutdown.log"
       echo 'G07_MOVING_GOAL_ORDERED_SHUTDOWN_ACK_BEFORE_SIGINT'
     fi
   fi
   # Owner parity: recorder remains active until official Nav2 shutdown;
   # close bag before sending launch SIGINT, just as WSL2 Owner does.
   if ! stop_owner_parity_bag; then rc=3; fi
   kill -INT -- "-$LAUNCH_PID" 2>/dev/null || true
   local launch_grace_steps=25
   if [[ "${AXIA_G07_TASK03_POSITIVE_ONLY:-0}" == 1
      && -f "$OUT/task03_disposable_shutdown.marker" ]]; then
     # Process exit budget only, NOT CM/Scan watchdog expansion.
     launch_grace_steps=$((G07_MANAGED_LAUNCH_EXIT_GRACE_SEC * 5 / 2))
     echo 'AXIA_G07_TASK03_NO_GOAL_DISPOSABLE_SIGINT_EXIT_BUDGET_26S'
   fi
   if [[ "${AXIA_G07_CI_OWNER_BAG_PARITY:-0}" == 1
      && "$rc" == 0
      && -f "$OUT/g07_ordered_shutdown.json" ]]; then
     launch_grace_steps=$((G07_MANAGED_LAUNCH_EXIT_GRACE_SEC * 5 / 2))
     echo 'G07_CI_MANAGED_LAUNCH_EXIT_26S Nav2_ACK_REQUIRED'
   fi
   # Actual student H01 rqt loop L2 #44063399501: all 4 Gazebo physical
   # stages and official Nav2 Path succeeded, but GUI+Nav2 teardown took
   # >10s. Reuse the pre-existing 26s managed exit budget ONLY for this
   # no-moving-Goal classroom run, including Ctrl+C. This is a PROCESS
   # shutdown grace, NOT an extension of CM 150ms or Scan 300ms safety TTL.
   if [[ "${AXIA_D07_H01_GUI_NO_GOAL:-0}" == 1
      && "${AXIA_D07_H01_TEACHING_LOOP:-0}" == 1 ]]; then
     launch_grace_steps=$((G07_MANAGED_LAUNCH_EXIT_GRACE_SEC * 5 / 2))
     echo 'D07_H01_TEACHING_MANAGED_LAUNCH_EXIT_26S_NO_GOAL'
   fi
   for ((i=0;i<launch_grace_steps;i++)); do launch_active || break; sleep .4; done
   if launch_active; then
     ps -eo pid,pgid,stat,args | awk -v pgid="$LAUNCH_PID" 'NR==1 || $2==pgid' \
       > "$OUT/teardown_processes.txt" 2>/dev/null || true
     echo 'G07_CI_LAUNCH_LIVE_AFTER_MANAGED_EXIT_BUDGET' >&2
     echo 'P2_L2_FORCED_TEARDOWN' > "$OUT/teardown.txt"
     rc=3
     kill -TERM -- "-$LAUNCH_PID" 2>/dev/null || true
     sleep 2
   else echo 'P2_L2_GRACEFUL_TEARDOWN' > "$OUT/teardown.txt"; fi
   if launch_active; then
     kill -KILL -- "-$LAUNCH_PID" 2>/dev/null || true
     echo 'P2_L2_FORCED_SIGKILL' >> "$OUT/teardown.txt"
     rc=3
   fi
   wait "$LAUNCH_PID" 2>/dev/null || true
   # Real public Gazebo #44220702329: the disposable NO_GOAL marker
   # previously existed only as .marker; downstream expected JSON.
   # Emit distinct NO_GOAL evidence AFTER actual graceful SIGINT teardown,
   # never implying Navigation/Localization lifecycle ACKs or moving L2.
   if [[ "${AXIA_G07_TASK03_POSITIVE_ONLY:-0}" == 1
      && -f "$OUT/task03_disposable_shutdown.marker"
      && "$rc" -eq 0
      && -f "$OUT/teardown.txt" ]] &&
      grep -Fxq 'P2_L2_GRACEFUL_TEARDOWN' "$OUT/teardown.txt"; then
     printf '%s\n' '{"schema":"axia.g07.task03.disposable_no_goal_sigint_v1","status":"DISPOSABLE_NO_GOAL_DIRECT_SIGINT_CONFIRMED","navigation_ack":false,"localization_ack":false,"goal_sent":false,"native_nav2_l2_pass":false,"certified_estop":false}' \
       > "$OUT/g07_ordered_shutdown.json"
     echo 'AXIA_G07_TASK03_NO_GOAL_DISPOSABLE_SIGINT_GRACEFUL_EVIDENCE_WRITTEN'
   fi
 fi
 # New exact-SHA, public-only simulation: evidence that CM truly exits
 # cleanly AFTER official managed lifecycle shutdown, not just a parent
 # shell exit 0 or Gazebo NO-GOAL readiness. Preserve old success evidence.
 if [[ "${AXIA_G07_SHUTDOWN_L2_ONLY:-0}" == 1
    || ( ( "${AXIA_G07_CI_SIM_GOAL_ALLOWED:-0}" == 1 || "$OWNER_MOVING" == 1 )
         && "${AXIA_G07_OWNER_STARTUP_PARITY:-0}" == 1
         && "${AXIA_G07_TASK03_POSITIVE_ONLY:-0}" != 1
         && "$rc" == 0 ) ]]; then
   if [[ ! -f "$OUT/g07_ordered_shutdown.json" ]]; then
     echo 'G07_REAL_SHUTDOWN_L2_NO_NAV2_ACK' >&2
     rc=3
   elif ! python3 tools/p2_g07_owner_shutdown_audit.py \
        --launch-log "$OUT/launch.log" \
        --live-log "$OUT/g07_ordered_shutdown.log" \
        --output "$OUT/g07_shutdown_audit.json"; then
     echo 'G07_REAL_SHUTDOWN_L2_CM_PROCESS_NONCLEAN' >&2
     rc=3
   elif [[ "$rc" -eq 0 ]];then
     echo 'G07_REAL_SHUTDOWN_L2_CM_CLEAN_EXIT_AFTER_NAV2_ACK_PASS'
     if [[ "${AXIA_G07_CI_SIM_GOAL_ALLOWED:-0}" == 1 ]]; then
       echo 'G07_MOVING_GOAL_CM_CLEAN_EXIT_AFTER_NAV2_ACK_PASS'
     fi
   fi
 fi
  if [[ "${AXIA_G07_CI_OWNER_BAG_PARITY:-0}" == 1 ]]; then
    # REAL rosbag SQLite evidence is mandatory; a fake marker is not enough.
    python3 - "$OUT/rosbag2" <<'PY' || rc=3
from pathlib import Path
import sqlite3,sys,json
p=Path(sys.argv[1])
assert (p/'metadata.yaml').is_file(), 'OWNER_PARITY_BAG_METADATA_MISSING'
files=list(p.glob('*.db3'))
assert len(files)==1, 'OWNER_PARITY_BAG_DB_MISSING'
c=sqlite3.connect('file:'+str(files[0])+'?mode=ro',uri=True)
assert c.execute('pragma quick_check').fetchone()[0]=='ok'
counts=dict(c.execute('select topics.name,count(messages.id) from topics left join messages on topics.id=messages.topic_id group by topics.name'))
need=('/clock','/scan','/odom','/cmd_vel_supervised','/cmd_vel_pre_guard','/axia/p2/base_guard')
for name in need:
    assert counts.get(name,0)>0,(name,counts.get(name))
print('G07_CI_OWNER_BAG_REAL_TOPIC_MESSAGES '+json.dumps({k:counts[k] for k in need},sort_keys=True))
PY
  fi
 (cd "$OUT" && find . -type f -not -name SHA256SUMS -printf '%P\0' | sort -z | xargs -0 -r sha256sum > SHA256SUMS)
 printf 'P2_L2_SMOKE_RC=%s\nEVIDENCE=%s\nG05_G06_G07_ACCEPTED=false\n' "$rc" "$OUT"
 exit "$rc"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
[[ -f /opt/ros/jazzy/setup.bash ]] || { echo 'ROS_JAZZY_REQUIRED' >&2; exit 2; }
set +u; source /opt/ros/jazzy/setup.bash; set -u
for cmd in ros2 colcon gz python3 setsid timeout; do command -v "$cmd" >/dev/null || exit 2; done
for pkg in nav2_bringup nav2_minimal_tb3_sim ros_gz_sim; do ros2 pkg prefix "$pkg" >/dev/null || exit 2; done
# Keep existing frozen P1 unchanged. New P2 package code built in overlay.
colcon build --base-paths ros2_ws/src --packages-select \
  axia_safety_supervisor axia_fault_injector axia_scenario_verifier \
  --event-handlers console_direct+ > "$OUT/build.log" 2>&1 || { echo 'P2_BUILD_BLOCKED'; exit 2; }
set +u; source install/setup.bash; set -u
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-56}"
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export GZ_PARTITION="${GZ_PARTITION:-axia_p2_ci_$$_$(date +%s)}"
if [[ "$SENSOR_NO_GOAL" == 1 ]];then
  # Do not force llvmpipe on the *sensor server*: capture actual WSLg
  # backend, unlike historical offscreen CI. No GUI/Gazebo new server.
  export QT_QPA_PLATFORM=offscreen AXIA_P0_SIM_ONLY=1
elif [[ "${AXIA_D07_H01_GUI_NO_GOAL:-0}" == 1 ]]; then
  # Explicit CLI/window mode; unlike existing CI H01 Gate this needs an
  # actual DISPLAY, never a spoofed GITHUB_ACTIONS=true on Owner WSL2.
  [[ -n "${DISPLAY:-}" && "${AXIA_G07_CI_SIM_GOAL_ALLOWED:-0}" != 1 ]] || {
    echo 'D07_H01_GUI_DISPLAY_OR_MOVING_GOAL_SCOPE_DENIED' >&2;exit 2;
  }
  export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}" LIBGL_ALWAYS_SOFTWARE=1 AXIA_P0_SIM_ONLY=1
elif [[ "$OWNER_MOVING" == 1 || "$CI_MOVING_GUI" == 1 ]];then
  export QT_QPA_PLATFORM=xcb AXIA_P0_SIM_ONLY=1
  if [[ "$CI_MOVING_GUI" == 1 ]];then export LIBGL_ALWAYS_SOFTWARE=1;else unset LIBGL_ALWAYS_SOFTWARE || true;fi
else
  export QT_QPA_PLATFORM=offscreen LIBGL_ALWAYS_SOFTWARE=1 AXIA_P0_SIM_ONLY=1
fi
# Owner-matched Jazzy/Harmonic core package and official-file parity.
# Bounded read-only check, only for the changed G07 no-Goal validation workflow.
if [[ "${AXIA_P2_G07_OWNER_PARITY_CHECK:-0}" == 1 ]]; then
  if ! python3 tools/p2_g07_owner_env_parity.py \
    --mode ci --output "$OUT/g07_userspace_parity.json" \
    > "$OUT/g07_userspace_parity.log" 2>&1; then
    cat "$OUT/g07_userspace_parity.log" >&2
    echo "P2_G07_NO_GOAL_CI_USERSPACE_PARITY_BLOCKED" >&2
    exit 2
  fi
  cat "$OUT/g07_userspace_parity.log"
fi

printf 'ROS_DOMAIN_ID=%s\nGZ_PARTITION=%s\n' "$ROS_DOMAIN_ID" "$GZ_PARTITION" > "$OUT/runtime.txt"
git -c safe.directory="$ROOT" rev-parse HEAD > "$OUT/source_sha.txt" 2>/dev/null || echo 'UNVERSIONED_LOCAL_SOURCE' > "$OUT/source_sha.txt"
LAUNCH="$ROOT/ros2_ws/src/axia_safety_bringup/launch/axia_tb3_p2.launch.py"
ros2 launch "$LAUNCH" --show-args > "$OUT/launch_args.log" 2>&1 || { echo 'P2_LAUNCH_ARGS_BLOCKED'; exit 2; }
# For physical G07 only, reuse the official WORLD with Contact system
# overlay; do not replace Nav2, its robot spawn, or the world layout.
# S03 experimental simulation ONLY: allow the existing /safety/scan relay
# services on this one exact scoped public Actions run. Default remains OFF.
AXIA_FAULT_LAUNCH_ALLOWED=false
if [[ "${AXIA_P3_S03_CI_COMPOUND_ALLOWED:-0}" == 1 ]]; then
  [[ "${GITHUB_ACTIONS:-}" == true
     && "${AXIA_P0_SIM_ONLY:-0}" == 1
     && "${AXIA_P3_S03_CI_CM_PAUSE_ALLOWED:-0}" == 1
     && "${AXIA_G07_CI_SIM_GOAL_ALLOWED:-0}" == 1
     && "${AXIA_G07_CI_OWNER_BAG_PARITY:-0}" == 1
     && "${AXIA_G07_OWNER_STARTUP_PARITY:-0}" == 1
     && "${AXIA_P3_S01_CI_GOAL_ALLOWED:-0}" != 1
     && "${AXIA_P3_S05_CI_GOAL_ALLOWED:-0}" != 1 ]] || {
    echo 'AXIA_P3_S03_FAULT_LAUNCH_SCOPE_DENIED'; exit 2;
  }
  AXIA_FAULT_LAUNCH_ALLOWED=true
fi
LAUNCH_ARGS=(headless:=True use_rviz:=False autostart:=false
   use_composition:=False use_respawn:=False allow_fault_injection:="$AXIA_FAULT_LAUNCH_ALLOWED")
# GUI H01 stays headless throughout the original LifecycleManager startup.
# The client is connected AFTER staged Nav2 readiness; never a 2nd server.
# S04 fixture P/N/U is a PUBLIC-SIM-ONLY default-disabled Supervisor adapter;
# never enable for existing G07, S01, S03, S05 or Owner without approval.
if [[ "${AXIA_P3_S04_CI_PNU_ALLOWED:-0}" == 1 ]]; then
  [[ "${GITHUB_ACTIONS:-}" == true
     && "${AXIA_P0_SIM_ONLY:-0}" == 1
     && "${AXIA_G07_CI_SIM_GOAL_ALLOWED:-0}" == 1
     && "${AXIA_G07_CI_OWNER_BAG_PARITY:-0}" == 1
     && "${AXIA_G07_OWNER_STARTUP_PARITY:-0}" == 1
     && "${AXIA_P3_S01_CI_GOAL_ALLOWED:-0}" != 1
     && "${AXIA_P3_S03_CI_COMPOUND_ALLOWED:-0}" != 1
     && "${AXIA_P3_S05_CI_GOAL_ALLOWED:-0}" != 1 ]] || {
    echo 'AXIA_P3_S04_FIXTURE_RISK_LAUNCH_SCOPE_DENIED' >&2; exit 2;
  }
  LAUNCH_ARGS+=(p3_fixture_risk_bridge_enabled:=true)
fi

if [[ "${AXIA_P2_G07_PHYSICAL_PREFLIGHT:-0}" == 1 ]]; then
  WORLD="$(ros2 pkg prefix nav2_minimal_tb3_sim)/share/nav2_minimal_tb3_sim/worlds/tb3_sandbox.sdf.xacro"
  python3 tools/p2_l3_world_overlay.py --source "$WORLD" \
    --output "$OUT/g07_world.sdf.xacro" --manifest "$OUT/g07_world_manifest.json" \
    > "$OUT/g07_world_overlay.log" 2>&1 || {
    echo "G07_PHYSICAL_WORLD_OVERLAY_BLOCKED" >&2
    exit 2
  }
  # H01 connects Gazebo GUI only after official Nav2 becomes ready.
  # In the upstream world xacro, headless:=True removes SceneBroadcaster,
  # leaving an otherwise healthy server /scan and Nav2 but a BLANK 3D GUI.
  # Keep staged headless startup and all P2/G07 motion cases untouched.
  if [[ "${AXIA_D07_H01_GUI_NO_GOAL:-0}" == 1
     || "$OWNER_MOVING" == 1 || "$CI_MOVING_GUI" == 1 ]];then
    [[ "${AXIA_P0_SIM_ONLY:-0}" == 1
       && ( ( "${AXIA_D07_H01_GUI_NO_GOAL:-0}" == 1
              && "${AXIA_G07_CI_SIM_GOAL_ALLOWED:-0}" == 0 )
            || "$OWNER_MOVING" == 1 || "$CI_MOVING_GUI" == 1 ) ]] || {
      echo 'G07_TASK04_SCENE_BROADCASTER_SCOPE_DENIED' >&2;exit 2;
    }
    python3 tools/d07_h01_scene_broadcaster_overlay.py \
      --source "$OUT/g07_world.sdf.xacro" \
      --output "$OUT/d07_gui_scene_world.sdf.xacro" \
      --manifest "$OUT/d07_gui_scene_world_manifest.json" || {
        echo D07_H01_SCENE_BROADCASTER_WORLD_FAIL_CLOSED_NO_GOAL >&2
        exit 2
      }
    LAUNCH_ARGS+=(world:="$OUT/d07_gui_scene_world.sdf.xacro")
  else
    LAUNCH_ARGS+=(world:="$OUT/g07_world.sdf.xacro")
  fi
  # G07 exact Owner profile: SAME temporary official Waffle 10Hz SDF
  # for CI staged no-Goal, CI moving Goal, and Owner WSLg moving Goal.
  # Never mutate /opt/ros; Guard/Scan safety TTL stay unchanged.
  if [[ "${AXIA_G07_CI_SIM_GOAL_ALLOWED:-0}" == 1
     || "${AXIA_G07_OWNER_STARTUP_PARITY:-0}" == 1 ]]; then
    WAFFLE="$(ros2 pkg prefix nav2_minimal_tb3_sim)/share/nav2_minimal_tb3_sim/urdf/gz_waffle.sdf.xacro"
    if ! python3 tools/p2_g07_demo_lidar_overlay.py \
       --source "$WAFFLE" \
       --output "$OUT/g07_demo_waffle.sdf.xacro" \
       --manifest "$OUT/g07_demo_waffle_manifest.json"; then
      echo 'AXIA_G07_CI_DEMO_LIDAR_OVERLAY_BLOCKED_NO_GOAL' >&2
      exit 2
    fi
    # Explicit D07 SIM-only no-moving-Goal teaching hypothesis:
    # the OFFICIAL Waffle has 1cm Gaussian GPU LiDAR noise, confirmed in
    # pinned Jazzy SDF. For this read-only GUI demo only, use a *second*
    # session-local copy, preserving the original G07 10Hz overlay and all
    # official Nav2/Collision Monitor/safety TTL settings unchanged.
    DEMO_WAFFLE="$OUT/g07_demo_waffle.sdf.xacro"
    if [[ "${AXIA_D07_H01_GUI_NO_GOAL:-0}" == 1 ]]; then
      [[ "${AXIA_P0_SIM_ONLY:-0}" == 1
         && "${AXIA_G07_CI_SIM_GOAL_ALLOWED:-0}" == 0 ]] || {
        echo D07_GUI_NOISE_PROFILE_DENIED_OUTSIDE_READONLY_SIM >&2
        exit 2
      }
      python3 tools/d07_h01_gui_lidar_noise_overlay.py \
        --source "$DEMO_WAFFLE" \
        --output "$OUT/d07_gui_waffle.sdf.xacro" \
        --manifest "$OUT/d07_gui_waffle_manifest.json" || {
        echo D07_GUI_NOISE_PROFILE_NO_SOURCE_VERIFICATION >&2
        exit 2
      }
      DEMO_WAFFLE="$OUT/d07_gui_waffle.sdf.xacro"
      echo 'D07_H01_GUI_SIM_NOISE_FREE_NOT_REAL_SENSOR_SAFETY_NO_GOAL'
    fi
    LAUNCH_ARGS+=(robot_sdf:="$DEMO_WAFFLE")
    if [[ "${AXIA_G07_OWNER_STARTUP_PARITY:-0}" == 1 ]]; then
      # Same ros2 launch/staged runner and G07 10Hz LiDAR as WSL2.
      # CI offscreen display is NOT equivalent to WSLg GUI scheduler.
      echo 'G07_SHARED_STARTUP_PROFILE_OWNER_PARITY LIDAR_10HZ WSLG_KERNEL_RENDER_NOT_EQUIVALENT NO_GOAL'
    fi
  fi
fi
setsid ros2 launch "$LAUNCH" "${LAUNCH_ARGS[@]}" \
   > "$OUT/launch.log" 2>&1 &
LAUNCH_PID=$!
# Owner WSL2 always runs the following real 14-topic SQLite recording
# concurrently with Gazebo, Nav2 and its two-worker Observer.
if [[ "${AXIA_G07_CI_OWNER_BAG_PARITY:-0}" == 1 ]]; then
  [[ ( ( "${GITHUB_ACTIONS:-}" == true
          && "${AXIA_G07_CI_SIM_GOAL_ALLOWED:-0}" == 1 )
        || ( "$OWNER_MOVING" == 1
             && "${GITHUB_ACTIONS:-}" != true
             && "${AXIA_G07_CI_SIM_GOAL_ALLOWED:-0}" != 1
             && -t 0 && -r /dev/tty ) )
     && "${AXIA_P0_SIM_ONLY:-0}" == 1
     && "${AXIA_P2_G07_PHYSICAL_PREFLIGHT:-0}" == 1
     && "${AXIA_G07_OWNER_STARTUP_PARITY:-0}" == 1 ]] || {
    echo 'G07_TASK04_BAG_AUTHORITY_BLOCKED_NO_GOAL' >&2
    exit 2
  }
  # G07 CI-only: isolate heavy SQLite evidence I/O from the real
  # CM/Guard callback cores. The same LAST allowed core is used for the
  # already low-priority Gazebo STOP transport CLI. No TTL or ROS QoS change.
  G07_EVIDENCE_CPU="$(python3 -c 'import os; assert len(os.sched_getaffinity(0))>=2; print(max(os.sched_getaffinity(0)))')" || {
    echo 'G07_CI_EVIDENCE_CPU_PARITY_BLOCKED_NO_GOAL' >&2
    exit 2
  }
  setsid nice -n 10 taskset -c "$G07_EVIDENCE_CPU" ros2 bag record --include-hidden-topics -s sqlite3 \
    --qos-profile-overrides-path "$ROOT/configs/p1_t08_action_status_qos.yaml" \
    -o "$OUT/rosbag2" /clock /tf /tf_static /map /scan /safety/scan /odom \
    /cmd_vel_smoothed /cmd_vel_supervised /cmd_vel_pre_guard /cmd_vel \
    /axia/safety/state /axia/p2/base_guard /navigate_to_pose/_action/status \
    > "$OUT/rosbag.log" 2>&1 & BAG_PID=$!
  echo 'G07_CI_OWNER_BAG_RECORDING_STARTED actual_topics=14'
fi
# Public CI and Owner use precisely the same G07 staged startup runner.
# The only admitted platform variance is offscreen CI vs WSLg Owner GUI.
if [[ "${AXIA_G07_OWNER_STARTUP_PARITY:-0}" == 1 ]]; then
  if [[ "$SENSOR_NO_GOAL" == 1 ]];then
    [[ "${GITHUB_ACTIONS:-}" != true
       && "$OWNER_MOVING" == 0 && "$CI_MOVING_GUI" == 0
       && "${AXIA_G07_CI_SIM_GOAL_ALLOWED:-0}" == 0
       && "${AXIA_P2_G07_PHYSICAL_PREFLIGHT:-0}" == 1
       && "${AXIA_P0_SIM_ONLY:-0}" == 1
       && "${ROS_DISTRO:-}" == jazzy
       && "${GZ_PARTITION:-}" == axia_p2_* ]] || {
      echo 'G07_WSLG_SENSOR_NO_GOAL_STAGED_START_DENIED' >&2; exit 2;
    }
  elif [[ "${AXIA_D07_H01_GUI_NO_GOAL:-0}" == 1 ]]; then
    # Local WSL2 stationary GUI may reuse the EXISTING shared staged startup.
    # This is NOT permission for a moving Goal, not a GITHUB_ACTIONS spoof.
    [[ "${AXIA_G07_CI_SIM_GOAL_ALLOWED:-0}" != 1
       && "${AXIA_P2_G07_PHYSICAL_PREFLIGHT:-0}" == 1
       && "${AXIA_P0_SIM_ONLY:-0}" == 1
       && "${ROS_DISTRO:-}" == jazzy
       && "${GZ_PARTITION:-}" == axia_p2_* ]] || {
      echo 'D07_H01_GUI_WSL2_SHARED_STARTUP_DENIED_NO_GOAL' >&2
      exit 2
    }
  else
    [[ ( "${GITHUB_ACTIONS:-}" == true
          && "${AXIA_G07_CI_SIM_GOAL_ALLOWED:-0}" == 1 )
       || ( "$OWNER_MOVING" == 1
            && "${GITHUB_ACTIONS:-}" != true
            && "${AXIA_G07_CI_SIM_GOAL_ALLOWED:-0}" != 1
            && -t 0 && -r /dev/tty ) ]] &&
    [[ "${AXIA_P2_G07_PHYSICAL_PREFLIGHT:-0}" == 1
       && "${AXIA_P0_SIM_ONLY:-0}" == 1 ]] || {
      echo 'G07_TASK04_STARTUP_AUTHORITY_BLOCKED_NO_GOAL' >&2
      exit 2
    }
  fi
  STAGED_START=(bash scripts/p2_g07_shared_staged_startup.sh
                "$OUT/startup_verdict.json" "$OUT/initialpose.json")
else
  STAGED_START=(timeout --signal=TERM --kill-after=5s 480s
                python3 tools/p2_staged_no_goal.py
                --output "$OUT/startup_verdict.json"
                --initialpose-output "$OUT/initialpose.json"
                --allow-sim-initialpose)
fi
# D07 GUI no-Goal L2 #43725213519: first failed boundary was
# NAVIGATION_START REJECTED while /planner_server was not discoverable.
# Native lifecycle startup is invoked ONLY after these real ROS services
# are advertised. This wait is GUI-only startup readiness, not safety TTL.
if [[ "${AXIA_D07_H01_GUI_NO_GOAL:-0}" == 1 ]]; then
  timeout --signal=TERM --kill-after=2s 55s python3 - <<'PY'
import rclpy,time,sys
from lifecycle_msgs.srv import GetState
rclpy.init()
node=rclpy.create_node("d07_h01_gui_pre_navigation_service_readiness")
services=("/planner_server/get_state",
          "/controller_server/get_state",
          "/bt_navigator/get_state")
clients={service:node.create_client(GetState,service)
         for service in services}
deadline=time.monotonic()+48.0
try:
    while time.monotonic()<deadline:
        absent=[service for service,client in clients.items()
                if not client.service_is_ready()]
        if not absent:
            print("D07_H01_GUI_NAV_SERVICES_DISCOVERED "+
                  " ".join(services),flush=True)
            break
        rclpy.spin_once(node,timeout_sec=.3)
    else:
        print("D07_H01_GUI_NAV_SERVICES_TIMEOUT_NO_GOAL missing="+
              ",".join(absent),flush=True)
        sys.exit(2)
finally:
    for client in clients.values():
        node.destroy_client(client)
    node.destroy_node()
    rclpy.shutdown()
PY
fi
if "${STAGED_START[@]}" > "$OUT/staged_startup.log" 2>&1; then
  echo 'P2_NO_GOAL_STATIC_AND_RUNTIME_READINESS_OBSERVED'
else
  echo 'P2_NO_GOAL_BLOCKED: see staged_startup.log/launch.log' >&2
  grep -E 'P2_STAGED_NO_GOAL_BLOCKED|P2_STAGED_NO_GOAL_ERROR|AXIA_D07_H01_FIRST_CM_MANAGER_STARTUP_FAILURE' "$OUT/staged_startup.log" || true
  if [[ "${GITHUB_ACTIONS:-}" == true
     && "${AXIA_G07_CI_SIM_GOAL_ALLOWED:-0}" == 1
     && "${AXIA_P2_G07_PHYSICAL_PREFLIGHT:-0}" == 1
     && "${AXIA_P0_SIM_ONLY:-0}" == 1 ]] \
     && grep -q 'CLOCK_MISSING' "$OUT/staged_startup.log"; then
    # Bounded read-only evidence of the FIRST failed startup stage.
    # No Goal, no fault, no safety bypass; retain source logs in CI only.
    echo 'AXIA_G07_CI_CLOCK_FIRST_FAILURE_DIAGNOSTICS' >&2
    if kill -0 "$LAUNCH_PID" 2>/dev/null; then
      echo 'AXIA_G07_CI_LAUNCH_PID_ALIVE=true' >&2
    else
      echo 'AXIA_G07_CI_LAUNCH_PID_ALIVE=false' >&2
    fi
    if timeout 8s ros2 topic list --no-daemon 2>/dev/null | grep -Fxq '/clock'; then
      echo 'AXIA_G07_CI_CLOCK_TOPIC_PRESENT=true' >&2
    else
      echo 'AXIA_G07_CI_CLOCK_TOPIC_PRESENT=false' >&2
    fi
    echo 'AXIA_G07_CI_CLOCK_TIMEOUT_NO_GOAL' >&2
  fi
  exit 2
fi
# Bounded Owner WSLg LiDAR truth: THE original G07 physical world, original
# 10Hz Waffle profile, no D07 sensor noise overlay, no Gazebo pose change,
# no Nav2 Goal and no CI/Owner Moving authority. Clean up only owned PIDs.
if [[ "$SENSOR_NO_GOAL" == 1 ]]; then
  duration="${AXIA_WSLG_SENSOR_PROBE_DURATION_SEC:-20}"
  [[ "$duration" =~ ^[0-9]+$ && "$duration" -ge 10 && "$duration" -le 30 ]] || {
    echo 'G07_WSLG_SENSOR_DURATION_INVALID_NO_GOAL' >&2;exit 2;
  }
  if timeout --signal=TERM --kill-after=5s 50s \
      python3 tools/g07_wslg_no_goal_sensor_probe.py \
        --duration-sec "$duration" \
        --output "$OUT/g07_wslg_sensor_truth.json" \
        > "$OUT/g07_wslg_sensor_truth.log" 2>&1; then
    cat "$OUT/g07_wslg_sensor_truth.log"
    echo 'G07_WSLG_NO_GOAL_SENSOR_WINDOW_CANDIDATE_NO_MOVING_ACCEPTANCE'
    exit 0
  else
    cat "$OUT/g07_wslg_sensor_truth.log" >&2 || true
    echo 'G07_WSLG_NO_GOAL_SENSOR_UNSAFE_HOLD' >&2
    exit 3
  fi
fi
# D07-H01 GUI renderers AFTER Nav2 readiness, NOT during CM get_state or
# lifecycle bond startup. Gazebo Harmonic -g is a GUI-only client joining
# the existing isolated GZ_PARTITION, never a second simulation server.
# No moving Goal, no safety TTL/parameters altered.
if [[ "${AXIA_D07_H01_GUI_NO_GOAL:-0}" == 1 ]]; then
  [[ -n "${DISPLAY:-}" && -r "$ROOT/training/block_B/instructor/rviz/d07_h01_physical_replan.rviz" ]] || {
    echo 'D07_H01_GUI_RENDERER_REQUIREMENTS_MISSING_NO_GOAL' >&2;exit 2;
  }
  # Start a zero-GUI-cost watcher; geometry writes the marker ONLY after
  # two genuine strictly stable free official Costmap samples. This shares
  # the exact same H01 session and keeps GUI lifetime process-group owned.
  GUI_MARKER="$OUT/d07_h01_geometry/gui_after_free_baseline.ready"
  PRIVATE_SHA="$(git -c safe.directory="$ROOT" rev-parse HEAD)"
  if [[ "${AXIA_D07_H01_GPU_GUI_TRIAL:-0}" == 1 ]]; then
    # This EXACT standalone program is executed by public CI with mocked
    # gz/RViz. The older inlined watcher had NO start acknowledgement;
    # Owner mVW had an empty log from spawn to DDS timeout.
    GUI_WATCH_ACK="$OUT/d07_gui_watcher_started.txt"
    GUI_WATCH_EXIT="$OUT/d07_gui_watcher_exit.txt"
    setsid bash "$ROOT/tools/d07_h01_gpu_gui_watcher.sh" \
      "$GUI_MARKER" \
      "$ROOT/training/block_B/instructor/rviz/d07_h01_physical_replan.rviz" \
      "$PRIVATE_SHA" "$OUT/d07_gui_transport_topics.txt" "$ROOT" \
      "$GUI_WATCH_ACK" "$GUI_WATCH_EXIT" \
      > "$OUT/d07_gui_watcher.log" 2>&1 &
  else
    # Keep existing CPU GUI default frozen; change only GPU trial.
  setsid bash -c '
    set -Eeuo pipefail
    marker="$1"; rviz_cfg="$2"; required_sha="$3"
    for ((i=0;i<1800;i++)); do
      [[ -f "$marker" ]] && break
      sleep .2
    done
    if [[ ! -f "$marker" || "$(cat "$marker")" != "$required_sha" ]]; then
      echo D07_H01_GUI_AFTER_FREE_BASELINE_MARKER_MISSING_NO_GOAL >&2
      exit 2
    fi
    echo "D07_H01_GUI_AFTER_FREE_BASELINE_MARKER sha=$required_sha"
    echo "D07_H01_GUI_GZ_PARTITION=${GZ_PARTITION:-unset}"
    # Preserve the formerly successful CPU-rendered default. The explicit
    # WSLg trial changes ONLY standalone GUI children, not the Gazebo server,
    # official Nav2, CM, timing TTL, Goal or original simulation files.
    if [[ "${AXIA_D07_H01_GPU_GUI_TRIAL:-0}" == 1 ]]; then
      [[ "${AXIA_D07_H01_GUI_NO_GOAL:-0}" == 1
         && "${AXIA_P0_SIM_ONLY:-0}" == 1
         && "${AXIA_G07_CI_SIM_GOAL_ALLOWED:-0}" != 1 ]] || {
         echo D07_H01_GUI_GPU_TRIAL_SCOPE_DENIED_NO_GOAL >&2; exit 2;
      }
      echo D07_H01_GUI_GPU_TRIAL_ONLY NO_GOAL_NOT_ESTOP
      echo "D07_H01_GUI_TRANSPORT_PARTITION=${GZ_PARTITION:-unset}"
      timeout 10s gz topic -l > "$4" 2>&1 || {
        echo D07_H01_GUI_TRANSPORT_TOPIC_PROBE_FAILED >&2; exit 2;
      }
      # Gazebo Sim server publishes clock+stats. scene/info is a
      # SERVICE and must NOT be demanded from 'gz topic -l'. Real Owner
      # t5 provided both topics yet the old gate rejected the world.
      if ! python3 "$5/tools/d07_h01_gz_world_topic_gate.py" \
           --topics-file "$4"; then
        echo D07_H01_GUI_TRANSPORT_WORLD_TOPIC_GATE_FAILED >&2
        exit 2
      fi
      echo D07_H01_GUI_SERVER_WORLD_DISCOVERED_NOT_GUI_RENDER_PROOF
      # WSLg D3D12 backend is opt-in and MUST be preflighted with glxinfo.
      # Scope D3D12 to the GUI children. No global ~/.bashrc dependency
      # and no D3D12 override on the Gazebo physics/sensor server.
      env -u LIBGL_ALWAYS_SOFTWARE \
        GALLIUM_DRIVER=d3d12 \
        MESA_D3D12_DEFAULT_ADAPTER_NAME="${AXIA_D07_H01_GPU_ADAPTER:-NVIDIA}" \
        gz sim -g -v 4 &
      env -u LIBGL_ALWAYS_SOFTWARE \
        GALLIUM_DRIVER=d3d12 \
        MESA_D3D12_DEFAULT_ADAPTER_NAME="${AXIA_D07_H01_GPU_ADAPTER:-NVIDIA}" \
        rviz2 -d "$rviz_cfg" --ros-args -p use_sim_time:=true &
    else
      # Original L2-proven behavior, identical when trial flag is absent.
      gz sim -g &
      rviz2 -d "$rviz_cfg" --ros-args -p use_sim_time:=true &
    fi
    wait
  ' _ "$GUI_MARKER" "$ROOT/training/block_B/instructor/rviz/d07_h01_physical_replan.rviz" "$PRIVATE_SHA" "$OUT/d07_gui_transport_topics.txt" "$ROOT" \
    > "$OUT/d07_gui_watcher.log" 2>&1 &
  fi
  GUI_WATCH_PID=$!
  if [[ "${AXIA_D07_H01_GPU_GUI_TRIAL:-0}" == 1 ]]; then
    # Bound spawn latency only; never relax Nav2 or safety TTL.
    for ((ack_i=0;ack_i<30;ack_i++)); do
      [[ -s "$GUI_WATCH_ACK" ]] && break
      kill -0 "$GUI_WATCH_PID" 2>/dev/null || break
      sleep .1
    done
    if [[ ! -s "$GUI_WATCH_ACK" ]] || ! kill -0 "$GUI_WATCH_PID" 2>/dev/null; then
      echo 'D07_H01_GUI_WATCHER_SPAWN_ACK_ABSENT' >&2
      cat "$OUT/d07_gui_watcher.log" >&2 || true
      [[ ! -f "$GUI_WATCH_EXIT" ]] || cat "$GUI_WATCH_EXIT" >&2
      exit 2
    fi
    echo "D07_H01_GUI_WATCHER_SPAWN_ACK_VERIFIED pid=$GUI_WATCH_PID"
  fi
  echo "D07_H01_GUI_RENDERERS_AFTER_NAV2_READY watcher_pid=$GUI_WATCH_PID awaiting_stable_free_baseline=1 NO_GOAL"
fi
# Client-only GUI: attach after real shared staged Nav2 readiness.
# Gazebo SERVER remains owned solely by the original ros2 launch process.
if [[ "$OWNER_MOVING" == 1 || "$CI_MOVING_GUI" == 1 ]];then
  [[ -r "$ROOT/training/block_B/instructor/rviz/d07_h01_physical_replan.rviz" ]] || {
    echo 'G07_TASK04_RVIZ_CONFIG_MISSING_NO_GOAL' >&2;exit 2;
  }
  setsid gz sim -g > "$OUT/task04_gazebo_gui.log" 2>&1 &
  MOVING_GAZEBO_GUI_PID=$!
  setsid rviz2 -d "$ROOT/training/block_B/instructor/rviz/d07_h01_physical_replan.rviz" \
    --ros-args -p use_sim_time:=true > "$OUT/task04_rviz.log" 2>&1 &
  MOVING_RVIZ_PID=$!
  sleep 3
  kill -0 "$MOVING_GAZEBO_GUI_PID" "$MOVING_RVIZ_PID" 2>/dev/null || {
    echo 'G07_TASK04_GUI_CLIENT_DIED_BEFORE_GOAL' >&2;exit 2;
  }
  echo 'AXIA_G07_TASK04_GAZEBO_SERVER_SINGLE_GUI_CLIENTS_ATTACHED'
fi
# New G07 shutdown-only regression: reuse the staged REAL Gazebo/Nav2
# no-Goal session, avoid re-running the previously successful moving L2.
# Explicit public Actions-only admission; never use this shortcut on Owner.
if [[ "${AXIA_G07_SHUTDOWN_L2_ONLY:-0}" == 1 ]];then
  [[ "${GITHUB_ACTIONS:-}" == true
     && "${AXIA_P2_G07_PHYSICAL_PREFLIGHT:-0}" == 1
     && "${AXIA_P0_SIM_ONLY:-0}" == 1
     && "${AXIA_G07_CI_SIM_GOAL_ALLOWED:-0}" != 1 ]] || {
    echo 'G07_SHUTDOWN_L2_NO_GOAL_SCOPE_INVALID' >&2;exit 2;
  }
  python3 - "$OUT/startup_verdict.json" <<'PY'
import json,sys
v=json.load(open(sys.argv[1]))
assert v['status']=='SMOKE_READY' and v['goal_sent'] is False
assert v['gate_accepted'] is False and v['fault_injected'] is False
PY
  echo 'G07_SHUTDOWN_L2_NO_GOAL REAL_CM_ACTIVE_BEFORE_SHUTDOWN'
  if ! timeout --signal=TERM --kill-after=3s 82s \
      python3 tools/p2_g07_ordered_shutdown.py \
        --output "$OUT/g07_ordered_shutdown.json" --timeout-sec 60 \
        > "$OUT/g07_ordered_shutdown.log" 2>&1;then
    cat "$OUT/g07_ordered_shutdown.log" >&2 || true
    echo 'G07_REAL_NAV2_ORDERED_SHUTDOWN_BLOCKED_BEFORE_SIGINT' >&2
    exit 3
  fi
  cat "$OUT/g07_ordered_shutdown.log"
  echo 'G07_REAL_NAV2_ORDERED_SHUTDOWN_ACK_BEFORE_SIGINT'
  exit 0
fi

# D07-H01 Instructor-only no-moving-Goal GUI, disabled unless wrapper opts in.
# Must be BEFORE the CI-only moving Goal dispatch; no CI-only bypass/flag.
if [[ "${AXIA_D07_H01_GUI_NO_GOAL:-0}" == 1 ]]; then
  [[ "${AXIA_G07_CI_SIM_GOAL_ALLOWED:-0}" != 1
     && "${AXIA_P2_G07_PHYSICAL_PREFLIGHT:-0}" == 1
     && "${AXIA_G07_OWNER_STARTUP_PARITY:-0}" == 1
     && "${AXIA_P0_SIM_ONLY:-0}" == 1
     && "${AXIA_D07_H01_GEOMETRY_ONLY:-0}" != 1
     && "${AXIA_P3_S01_CI_GOAL_ALLOWED:-0}" != 1
     && "${AXIA_P3_S03_CI_COMPOUND_ALLOWED:-0}" != 1
     && "${AXIA_P3_S04_CI_PNU_ALLOWED:-0}" != 1
     && "${AXIA_P3_S05_CI_GOAL_ALLOWED:-0}" != 1 ]] || {
    echo 'D07_H01_GUI_SCOPE_DENIED_NO_MOVING_GOAL' >&2;exit 2;
  }
  timeout --signal=TERM --kill-after=5s 75s \
    python3 tools/p2_g07_owner_pregoal_l2.py --output "$OUT/d07_gui_pregoal" \
    > "$OUT/d07_gui_pregoal.log" 2>&1 || {
    tail -n 70 "$OUT/d07_gui_pregoal.log" >&2;exit 2;
  }
  EXPECTED_CI_SHA="$(git -c safe.directory="$ROOT" rev-parse HEAD)"
  timeout --signal=TERM --kill-after=10s 360s \
    python3 tools/d07_h01_geometry_l2.py \
      --startup "$OUT/startup_verdict.json" \
      --pregoal "$OUT/d07_gui_pregoal/owner_pregoal_l2.json" \
      --source-sha "$EXPECTED_CI_SHA" \
      --output "$OUT/d07_h01_geometry" --gui \
    > "$OUT/d07_h01_geometry.log" 2>&1 || {
    # Diagnose the earliest GUI process transition before the secondary
    # missing DDS/RViz subscriber exception. Preserve all raw evidence.
    if [[ "${AXIA_D07_H01_GPU_GUI_TRIAL:-0}" == 1 ]]; then
      if [[ -s "${GUI_WATCH_EXIT:-}" ]] || ! kill -0 "$GUI_WATCH_PID" 2>/dev/null; then
        echo 'D07_H01_FIRST_GUI_FAILURE_PRECEDES_RVIZ_SUBSCRIBER' >&2
        cat "$OUT/d07_gui_watcher.log" >&2 || true
        [[ ! -s "${GUI_WATCH_EXIT:-}" ]] || cat "$GUI_WATCH_EXIT" >&2
      elif [[ ! -s "$OUT/d07_gui_watcher.log" ]]; then
        echo 'D07_H01_GUI_WATCHER_LOG_EMPTY_WHILE_PROCESS_LIVE_UNRESOLVED' >&2
      fi
    fi
    tail -n 120 "$OUT/d07_h01_geometry.log" >&2
    echo 'D07_H01_GUI_GEOMETRY_BLOCKED_NO_GOAL' >&2;exit 2;
  }
  tail -n 100 "$OUT/d07_h01_geometry.log"
  echo 'D07_H01_GUI_H01_GEOMETRY_RETURNED_NO_GOAL'
  # New classroom mode starts ONLY AFTER unchanged real 3-phase H01 L2
  # evidence passes. It owns no motor authority and retains official Nav2.
  # Original finite L2 remains the default for any non-teaching runner.
  if [[ "${AXIA_D07_H01_TEACHING_LOOP:-0}" == 1 ]]; then
    [[ "${AXIA_D07_H01_GUI_NO_GOAL:-0}" == 1
       && "${AXIA_G07_CI_SIM_GOAL_ALLOWED:-0}" == 0 ]] || {
      echo D07_H01_TEACHING_MOVING_GOAL_SCOPE_DENIED >&2; exit 3;
    }
    max_cycles="${AXIA_D07_H01_TEACHING_MAX_CYCLES:-0}"
    [[ "$max_cycles" == 0 || ( "$max_cycles" == 1
       && "${GITHUB_ACTIONS:-}" == true ) ]] || {
      echo D07_H01_TEACHING_MAX_CYCLES_SCOPE_DENIED >&2; exit 3;
    }
    # WSL2: intentionally NO timeout, Ctrl+C ends the session through
    # this shell's existing owned-process cleanup and native Nav2 shutdown.
    # CI: precisely ONE real physical 4-position cycle, then bounded exit.
    if [[ "$max_cycles" == 1 ]]; then
      timeout --signal=TERM --kill-after=10s 240s \
        python3 tools/d07_h01_teaching_loop.py \
          --evidence "$OUT/d07_h01_geometry" \
          --source-sha "$PRIVATE_SHA" \
          --hold-s "$AXIA_D07_GUI_HOLD_S" --max-cycles 1 \
        > "$OUT/d07_h01_teaching_loop.log" 2>&1 || {
          tail -n 65 "$OUT/d07_h01_teaching_loop.log" >&2
          echo D07_H01_TEACHING_REAL_CYCLE_BLOCKED >&2;exit 3;
        }
    else
      python3 tools/d07_h01_teaching_loop.py \
        --evidence "$OUT/d07_h01_geometry" \
        --source-sha "$PRIVATE_SHA" \
        --hold-s "$AXIA_D07_GUI_HOLD_S" \
        > "$OUT/d07_h01_teaching_loop.log" 2>&1 || {
          tail -n 65 "$OUT/d07_h01_teaching_loop.log" >&2
          echo D07_H01_TEACHING_REAL_CYCLE_BLOCKED >&2;exit 3;
        }
    fi
    tail -n 14 "$OUT/d07_h01_teaching_loop.log"
    echo 'D07_H01_TEACHING_LOOP_FINISHED_NO_MOVING_GOAL'
  fi
  exit 0
fi

# Owner Moving reuses the unchanged public-CI physical scenario.
# CI authority and Owner controlling-TTY authority never overlap.
if [[ "${AXIA_G07_CI_SIM_GOAL_ALLOWED:-0}" == 1 || "$OWNER_MOVING" == 1 ]];then
  [[ ( ( "${GITHUB_ACTIONS:-}" == true
          && "${AXIA_G07_CI_SIM_GOAL_ALLOWED:-0}" == 1
          && "$OWNER_MOVING" == 0 )
        || ( "${GITHUB_ACTIONS:-}" != true
             && "${AXIA_G07_CI_SIM_GOAL_ALLOWED:-0}" != 1
             && "$OWNER_MOVING" == 1
             && -t 0 && -r /dev/tty ) )
     && "${AXIA_P2_G07_PHYSICAL_PREFLIGHT:-0}" == 1
     && "${AXIA_P0_SIM_ONLY:-0}" == 1 ]] || {
    echo 'AXIA_G07_CI_MOVING_GOAL_SCOPE_NOT_AUTHORIZED' >&2
    exit 2
  }
  # Confirm the real lifecycle node loaded the G07-only window from its
  # generated Nav2 parameters BEFORE issuing any moving Goal. A static YAML
  # unit test alone cannot establish this runtime delivery contract.
  CM_ZERO_PARAM="$(timeout 12s ros2 param get /collision_monitor stop_pub_timeout)" || {
    echo 'AXIA_G07_CI_REAL_CM_ZERO_PARAM_READBACK_FAILED' >&2
    exit 2
  }
  printf '%s\n' "$CM_ZERO_PARAM"
  if ! python3 -c 'import re,sys; s=sys.stdin.read(); assert re.search(r"(?m)(?:Double value is:|Double value:)\s*5(?:\.0+)?\s*$",s), "CM_STOP_ZERO_WINDOW_NOT_FIVE_SEC"' <<< "$CM_ZERO_PARAM"; then
    echo 'AXIA_G07_CI_REAL_CM_ZERO_PARAM_MISMATCH_NO_GOAL' >&2
    exit 2
  fi
  echo 'AXIA_G07_CI_REAL_CM_STOP_ZERO_WINDOW_5S_GUARD_TTL_150MS_UNCHANGED'
  # Task02 CI-only: read back the active official CM simple-TF option.
  # Reject any missing runtime override BEFORE publishing a real Goal.
  if [[ "${AXIA_G07_TASK02_SIMPLE_TF_CANDIDATE:-0}" == 1 ]]; then
    TF_SHIFT="$(timeout 12s ros2 param get /collision_monitor base_shift_correction)" || {
      echo 'AXIA_G07_TASK02_SIMPLE_TF_ACTIVE_PARAM_MISSING_NO_GOAL' >&2;exit 2;
    }
    TF_TIMEOUT="$(timeout 12s ros2 param get /collision_monitor transform_tolerance)" || {
      echo 'AXIA_G07_TASK02_SIMPLE_TF_TIMEOUT_READBACK_MISSING_NO_GOAL' >&2;exit 2;
    }
    TF_SOURCE="$(timeout 12s ros2 param get /collision_monitor source_timeout)" || {
      echo 'AXIA_G07_TASK02_SIMPLE_TF_SOURCE_TIMEOUT_MISSING_NO_GOAL' >&2;exit 2;
    }
    if ! python3 - "$TF_SHIFT" "$TF_TIMEOUT" "$TF_SOURCE" <<'PY'
import sys
shift,tol,source=(x.strip() for x in sys.argv[1:])
assert shift.startswith('Boolean value') and shift.rsplit(':',1)[-1].strip().lower()=='false'
assert tol.startswith('Double value') and abs(float(tol.rsplit(':',1)[-1])-0.2)<1e-9
assert source.startswith('Double value') and abs(float(source.rsplit(':',1)[-1])-1.0)<1e-9
PY
    then
      echo 'AXIA_G07_TASK02_SIMPLE_TF_ACTIVE_SAFETY_READBACK_MISMATCH_NO_GOAL' >&2
      exit 2
    fi
    echo 'AXIA_G07_TASK02_SIMPLE_TF_ACTIVE_READBACK_PASS SHIFT_FALSE TF_TOL_0.2 SOURCE_TIMEOUT_1.0 GUARD_150MS_UNCHANGED'
  fi
  echo 'AXIA_G07_CI_MOVING_GOAL_PREG0AL_NATIVE_FIXTURE_BEGIN'
  timeout --signal=TERM --kill-after=5s 70s \
    python3 tools/p2_g07_owner_pregoal_l2.py --output "$OUT/g07_ci_pregoal" \
    > "$OUT/g07_ci_pregoal.log" 2>&1 || {
    cat "$OUT/g07_ci_pregoal.log" >&2 || true
    echo 'AXIA_G07_CI_MOVING_GOAL_REAL_GAZEBO_PREG0AL_BLOCKED' >&2
    exit 2
  }
  cat "$OUT/g07_ci_pregoal.log"
  EXPECTED_CI_SHA="$(git -c safe.directory="$ROOT" rev-parse HEAD)"

  # Task03 disposable ECM positive calibration only. A real Gazebo
  # obstacle/robot contact is deliberately introduced with NO ROS Goal;
  # this world is destroyed before the independent moving-Goal run.
  if [[ "${AXIA_G07_TASK03_POSITIVE_ONLY:-0}" == 1 ]]; then
    [[ "${GITHUB_ACTIONS:-}" == true
       && "${AXIA_P0_SIM_ONLY:-0}" == 1
       && "${AXIA_G07_TASK03_ECM_WITNESS:-0}" == 1
       && "${AXIA_G07_CI_SIM_GOAL_ALLOWED:-0}" == 1
       && "${AXIA_G07_OWNER_STARTUP_PARITY:-0}" == 1
       && "${AXIA_G07_TASK02_SIMPLE_TF_CANDIDATE:-0}" == 1 ]] || {
      echo 'AXIA_G07_TASK03_POSITIVE_SCOPE_NOT_AUTHORIZED_NO_GOAL' >&2; exit 2;
    }
    timeout --signal=TERM --kill-after=5s 40s python3 tools/p2_g07_task03_ecm_positive.py \
      --source-sha "$EXPECTED_CI_SHA" \
      --startup "$OUT/startup_verdict.json" \
      --pregoal "$OUT/g07_ci_pregoal/owner_pregoal_l2.json" || {
      echo 'AXIA_G07_TASK03_ECM_POSITIVE_CALIBRATION_FAILED_NO_GOAL' >&2; exit 2;
    }
    echo 'AXIA_G07_TASK03_NO_GOAL_POSITIVE_CONTROL_COMPLETE_DISCARD_WORLD'
    exit 0
  fi

  # D07 H01 optional read-only ROS/Gazebo callback timing. NO moving Goal.
  # Callback gaps are NOT causal CM→Guard delivery or ROS sensor header proof.
  if [[ "${AXIA_D07_H01_TTL_DIAGNOSTIC_ONLY:-0}" == 1 ]]; then
    [[ "${GITHUB_ACTIONS:-}" == true
       && "${AXIA_D07_H01_CI_ALLOWED:-0}" == 1
       && "${AXIA_G07_OWNER_STARTUP_PARITY:-0}" == 1
       && "${AXIA_G07_CI_OWNER_BAG_PARITY:-0}" == 1
       && "${AXIA_D07_H01_GEOMETRY_ONLY:-0}" != 1
       && "${AXIA_D07_H01_CONTACT_CALIBRATION_ONLY:-0}" != 1
       && "${AXIA_P3_S01_CI_GOAL_ALLOWED:-0}" != 1
       && "${AXIA_P3_S03_CI_COMPOUND_ALLOWED:-0}" != 1
       && "${AXIA_P3_S04_CI_PNU_ALLOWED:-0}" != 1
       && "${AXIA_P3_S05_CI_GOAL_ALLOWED:-0}" != 1 ]] || {
      echo 'AXIA_D07_H01_TTL_DIAGNOSTIC_DENIED_NO_GOAL' >&2
      exit 2
    }
    timeout --signal=TERM --kill-after=5s 55s \
      python3 tools/d07_h01_ttl_no_goal_l2.py \
        --startup "$OUT/startup_verdict.json" \
        --pregoal "$OUT/g07_ci_pregoal/owner_pregoal_l2.json" \
        --source-sha "$EXPECTED_CI_SHA" \
        --output "$OUT/d07_h01_ttl_no_goal" \
      > "$OUT/d07_h01_ttl_no_goal.log" 2>&1 || {
      tail -n 100 "$OUT/d07_h01_ttl_no_goal.log" >&2 || true
      echo 'AXIA_D07_H01_TTL_LIVE_CALLBACKS_BLOCKED_NO_GOAL' >&2
      exit 2
    }
    cat "$OUT/d07_h01_ttl_no_goal.log"
    echo 'AXIA_D07_H01_TTL_CALLBACKS_DIAGNOSTIC_ONLY_NO_GOAL'
    exit 0
  fi

  # Native Gazebo Contact positive-control in a disposable PUBLIC CI world.
  # Never publishes Nav2 Goal, never runs on Owner; prior P2/G07 unchanged.
  if [[ "${AXIA_D07_H01_CONTACT_CALIBRATION_ONLY:-0}" == 1 ]]; then
    [[ "${GITHUB_ACTIONS:-}" == true
       && "${AXIA_D07_H01_CI_ALLOWED:-0}" == 1
       && "${AXIA_G07_OWNER_STARTUP_PARITY:-0}" == 1
       && "${AXIA_G07_CI_OWNER_BAG_PARITY:-0}" == 1
       && "${AXIA_D07_H01_GEOMETRY_ONLY:-0}" != 1
       && "${AXIA_P3_S01_CI_GOAL_ALLOWED:-0}" != 1
       && "${AXIA_P3_S05_CI_GOAL_ALLOWED:-0}" != 1
       && "${AXIA_P3_S03_CI_COMPOUND_ALLOWED:-0}" != 1
       && "${AXIA_P3_S04_CI_PNU_ALLOWED:-0}" != 1 ]] || {
      echo 'AXIA_D07_H01_CONTACT_CALIBRATION_SCOPE_DENIED_NO_GOAL' >&2
      exit 2
    }
    timeout --signal=TERM --kill-after=5s 100s \
      python3 tools/d07_h01_contact_calibration_l2.py \
        --startup "$OUT/startup_verdict.json" \
        --pregoal "$OUT/g07_ci_pregoal/owner_pregoal_l2.json" \
        --source-sha "$EXPECTED_CI_SHA" \
        --output "$OUT/d07_h01_contact_calibration" \
      > "$OUT/d07_h01_contact_calibration.log" 2>&1 || {
      tail -n 120 "$OUT/d07_h01_contact_calibration.log" >&2 || true
      echo 'AXIA_D07_H01_NATIVE_CONTACT_POSITIVE_CALIBRATION_BLOCKED_NO_GOAL' >&2
      exit 2
    }
    cat "$OUT/d07_h01_contact_calibration.log"
    echo 'AXIA_D07_H01_CONTACT_CALIBRATION_COMPLETE_NO_MOTION_GOAL'
    exit 0
  fi

  # D07 H01 geometry-only REAL Gazebo / official Nav2, no moving Goal.
  # Hard-gated before the existing single-Goal dispatch; default OFF.
  if [[ "${AXIA_D07_H01_GEOMETRY_ONLY:-0}" == 1 ]]; then
    [[ "${GITHUB_ACTIONS:-}" == true
       && "${AXIA_D07_H01_CI_ALLOWED:-0}" == 1
       && "${AXIA_G07_OWNER_STARTUP_PARITY:-0}" == 1
       && "${AXIA_G07_CI_OWNER_BAG_PARITY:-0}" == 1
       && "${AXIA_P3_S01_CI_GOAL_ALLOWED:-0}" != 1
       && "${AXIA_P3_S04_CI_PNU_ALLOWED:-0}" != 1
       && "${AXIA_P3_S03_CI_COMPOUND_ALLOWED:-0}" != 1
       && "${AXIA_P3_S05_CI_GOAL_ALLOWED:-0}" != 1 ]] || {
      echo 'AXIA_D07_H01_GEOMETRY_SCOPE_DENIED_NO_GOAL' >&2; exit 2;
    }
    timeout --signal=TERM --kill-after=10s 210s \
      python3 tools/d07_h01_geometry_l2.py \
        --startup "$OUT/startup_verdict.json" \
        --pregoal "$OUT/g07_ci_pregoal/owner_pregoal_l2.json" \
        --source-sha "$EXPECTED_CI_SHA" \
        --output "$OUT/d07_h01_geometry" \
      > "$OUT/d07_h01_geometry.log" 2>&1 || {
      tail -n 110 "$OUT/d07_h01_geometry.log" >&2 || true
      echo 'AXIA_D07_H01_REAL_NAV2_GEOMETRY_BLOCKED_NO_GOAL' >&2
      exit 2
    }
    cat "$OUT/d07_h01_geometry.log"
    echo 'AXIA_D07_H01_REAL_NAV2_GEOMETRY_ONLY_GOAL_NOT_SENT'
    exit 0
  fi
  # P3 S01: existing real G07 CI startup/Observer/14-topic bag/shutdown,
  # but ONE NOMINAL P1 corridor Goal and NO new G07 stop-zone intrusion.
  # The default G07 path remains unchanged when this opt-in is absent.
  if [[ "${AXIA_P3_S01_CI_GOAL_ALLOWED:-0}" == 1 ]]; then
    [[ "${GITHUB_ACTIONS:-}" == true
       && "${AXIA_G07_CI_OWNER_BAG_PARITY:-0}" == 1
       && "${AXIA_G07_OWNER_STARTUP_PARITY:-0}" == 1 ]] || {
      echo 'AXIA_P3_S01_REAL_GOAL_SCOPE_DENIED'; exit 2;
    }
    timeout --signal=TERM --kill-after=7s 132s \
      python3 tools/p3_s01_actual_goal_ci.py \
        --startup "$OUT/startup_verdict.json" \
        --pregoal "$OUT/g07_ci_pregoal/owner_pregoal_l2.json" \
        --source-sha "$EXPECTED_CI_SHA" \
        --output "$OUT/p3_s01_actual" \
      > "$OUT/p3_s01_actual.log" 2>&1 || {
      tail -n 100 "$OUT/p3_s01_actual.log" >&2 || true
      echo 'AXIA_P3_S01_ACTUAL_NAV2_GOAL_BLOCKED' >&2
      exit 2
    }
    cat "$OUT/p3_s01_actual.log"
    echo 'AXIA_P3_S01_REAL_GAZEBO_NOMINAL_GOAL_CANDIDATE_FORMAL_HOLD'
    exit 0
  fi
  # S04 PNU fixture -> G09 ROS node -> EXISTING Supervisor LIMIT -> CM/Guard.
  # Same official Gazebo/Nav2/14-topic bag/ordered shutdown as G07.
  if [[ "${AXIA_P3_S04_CI_PNU_ALLOWED:-0}" == 1 ]]; then
    timeout --signal=TERM --kill-after=7s 132s \
      python3 tools/p3_s04_live_risk_to_cmd_ci.py \
        --startup "$OUT/startup_verdict.json" \
        --pregoal "$OUT/g07_ci_pregoal/owner_pregoal_l2.json" \
        --source-sha "$EXPECTED_CI_SHA" \
        --output "$OUT/p3_s04_risk_real" \
      > "$OUT/p3_s04_risk_real.log" 2>&1 || {
      tail -n 120 "$OUT/p3_s04_risk_real.log" >&2 || true
      echo 'AXIA_P3_S04_ACTUAL_RISK_TO_CMD_BLOCKED' >&2
      exit 2
    }
    cat "$OUT/p3_s04_risk_real.log"
    echo 'AXIA_P3_S04_REAL_RISK_LIMITED_FINAL_SCOPED_CANDIDATE_FORMAL_HOLD'
    exit 0
  fi
  # G10 simulation-only: S03 Scan+CM held fault and existing protective FSM.
  if [[ "${AXIA_P3_G10_CI_HELD_RECOVERY_ALLOWED:-0}" == 1 ]]; then
    [[ "${GITHUB_ACTIONS:-}" == true
       && "${AXIA_P0_SIM_ONLY:-0}" == 1
       && "${AXIA_P3_S03_CI_COMPOUND_ALLOWED:-0}" == 1
       && "${AXIA_P3_S03_CI_CM_PAUSE_ALLOWED:-0}" == 1
       && "${AXIA_G07_CI_SIM_GOAL_ALLOWED:-0}" == 1
       && "${AXIA_G07_CI_OWNER_BAG_PARITY:-0}" == 1
       && "${AXIA_G07_OWNER_STARTUP_PARITY:-0}" == 1
       && "${AXIA_P3_S01_CI_GOAL_ALLOWED:-0}" != 1
       && "${AXIA_P3_S04_CI_PNU_ALLOWED:-0}" != 1
       && "${AXIA_P3_S05_CI_GOAL_ALLOWED:-0}" != 1 ]] || {
      echo 'AXIA_P3_G10_HELD_FAULT_SCOPE_DENIED' >&2; exit 2;
    }
    timeout --signal=TERM --kill-after=9s 160s \
      python3 tools/p3_g10_held_fault_recovery_ci.py \
        --startup "$OUT/startup_verdict.json" \
        --pregoal "$OUT/g07_ci_pregoal/owner_pregoal_l2.json" \
        --source-sha "$EXPECTED_CI_SHA" \
        --output "$OUT/p3_g10_held_recovery" \
      > "$OUT/p3_g10_held_recovery.log" 2>&1 || {
      tail -n 150 "$OUT/p3_g10_held_recovery.log" >&2 || true
      echo 'AXIA_P3_G10_ACTUAL_HELD_COMPOUND_RECOVERY_BLOCKED' >&2
      exit 2
    }
    cat "$OUT/p3_g10_held_recovery.log"
    echo 'AXIA_P3_G10_HELD_SCAN_CM_DENIAL_RECOVERY_SCOPED_G10_G11_FORMAL_HOLD'
    exit 0
  fi
  # S03 exact public sim-only compound: actual Scan drop + bounded CM pause.
  # G07/S01/S05 default paths and all P1/P2 policies remain unchanged.
  if [[ "${AXIA_P3_S03_CI_COMPOUND_ALLOWED:-0}" == 1 ]]; then
    timeout --signal=TERM --kill-after=7s 132s \
      python3 tools/p3_s03_compound_live_ci.py \
        --startup "$OUT/startup_verdict.json" \
        --pregoal "$OUT/g07_ci_pregoal/owner_pregoal_l2.json" \
        --source-sha "$EXPECTED_CI_SHA" \
        --output "$OUT/p3_s03_compound" \
      > "$OUT/p3_s03_compound.log" 2>&1 || {
      tail -n 130 "$OUT/p3_s03_compound.log" >&2 || true
      echo 'AXIA_P3_S03_ACTUAL_COMPOUND_BLOCKED' >&2
      exit 2
    }
    cat "$OUT/p3_s03_compound.log"
    echo 'AXIA_P3_S03_REAL_SCAN_DROP_CM_SIGSTOP_SCOPED_CANDIDATE_FORMAL_HOLD'
    exit 0
  fi
  # One CI-only S05 live recovery case, same startup/14-topic bag/shutdown.
  # No fault, no new final /cmd_vel publisher and no unapproved second Goal.
  if [[ "${AXIA_P3_S05_CI_GOAL_ALLOWED:-0}" == 1 ]]; then
    [[ "${GITHUB_ACTIONS:-}" == true
       && "${AXIA_G07_CI_OWNER_BAG_PARITY:-0}" == 1
       && "${AXIA_G07_OWNER_STARTUP_PARITY:-0}" == 1
       && "${AXIA_P3_S01_CI_GOAL_ALLOWED:-0}" != 1 ]] || {
      echo 'AXIA_P3_S05_REAL_GOAL_SCOPE_DENIED'; exit 2;
    }
    timeout --signal=TERM --kill-after=7s 132s \
      python3 tools/p3_s05_actual_stop_ci.py \
        --startup "$OUT/startup_verdict.json" \
        --pregoal "$OUT/g07_ci_pregoal/owner_pregoal_l2.json" \
        --source-sha "$EXPECTED_CI_SHA" \
        --output "$OUT/p3_s05_actual" \
      > "$OUT/p3_s05_actual.log" 2>&1 || {
      tail -n 100 "$OUT/p3_s05_actual.log" >&2 || true
      echo 'AXIA_P3_S05_ACTUAL_SW_STOP_GAZEBO_BLOCKED' >&2
      exit 2
    }
    cat "$OUT/p3_s05_actual.log"
    echo 'AXIA_P3_S05_ACTUAL_GAZEBO_SW_STOP_SCOPED_CANDIDATE_FORMAL_HOLD'
    exit 0
  fi
  # The real Owner shell must read the exact consent phrase from /dev/tty.
  # The single Goal is sent later by the existing Python Supervisor path.
  OWNER_GOAL_ARGS=()
  if [[ "$OWNER_MOVING" == 1 ]];then
    [[ -n "${AXIA_G07_TASK04_EXPECTED_STUDENT_SHA:-}"
       && "$EXPECTED_CI_SHA" == "$AXIA_G07_TASK04_EXPECTED_STUDENT_SHA"
       && "$EXPECTED_CI_SHA" =~ ^[a-f0-9]{40}$ ]] || {
      echo 'G07_TASK04_OWNER_EXACT_SHA_PREGOAL_BLOCKED' >&2;exit 2;
    }
    [[ -t 0 && -r /dev/tty ]] || {
      echo 'G07_TASK04_OWNER_CONTROLLING_TTY_MISSING' >&2;exit 2;
    }
    printf '%s\n' 'Simulation-only Moving Goal: type YES-P2-G07-GOAL to approve exactly one Goal:' > /dev/tty
    owner_answer=''
    IFS= read -r -t 180 owner_answer < /dev/tty || {
      echo 'G07_TASK04_OWNER_TTY_APPROVAL_TIMEOUT_OR_EOF_NO_GOAL' >&2;exit 2;
    }
    [[ "$owner_answer" == 'YES-P2-G07-GOAL' ]] || {
      echo 'G07_TASK04_OWNER_GOAL_DENIED_BY_TTY_NO_GOAL' >&2;exit 2;
    }
    unset owner_answer
    export AXIA_G07_OWNER_COMMON_RUNNER_AUTHORIZED=1
    export AXIA_P2_OWNER_PINNED_SHA="$EXPECTED_CI_SHA"
    OWNER_GOAL_ARGS=(--owner-launch-pid "$LAUNCH_PID")
    echo 'AXIA_G07_TASK04_OWNER_MANUAL_CONTROLLING_TTY_GOAL_CONSENT_PASS'
  fi
  timeout --signal=TERM --kill-after=7s 132s \
    python3 tools/p2_g07_ci_moving_goal.py \
      --startup "$OUT/startup_verdict.json" \
      --pregoal "$OUT/g07_ci_pregoal/owner_pregoal_l2.json" \
      --source-sha "$EXPECTED_CI_SHA" \
      --output "$OUT/g07_ci_moving" \
      "${OWNER_GOAL_ARGS[@]}" \
    > "$OUT/g07_ci_moving.log" 2>&1 || {
    tail -n 100 "$OUT/g07_ci_moving.log" >&2 || true
    echo 'AXIA_G07_CI_MOVING_GOAL_ACTUAL_NAV2_BLOCKED' >&2
    exit 2
  }
  cat "$OUT/g07_ci_moving.log"
  echo 'AXIA_G07_CI_MOVING_GOAL_REAL_GAZEBO_CANDIDATE_ONLY_OWNER_L3_NOT_RUN'
  exit 0
fi
# New G07 opt-in: verify official STATIC MAP route is geometrically open
# without changing the official world, base map or Nav2 parameters.
if [[ "${AXIA_P2_G07_DEMO_CORRIDOR_SURVEY:-0}" == 1 ]]; then
  MAP_DIR="$(ros2 pkg prefix nav2_bringup)/share/nav2_bringup/maps"
  python3 tools/p2_g07_demo_corridor.py \
    --map-pgm "$MAP_DIR/tb3_sandbox.pgm" \
    --map-yaml "$MAP_DIR/tb3_sandbox.yaml" \
    --output "$OUT/g07_demo_corridor.json" \
    > "$OUT/g07_demo_corridor.log" 2>&1 || {
    cat "$OUT/g07_demo_corridor.log" >&2 || true
    echo "P2_G07_DEMO_CORRIDOR_OFFICIAL_MAP_BLOCKED" >&2
    exit 2
  }
  cat "$OUT/g07_demo_corridor.log"
fi
# The real PR #106 mode is PRE-GOAL physical prepositioning, not an
# in-motion Gazebo set_pose. Test that exact sequence in a single isolated L2
# session without Nav2 Goal; original 3-zone L2 remains separately frozen.
if [[ "${AXIA_P2_G07_OWNER_PREGOAL_L2:-0}" == 1 ]]; then
  [[ "${AXIA_P2_G07_PHYSICAL_PREFLIGHT:-0}" == 1 ]] || {
    echo 'P2_G07_OWNER_PREGOAL_L2_BLOCKED_NO_WORLD_OVERLAY' >&2
    exit 2
  }
  timeout --signal=TERM --kill-after=5s 65s \
    python3 tools/p2_g07_owner_pregoal_l2.py \
      --output "$OUT/g07_owner_pregoal" \
      > "$OUT/g07_owner_pregoal.log" 2>&1 || {
    cat "$OUT/g07_owner_pregoal.log" >&2 || true
    echo 'P2_G07_OWNER_PREGOAL_L2_BLOCKED' >&2
    exit 2
  }
  cat "$OUT/g07_owner_pregoal.log"
  echo 'P2_G07_OWNER_PREGOAL_L2_NO_GOAL_COMPLETE'
  exit 0
fi
# Actual Gazebo transport and LiDAR proof, WITHOUT any Goal or Fault.
if [[ "${AXIA_P2_G07_PHYSICAL_PREFLIGHT:-0}" == 1 ]]; then
  if timeout --signal=TERM --kill-after=5s 75s \
      python3 tools/p2_g07_physical_preflight.py --output "$OUT/g07_physical" \
      > "$OUT/g07_physical.log" 2>&1; then
    cat "$OUT/g07_physical.log"
    echo 'P2_G07_L2_NATIVE_OBSTACLE_LASER_PROVEN_GOAL_NOT_RUN'
    if [[ "${AXIA_P2_G07_DEMO_CORRIDOR_SURVEY:-0}" == 1 ]]; then
      # Same real Harmonic process; native set_pose/readback at the extended
      # northern G07 demo position, still NO Goal and NO Fault.
      timeout --signal=TERM --kill-after=5s 45s \
        python3 tools/p2_g07_relocated_no_goal_probe.py \
          --output "$OUT/g07_relocated_probe.json" \
          > "$OUT/g07_relocated_probe.log" 2>&1 || {
        cat "$OUT/g07_relocated_probe.log" >&2 || true
        echo "P2_G07_DEMO_OBSTACLE_NATIVE_RELOCATION_BLOCKED" >&2
        exit 2
      }
      cat "$OUT/g07_relocated_probe.log"
    fi
  else
    echo 'P2_G07_L2_PHYSICAL_PREFLIGHT_BLOCKED' >&2
    cat "$OUT/g07_physical.log" >&2 || true
    exit 2
  fi
fi
# Stop the observer-owned launch; its clean shutdown remains independent
# from the above readiness outcome.
