"""Scope two read-only G07 moving Observer subscribers to independent groups.

ROS2 Jazzy's default callback group is mutually exclusive. The existing
2-worker observer therefore serializes /clock, /scan, guard, CM and supervisor
speed callbacks. This policy only changes callback dispatch for TWO existing
read-only Twist subscriptions; it never modifies publisher/Guard/CM safety.
"""
def scoped_cm_groups(environ, factory):
    mode=environ.get("AXIA_G07_CM_OBSERVER_GROUPS","0")
    if mode=="0":
        return (None,None)
    if mode!="1" or environ.get("AXIA_G07_OWNER_STARTUP_PARITY")!="1":
        raise ValueError("G07_CM_OBSERVER_GROUPS_REQUIRES_SCOPED_OWNER_PARITY")
    # Do not use ReentrantCallbackGroup: a single topic's sequence ordering
    # must remain mutually exclusive for the strict existing sequence oracle.
    a,b=factory(),factory()
    if a is b:
        raise ValueError("G07_CM_OBSERVER_GROUPS_MUST_BE_DISTINCT")
    return a,b
