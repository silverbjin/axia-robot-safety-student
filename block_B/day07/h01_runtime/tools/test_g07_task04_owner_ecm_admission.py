"""Actual original world overlay boundary: Owner WSL2 must not inherit CI-only ECM block."""
import os
import pathlib
import pty
import subprocess
import sys
import tempfile
import unittest

TOOLS = pathlib.Path(__file__).resolve().parent
ROOT = TOOLS.parent
CLI = TOOLS / "p2_l3_world_overlay.py"
WORLD = """<sdf version="1.10"><world name="default">
  <plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/>
</world></sdf>"""

class G07OwnerECMAdmission(unittest.TestCase):
    def run_overlay(self, *, owner=True, use_tty=True, exact=True, github=False):
        with tempfile.TemporaryDirectory() as td:
            base=pathlib.Path(td)
            (base/"world.sdf.xacro").write_text(WORLD)
            sha=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
            env=os.environ.copy()
            env.update({
                "AXIA_G07_TASK03_ECM_WITNESS":"1",
                "AXIA_G07_TASK04_OWNER_MOVING_L3":"1" if owner else "0",
                "AXIA_G07_CI_SIM_GOAL_ALLOWED":"0",
                "AXIA_P0_SIM_ONLY":"1",
                "AXIA_P2_G07_PHYSICAL_PREFLIGHT":"1",
                "AXIA_G07_OWNER_STARTUP_PARITY":"1",
                "AXIA_G07_CI_OWNER_BAG_PARITY":"1",
                "AXIA_G07_TASK04_EXPECTED_STUDENT_SHA":sha if exact else "0"*40,
            })
            env["GITHUB_ACTIONS"]="true" if github else "false"
            args=[sys.executable,str(CLI),"--source",str(base/"world.sdf.xacro"),
                  "--output",str(base/"world-out.sdf"),"--manifest",str(base/"manifest.json")]
            master=slave=None
            try:
                if use_tty:
                    master,slave=pty.openpty()
                result=subprocess.run(args,env=env,stdin=slave if use_tty else subprocess.DEVNULL,
                                      capture_output=True,text=True,timeout=12)
            finally:
                if master is not None: os.close(master)
                if slave is not None: os.close(slave)
            out=(base/"world-out.sdf").read_text() if (base/"world-out.sdf").exists() else ""
            return result.returncode,result.stdout,result.stderr,out

    def test_reproduce_old_ci_only_ecm_rejection_on_owner(self):
        # With previous 1129cd88 source this was RED: expected Owner to work.
        rc,stdout,stderr,world=self.run_overlay()
        self.assertEqual(rc,0,(stdout,stderr))
        self.assertIn("gz::sim::systems::Contact",world)
        self.assertEqual(world.count('axia::G07S02Witness'),1)

    def test_no_tty_does_not_admit_owner_witness(self):
        rc,stdout,stderr,world=self.run_overlay(use_tty=False)
        self.assertEqual(rc,2)
        self.assertIn("P2_G07_WORLD_OVERLAY_BLOCKED:ValueError",stdout)
        self.assertEqual(world,"")

    def test_bad_exact_source_rejected(self):
        rc,stdout,stderr,world=self.run_overlay(exact=False)
        self.assertEqual(rc,2)
        self.assertIn("ValueError",stdout)

    def test_github_actions_owner_never_admitted(self):
        rc,stdout,stderr,world=self.run_overlay(github=True)
        self.assertEqual(rc,2)
        self.assertIn("ValueError",stdout)

    def test_regular_no_goal_overlay_still_works(self):
        # original default route (native witness off) is unmodified
        with tempfile.TemporaryDirectory() as td:
            p=pathlib.Path(td)
            (p/"world.sdf.xacro").write_text(WORLD)
            env={**os.environ, "AXIA_G07_TASK03_ECM_WITNESS":"0"}
            r=subprocess.run([sys.executable,str(CLI),"--source",str(p/"world.sdf.xacro"),
                              "--output",str(p/"out.sdf"),"--manifest",str(p/"out.json")],
                             env=env,capture_output=True,text=True,timeout=10)
            self.assertEqual(r.returncode,0,(r.stdout,r.stderr))
            self.assertNotIn("axia::G07S02Witness",(p/"out.sdf").read_text())

if __name__=="__main__":
    unittest.main()
