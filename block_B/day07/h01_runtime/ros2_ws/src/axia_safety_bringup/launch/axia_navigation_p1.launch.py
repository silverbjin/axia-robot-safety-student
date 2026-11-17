"""P0 fail-closed official Nav2 sans DockingServer + AXIA Supervisor.

CollisionMonitor remains a Nav2 managed lifecycle node and the sole final
/cmd_vel publisher. This file does not start a second collision monitor.
"""
from pathlib import Path
import sys
from ament_index_python.packages import get_package_share_directory
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from axia_launch_tools import load_upstream_launch


def generate_launch_description():
    source = Path(get_package_share_directory("nav2_bringup")) / "launch" / "navigation_launch.py"
    description = load_upstream_launch(source, strip_docking=True)
    description.add_action(
        Node(
            package="axia_fault_injector",
            executable="fault_injector_node",
            name="axia_fault_injector",
            output="screen",
            parameters=[{
                "use_sim_time": LaunchConfiguration("use_sim_time"),
                "allow_fault_injection": ParameterValue(
                    LaunchConfiguration("allow_fault_injection"), value_type=bool
                ),
            }],
        )
    )
    description.add_action(
        Node(
            package="axia_safety_supervisor",
            executable="supervisor_node",
            name="axia_safety_supervisor",
            output="screen",
            parameters=[{"use_sim_time": LaunchConfiguration("use_sim_time")}],
            remappings=[("/safety/scan", LaunchConfiguration("safety_scan_topic"))],
        )
    )
    return description
