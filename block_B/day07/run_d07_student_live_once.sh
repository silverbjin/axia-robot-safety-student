#!/usr/bin/env bash
# AXIA Block B D07 student independent ROS Jazzy official Nav2 L1 LIVE.
# Public pinned source only; NEVER Instructor private H01 or moving Goal.
# Actual ROS Costmap/Planner YES; Gazebo/RViz/physical obstacle NO.
set -Eeuo pipefail
umask 077

readonly PUBLIC_REPO="silverbjin/axia-robot-safety-ci-public"
readonly PUBLIC_SHA="158b7c6032d987177d1e1302bf85fd741120fd9e"
MODE="${1:---run}"
[[ "$#" -le 1 ]] || { echo D07_STUDENT_INVALID_ARGUMENTS_NO_GOAL >&2; exit 2; }
case "$MODE" in
  --self-check)
    bash -n "${BASH_SOURCE[0]}"
    [[ "$PUBLIC_SHA" =~ ^[0-9a-f]{40}$ ]] || exit 2
    echo "D07_STUDENT_LIVE_STATIC_PASS NAV2_NOT_RUN_GAZEBO_NOT_RUN NO_GOAL source=$PUBLIC_SHA"
    exit 0
    ;;
  --doctor|--run) ;;
  *) echo D07_STUDENT_USAGE=--self-check\|--doctor\|--run >&2; exit 2 ;;
esac

for tool in bash git python3 timeout sha256sum mktemp ros2; do
  command -v "$tool" >/dev/null 2>&1 || {
    echo "D07_STUDENT_MISSING_COMMAND=$tool NO_GOAL" >&2
    exit 2
  }
done
[[ -r /opt/ros/jazzy/setup.bash ]] || {
  echo D07_STUDENT_ROS_JAZZY_MISSING_NO_GOAL >&2; exit 2;
}
# ROS generated environment setup may reference unset variables under set -u.
set +u
source /opt/ros/jazzy/setup.bash
set -u
[[ "${ROS_DISTRO:-}" == jazzy ]] || {
  echo D07_STUDENT_WRONG_ROS_DISTRO_NO_GOAL >&2; exit 2;
}
for package in nav2_planner nav2_navfn_planner nav2_costmap_2d nav2_msgs tf2_ros; do
  ros2 pkg prefix "$package" >/dev/null 2>&1 || {
    echo "D07_STUDENT_OFFICIAL_PACKAGE_MISSING=$package NO_GOAL" >&2
    exit 2
  }
done
if [[ "$MODE" == --doctor ]]; then
  echo "D07_STUDENT_DOCTOR_READY ROS_JAZZY_OFFICIAL_NAV2_PRESENT NAV2_NOT_RUN_GAZEBO_NOT_RUN NO_GOAL"
  exit 0
fi

