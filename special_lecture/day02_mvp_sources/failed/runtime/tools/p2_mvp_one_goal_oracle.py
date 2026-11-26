"""One-Goal *education demo* slow+stop numerical screen.

This is not formal G07/G05/G06 acceptance, certified E-Stop or collision truth.
Values must come from actual Owner ROS/Gazebo Observer and native move ACK,
not synthetic inputs. Pure helper is also used for negative L0 tests.
"""
import math

DEMO_GOAL_TOLERANCE_M = 0.05


def classify_mvp_phase_order(*,goal_sent,action_succeeded,first_slow_move_ack):
    if not all(type(x) in (float,int) and math.isfinite(x)
               for x in (goal_sent,action_succeeded,first_slow_move_ack)):
        return "INVALID_TIME"
    if action_succeeded<=first_slow_move_ack:
        return "GOAL_TERMINATED_BEFORE_OBSTACLE_SLOWDOWN"
    return "GOAL_ALIVE_AT_OBSTACLE_SLOWDOWN"


def _blocked(reason):
    return {
      "status":"BLOCKED","reason":reason,"scope":"SIMULATION_ONLY_MVP_ONE_GOAL",
      "numerical_candidate":False,"gate_accepted":False,
      "formal_g07_accepted":False,"certified_estop":False,
      "collision_ground_truth":False,
    }


def _finite(v):
    return type(v) in (int,float) and math.isfinite(v)


def check_demo_zone_motion(raw):
    if not isinstance(raw,dict) or raw.get("case")!="G07":
        return _blocked("CASE_INVALID")
    if not all(isinstance(raw.get(k),str) and raw[k] for k in (
            "source_sha","gz_partition","goal_uuid")):
        return _blocked("PROVENANCE_MISSING")
    if any(raw.get(k) is not True for k in (
            "physical_obstacle_scan","entity_preloaded_world",
            "set_pose_ack","slowdown_pose_ack","stop_pose_ack")):
        return _blocked("PHYSICAL_GAZEBO_ACK_MISSING")
    if raw.get("collision_ground_truth") is not False or raw.get("collision_count") is not None:
        return _blocked("CONTACT_TRUTH_MUST_NOT_BE_INFERRED")
    if raw.get("slow_action_status")!=2 or raw.get("stop_action_status")!=2:
        return _blocked("ACTION_NOT_EXECUTING_AT_SLOW_OR_STOP")
    slow=raw.get("slow")
    stop=raw.get("stop")
    if not isinstance(slow,dict) or not isinstance(stop,dict):
        return _blocked("MISSING_SLOW_STOP_PHASES")
    for stage,row in (("slowdown",slow),("stop",stop)):
        if row.get("phase")!=stage or any(not _finite(row.get(k)) for k in
                ("distance","vin","vout","win","wout")):
            return _blocked("PHASE_VALUE_INVALID")
    if not (.4<slow["distance"]<.75 and slow["vin"]>.03 and
            0<slow["vout"]<=.30*slow["vin"]+.01):
        return _blocked("MOVING_SLOWDOWN_NOT_PROVEN")
    if not (.14<=stop["distance"]<.4 and stop["vin"]>.03 and
            abs(stop["vout"])<.01 and abs(stop["wout"])<.02):
        return _blocked("MOVING_STOP_NOT_PROVEN")
    if not _finite(raw.get("odom_stop_dwell_sec")) or raw["odom_stop_dwell_sec"]<1.0:
        return _blocked("REAL_ODOM_STOP_DWELL_MISSING")
    return {
        **_blocked("MVP_NUMERICAL_CANDIDATE_RAW_REVIEW_REQUIRED"),
        "status":"NUMERICAL_CANDIDATE",
        "reason":"MVP_ONE_GOAL_SLOW_AND_STOP_MOTION_NUMERICAL_CANDIDATE",
        "numerical_candidate":True,
        "stopped_odom_dwell_sec":raw["odom_stop_dwell_sec"]
    }
