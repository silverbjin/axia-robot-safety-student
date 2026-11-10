"""D07 student TODO. Read-only evaluation of external Nav2 plans, never a controller."""
def route_obstacle_status(path, person_xy, *, valid=True, age_s=0.0,
                          max_age_s=0.5, buffer_radius_m=0.35):
    """TODO: CLEAR/BLOCKED/UNKNOWN. Check *segments*, not just sampled points.
    Invalid person coordinates, stale age, invalid route -> UNKNOWN.
    Do not write a planner, call Nav2 Goal, or publish /cmd_vel.
    """
    raise NotImplementedError("TODO_D07_ROUTE_OBSTACLE")

def assess_replan(path_before,path_after,person_xy,**kwargs):
    """TODO: REPLAN_EVIDENCED iff original BLOCKED and new path CLEAR.
    Always robot_moved=False, collision_free_verified=False, safety_certified=False.
    """
    raise NotImplementedError("TODO_D07_REPLAN_EVIDENCE")
