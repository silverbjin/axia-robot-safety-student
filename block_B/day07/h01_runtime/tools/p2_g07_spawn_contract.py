"""Fixed official Nav2 Jazzy TB3 Waffle WORLD spawn contract (no Gazebo CLI).

The official tb3_simulation_launch.py spawns turtlebot3_waffle in Gazebo WORLD
at (-2.00, -0.50, yaw=0). /odom starts close to (0,0), but is an independent
relative frame. Never infer WORLD=(0,0) from /odom. Fail on launch drift.

The value is not itself physical obstacle proof: G07 must also verify real
Gazebo entity creation/pose acknowledgement and LaserScan distance change.
"""
import ast
from pathlib import Path

APPROVED_WORLD=(-2.0,-0.5,0.0)


def _call_name(call):
    return call.func.id if isinstance(call.func,ast.Name) else (
        call.func.attr if isinstance(call.func,ast.Attribute) else '')


def official_tb3_spawn_from_source(source: str):
    if not isinstance(source,str) or len(source)>500000:
        raise ValueError('OFFICIAL_LAUNCH_SOURCE_INVALID')
    try:tree=ast.parse(source)
    except SyntaxError as exc:raise ValueError('OFFICIAL_LAUNCH_SYNTAX_INVALID') from exc
    poses=[]
    for node in ast.walk(tree):
        if not isinstance(node,ast.Assign) or not any(
            isinstance(t,ast.Name) and t.id=='pose' for t in node.targets
        ):
            continue
        if not isinstance(node.value,ast.Dict):
            raise ValueError('OFFICIAL_SPAWN_POSE_DICTIONARY_MISSING')
        p={}
        for key,call in zip(node.value.keys,node.value.values):
            if not isinstance(key,ast.Constant) or not isinstance(key.value,str):
                raise ValueError('OFFICIAL_SPAWN_KEY_INVALID')
            p[key.value]=call
        poses.append(p)
    if len(poses)!=1:
        raise ValueError('OFFICIAL_SPAWN_POSE_AMBIGUOUS')
    p=poses[0]
    result=[]
    for key,arg,nominal in [('x','x_pose',-2.0),('y','y_pose',-.5),('Y','yaw',0.0)]:
        node=p.get(key)
        if not isinstance(node,ast.Call) or _call_name(node)!='LaunchConfiguration':
            raise ValueError('OFFICIAL_SPAWN_CONFIG_MISSING_'+key)
        if len(node.args)!=1 or not isinstance(node.args[0],ast.Constant) or node.args[0].value!=arg:
            raise ValueError('OFFICIAL_SPAWN_ARG_CHANGED_'+key)
        default=[kw.value for kw in node.keywords if kw.arg=='default']
        if len(default)!=1 or not isinstance(default[0],ast.Constant):
            raise ValueError('OFFICIAL_SPAWN_DEFAULT_MISSING_'+key)
        try:value=float(default[0].value)
        except (TypeError,ValueError) as exc:
            raise ValueError('OFFICIAL_SPAWN_DEFAULT_INVALID_'+key) from exc
        if abs(value-nominal)>1e-9:
            raise ValueError('OFFICIAL_SPAWN_DEFAULT_CHANGED_'+key)
        result.append(value)
    def find_declared_arg(name):
        for node in ast.walk(tree):
            if not isinstance(node,ast.Call) or _call_name(node)!='DeclareLaunchArgument':
                continue
            if not node.args or not isinstance(node.args[0],ast.Constant) or node.args[0].value!=name:
                continue
            vals=[kw.value for kw in node.keywords if kw.arg=='default_value']
            if len(vals)==1:return vals[0]
        raise ValueError('OFFICIAL_SPAWN_DECLARATION_MISSING_'+name)
    robot=find_declared_arg('robot_name')
    if not isinstance(robot,ast.Constant) or robot.value!='turtlebot3_waffle':
        raise ValueError('OFFICIAL_SPAWN_ROBOT_CHANGED')
    world=find_declared_arg('world')
    if not isinstance(world,ast.Call) or _call_name(world)!='join':
        raise ValueError('OFFICIAL_SPAWN_WORLD_CHANGED')
    if not any(isinstance(a,ast.Constant) and a.value=='tb3_sandbox.sdf.xacro' for a in world.args):
        raise ValueError('OFFICIAL_SPAWN_WORLD_CHANGED')
    return tuple(result)


def official_tb3_spawn():
    from ament_index_python.packages import get_package_share_directory
    path=Path(get_package_share_directory('nav2_bringup'))/'launch'/'tb3_simulation_launch.py'
    return official_tb3_spawn_from_source(path.read_text(encoding='utf-8'))
