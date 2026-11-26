"""Use official Waffle Gazebo/sensors/TF, replace only the Nav2 bringup include."""
from pathlib import Path
import sys
from ament_index_python.packages import get_package_share_directory

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from axia_launch_tools import load_upstream_launch, replace_upstream_include


def generate_launch_description():
    upstream = Path(get_package_share_directory("nav2_bringup")) / "launch" / "tb3_simulation_launch.py"
    original = load_upstream_launch(upstream)
    return replace_upstream_include(
        original, "bringup_launch.py", HERE / "axia_bringup_p0.launch.py"
    )
