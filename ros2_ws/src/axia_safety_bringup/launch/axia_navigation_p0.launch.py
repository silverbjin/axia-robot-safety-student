"""Official Nav2 Jazzy navigation nodes, except out-of-scope DockingServer.

Fail-closed if installed upstream no longer has exactly two docking node
descriptions and one docking lifecycle entry. No changes to official packages.
"""
from pathlib import Path
import sys
from ament_index_python.packages import get_package_share_directory

sys.path.insert(0, str(Path(__file__).resolve().parent))
from axia_launch_tools import load_upstream_launch


def generate_launch_description():
    upstream = Path(get_package_share_directory("nav2_bringup")) / "launch" / "navigation_launch.py"
    return load_upstream_launch(upstream, strip_docking=True)
