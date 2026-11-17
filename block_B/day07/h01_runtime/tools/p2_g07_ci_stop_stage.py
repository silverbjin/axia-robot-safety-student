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
