"""G07 Owner 0.4m STOP race correction: physical obstacle prepositioned.

Only changes explicit --mvp-relocated-obstacle demo mode. Never weakens
sensor/CM speed bounds, Goal TTY approval, formal G07, or certification labels.
These pure helpers cannot prove ROS/Gazebo L3 behavior.
"""
from __future__ import annotations
import math

def _real(v):
    return type(v) in (float,int) and math.isfinite(v)

def evaluate_previous_owner_race(*,move_requested_monotonic,pose_ack_monotonic,
                                  heading_at_request,heading_at_ack,
                                  front_after_ack,slowdown_front_limit=.75):
    """Numerical diagnosis from immutable raw Owner audit, NOT Goal PASS."""
    values=(move_requested_monotonic,pose_ack_monotonic,heading_at_request,
            heading_at_ack,front_after_ack,slowdown_front_limit)
    if not all(_real(v) for v in values):
        raise ValueError("INVALID_ORIGINAL_OWNER_TRACE")
    dt=pose_ack_monotonic-move_requested_monotonic
    dh=abs(math.atan2(math.sin(heading_at_ack-heading_at_request),
                      math.cos(heading_at_ack-heading_at_request)))
    if not 0<=dt<=20 or not 0<=front_after_ack<=10 or not .3<=slowdown_front_limit<=1:
        raise ValueError("UNBOUNDED_OWNER_TRACE")
    diagnosed=(dt>=1.0 and dh>.30 and front_after_ack>slowdown_front_limit)
    return {
        "diagnosis": ("MOVING_ROBOT_GZ_POSE_RACE_OUTSIDE_SLOW_ZONE"
                      if diagnosed else "CAUSE_NOT_DETERMINED"),
        "pose_ack_delay_s":dt, "heading_change_rad":dh,
        "front_after_ack_m":front_after_ack,
        "physical_motion_l3_success":False,
        "formal_g07_accepted":False
    }

def pregoal_side_obstacle_ready(*,side_m,front_m,laser_at,pose_ack_at,now,
                                odom_vx,odom_wz,goal_sent):
    """Fresh post-ACK actual physical lidar + stationary Waffle before Goal.

    The side sector is the SAME physical bearing demonstrated in matched L2.
    A valid side sector never proves an obstacle will produce moving STOP.
    """
    values=(side_m,front_m,laser_at,pose_ack_at,now,odom_vx,odom_wz)
    if not all(_real(v) for v in values) or goal_sent is not False:
        return False
    return (
        .55<=side_m<=.95 and front_m>.75 and
        0<=now-laser_at<=.4 and laser_at>pose_ack_at and
        abs(odom_vx)<.015 and abs(odom_wz)<.05
    )

def demo_moving_stage_allowed(demo_corridor,phase):
    """No post-Goal physical Gazebo command in opt-in G07 demo corridor."""
    if type(demo_corridor) is not bool or phase not in ("clear","slowdown","stop"):
        raise ValueError("INVALID_DEMO_PHYSICAL_MOVE_SCOPE")
    return not demo_corridor and phase in ("slowdown","stop")
