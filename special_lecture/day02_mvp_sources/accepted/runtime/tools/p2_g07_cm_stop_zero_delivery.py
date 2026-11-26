"""Bounded G07 simulation-only official CM repeated-ZERO delivery configuration.

Nav2 Jazzy's stop_pub_timeout limits repeated ZERO output after a STOP.
With an independent AXIA 150ms CM input TTL, a healthy stopped Collision
Monitor can be misclassified as dead once the default 1s ZERO publication
window ends. Only the explicitly isolated G07 simulation exercise may extend
the repeated-ZERO window; Guard watchdog, physical obstacle zone, slowdown,
source timeout, Nav2 source, and all non-G07 modes remain unchanged.

The extension does NOT itself prove the observed 186ms gap was caused by
stop_pub_timeout; actual Gazebo runtime param readback + delivery cadence,
STOP LaserScan and odom are separate required CI acceptance evidence.
"""
import math

G07_STOP_ZERO_WINDOW_SEC=5.0

def _scoped(env):
    if not isinstance(env, dict) and not hasattr(env,"get"):
        raise ValueError("INVALID_G07_ENVIRONMENT")
    if env.get("AXIA_P0_SIM_ONLY")!="1":
        return False
    ci=(env.get("GITHUB_ACTIONS")=="true"
        and env.get("AXIA_G07_CI_SIM_GOAL_ALLOWED")=="1"
        and env.get("AXIA_P2_G07_PHYSICAL_PREFLIGHT")=="1")
    owner=(env.get("GITHUB_ACTIONS")!="true"
           and env.get("AXIA_P2_G07_RELOCATED_OBSTACLE")=="1")
    return ci or owner

def apply_g07_zero_delivery(cm: dict, env) -> bool:
    """Only change CM's repeated ZERO publication duration, fail closed."""
    if not _scoped(env):
        return False
    if not isinstance(cm,dict) or (
            cm.get("cmd_vel_in_topic")!="cmd_vel_supervised"
            or cm.get("cmd_vel_out_topic")!="cmd_vel_pre_guard"):
        raise ValueError("G07_CM_EXCLUSIVE_GRAPH_REQUIRED")
    original=cm.get("stop_pub_timeout",1.0)
    if (type(original) not in (int,float) or not math.isfinite(original)
            or not .5<=original<=2.0):
        raise ValueError("G07_CM_ORIGINAL_ZERO_WINDOW_UNEXPECTED")
    source_timeout=cm.get("source_timeout")
    if (type(source_timeout) not in (int,float)
            or not math.isfinite(source_timeout)
            or not 0<source_timeout<=5.0):
        raise ValueError("G07_CM_SOURCE_TIMEOUT_INVALID")
    cm["stop_pub_timeout"]=G07_STOP_ZERO_WINDOW_SEC
    return True

