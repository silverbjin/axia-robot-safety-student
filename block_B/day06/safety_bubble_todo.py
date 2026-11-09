"""D06 student exercise — classroom comparison ONLY, not a robot controller.

Do not publish /cmd_vel, call Nav2 actions, or modify the P1 command chain.
The official Nav2 Collision Monitor handles real stop/slowdown.
"""
def classify_range(distance_m, *, valid=True, age_s=0.0,
                   stop_radius_m=0.40, slowdown_radius_m=0.75,
                   slowdown_ratio=0.30, max_age_s=0.50):
    """TODO: return CLEAR, SLOWDOWN, STOP, or UNKNOWN.

    Distance <= stop -> STOP, <= slowdown -> SLOWDOWN, else CLEAR.
    Missing/stale/NaN/Inf/negative/bool/non-numeric -> UNKNOWN.
    Validate configuration (positive stop < slowdown, 0 < ratio < 1).
    No ROS or actuator code is permitted in this student exercise.
    """
    raise NotImplementedError("TODO_D06_CLASSIFY_RANGE")


def bubble_policy(distance_m, **kwargs):
    """TODO: return educational dict with status/expected_ratio/flags.

    CLEAR ratio=1.0; SLOWDOWN ratio=0.3 (configurable); STOP ratio=0;
    UNKNOWN ratio=None; safety_certified=False, control_published=False.
    """
    raise NotImplementedError("TODO_D06_BUBBLE_POLICY")
