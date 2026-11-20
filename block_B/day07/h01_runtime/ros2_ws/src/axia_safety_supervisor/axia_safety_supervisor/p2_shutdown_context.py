"""ROS 2 Jazzy SIGINT cleanup-only RCLError classifier (no safety logic).

Owner vJpsc6Wy after its pre-Goal abort: the two actual P2 processes saw
rclpy WaitSet context invalid during launch SIGINT and exited 1, although
official Nav2 and Gazebo children exited cleanly. Suppress ONLY the exact
shutdown-origin wait-set exception; any active-context/error remains fatal.
"""

def is_context_waitset_shutdown(exc, *, context_ok):
    """Return True only for already-shutdown rclpy WaitSet race after SIGINT."""
    detail=str(exc)
    return (
        context_ok is False
        and type(exc).__name__=="RCLError"
        and "failed to initialize wait set" in detail
        and "context is not valid" in detail
    )


def is_context_publish_shutdown(exc, *, context_ok):
    """Ignore ONLY a P2 timer's publisher after actual Jazzy context shutdown.

    The exact public Gazebo L2 #44697450829 P2 Supervisor exited 1 when
    rclpy's SIGINT shutdown invalidated the context between a safety timer
    callback's command/status publishing. On a LIVE context the exact same
    failure must still propagate; no safety TTL or state is changed.
    """
    return (
        context_ok is False
        and type(exc).__name__=="RCLError"
        and str(exc).startswith("Failed to publish: publisher's context is invalid")
    )
