"""Official Waffle sim + P2-only safety graph; NO goal/fault by default."""
from pathlib import Path
import os
import sys
import xml.etree.ElementTree as ET
from ament_index_python.packages import get_package_share_directory
from launch.actions import (DeclareLaunchArgument, ExecuteProcess,
                            IncludeLaunchDescription, OpaqueFunction,
                            RegisterEventHandler, SetLaunchConfiguration,
                            Shutdown)
from launch.event_handlers import OnProcessExit
from launch.substitutions import LaunchConfiguration
from launch.utilities import perform_substitutions
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from axia_launch_tools import load_upstream_launch
from axia_p2_include import replace_include
from axia_p2_launch_policy import write_p2_parameters


def _configure_nav2(context):
    return [SetLaunchConfiguration('params_file',
                                   str(write_p2_parameters(LaunchConfiguration('params_file').perform(context))))]


def _on_world_xacro_exit(event, context, gazebo_server):
    """Real upstream Xacro completion: reject a failed or invalid temp SDF.

    Never launch Gazebo based on an event alone. Preserve official Xacro,
    Gazebo, Nav2 and their safety configuration unchanged.
    """
    if event.returncode != 0:
        print("G07_WORLD_XACRO_FAILED_NO_GAZEBO", flush=True)
        return [Shutdown(reason="G07_WORLD_XACRO_FAILED_NO_GAZEBO")]
    try:
        cmd = gazebo_server.process_description.cmd
        if len(cmd) != 5:
            raise ValueError("OFFICIAL_GAZEBO_EXECUTABLE_SHAPE_CHANGED")
        world_sdf = Path(perform_substitutions(context, cmd[-1]))
        if not world_sdf.is_file() or world_sdf.stat().st_size < 32:
            raise ValueError("WORLD_SDF_NOT_READY")
        root = ET.parse(world_sdf).getroot()
        if root.tag != "sdf" or root.find("world") is None:
            raise ValueError("WORLD_SDF_INVALID")
    except (OSError, ValueError, ET.ParseError, TypeError) as exc:
        print("G07_WORLD_SDF_INVALID_NO_GAZEBO " + str(exc)[:180], flush=True)
        return [Shutdown(reason="G07_WORLD_SDF_INVALID_NO_GAZEBO")]
    print("G07_WORLD_XACRO_SDF_READY_BEFORE_GAZEBO", flush=True)
    return [gazebo_server]


def _order_h01_world_xacro_before_gazebo(d):
    """Order official Jazzy Xacro writer before Gazebo reader for demo only.

    The upstream two-process launch has a real temp-SDF race (Nav2 #5350).
    Reuse the same sequence for D07 NO_GOAL and G07 Task04 Owner/CI moving;
    check exit code and actual SDF before starting Gazebo. Any other mode
    retains the original upstream launch graph.
    """
    env = os.environ
    h01 = (env.get("AXIA_D07_H01_GUI_NO_GOAL") == "1"
           and env.get("AXIA_P0_SIM_ONLY") == "1"
           and env.get("AXIA_G07_CI_SIM_GOAL_ALLOWED") == "0")
    owner = (env.get("GITHUB_ACTIONS") != "true"
             and env.get("AXIA_G07_TASK04_OWNER_MOVING_L3") == "1"
             and env.get("AXIA_G07_CI_SIM_GOAL_ALLOWED") == "0"
             and env.get("AXIA_P0_SIM_ONLY") == "1"
             and env.get("AXIA_G07_OWNER_STARTUP_PARITY") == "1"
             and env.get("AXIA_P2_G07_PHYSICAL_PREFLIGHT") == "1"
             and env.get("AXIA_P2_G07_RELOCATED_OBSTACLE") == "1")
    ci = (env.get("GITHUB_ACTIONS") == "true"
          and env.get("AXIA_G07_TASK04_CI_GUI_MOVING") == "1"
          and env.get("AXIA_G07_CI_SIM_GOAL_ALLOWED") == "1"
          and env.get("AXIA_P0_SIM_ONLY") == "1"
          and env.get("AXIA_G07_OWNER_STARTUP_PARITY") == "1"
          and env.get("AXIA_P2_G07_PHYSICAL_PREFLIGHT") == "1")
    sensor_no_goal = (
        env.get("AXIA_G07_OWNER_SENSOR_TRUTH_NO_GOAL") == "1"
        and ((env.get("GITHUB_ACTIONS") != "true"
              and env.get("AXIA_G07_CI_SENSOR_TRUTH_NO_GOAL", "0") == "0")
             or (env.get("GITHUB_ACTIONS") == "true"
                 and env.get("AXIA_G07_CI_SENSOR_TRUTH_NO_GOAL") == "1"))
        and env.get("AXIA_G07_TASK04_OWNER_MOVING_L3", "0") == "0"
        and env.get("AXIA_G07_CI_SIM_GOAL_ALLOWED") == "0"
        and env.get("AXIA_P0_SIM_ONLY") == "1"
        and env.get("AXIA_G07_OWNER_STARTUP_PARITY") == "1"
        and env.get("AXIA_P2_G07_PHYSICAL_PREFLIGHT") == "1"
        and env.get("AXIA_P2_G07_RELOCATED_OBSTACLE") == "1")
    if not (h01 or owner or ci or sensor_no_goal):
        return
    processes = [item for item in d.entities if type(item) is ExecuteProcess]
    if len(processes) != 2:
        raise ValueError("D07_H01_OFFICIAL_WORLD_PROCESS_SHAPE_CHANGED")
    world_xacro, gazebo_server = processes
    if d.entities.index(world_xacro) >= d.entities.index(gazebo_server):
        raise ValueError("D07_H01_OFFICIAL_WORLD_PROCESS_ORDER_CHANGED")
    d.entities.remove(gazebo_server)
    # Register before the writer to catch even a very fast process exit.
    d.entities.insert(
        d.entities.index(world_xacro),
        RegisterEventHandler(OnProcessExit(
            target_action=world_xacro,
            on_exit=lambda event, context: _on_world_xacro_exit(
                event, context, gazebo_server))),
    )


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
