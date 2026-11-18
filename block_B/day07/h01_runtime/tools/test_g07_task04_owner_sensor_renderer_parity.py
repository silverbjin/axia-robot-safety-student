"""Owner WSL2 GPU-LiDAR regression: renderer parity with proven public L2.

The field bag recorded 353/360 rays near 0.5m with a stationary robot.
The public CI Gazebo L2 ran with LIBGL_ALWAYS_SOFTWARE=1. The Owner
previously UNSET that variable even though GUI clients already explicitly
select their independent D3D12 adapter. No synthetic ROS or Goal here.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "p2_no_goal_smoke_ci.sh"


class OwnerSensorRendererParity(unittest.TestCase):
    def test_owner_gazebo_server_uses_same_software_lidar_renderer_as_ci(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertRegex(source, re.compile(
            r'elif \[\[ "\$OWNER_MOVING" == 1 \|\| "\$CI_MOVING_GUI" == 1 \]\];then'
            r'.*?export LIBGL_ALWAYS_SOFTWARE=1'
            r'.*?if \[\[ "\$OWNER_MOVING" == 1 \]\];then',
            re.DOTALL))
        self.assertNotIn('else unset LIBGL_ALWAYS_SOFTWARE', source)
        self.assertIn("AXIA_G07_OWNER_GAZEBO_LIDAR_SOFTWARE_RENDERER_SELECTED", source)

    def test_d3d12_stays_in_gui_children_not_server(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("GALLIUM_DRIVER=d3d12", source)
        self.assertIn("MESA_D3D12_DEFAULT_ADAPTER_NAME=", source)
        self.assertIn("env -u LIBGL_ALWAYS_SOFTWARE GALLIUM_DRIVER=d3d12", source)
        self.assertIn("unset GALLIUM_DRIVER MESA_D3D12_DEFAULT_ADAPTER_NAME", source)

    def test_nearfield_ring_cannot_authorize_a_goal(self):
        source = (ROOT / "tools" / "p2_g07_owner_pregoal_l2.py").read_text()
        self.assertIn("OWNER_PREGOAL_NOT_CLEAR_BEFORE_FIXTURE", source)
        self.assertIn('baseline["status"] != "CLEAR"', source)
        self.assertIn("raise RuntimeError", source)


if __name__ == "__main__":
    unittest.main()
