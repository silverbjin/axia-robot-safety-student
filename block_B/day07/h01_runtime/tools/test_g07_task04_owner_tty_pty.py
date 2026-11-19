"""HFbmAW8N: real PTY consent boundary; never starts ROS, Gazebo, or a Goal.

RED before adding p2_g07_owner_tty_consent.sh. Tests run in disposable
PTY children, not an Owner session. No CI credentials bypass the real consent.
"""
import os
from pathlib import Path
import pty
import select
import signal
import time
import unittest

HERE = Path(__file__).resolve().parent
HELPER = HERE / "p2_g07_owner_tty_consent.sh"
RUNNER = HERE.parent / "scripts/p2_no_goal_smoke_ci.sh"

class ConsentPTY(unittest.TestCase):
    def run_pty(self, answer=None, seconds=1):
        pid, fd = pty.fork()
        if pid == 0:
            os.execv("/bin/bash", ["bash", "-c",
                      f"set -e; source '{HELPER}'; axia_owner_tty_consent {seconds}"])
        chunks=[]
        rc=None
        sent=False
        deadline=time.monotonic()+7
        try:
            while time.monotonic()<deadline:
                ready,_,_=select.select([fd],[],[],.1)
                if ready:
                    try:
                        chunk=os.read(fd,4096)
                    except OSError:
                        chunk=b""
                    if chunk:
                        chunks.append(chunk)
                        if (not sent and answer is not None
                                and b"OWNER_GOAL_CONSENT_PENDING" in b"".join(chunks)):
                            os.write(fd,answer)
                            sent=True
                done,status=os.waitpid(pid,os.WNOHANG)
                if done:
                    rc=os.waitstatus_to_exitcode(status)
                    break
            if rc is None:
                raise AssertionError("PTY_TEST_CHILD_STUCK")
            return rc, b"".join(chunks).decode(errors="replace")
        finally:
            if rc is None:
                os.kill(pid,signal.SIGKILL)
                os.waitpid(pid,0)
            os.close(fd)

    def test_exact_manual_consent_one_time(self):
        rc,log=self.run_pty(b"YES-P2-G07-GOAL\n")
        self.assertEqual(rc,0,log)
        self.assertIn("OWNER_GOAL_CONSENT_ACCEPTED",log)
        self.assertIn("OWNER_GOAL_CONSENT_PENDING",log)
        self.assertNotIn("OWNER_GOAL_CONSENT_DENIED",log)

    def test_wrong_phrase_is_denied(self):
        rc,log=self.run_pty(b"NO\n")
        self.assertEqual(rc,2,log)
        self.assertIn("OWNER_GOAL_CONSENT_DENIED",log)
        self.assertNotIn("OWNER_GOAL_CONSENT_ACCEPTED",log)

    def test_ctrl_d_is_not_misreported_as_timeout(self):
        rc,log=self.run_pty(b"\x04")
        self.assertEqual(rc,2,log)
        self.assertIn("OWNER_GOAL_CONSENT_EOF_OR_TTY_ERROR",log)
        self.assertNotIn("OWNER_GOAL_CONSENT_TIMEOUT",log)

    def test_no_user_input_is_180s_runtime_timeout_but_1s_ci(self):
        rc,log=self.run_pty(None,seconds=1)
        self.assertEqual(rc,2,log)
        self.assertIn("OWNER_GOAL_CONSENT_TIMEOUT",log)
        self.assertNotIn("OWNER_GOAL_CONSENT_ACCEPTED",log)

    def test_no_tty_is_fail_closed(self):
        import subprocess
        p=subprocess.run(["bash","-c",
                          f"source '{HELPER}'; axia_owner_tty_consent 1"],
                         stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=3)
        self.assertEqual(p.returncode,2)
        self.assertIn("OWNER_GOAL_CONSENT_TTY_UNAVAILABLE",p.stdout+p.stderr)

    def test_runtime_calls_same_helper_not_old_collapsed_error(self):
        s=RUNNER.read_text()
        self.assertIn('source tools/p2_g07_owner_tty_consent.sh',s)
        self.assertIn('axia_owner_tty_consent 180',s)
        self.assertNotIn('G07_TASK04_OWNER_TTY_APPROVAL_TIMEOUT_OR_EOF_NO_GOAL',s)
        self.assertNotIn('read -r -t 180 owner_answer',s)
        self.assertIn('AXIA_G07_TASK04_OWNER_MANUAL_CONTROLLING_TTY_GOAL_CONSENT_PASS',s)

    def test_goal_requires_fresh_post_consent_observer_data(self):
        s=(HERE/"p2_g07_ci_moving_goal.py").read_text()
        self.assertIn("def _pre_goal_safety_fresh(",s)
        self.assertIn('wait(_pre_goal_safety_fresh,5,"PRE_GOAL_SAFETY_FRESH")',s)
        self.assertIn('wait(_pre_goal_safety_fresh,3,"PRE_PUBLISH_GOAL_SAFETY_FRESH")',s)

if __name__ == "__main__":
    unittest.main()
