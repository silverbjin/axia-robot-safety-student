"""P2 G07 simulation-only coordinate contract (pure; no ROS / Gazebo imports).

Map pose is provided by actual TF (map -> base_link). Gazebo world
pose is provided by the native `gz model -m turtlebot3_waffle --pose`.
Odometry tracks short-range relative motion between the verified anchors.
Never compare raw /odom (0,0) to the P1 map corridor (-2,-0.5).
"""
import math
import re

# Gazebo Harmonic `gz model --pose` prints separate XYZ and RPY triplets.
_ROW=re.compile(
    r"^\s*\[\s*([-+0-9.eE]+)\s*\|\s*([-+0-9.eE]+)\s*\|\s*([-+0-9.eE]+)\s*\]\s*$",
    re.MULTILINE
)


def _pose(p):
    if not isinstance(p,(tuple,list)) or len(p)!=3 or any(
        type(x) not in (float,int) or not math.isfinite(x) for x in p
    ):
        raise ValueError('INVALID_FRAME_POSE')
    return tuple(float(x) for x in p)


def parse_gz_model_pose(text):
    if not isinstance(text,str) or len(text)>40000 or not re.search(
        r'^\s*- Name: turtlebot3_waffle\s*$',text,re.MULTILINE
    ):
        raise ValueError('GAZEBO_ROBOT_MODEL_NOT_PROVEN')
    rows=_ROW.findall(text)
    if len(rows)!=2:
        raise ValueError('GAZEBO_WORLD_POSE_ROWS_MISSING')
    try:
        xyz=_pose(tuple(float(x) for x in rows[0]))
        rpy=_pose(tuple(float(x) for x in rows[1]))
    except (TypeError,ValueError,OverflowError) as e:
        raise ValueError('GAZEBO_WORLD_POSE_INVALID') from e
    if abs(rpy[0])>.25 or abs(rpy[1])>.25:
        raise ValueError('GAZEBO_ROBOT_NOT_UPRIGHT')
    return xyz[0],xyz[1],rpy[2]


def _angle(delta):
    return math.atan2(math.sin(delta),math.cos(delta))


def make_frame_anchor(map_pose,odom_pose,world_pose,*,map_pose_source='tf_map_base_link'):
    if map_pose_source not in ('tf_map_base_link','amcl_pose_map_transient_local'):
        raise ValueError('INVALID_MAP_POSE_PROVENANCE')
    mp=_pose(map_pose)
    op=_pose(odom_pose)
    try:
        wp=_pose(world_pose)
    except ValueError as exc:
        raise ValueError('WORLD_SPAWN_POSE_INVALID') from exc
    if not (-2.35<=mp[0]<=-1.3 and -.85<=mp[1]<=-.15
            and abs(_angle(mp[2]))<.32):
        raise ValueError('MAP_CORRIDOR_POSE_OUTSIDE_KNOWN_CORRIDOR')
    # Fixed official TB3 world / P1 startup. If robot was spawned elsewhere,
    # do NOT infer a map-world transform or teleport a collision obstacle.
    if not (-2.15<=wp[0]<=-1.85 and -.65<=wp[1]<=-.35
            and abs(_angle(wp[2]))<.15):
        raise ValueError('WORLD_SPAWN_POSE_OUTSIDE_KNOWN_CORRIDOR')
    return {'map_pose':mp,'odom_pose':op,'world_pose':wp,
            'world_pose_source':'validated_official_nav2_world_spawn',
            'map_pose_source':map_pose_source,
            'relative_motion_source':'ros_odom'}


