"""Task04 Owner moving-Goal minimal regressions. ROS-free; no authorization spoof."""
import ast
import contextlib
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import p2_g07_ci_moving_goal as moving
from p2_g07_shared_admission import admit_owner

SHA = "a" * 40
BASE_ENV = {
    "AXIA_G07_OWNER_COMMON_RUNNER_AUTHORIZED": "1",
    "AXIA_P2_OWNER_PINNED_SHA": SHA,
    "ROS_DISTRO": "jazzy", "AXIA_P0_SIM_ONLY": "1",
    "GZ_PARTITION": "axia_p2_test_1", "ROS_DOMAIN_ID": "86",
}

def valid_inspect(launch_pid, expected_sha, actual_sha, env):
    return {"status": "P2_PRE_GOAL_PID_CANDIDATE",
            "pid_by_role": {"p2_supervisor_node": 101,
                            "collision_monitor": 102,
                            "p2_base_guard_node": 103}}

class Task04OwnerMovingEntry(unittest.TestCase):
    def test_owner_pid_cli_reaches_existing_runner_no_ros(self):
        args = ["p2_g07_ci_moving_goal.py", "--output", "/tmp/unused",
                "--startup", "/tmp/startup", "--pregoal", "/tmp/pregoal",
                "--source-sha", SHA, "--owner-launch-pid", "100"]
        with patch.object(sys, "argv", args), patch.object(moving, "run", return_value=0) as invoke:
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(moving.main(), 0)
            self.assertEqual(invoke.call_args.args[0].owner_launch_pid, 100)

    def test_owner_uses_same_exact_goal_cancel_after_stop(self):
        tree = ast.parse(Path(moving.__file__).read_text())
        run = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run")
        checks = []
        for n in ast.walk(run):
            if isinstance(n, ast.If):
                child = ast.walk(ast.Module(body=n.body, type_ignores=[]))
                calls = {getattr(c.func, "id", None) for c in child if isinstance(c, ast.Call)}
                if "_task03_exact_goal_terminal" in calls:
                    checks.append(ast.unparse(n.test))
        # Normal post-STOP and guarded exceptional cleanup are mutually
        # exclusive: one physical Goal, never two CancelGoal requests.
        call_count=sum(1 for n in ast.walk(run)
                       if isinstance(n,ast.Call)
                       and getattr(n.func,"id",None)=="_task03_exact_goal_terminal")
        self.assertEqual(call_count,2)
        self.assertTrue(any("owner_mode" in cond
                            and "AXIA_G07_TASK03_FORMAL_CI" in cond
                            for cond in checks))
        src=Path(moving.__file__).read_text()
        self.assertIn('report["goal_cancel_attempted"]=True',src)
        self.assertIn('report.get("goal_cancel_attempted") is not True',src)
        self.assertIn('guard_latched is False',src)

    def test_owner_motion_window_marker_does_not_require_ci_credentials(self):
        src = Path(moving.__file__).read_text()
        self.assertIn('if owner_mode or os.environ.get("AXIA_G07_TASK03_FORMAL_CI")=="1":', src)
        self.assertIn('obs._write("task03_motion_window_end",at=t1)', src)

    def test_owner_pid_tty_sha_ci_authority_all_fail_closed(self):
        ok = admit_owner(expected_sha=SHA, actual_sha=SHA, launch_pid=100,
                         env=BASE_ENV, has_tty=True, inspect=valid_inspect)
        self.assertEqual(ok["mode"], "owner")
        self.assertFalse(ok["goal_sent"])
        bad_cases = [
            dict(has_tty=False),
            dict(actual_sha="b"*40),
            dict(launch_pid=101),
            dict(env={**BASE_ENV, "GITHUB_ACTIONS": "true"}),
            dict(env={**BASE_ENV, "AXIA_G07_CI_SIM_GOAL_ALLOWED": "1"}),
            dict(env={**BASE_ENV, "AXIA_P2_OWNER_PINNED_SHA": "b"*40}),
            dict(inspect=lambda *_: {"status": "P2_PRE_GOAL_PID_BLOCKED"}),
        ]
        for bad in bad_cases:
            args=dict(expected_sha=SHA, actual_sha=SHA, launch_pid=100,
                      env=BASE_ENV, has_tty=True, inspect=valid_inspect)
            args.update(bad)
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                admit_owner(**args)

if __name__ == "__main__":
    unittest.main()
