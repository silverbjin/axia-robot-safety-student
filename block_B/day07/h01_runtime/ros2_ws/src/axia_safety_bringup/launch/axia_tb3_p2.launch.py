"""Official Waffle sim + P2-only safety graph; NO goal/fault by default."""
from pathlib import Path
import sys
from ament_index_python.packages import get_package_share_directory
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction, SetLaunchConfiguration
from launch.substitutions import LaunchConfiguration
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from axia_launch_tools import load_upstream_launch
from axia_p2_include import replace_include
from axia_p2_launch_policy import write_p2_parameters


def _configure_nav2(context):
    return [SetLaunchConfiguration('params_file',
                                   str(write_p2_parameters(LaunchConfiguration('params_file').perform(context))))]


def generate_launch_description():
    source = Path(get_package_share_directory('nav2_bringup'))/'launch'/'tb3_simulation_launch.py'
    d = load_upstream_launch(source)
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
