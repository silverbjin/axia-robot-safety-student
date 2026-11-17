"""Official TurtleBot3 Waffle simulation + fail-closed P1 Nav2 command chain.

Official upstream launch used in memory. P0 DockingServer source removal retained.
"""
from pathlib import Path
import sys

from ament_index_python.packages import get_package_share_directory
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction, SetLaunchConfiguration
from launch.substitutions import LaunchConfiguration

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from axia_launch_tools import load_upstream_launch, replace_upstream_include
from axia_p1_launch_policy import write_p1_parameters


def _configure_nav2(context):
    source = LaunchConfiguration("params_file").perform(context)
    patched = write_p1_parameters(source)
    return [SetLaunchConfiguration("params_file", str(patched))]


def _insert_guard_before_bringup(description):
    expected = {
        "namespace", "use_namespace", "slam", "map", "use_sim_time",
        "params_file", "autostart", "use_composition", "use_respawn",
    }
    candidates = [
        i for i, action in enumerate(description.entities)
        if isinstance(action, IncludeLaunchDescription)
        and {k for k, _ in action.launch_arguments} == expected
    ]
    if len(candidates) != 1:
        raise ValueError("Unexpected upstream bringup include count: " + str(len(candidates)))
    description.entities.insert(candidates[0], OpaqueFunction(function=_configure_nav2))
    return description


def generate_launch_description():
    source = Path(get_package_share_directory("nav2_bringup")) / "launch" / "tb3_simulation_launch.py"
    description = load_upstream_launch(source)
    replace_upstream_include(
        description, "bringup_launch.py", HERE / "axia_bringup_p1.launch.py"
    )
    # Declare the guard's scan input explicitly; future T06 can redirect
    # this to a controlled fault-injection relay instead of /scan.
    description.entities.insert(
        0, DeclareLaunchArgument("safety_scan_topic", default_value="/safety/scan",
                                 description="Trusted LaserScan topic for AXIA supervisor")
    )
    description.entities.insert(
        1, DeclareLaunchArgument("allow_fault_injection", default_value="false",
                                  description="P1-T06 simulation-only scan fault controls")
    )
    return _insert_guard_before_bringup(description)
