"""DAY02 advanced case: exact failed L2 source/evidence contracts, no new ROS/Gazebo run."""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DAY02 = Path(__file__).resolve().parents[1]
MANIFEST = DAY02 / "FAILED_MVP_MANIFEST.json"
FIXTURE = DAY02 / "evidence/OBSERVED_L2_0OF2_SANITIZED.json"
VERIFIER = DAY02 / "scripts/verify_failed_case.py"

class FailedCaseContract(unittest.TestCase):
    def test_01_exact_failed_source_and_public_ci(self):
        self.assertTrue(MANIFEST.exists(),"RED: failed snapshot manifest missing")
        m=json.loads(MANIFEST.read_text())
        self.assertEqual(m["failed_student_source_sha"],"a04f9a7da8d54bbd9f944d05388792cb706adf28")
        self.assertEqual(m["failed_public_workflow_sha"],"8e03ac0a912ca9b81bdddda70212e52e6d804389")
        self.assertEqual(m["failed_run_id"],44914827138)
        self.assertEqual(m["actual_moving_l2_result"],"FAIL_0_OF_2")
        self.assertFalse(m["authorized_for_owner_release"])

    def test_02_real_first_boundaries_and_not_proven_cause(self):
        self.assertTrue(FIXTURE.exists(),"RED: observed first-boundary fixture missing")
        x=json.loads(FIXTURE.read_text())
        self.assertEqual(x["evidence_type"],"SANITIZED_EXCERPT_OF_HISTORIC_RUN_NOT_SIMULATION")
        self.assertEqual(x["root_cause"],"UNDETERMINED")
        self.assertGreater(x["cycle1"]["scan_callback_max_ms"],300)
        self.assertGreater(x["cycle1"]["clock_callback_max_ms"],300)
        self.assertGreater(x["cycle1"]["odom_callback_max_ms"],300)
        self.assertGreater(x["cycle2"]["first_blocking_odom_ms"],300)
        self.assertGreater(x["cycle2"]["cmd_vel_pre_guard_max_ms"],120)
        self.assertEqual(x["cycle1"]["goal_sent"],False)

    def test_03_release_readonly_verifier(self):
        self.assertTrue(VERIFIER.exists(),"RED: read-only verifier missing")
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/"audit.json"
            q=subprocess.run([sys.executable,str(VERIFIER),"--out",str(out)],text=True,capture_output=True)
            self.assertEqual(q.returncode,0,q.stdout+"\n"+q.stderr)
            d=json.loads(out.read_text())
            self.assertEqual(d["status"],"L0_FAILED_CASE_SOURCE_AND_EVIDENCE_PASS")
            self.assertEqual(d["checked_runtime_blobs"],8)
            self.assertEqual(d["simulated_runs"],0)
            self.assertEqual(d["goals_sent"],0)
            self.assertFalse(d["release_accepted"])

    def test_04_missing_fixture_fails_closed(self):
        spec=importlib.util.spec_from_file_location("failed_release_verifier",VERIFIER)
        mod=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        with tempfile.TemporaryDirectory() as td:
            d=mod.validate(root=ROOT,manifest=MANIFEST,fixture=Path(td)/"missing.json")
        self.assertEqual(d["status"],"L0_FAILED_CASE_CONTRACT_FAIL")

    def test_05_blob_tamper_fails_closed(self):
        import copy
        spec=importlib.util.spec_from_file_location("failed_release_verifier",VERIFIER)
        mod=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        m=json.loads(MANIFEST.read_text())
        x=json.loads(FIXTURE.read_text())
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            mock=copy.deepcopy(m)
            for path in mock["locked_runtime_blobs"]:
                f=root/path
                f.parent.mkdir(parents=True,exist_ok=True)
                f.write_text("unit-fixture")
                mock["locked_runtime_blobs"][path]=mod.blob_sha(f)
            tmpm=root/"manifest.json"
            tmpf=root/"fixture.json"
            tmpm.write_text(json.dumps(mock))
            tmpf.write_text(json.dumps(x))
            self.assertEqual(mod.validate(root=root,manifest=tmpm,fixture=tmpf)["status"],"L0_FAILED_CASE_SOURCE_AND_EVIDENCE_PASS")
            (root/next(iter(mock["locked_runtime_blobs"]))).write_text("tamper")
            d=mod.validate(root=root,manifest=tmpm,fixture=tmpf)
        self.assertEqual(d["status"],"L0_FAILED_CASE_CONTRACT_FAIL")
        self.assertTrue(any("BLOB_DRIFT" in e for e in d["errors"]))

    def test_06_not_a_certified_estop_or_owner_success(self):
        m=json.loads(MANIFEST.read_text())
        self.assertFalse(m["certified_estop"])
        self.assertEqual(m["owner_l3"],"NOT_RUN")
        self.assertFalse(m["moving_l2_pass"])
        self.assertEqual(m["first_failure_policy"],"FIRST_SAFETY_TRANSITION_AND_TIMING_BOUNDARY")
if __name__ == "__main__":
    unittest.main()
