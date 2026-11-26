"""Official Waffle sim + P2-only safety graph; NO goal/fault by default."""
from pathlib import Path
import os
import sys
from ament_index_python.packages import get_package_share_directory
from launch.actions import (DeclareLaunchArgument, ExecuteProcess,
                            IncludeLaunchDescription, OpaqueFunction,
                            RegisterEventHandler, SetLaunchConfiguration)
from launch.event_handlers import OnProcessExit
from launch.substitutions import LaunchConfiguration
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from axia_launch_tools import load_upstream_launch
from axia_p2_include import replace_include
from axia_p2_launch_policy import write_p2_parameters


def _configure_nav2(context):
    return [SetLaunchConfiguration('params_file',
                                   str(write_p2_parameters(LaunchConfiguration('params_file').perform(context))))]


def _order_h01_world_xacro_before_gazebo(d):
    """Fix upstream async tempfile race ONLY for H01 stationary physical GUI.

    Official Jazzy tb3_simulation_launch has two direct ExecuteProcess actions:
    world Xacro writer and Gazebo server reader. Starting them together can
    yield gz exit255 before the world SDF exists (upstream Nav2 #5350).
    Register OnProcessExit before launching Xacro; never change Nav2 internals
    or the moving-goal/safety paths.
    """
    if not (os.environ.get("AXIA_D07_H01_GUI_NO_GOAL") == "1"
            and os.environ.get("AXIA_P0_SIM_ONLY") == "1"
            and os.environ.get("AXIA_G07_CI_SIM_GOAL_ALLOWED") == "0"):
        return
    processes=[item for item in d.entities if type(item) is ExecuteProcess]
    if len(processes)!=2:
        raise ValueError("D07_H01_OFFICIAL_WORLD_PROCESS_SHAPE_CHANGED")
    world_xacro, gazebo_server = processes
    if d.entities.index(world_xacro) >= d.entities.index(gazebo_server):
        raise ValueError("D07_H01_OFFICIAL_WORLD_PROCESS_ORDER_CHANGED")
    d.entities.remove(gazebo_server)
    # Registration MUST precede world_xacro to avoid missing a fast exit.
    d.entities.insert(d.entities.index(world_xacro),
                      RegisterEventHandler(OnProcessExit(
                          target_action=world_xacro,
                          on_exit=[gazebo_server])))


def generate_launch_description():
    source = Path(get_package_share_directory('nav2_bringup'))/'launch'/'tb3_simulation_launch.py'
    d = load_upstream_launch(source)
    _order_h01_world_xacro_before_gazebo(d)
    replace_include(d, 'bringup_launch.py', HERE/'axia_bringup_p2.launch.py')
    expected = {'namespace','use_namespace','slam','map','use_sim_time','params_file',
                'autostart','use_composition','use_respawn'}
    matches = [i for i,x in enumerate(d.entities) if isinstance(x, IncludeLaunchDescription)
               and {k for k, _ in x.launch_arguments} == expected]
    if len(matches) != 1:
        raise ValueError('Cannot identify exactly one official Nav2 bringup include')
    d.entities.insert(matches[0], OpaqueFunction(function=_configure_nav2))
    d.entities.insert(0, DeclareLaunchArgument('safety_scan_topic',default_value='/safety/scan'))
    d.entities.insert(1, DeclareLaunchArgument('allow_fault_injection',default_value='false'))
    d.entities.insert(2, DeclareLaunchArgument('p3_fixture_risk_bridge_enabled',default_value='false'))
    return d
