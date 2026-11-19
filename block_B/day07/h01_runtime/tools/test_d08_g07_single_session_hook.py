"""RED→GREEN: only the existing G07 owner may launch D08's optical overlay.

This is source-contract L0, NOT actual Gazebo/ROS safety acceptance.
"""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
SHELL=(ROOT/"scripts/p2_no_goal_smoke_ci.sh").read_text()


class TestD08SingleSessionHook(unittest.TestCase):
    def test_guarded_opt_in_only_existing_moving_authority(self):
        self.assertIn('AXIA_D08_G07_SINGLE_SESSION',SHELL)
        self.assertIn('D08_G07_SINGLE_SESSION_SCOPE_DENIED',SHELL)
        self.assertIn('AXIA_P2_G07_PHYSICAL_PREFLIGHT',SHELL)
        self.assertIn('AXIA_P0_SIM_ONLY',SHELL)
        self.assertIn('AXIA_G07_CI_SIM_GOAL_ALLOWED',SHELL)
        self.assertIn('OWNER_MOVING',SHELL)

    def test_one_gazebo_original_launch_and_single_world_robot_argument(self):
        self.assertIn('AXIA_D08_G07_ADAPTER_SCRIPT',SHELL)
        self.assertIn('AXIA_D08_G07_PERSON_MESH',SHELL)
        self.assertIn('D08_G07_WORLD_ROBOT_LAUNCH_ARGS_NOT_UNIQUE',SHELL)
        self.assertIn('D08_G07_SINGLE_WORLD_SOURCE_OVERLAY_READY_NO_GOAL',SHELL)
        self.assertEqual(SHELL.count('setsid ros2 launch "$LAUNCH" "${LAUNCH_ARGS[@]}"'),1)

    def test_d08_hook_precedes_ros_launch_and_manual_goal_consent(self):
        idx=SHELL.index('D08_G07_SINGLE_WORLD_SOURCE_OVERLAY_READY_NO_GOAL')
        self.assertLess(idx,SHELL.index('setsid ros2 launch "$LAUNCH"'))
        self.assertLess(idx,SHELL.index('axia_owner_tty_consent 180'))
        self.assertIn('AXIA_D08_G07_EXPECTED_STUDENT_SHA',SHELL)
        self.assertIn('AXIA_D08_G07_EXPECTED_PUBLIC_SHA',SHELL)


if __name__=="__main__":
    unittest.main()
