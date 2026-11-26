"""P2 G07 simulation-only bounded physical STOP geometry.

Immutable Owner trace 0UqpnePv:
* original set_pose dispatch = 0.52m in robot-local obstacle SURFACE range
* gz ACK = 2.595622s, actual post-ACK minimum LaserScan = 0.458467m
* CM STOP requires fresh measured front < 0.4m
An immutable, linear translation replay can forecast but never proves physical
L3 motion. Real Gazebo no-Goal must separately verify this pose is sensed;
Owner L3 is still the only accepted moving-Goal measurement.
"""
import math

STOP_DISPATCH_M = 0.43
STOP_DISPATCH_RANGE_M = (0.41, 0.45)
OLD_OWNER_STOP_DISPATCH_M = 0.52
CM_STOP_FRONT_LIMIT_M = 0.40


def _finite(x):
    return type(x) in (int, float) and math.isfinite(x)


def stop_geometry_replay(*, previous_dispatch_m, corrected_dispatch_m,
                         original_post_ack_front_m, gz_move_ack_duration_s):
    """Pure translation model for same robot trajectory / Gazebo service delay.

    NO claim of robot footprint clearance, live collision count, or actual STOP.
    Fail closed if the previous trace or new command falls out of bounds.
    """
    if (not _finite(previous_dispatch_m) or
            abs(previous_dispatch_m - OLD_OWNER_STOP_DISPATCH_M) > 1e-9):
        raise ValueError("UNKNOWN_OWNER_STOP_GEOMETRY")
    if not _finite(corrected_dispatch_m) or (
        abs(corrected_dispatch_m - previous_dispatch_m)>1e-9 and
        not STOP_DISPATCH_RANGE_M[0] <= corrected_dispatch_m <=
            STOP_DISPATCH_RANGE_M[1]
    ):
        raise ValueError("UNBOUNDED_STOP_DISPATCH")
    if (not _finite(original_post_ack_front_m) or
            not .35 <= original_post_ack_front_m <= .60):
        raise ValueError("OWNER_PHYSICAL_SCAN_UNAVAILABLE")
    if (not _finite(gz_move_ack_duration_s) or
            not .1 <= gz_move_ack_duration_s <= 7):
        raise ValueError("OWNER_GZ_ACK_DELAY_UNAVAILABLE")
    forecast = (original_post_ack_front_m +
                (corrected_dispatch_m - previous_dispatch_m))
    return {
        "expected_front_m": forecast,
        "stop_crossing_predicted": .14 <= forecast < CM_STOP_FRONT_LIMIT_M,
        "actual_moving_stop_verified": False,
        "forecast_only": True,
        "old_gz_ack_duration_s": gz_move_ack_duration_s,
    }


def pregoal_stop_probe_acceptable(front):
    """Real no-Goal scan band for obstacle at 0.43m from stationary Waffle.

    This is deliberately OUTSIDE stop range before the Goal.
    Moving scenario must separately prove <0.40m with actual LaserScan.
    """
    return _finite(front) and .40 < front < .60
