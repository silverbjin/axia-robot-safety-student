"""CI-only G07 dynamic physical STOP intrusion admission (pure geometry).

A real Nav2 Goal turned away from the originally prepositioned obstacle,
reaching min LaserScan 0.6545m in CI #42971453613. This guard computes a
ONE-TIME native Gazebo set_pose target using independently checked initial
map/odom/world anchors and actual live odom. It never publishes a Goal, Twist,
LaserScan, or auto-approves Owner L3. CI runner must prove native ACK and two
new physical LaserScan samples; this function alone does not prove STOP.
"""
import math
from p2_l3_coordinate_frames import obstacle_world_pose

CI_STOP_SURFACE_M = 0.34
CI_G07_RADIUS_M = 0.07
CI_MAX_ODOM_FROM_START_M = 0.70
CI_MAX_YAW_CHANGE_RAD = 1.0

def _yaw_change(a, b):
    return math.atan2(math.sin(a-b), math.cos(a-b))

def plan_stop_fixture(anchor, live_odom, *, goal_status,
                      guard_latched, real_slow_observed):
    """Reject any uncertain status, escape from lane, or invalid motion."""
    if (type(goal_status) is not int or goal_status != 2
            or guard_latched is not False
            or real_slow_observed is not True):
        raise ValueError("CI_STOP_INTRUSION_REQUIRES_LIVE_SLOW_AND_SAFE_GOAL")
    if not isinstance(anchor, dict):
        raise ValueError("CI_STOP_INVALID_FRAME_ANCHOR")
    odom0 = anchor.get("odom_pose")
    if (not isinstance(live_odom, (tuple, list)) or len(live_odom)!=3
            or not isinstance(odom0, (tuple,list)) or len(odom0)!=3
            or any(type(v) not in (int,float) or not math.isfinite(v)
                   for v in (*live_odom,*odom0))):
        raise ValueError("CI_STOP_INVALID_LIVE_ODOMETRY")
    distance=math.hypot(live_odom[0]-odom0[0],live_odom[1]-odom0[1])
    if (distance > CI_MAX_ODOM_FROM_START_M or
            abs(_yaw_change(live_odom[2],odom0[2])) > CI_MAX_YAW_CHANGE_RAD):
        raise ValueError("CI_STOP_ROBOT_LEFT_APPROVED_PREGOAL_LANE")
    return obstacle_world_pose(
        anchor,live_odom,CI_STOP_SURFACE_M,CI_G07_RADIUS_M,demo_corridor=True)


def classify_slow_fixture_alignment(*,start_pose,live_odom,odom_speed,
                                    odom_yaw_rate,supervised_speed,
                                    goal_status,guard_latched):
    """Read-only first physical SLOW fixture heading/velocity audit.

    Never authorizes a Goal, fixture, speed, timeout extension or acceptance.
    Only real post-CLEAR snapshots in one host-monotonic session are valid.
    """
    out={"schema":"axia.g07.slow_fixture_forward_alignment.v1",
         "status":"FORWARD_ALIGNMENT_NOT_PROVEN_HOLD",
         "aligned_for_positive_slow_demo":False,
         "yaw_change_rad":None,
         "odom_forward_vx":None,
         "supervised_forward_vx":None,
         "odom_yaw_rate":None,
         "root_cause_proven":False,"timing_safety_pass":False,
         "release":"HOLD","certified_estop":False}
    if (not isinstance(start_pose,(tuple,list)) or len(start_pose)!=3
            or not isinstance(live_odom,(tuple,list)) or len(live_odom)!=3):
        return out
    values=(*start_pose,*live_odom,odom_speed,odom_yaw_rate,supervised_speed)
    if any(type(v) not in (float,int) or not math.isfinite(v) for v in values):
        return out
    yaw=abs(_yaw_change(live_odom[2],start_pose[2]))
    out.update(yaw_change_rad=round(yaw,6),
               odom_forward_vx=round(odom_speed,6),
               supervised_forward_vx=round(supervised_speed,6),
               odom_yaw_rate=round(odom_yaw_rate,6))
    if (goal_status==2 and guard_latched is False
            and .005 < supervised_speed <= .22 and odom_speed>0.005
            # Fixture is projected from the CURRENT robot world yaw.
            # Its cumulative yaw from the original Goal is diagnostic, not
            # physical heading readiness. Require actual near-straight
            # angular velocity, stronger than old .20 rad/s threshold.
            and abs(odom_yaw_rate)<=.05):
        out.update(status="FORWARD_ALIGNMENT_CANDIDATE_ONLY",
                   aligned_for_positive_slow_demo=True)
    return out
