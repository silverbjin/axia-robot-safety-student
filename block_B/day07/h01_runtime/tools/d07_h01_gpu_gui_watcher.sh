#!/usr/bin/env bash
# D07 GPU read-only GUI worker: public CI mocks + real Owner WSLg.
set -Eeuo pipefail
[[ $# -eq 7 ]] || { echo D07_H01_GUI_WATCHER_ARGUMENTS_INVALID >&2; exit 2; }
marker="$1"; rviz_cfg="$2"; required_sha="$3"; topics_file="$4"
repo_root="$5"; ack_file="$6"; exit_file="$7"
gz_pid=''; rviz_pid=''
watcher_cleanup() {
  local rc=$?
  trap - EXIT INT TERM
  set +e
  [[ -z "$rviz_pid" ]] || kill -TERM "$rviz_pid" 2>/dev/null || true
  [[ -z "$gz_pid" ]] || kill -TERM "$gz_pid" 2>/dev/null || true
  printf 'rc=%s\npid=%s\nutc=%s\n' "$rc" "$$" "$(date -u +%FT%TZ)" > "$exit_file" 2>/dev/null || true
  echo "D07_H01_GUI_WATCHER_EXIT rc=$rc pid=$$" >&2
  exit "$rc"
}
trap watcher_cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
printf 'pid=%s\nutc=%s\n' "$$" "$(date -u +%FT%TZ)" > "$ack_file" || {
  echo D07_H01_GUI_WATCHER_SPAWN_ACK_UNWRITABLE >&2; exit 2;
}
echo "D07_H01_GUI_WATCHER_PROCESS_ENTERED pid=$$"
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
[[ "${AXIA_D07_H01_GPU_GUI_TRIAL:-0}" == 1
   && "${AXIA_D07_H01_GUI_NO_GOAL:-0}" == 1
   && "${AXIA_P0_SIM_ONLY:-0}" == 1
   && "${AXIA_G07_CI_SIM_GOAL_ALLOWED:-0}" != 1 ]] || {
  echo D07_H01_GUI_GPU_TRIAL_SCOPE_DENIED_NO_GOAL >&2
  exit 2
}
echo D07_H01_GUI_GPU_TRIAL_ONLY NO_GOAL_NOT_ESTOP
echo "D07_H01_GUI_TRANSPORT_PARTITION=${GZ_PARTITION:-unset}"
timeout 10s gz topic -l > "$topics_file" 2>&1 || {
  echo D07_H01_GUI_TRANSPORT_TOPIC_PROBE_FAILED >&2
  exit 2
}
python3 "$repo_root/tools/d07_h01_gz_world_topic_gate.py" --topics-file "$topics_file" || {
  echo D07_H01_GUI_TRANSPORT_WORLD_TOPIC_GATE_FAILED >&2
  exit 2
}
echo D07_H01_GUI_SERVER_WORLD_DISCOVERED_NOT_GUI_RENDER_PROOF
# CI exercises the SAME real Gazebo GUI/RViz child execution and DDS handshake
# under Xvfb. WSLg D3D12 cannot be rendered on a GitHub Ubuntu runner.
# Explicitly separate the renderer only; no fake GPU admission or Goal.
if [[ "${AXIA_D07_H01_CI_SOFTWARE_GUI:-0}" == 1 ]]; then
  [[ "${GITHUB_ACTIONS:-false}" == true
     && "${AXIA_D07_H01_GUI_NO_GOAL:-0}" == 1
     && "${AXIA_P0_SIM_ONLY:-0}" == 1
     && "${AXIA_G07_CI_SIM_GOAL_ALLOWED:-0}" != 1 ]] || {
    echo D07_H01_GUI_CI_SOFTWARE_BACKEND_SCOPE_DENIED >&2
    exit 2
  }
  gui_render_env=(env -u GALLIUM_DRIVER -u MESA_D3D12_DEFAULT_ADAPTER_NAME
                  LIBGL_ALWAYS_SOFTWARE=1)
  echo D07_H01_GUI_CI_SOFTWARE_BACKEND_XVFB_NO_WSLG_GPU_PROOF
else
  gui_render_env=(env -u LIBGL_ALWAYS_SOFTWARE
                  GALLIUM_DRIVER=d3d12
                  MESA_D3D12_DEFAULT_ADAPTER_NAME="${AXIA_D07_H01_GPU_ADAPTER:-NVIDIA}")
  echo D07_H01_GUI_OWNER_D3D12_BACKEND_NOT_CI_GPU_PROOF
fi
"${gui_render_env[@]}" gz sim -g -v 4 &
gz_pid=$!
"${gui_render_env[@]}" rviz2 -d "$rviz_cfg" --ros-args -p use_sim_time:=true &
rviz_pid=$!
echo "D07_H01_GUI_CHILDREN_SPAWNED gz_pid=$gz_pid rviz_pid=$rviz_pid"
# An early exit is a fail-closed FIRST GUI failure, not a DDS/Path problem.
set +e
wait -n "$gz_pid" "$rviz_pid"
child_rc=$?
set -e
echo "D07_H01_GUI_CHILD_TERMINATED_BEFORE_PHASE_COMPLETE first_exit_rc=$child_rc" >&2
exit 3
