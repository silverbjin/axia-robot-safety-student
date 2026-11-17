"""H01 NO-GOAL actual AMCL map pose delivery: bounded retry ONLY.

Real public L2 #43597565919 had P2 pregoal scan/odom/nav ready and the
H01 pre-executor TF listener, yet the first _map_robot_pose() attempt
exhausted its fixed 3s AMCL transient-local window. That first exception
bypassed H01 outer until() entirely. Retry only this exact safety-preserving
absence, for three existing 3s bounded ROS reads (<=~9s total).
Never substitute /odom as map, fixed coordinates, world pose or fake TF.
Do not change G07 Owner path, QoS, navigation Goal or safety TTL.
"""
from __future__ import annotations
import math


def retry_actual_amcl_map_pose(probe):
    """Return one ACTUAL fresh pose from the existing ROS/AMCL reader."""
    if not callable(probe):
        raise ValueError("REAL_AMCL_PROBE_NOT_CALLABLE")
    last=None
    for _ in range(3):
        try:
            value=probe()
        except RuntimeError as err:
            if str(err)!="G07_AMCL_MAP_POSE_UNAVAILABLE_BEFORE_GOAL":
                raise
            last=err
            continue
        if (not isinstance(value,(list,tuple)) or len(value)!=3
            or any(type(v) not in (int,float) or not math.isfinite(v)
                   for v in value)):
            raise RuntimeError("INVALID_REAL_AMCL_MAP_POSE")
        return tuple(value)
    if last is not None:
        raise RuntimeError("G07_AMCL_MAP_POSE_UNAVAILABLE_BEFORE_GOAL") from last
    raise RuntimeError("G07_AMCL_MAP_POSE_UNAVAILABLE_BEFORE_GOAL")
