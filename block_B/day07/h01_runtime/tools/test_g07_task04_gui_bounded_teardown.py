"""Exact first regression for G07 #44679704946 rc124 after Nav/Loc ACK.

Checks only cleanup of the two already-owned GUI PGIDs. Does not relax
Nav2 ACK, CM/Guard, real Goal, or simulated E-stop requirements.
"""
from pathlib import Path
import re
import subprocess
import unittest

SOURCE=Path(__file__).resolve().parents[1]/"scripts/p2_no_goal_smoke_ci.sh"


def helper():
    s=SOURCE.read_text()
    match=re.search(r"(?ms)^stop_owned_gui_group\(\) \{\n.*?^\}\n",s)
    if not match:
        raise AssertionError("OWNED_GUI_BOUNDED_TEARDOWN_NOT_IMPLEMENTED")
    return match.group(0)


class OwnedGUIBoundedExit(unittest.TestCase):
    def test_after_nav2_ack_gui_wait_has_a_bounded_fallback(self):
        s=SOURCE.read_text()
        # Waiting AFTER the bounded status transition is legal; the old
        # unbounded wait in cleanup's own GUI loop is not.
        cleanup=s.split("cleanup() {",1)[1].split("trap cleanup EXIT",1)[0]
        self.assertNotIn('wait "$gui_pid" 2>/dev/null || true',cleanup)
        self.assertIn('stop_owned_gui_group "$gui_pid"',s)
        self.assertIn('kill -INT -- "-$gui_pid"',helper())
        self.assertIn('kill -TERM -- "-$gui_pid"',helper())
        self.assertIn('kill -KILL -- "-$gui_pid"',helper())
        self.assertNotIn("pkill",helper())

    def test_sigint_ignoring_owned_gui_process_cannot_hang_runner(self):
        code=helper()+"""
set -Eeuo pipefail
setsid bash -c 'trap "" INT; while :; do sleep 0.2; done' &
gui_pid=$!
trap 'kill -KILL -- "-$gui_pid" 2>/dev/null || true' EXIT
sleep 0.15
stop_owned_gui_group "$gui_pid"
echo 'G07_BOUNDED_OWNED_GUI_TERMINATION_TEST_PASS'
"""
        result=subprocess.run(["bash","-c",code],capture_output=True,text=True,timeout=12)
        self.assertEqual(result.returncode,0,result.stdout+"\n"+result.stderr)
        self.assertIn("G07_BOUNDED_OWNED_GUI_TERMINATION_TEST_PASS",result.stdout)


if __name__=="__main__":
    unittest.main()
