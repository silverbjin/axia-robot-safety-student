"""Task04 WSLg D3D12 is strictly GUI-child-only, never Gazebo sensor server.

Existing successful NO_GOAL GPU path isolated GALLIUM_DRIVER=d3d12 to
'gz sim -g' and rviz2 processes. The published Owner Moving wrapper
exported D3D12 globally; this regression prevents inherited D3D12
from changing the server/CM/scan scheduling safety boundary.
"""
from pathlib import Path
import unittest

SH=Path(__file__).resolve().parents[1]/"scripts/p2_no_goal_smoke_ci.sh"

class WSLgOwnerChildOnlyRenderer(unittest.TestCase):
    def test_owner_gui_children_get_verified_d3d12_only(self):
        source=SH.read_text(encoding="utf-8")
        self.assertIn("AXIA_G07_TASK04_GUI_D3D12_ADAPTER",source)
        self.assertIn("MESA_D3D12_DEFAULT_ADAPTER_NAME=",source)
        self.assertIn("GALLIUM_DRIVER=d3d12",source)
        self.assertIn("env -u LIBGL_ALWAYS_SOFTWARE",source)
        self.assertIn("setsid nice -n 10",source)

    def test_existing_ci_gui_path_remains_software(self):
        source=SH.read_text(encoding="utf-8")
        self.assertIn('setsid nice -n 10 gz sim -g',source)
        self.assertIn('setsid nice -n 10 rviz2 -d',source)
        self.assertIn('if [[ "$OWNER_MOVING" == 1 ]]',source)
        self.assertNotIn("pkill -f",source)

if __name__=="__main__":
    unittest.main()
