"""D08 one educational TODO: integrate *existing* D04-D07 results only.

No ROS/Gazebo imports, no Nav2 Goal, no /cmd_vel publisher and no HW safety.
Prerequisite: student has completed D04, D05, D06 and D07 TODO functions.
"""
from block_B.block_b_todo import select_person,measure_person_range
from block_B.day06.safety_bubble_todo import bubble_policy
from block_B.day07.route_todo import assess_replan

def integrate_case(case:dict, routes:dict)->dict:
    """Combine recorded synthetic observation into a classroom report.

    Required output:
      case_id; person_detected; distance_m; range_status
      (CLEAR/SLOWDOWN/STOP/UNKNOWN); route_status
      (REPLAN_EVIDENCED/NOT_VERIFIED/UNKNOWN); advice
      (UNKNOWN_REVIEW,STOP_EXPECTED,SLOWDOWN_EXPECTED,
       REPLAN_REVIEW,MONITOR_ONLY); expected_ratio (float or None);
      source='D08_SYNTHETIC_CLASSROOM'; verified_level='PYTHON_ONLY'.
    ALWAYS False: robot_moved,collision_free_verified,
      control_published,safety_certified,ros_verified,gazebo_verified.

    Stale/unavailable/invalid depth or person makes range UNKNOWN.
    If range STOP, STOP_EXPECTED takes priority over untrusted route;
    otherwise UNKNOWN route must not give a CLEAR permission.
    Existing functions above are the only permitted classifier/planner inputs:
    do not implement a new Nav2 planner/CM controller.
    """
    # TODO(D08): compose D04/05/06/07; fail closed, produce only evidence.
    raise NotImplementedError("TODO_D08_INTEGRATE_CASE")
