"""Task04 native shutdown ordering: retain Gazebo/RViz GUI until Nav2 ACK.

#44258495534 completed real Goal, STOP, odom, CANCELED and navigation ACK,
but failed Localization manage_nodes response. Original cleanup killed GUI
before orderly lifecycle shutdown. Change only resource teardown order.
"""
from pathlib import Path
import unittest

SHELL=Path(__file__).resolve().parents[1]/"scripts/p2_no_goal_smoke_ci.sh"

class Task04GuiTeardownAfterNav2(unittest.TestCase):
    def test_moving_gui_clients_outlive_ordered_nav2_shutdown(self):
        s=SHELL.read_text().split("cleanup() {",1)[1].split("trap cleanup EXIT",1)[0]
        nav=s.index("python3 tools/p2_g07_ordered_shutdown.py")
        local_audit=s.index("python3 tools/p2_g07_owner_shutdown_audit.py")
        gui_close=s.index('kill -INT -- "-$gui_pid"')
        self.assertLess(nav,gui_close)
        self.assertLess(local_audit,gui_close)

    def test_gui_only_stops_own_process_groups(self):
        s=SHELL.read_text()
        self.assertIn('kill -INT -- "-$gui_pid"',s)
        self.assertNotIn("pkill -f",s)
        self.assertIn("MOVING_RVIZ_PID",s)
        self.assertIn("MOVING_GAZEBO_GUI_PID",s)

if __name__=="__main__":
    unittest.main()
