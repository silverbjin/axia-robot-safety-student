"""Task04 localization timeout #44261927169: bounded diagnostics and GUI CPU competition.

Safety graph/TTL and Lifecycle ACK requirements remain unchanged.
"""
import inspect
import unittest
from pathlib import Path
import p2_g07_ordered_shutdown as shutdown

SHELL=Path(__file__).resolve().parents[1]/"scripts/p2_no_goal_smoke_ci.sh"

class NativeLocalizationShutdownEvidence(unittest.TestCase):
    def test_native_response_elapsed_and_request_sent_preserved(self):
        source=inspect.getsource(shutdown.run)
        self.assertIn('stages[key+"_response_elapsed_sec"]',source)
        self.assertIn('stages[key+"_service_request_sent"]',source)
        self.assertIn('stages[key+"_service_status"]',source)
        self.assertIn('ack["status"]!="ACK"',source)
        self.assertIn('deadline = monotonic() + limit',source)

    def test_gui_clients_lower_priority_than_safety_processes(self):
        text=SHELL.read_text()
        self.assertIn('setsid nice -n 10 gz sim -g',text)
        self.assertIn('setsid nice -n 10 rviz2 -d',text)
        self.assertIn('ros2 launch "$LAUNCH"',text)
        self.assertNotIn('pkill -f',text)

if __name__=="__main__":
    unittest.main()
