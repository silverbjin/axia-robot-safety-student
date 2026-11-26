"""DAY02 G07 scenario demonstrations are read-only historical evidence, not ROS re-runs."""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"scenarios/PROVEN_G07_SCENARIO_SNAPSHOT_20261122.json"
SCRIPT=ROOT/"scripts/g07_scenario_replay.py"

class ScenarioDemoContract(unittest.TestCase):
    def test_01_immutable_provenance(self):
        self.assertTrue(DATA.exists(),"RED: historic scenario snapshot missing")
        data=json.loads(DATA.read_text())
        self.assertEqual(data["student_source_sha"],"f7edb2d126502eeeed58ae014adadc7a2096d41b")
        self.assertEqual(data["native_l2_run_id"],44965035965)
        self.assertEqual(data["historic_owner"]["result"],"PASS_SCOPED")
        self.assertEqual(data["historic_owner"]["automatic_verdict"],"HOLD_RAW_REVIEW_AND_VISUAL_PENDING")
        self.assertFalse(data["claims"]["certified_estop"])

    def test_02_true_stage_measurements_not_synthetic(self):
        data=json.loads(DATA.read_text())
        stages=data["historic_owner"]["phases"]
        self.assertAlmostEqual(stages["CLEAR"]["front_m"],2.048107)
        self.assertAlmostEqual(stages["SLOW"]["cm_linear_mps"],.004810)
        self.assertEqual(stages["STOP"]["final_linear_mps"],0)
        self.assertEqual(data["historic_owner"]["goal_terminal_status"],5)
        self.assertGreaterEqual(data["historic_owner"]["odom_zero_dwell_sec"],1.)
        self.assertEqual(data["historic_owner"]["contact_count"],0)

    def test_03_rejected_0of2_first_boundary(self):
        data=json.loads(DATA.read_text())
        bad=data["historical_failed"]
        self.assertEqual(bad["moving_l2"],"0_OF_2_FAIL")
        self.assertEqual(bad["root_cause"],"UNDETERMINED")
        self.assertGreater(bad["cycle1"]["scan_callback_max_ms"],300)
        self.assertGreater(bad["cycle2"]["first_blocking_odom_ms"],300)
        self.assertFalse(bad["cycle1"]["goal_sent"])

    def test_04_cli_all_three_cases_are_no_goal(self):
        self.assertTrue(SCRIPT.exists(),"RED: read-only scenario script missing")
        for name in ("success","failed","compare"):
            with self.subTest(case=name):
                p=subprocess.run([sys.executable,str(SCRIPT),"--case",name],text=True,capture_output=True)
                self.assertEqual(p.returncode,0,p.stdout+p.stderr)
                self.assertIn("HISTORICAL_EVIDENCE_REPLAY_NO_ROS_NO_GOAL",p.stdout)
                self.assertIn("NEW_L2_L3_NOT_RUN",p.stdout)
                self.assertIn("CERTIFIED_ESTOP=false",p.stdout)

    def test_05_mutated_numeric_history_fails_closed(self):
        self.assertTrue(SCRIPT.exists(),"RED: fail-closed validator missing")
        spec=importlib.util.spec_from_file_location("g07_scenario_replay",SCRIPT)
        mod=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        good=json.loads(DATA.read_text())
        self.assertEqual(mod.validate(good),[])
        good["historic_owner"]["phases"]["STOP"]["front_m"]=999.
        self.assertTrue(mod.validate(good))

    def test_06_evidence_output_is_not_new_acceptance(self):
        self.assertTrue(SCRIPT.exists())
        with tempfile.TemporaryDirectory() as td:
            outfile=Path(td)/"demo.json"
            p=subprocess.run([sys.executable,str(SCRIPT),"--case","compare","--json-out",str(outfile)],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr)
            result=json.loads(outfile.read_text())
            self.assertEqual(result["verification_level"],"HISTORIC_EVIDENCE_REPLAY_L0_ONLY")
            self.assertFalse(result["new_ros_gazebo_run"])
            self.assertEqual(result["failed_case_status"],"0_OF_2_FAIL")
            self.assertEqual(result["accepted_owner_scope"],"PASS_SCOPED")
            self.assertFalse(result["certified_estop"])

    def test_07_private_raw_not_packaged(self):
        d=ROOT/"scenarios"
        banned=[str(x) for x in d.rglob("*") if x.is_file() and (x.suffix.lower() in (".db3",".tar",".gz",".zip",".pt",".onnx") or "solution" in x.name.lower())] if d.exists() else []
        self.assertEqual(banned,[])

if __name__=="__main__":
    unittest.main()
