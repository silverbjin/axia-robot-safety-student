"""Use official Nav2 bringup+localization, replace navigation include only."""
from pathlib import Path
import sys
from ament_index_python.packages import get_package_share_directory

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from axia_launch_tools import load_upstream_launch, replace_upstream_include


def generate_launch_description():
    upstream = Path(get_package_share_directory("nav2_bringup")) / "launch" / "bringup_launch.py"
    original = load_upstream_launch(upstream)
    return replace_upstream_include(
        original, "navigation_launch.py", HERE / "axia_navigation_p0.launch.py"
    )
