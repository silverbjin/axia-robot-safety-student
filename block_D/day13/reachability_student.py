"""D13 synthetic P/N/U prediction student TODO (offline, no ROS/Goal/cmd_vel).

Original G09 oracle pin: instructor P3 staging p3_oracles.py
Git blob SHA1: 85dd0fa35b2e7982b0c86020fdd4f4952e6a039f
"""
def classify_time_indexed(robot_trajectory, person, *, now_sec,
                          dt_sec=0.2, horizon_sec=3.0, stale_sec=0.5,
                          confidence_min=0.5):
    """P=co-timed disk overlap; N=no overlap; U=invalid/stale/unknown.

    TODO(1): finite numeric input, timestamp age and confidence.
    TODO(2): complete 3.0s / 0.2s time-grid (16 robot points).
    TODO(3): constant-velocity human projection at the SAME timestamps.
    TODO(4): aggregate overlap only after validating EVERY sample.
    """
    return "U"  # EXPECTED RED: learners replace ONLY this educational function.
