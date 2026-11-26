"""Official Nav2 bringup with P2 Navigation only."""
from pathlib import Path
import sys
from ament_index_python.packages import get_package_share_directory
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from axia_launch_tools import load_upstream_launch
from axia_p2_include import replace_include


def generate_launch_description():
    source = Path(get_package_share_directory('nav2_bringup'))/'launch'/'bringup_launch.py'
    return replace_include(load_upstream_launch(source), 'navigation_launch.py',
                           HERE/'axia_navigation_p2.launch.py')
