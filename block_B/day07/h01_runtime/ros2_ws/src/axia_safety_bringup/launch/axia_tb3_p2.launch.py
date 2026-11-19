"""Official Waffle sim + P2-only safety graph; NO goal/fault by default."""
from pathlib import Path
import os
import sys
import hashlib
import xml.etree.ElementTree as ET
from ament_index_python.packages import get_package_share_directory
from launch.actions import (DeclareLaunchArgument, ExecuteProcess,
                            IncludeLaunchDescription, OpaqueFunction,
                            RegisterEventHandler, SetLaunchConfiguration)
from launch.event_handlers import OnProcessExit
from launch.actions import EmitEvent
from launch.events import Shutdown
from launch.substitutions import LaunchConfiguration
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from axia_launch_tools import load_upstream_launch
from axia_p2_include import replace_include
from axia_p2_launch_policy import write_p2_parameters


def _configure_nav2(context):
    return [SetLaunchConfiguration('params_file',
                                   str(write_p2_parameters(LaunchConfiguration('params_file').perform(context))))]



def _world_xacro_sync_scope(environ):
    """Only the three approved simulation demo modes may alter upstream launch."""
    if environ.get('AXIA_P0_SIM_ONLY') != '1':
        return None
    h01=(environ.get('AXIA_D07_H01_GUI_NO_GOAL') == '1'
         and environ.get('AXIA_G07_CI_SIM_GOAL_ALLOWED') == '0')
    owner=(environ.get('AXIA_G07_TASK04_OWNER_MOVING_L3') == '1'
           and environ.get('AXIA_G07_OWNER_STARTUP_PARITY') == '1'
           and environ.get('AXIA_G07_CI_SIM_GOAL_ALLOWED') == '0'
           and environ.get('GITHUB_ACTIONS') != 'true')
    ci=(environ.get('AXIA_G07_TASK04_CI_GUI_MOVING') == '1'
        and environ.get('AXIA_G07_TASK03_FORMAL_CI') == '1'
        and environ.get('AXIA_G07_CI_SIM_GOAL_ALLOWED') == '1'
        and environ.get('GITHUB_ACTIONS') == 'true')
    if sum((h01,owner,ci)) != 1:
        return None
    return 'h01' if h01 else ('owner' if owner else 'ci_moving')


def _check_world_sdf_after_xacro_exit(returncode, cmd):
    """Verify upstream xacro finished and produced actual parseable world SDF."""
    if (not isinstance(cmd,(list,tuple)) or len(cmd) < 4
            or cmd[0] != 'xacro' or '-o' not in cmd):
        return 'GAZEBO_WORLD_XACRO_COMMAND_CHANGED', {}
    output_index=cmd.index('-o')+1
    if output_index >= len(cmd) or not isinstance(cmd[output_index],str):
        return 'GAZEBO_WORLD_XACRO_COMMAND_CHANGED', {}
    path=Path(cmd[output_index])
    if not path.is_absolute() or path.suffix != '.sdf':
        return 'GAZEBO_WORLD_XACRO_COMMAND_CHANGED', {}
    if returncode != 0:
        return 'GAZEBO_WORLD_XACRO_FAILED', {'returncode':returncode}
    if not path.is_file():
        return 'GAZEBO_WORLD_SDF_MISSING', {}
    try:
        raw=path.read_bytes()
        if not raw.strip():
            return 'GAZEBO_WORLD_SDF_INVALID', {'bytes':len(raw)}
        root=ET.fromstring(raw)
        if root.tag != 'sdf' or root.find('world') is None:
            return 'GAZEBO_WORLD_SDF_INVALID', {'bytes':len(raw)}
    except (OSError,ET.ParseError):
        return 'GAZEBO_WORLD_SDF_INVALID', {}
    return 'WORLD_SDF_READY', {
        'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
        'sdf_name':path.name,
    }


def _order_world_xacro_before_gazebo(d):
    """Reuse H01's launch event ordering for approved Owner / CI moving demos.

    Upstream Nav2's two direct ExecuteProcess actions are both scheduled in
    one LaunchDescription; textual order alone cannot await xacro completion.
    Do not change official Nav2, timers, planner, Supervisor or Guard.
    """
    scope=_world_xacro_sync_scope(os.environ)
    if scope is None:
        return
    processes=[item for item in d.entities if type(item) is ExecuteProcess]
    if len(processes)!=2:
        raise ValueError("G07_WORLD_XACRO_UPSTREAM_PROCESS_SHAPE_CHANGED")
    world_xacro, gazebo_server=processes
    if d.entities.index(world_xacro) >= d.entities.index(gazebo_server):
        raise ValueError("G07_WORLD_XACRO_UPSTREAM_PROCESS_ORDER_CHANGED")
    d.entities.remove(gazebo_server)

    def _on_xacro_exit(event, context):
        status, evidence=_check_world_sdf_after_xacro_exit(
            event.returncode,event.cmd)
        if status!='WORLD_SDF_READY':
            print('AXIA_G07_WORLD_XACRO_FIRST_FAILURE='+status+
                  ' scope='+scope+' evidence='+repr(evidence),flush=True)
            return [EmitEvent(event=Shutdown(reason=status))]
        print('AXIA_G07_WORLD_SDF_VALID_BEFORE_GAZEBO'
              ' scope='+scope+' bytes='+str(evidence['bytes'])+
              ' sha256='+evidence['sha256'],flush=True)
        return [gazebo_server]

    # Event handler must be registered BEFORE the xacro process is started.
    d.entities.insert(d.entities.index(world_xacro),
                      RegisterEventHandler(OnProcessExit(
                          target_action=world_xacro,
                          on_exit=_on_xacro_exit)))


def generate_launch_description():
    source = Path(get_package_share_directory('nav2_bringup'))/'launch'/'tb3_simulation_launch.py'
    d = load_upstream_launch(source)
    _order_world_xacro_before_gazebo(d)
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