def obstacle_world_pose(anchor,live_odom_pose,distance,obstacle_radius,*,demo_corridor=False):
    if not isinstance(anchor,dict):
        raise ValueError('INVALID_FRAME_ANCHOR')
    map0=_pose(anchor.get('map_pose'))
    odom0=_pose(anchor.get('odom_pose'))
    world0=_pose(anchor.get('world_pose'))
    live=_pose(live_odom_pose)
    if (type(distance) not in (int,float) or not math.isfinite(distance)
        or type(obstacle_radius) not in (int,float) or not math.isfinite(obstacle_radius)
        or not .20<=distance<=1.5 or not .01<=obstacle_radius<=.15):
        raise ValueError('INVALID_OBSTACLE_RANGE')
    dx=live[0]-odom0[0];dy=live[1]-odom0[1]
    yaw_delta=_angle(live[2]-odom0[2])
    # Map coordinates are used ONLY for P1 map-corridor verification.
    cm=math.cos(map0[2]-odom0[2]);sm=math.sin(map0[2]-odom0[2])
    mx=map0[0]+cm*dx-sm*dy
    my=map0[1]+sm*dx+cm*dy
    myaw=_angle(map0[2]+yaw_delta)
    if demo_corridor:
        # G07 demo-only corridor uses the official static map check; never
        # widen the original frozen P1/G05/G06 Goal geometry.
        from p2_g07_demo_corridor import within_demo_corridor
        if not within_demo_corridor((mx,my)):
            raise ValueError('G07_DEMO_MAP_CORRIDOR_OUT_OF_BOUNDS')
    elif not (-2.35<=mx<=-1.3 and -.85<=my<=-.15 and abs(myaw)<.32):
        raise ValueError('MAP_CORRIDOR_POSE_OUTSIDE_KNOWN_CORRIDOR')
    # Gazebo obstacle coordinates use independently measured WORLD anchor
    # and the odom motion since that anchor (not AMCL's -2m map offset).
    cw=math.cos(world0[2]-odom0[2]);sw=math.sin(world0[2]-odom0[2])
    wx=world0[0]+cw*dx-sw*dy
    wy=world0[1]+sw*dx+cw*dy
    wyaw=_angle(world0[2]+yaw_delta)
    c=distance+obstacle_radius
    target=(wx+c*math.cos(wyaw),wy+c*math.sin(wyaw))
    if not all(math.isfinite(v) for v in target):
        raise ValueError('INVALID_WORLD_OBSTACLE_POSE')
    if demo_corridor and not (-2.6 <= target[0] <= -1.0 and
                              -0.95 <= target[1] <= 1.55):
        raise ValueError('G07_DEMO_WORLD_OBSTACLE_OUT_OF_BOUNDS')
    return target


def wait_for_actual_map_tf(can_transform, *, budget_sec=10.0,
                           clock=None, sleep=None):
    """Wait only for a *real* TF transform callback before any G07 Goal.

    The previous 3s late-created TF listener gave a false negative in actual
    public CI #43242131339 after staged Nav2 had already reported READY.
    No guessed /odom, world/map offset, fake transform, or safety TTL bypass.
    On permanent absence return False; caller blocks Goal.
    """
    import time
    if not callable(can_transform) or (type(budget_sec) not in (int,float)
            or not math.isfinite(budget_sec) or not 3<=budget_sec<=12):
        raise ValueError("INVALID_G07_TF_READINESS_BOUNDARY")
    clock=clock or time.monotonic
    sleep=sleep or time.sleep
    start=clock()
    if not math.isfinite(start):
        raise ValueError("INVALID_G07_TF_CLOCK")
    while True:
        if can_transform() is True:
            return True
        left=budget_sec-(clock()-start)
        if left<=0:
            return False
        sleep(min(.05,left))


def verified_amcl_map_pose(frame_id, x, y, qx, qy, qz, qw):
    """Map pose from actual reliable/transient-local Nav2 AMCL localization.

    This is NOT a TF publisher or an odom/world coordinate fallback.
    Reject any non-map frame, invalid quaternion, nonfinite data or pose
    outside the unchanged G07 known map-start corridor before any Goal.
    """
    values=(x,y,qx,qy,qz,qw)
    if frame_id!='map' or any(
            type(v) not in (float,int) or not math.isfinite(v)
            for v in values):
        raise ValueError('UNTRUSTED_AMCL_MAP_FRAME_OR_NUMERIC')
    norm=qx*qx+qy*qy+qz*qz+qw*qw
    if not .95<=norm<=1.05:
        raise ValueError('UNTRUSTED_AMCL_QUATERNION')
    yaw=math.atan2(2*(qw*qz+qx*qy),1-2*(qy*qy+qz*qz))
    if not (-2.35<=x<=-1.3 and -.85<=y<=-.15
            and abs(_angle(yaw))<.32):
        raise ValueError('AMCL_MAP_START_OUTSIDE_KNOWN_CORRIDOR')
    return (float(x),float(y),yaw)
