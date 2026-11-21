"""Public D15 read-only replay and tamper detection tests."""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

DAY=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(DAY))
from evidence_review import load_evidence, negative_counterexamples, validate_g09_g10_separation
from run_lab import STAGES,ordered_snapshots,offline_replay_html

class D15ReplayContract(unittest.TestCase):
    def test_public_derived_exact_git_blob(self):
        data=(DAY/"fixtures/jrcigogl_public_derived.json").read_bytes()
        sha=hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
        self.assertEqual(sha,"ae7d594b5452d96cc8802bc53bc8ad578fe99fb7")
        self.assertEqual(load_evidence()["run_id"],"jrCIgoGl")
    def test_replay_has_only_seven_ordinal_stages(self):
        stage=ordered_snapshots(load_evidence())
        self.assertEqual([x["id"] for x in stage],[
            "CLEAR","SLOW","STOP","CANCEL","ODOM_DWELL","SAFETY_TTL","PNU_AND_SCOPE"])
        self.assertEqual(stage[5]["kind"],"aggregated_maxima_no_event_timestamps")
    def test_html_has_navigation_but_no_external_dependencies(self):
        from evidence_review import review_baseline
        data=load_evidence()
        html=offline_replay_html(data,review_baseline(data),validate_g09_g10_separation(),ordered_snapshots(data))
        for s in ('id="previous"','id="next"','id="slide"','HOLD_RAW_REVIEW_AND_VISUAL_PENDING','CERTIFIED_ESTOP=false'):
            self.assertIn(s,html)
        for s in ('<script src=', '<img src="https:', 'fetch(', 'https://cdn'):
            self.assertNotIn(s,html)
    def test_five_mutation_cases_are_rejected(self):
        mutations=negative_counterexamples(load_evidence())
        self.assertEqual(len(mutations),5)
        self.assertTrue(all(x["detected"] and x["not_accepted"] for x in mutations))
        self.assertTrue(all(x["scope"].startswith("EDUCATIONAL_INJECTED") for x in mutations))
    def test_replay_cli_emits_three_report_files(self):
        with tempfile.TemporaryDirectory() as t:
            p=subprocess.run([sys.executable,str(DAY/"run_lab.py"),"--out",t],
                             capture_output=True,text=True,timeout=15)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertIn("D15_SYNTHETIC_NEGATIVE_DETECTION=5/5",p.stdout)
            self.assertIn("D15_EDUCATION_NUMERIC_GATE=EDUCATION_NUMERIC_ACCEPTED",p.stdout)
            self.assertIn("NO_NEW_ROS_GAZEBO",p.stdout)
            for f in ("d15_evidence_review.json","d15_counterexamples.json","d15_offline_replay.html"):
                self.assertTrue((Path(t)/f).stat().st_size>200)
            obj=json.loads((Path(t)/"d15_evidence_review.json").read_text())
            self.assertFalse(obj["new_gazebo_or_wsl2_executed"])
            self.assertIsNone(obj["baseline"]["first_violation_timestamp"])
            self.assertFalse(obj["pnu_separation"]["g07_owner_human_detector_attested"])
    def test_no_source_solution_or_runtime_authority_added(self):
        for f in ("evidence_review.py","run_lab.py"):
            source=(DAY/f).read_text()
            self.assertNotIn("import rclpy",source)
            self.assertNotIn("create_publisher(",source)
            self.assertNotIn("send_goal_async(",source)
        self.assertFalse((DAY/"private_rosbag.db3").exists())
        self.assertFalse((DAY/"solution").exists())
    def test_student_practical_docs_complete(self):
        for f in ("STUDENT_LAB_GUIDE_KO.md","STUDENT_EVIDENCE_WORKSHEET_KO.md",
                  "FINAL_EVALUATION_RUBRIC_KO.md"):
            text=(DAY/f).read_text(encoding="utf-8")
            self.assertIn("D15",text)
            self.assertTrue(len(text)>500)
if __name__=="__main__":
    unittest.main()
