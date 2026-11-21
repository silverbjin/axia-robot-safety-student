"""Official ROS2 Jazzy EventsExecutor backport PR #1435, opt-in only.

For real G07 native CI A/B only, never automatic Owner authorization.
All read-only pregoal and moving observer subscriptions keep their existing
QoS and strict 120/150/300ms limits. No ROS imports or safety commands.
"""

def select_events_executor(environ, *, owner_mode):
    value=environ.get("AXIA_G07_EVENTS_EXECUTOR_AB","0")
    if value not in ("","0","1"):
        raise ValueError("G07_EVENTS_EXECUTOR_INVALID_VALUE")
    if value!="1":
        return False
    allowed=(not owner_mode
             and environ.get("GITHUB_ACTIONS")=="true"
             and environ.get("AXIA_G07_CI_SIM_GOAL_ALLOWED")=="1"
             and environ.get("AXIA_P0_SIM_ONLY")=="1"
             and environ.get("AXIA_G07_OWNER_STARTUP_PARITY")=="1")
    if not allowed:
        raise ValueError("G07_EVENTS_EXECUTOR_SCOPE_DENIED")
    return True