# Do not delete student TODO files, edits, overlays or other ROS/Gazebo nodes.
readonly ROOT="${AXIA_D07_STUDENT_LIVE_EVIDENCE:-$HOME/axia_d07_student_live_evidence}"
[[ ! -L "$ROOT" ]] || {
  echo D07_STUDENT_EVIDENCE_SYMLINK_BLOCKED_NO_GOAL >&2; exit 2;
}
mkdir -p "$ROOT"; chmod 700 "$ROOT"
readonly OUT="$(mktemp -d "$ROOT/session-XXXXXXXX")"
readonly SOURCE="$(mktemp -d)"
STATUS="HOLD"
cleanup() {
  rc="$?"
  trap - EXIT INT TERM
  set +e
  if [[ -d "$SOURCE" && "$SOURCE" == /tmp/tmp.* ]]; then
    rm -rf -- "$SOURCE"
  fi
  if [[ -d "$OUT" ]]; then
    python3 - "$OUT/student_run_summary.json" "$STATUS" "$rc" "$PUBLIC_SHA" <<'PY_SUMMARY'
import json,sys
from pathlib import Path
dest,status,rc,source=sys.argv[1:]
Path(dest).write_text(json.dumps({
 "scope":"student_public_ros_jazzy_official_nav2_l1_only",
 "status":status,
 "wrapper_rc":int(rc),
 "public_source_sha":source,
 "gazebo_actual":False,
 "rviz_actual":False,
 "physical_obstacle_actual":False,
 "navigate_to_pose_sent":False,
 "cmd_vel_published":False,
 "certified_estop":False,
 "axia_mvp_demo_accepted":"HOLD",
},indent=2,sort_keys=True)+"\n")
PY_SUMMARY
    (cd "$OUT"; find . -type f ! -name SHA256SUMS -print0 |
      sort -z | xargs -0 -r sha256sum > SHA256SUMS) || true
  fi
  echo "D07_STUDENT_LIVE_STATUS=$STATUS WRAPPER_RC=$rc EVIDENCE=$OUT"
  echo AXIA_MVP_DEMO_ACCEPTED=HOLD
  exit "$rc"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

git -C "$SOURCE" init -q
git -C "$SOURCE" remote add origin "https://github.com/$PUBLIC_REPO.git"
git -C "$SOURCE" fetch -q --depth 1 origin "$PUBLIC_SHA"
git -C "$SOURCE" checkout -q --detach FETCH_HEAD
[[ "$(git -C "$SOURCE" rev-parse HEAD)" == "$PUBLIC_SHA" ]] || {
  echo D07_STUDENT_PUBLIC_SHA_MISMATCH_NO_GOAL >&2; exit 3;
}
for source_file in d07/scripts/d07_nav2_planner_l1.py d07/params/nav2_d07_planner.yaml; do
  [[ -s "$SOURCE/$source_file" ]] || {
    echo "D07_STUDENT_PUBLIC_SOURCE_MISSING=$source_file NO_GOAL" >&2;exit 3;
  }
done
printf '%s\n' "$PUBLIC_SHA" > "$OUT/pinned_public_source.sha"
echo "D07_STUDENT_PUBLIC_NAV2_SOURCE_VERIFIED=$PUBLIC_SHA"
mkdir -p "$OUT/actual_ros_l1"
# Run the *same* official PlannerServer/Costmap Python entrypoint in student CI
# and students' WSL2. No /cmd_vel, NavigateToPose, physical Gazebo or Instructor.
set +e
(
  set -o pipefail
  timeout --signal=TERM --kill-after=20s 170s python3 -u \
    "$SOURCE/d07/scripts/d07_nav2_planner_l1.py" \
    --params "$SOURCE/d07/params/nav2_d07_planner.yaml" \
    --out "$OUT/actual_ros_l1" 2>&1 | tee "$OUT/actual_ros_l1.stdout.log"
)
RUN_RC=$?
set -e
if [[ "$RUN_RC" != 0 ]]; then
  echo "D07_STUDENT_NAV2_L1_BLOCKED actual_ros_rc=$RUN_RC" >&2
  exit 3
fi
python3 - "$OUT/actual_ros_l1/verdict.json" <<'PY_VERIFY'
import json,sys
from pathlib import Path
v=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert v["status"]=="PASS_OFFICIAL_NAV2_COSTMAP_REPLAN_L1"
assert v["ros_actual"] is True and v["gazebo_actual"] is False
for key in ("goal_sent","navigate_to_pose_sent","cmd_vel_published",
            "robot_moved","certified_estop"):
    assert v[key] is False, key
g=v["graph"]
assert g["actual_nav2_costmap_publishers"]>=1
assert g["actual_nav2_scan_subscribers"]==1
assert g["actual_robot_cmd_publishers"]==0
a,b,c=(v["stages"][k] for k in
       ("clear_before","person_blocking","person_cleared"))
assert all(x["route"]["status"]=="SUCCEEDED" for x in (a,b,c))
assert a["grid"]["actual_obstacle_lethal_cells"]<=2
assert b["grid"]["actual_obstacle_lethal_cells"]>=3
assert c["grid"]["actual_obstacle_lethal_cells"]<=2
assert b["route"]["min_distance_to_person_proxy_m"]>=.30
assert b["route"]["max_abs_y_m"]>=a["route"]["max_abs_y_m"]+.12
print("D07_STUDENT_NAV2_L1_REAL_PASS "
      f"lethal={a['grid']['actual_obstacle_lethal_cells']}/"
      f"{b['grid']['actual_obstacle_lethal_cells']}/"
      f"{c['grid']['actual_obstacle_lethal_cells']} "
      f"path={a['route']['path_point_count']}/"
      f"{b['route']['path_point_count']}/"
      f"{c['route']['path_point_count']} NO_GAZEBO NO_GOAL")
PY_VERIFY
STATUS="PASS_OFFICIAL_NAV2_COSTMAP_REPLAN_L1"
