"""RED→GREEN: D15 Evidence Theater offline browser contract; no ROS/Gazebo."""
import json
import re
import sys
import subprocess
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
DAY=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(DAY))
from evidence_review import load_evidence, review_baseline, validate_g09_g10_separation, negative_counterexamples
from run_lab import ordered_snapshots, offline_replay_html

class HTMLNodes(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids=set()
        self.remote=[]
        self.scripts=[]
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if "id" in a:self.ids.add(a["id"])
        if tag in ("script","img","iframe","link") and (a.get("src") or a.get("href")):
            self.remote.append((tag,a.get("src",a.get("href"))))

class EvidenceTheaterContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        d=load_evidence()
        cls.html=offline_replay_html(d,review_baseline(d),
             validate_g09_g10_separation(),ordered_snapshots(d))
    def test_theater_replaces_static_old_guide(self):
        for label in ("EVIDENCE THEATER", "학생 예측", "증거 공개", "FAULT CHALLENGE",
                      "교육용 장면", "실제 주행 영상 아님"):
            with self.subTest(label=label): self.assertIn(label,self.html)
    def test_seven_steps_and_compatibility_navigation(self):
        parser=HTMLNodes();parser.feed(self.html)
        for id_ in ("previous","next","slide","predict","reveal","evidence",
                    "evidenceFields","stageLabel","distanceFill","faultCase",
                    "faultGuess","faultResult","riskBoundary"):
            with self.subTest(id=id_): self.assertIn(id_,parser.ids)
        self.assertEqual(len([x for x in ("CLEAR","SLOW","STOP","CANCEL","ODOM_DWELL","SAFETY_TTL","PNU_AND_SCOPE") if x in self.html]),7)
    def test_no_network_or_fake_time_or_ros_authority(self):
        p=HTMLNodes();p.feed(self.html)
        self.assertEqual(p.remote,[])
        for forbidden in ("fetch(", "XMLHttpRequest", "WebSocket", "setInterval(",
                          "actual_rosbag_frame", "CERTIFIED_ESTOP=true", "G11_FORMAL_ACCEPTED=true",
                          "send_goal_async", "create_publisher("):
            self.assertNotIn(forbidden,self.html)
        self.assertIn("HOLD_RAW_REVIEW_AND_VISUAL_PENDING",self.html)
        self.assertIn("CERTIFIED_ESTOP=false",self.html)
        self.assertIn("first_violation_timestamp",self.html)
        self.assertIn("NOT_PRESENT_IN_PUBLIC_AGGREGATE_DERIVED_EVIDENCE",self.html)
    def test_payload_uses_protected_data_and_five_mutations(self):
        m=re.search(r'<script type="application/json" id="evidence">([^<]+)</script>',self.html)
        self.assertIsNotNone(m)
        payload=json.loads(m.group(1))
        d=load_evidence()
        self.assertEqual(payload["data"]["goal_uuid"],d["goal_uuid"])
        self.assertEqual(payload["data"]["scan_gap_max_ms"],d["scan_gap_max_ms"])
        self.assertEqual(payload["review"]["numeric_gate"],"EDUCATION_NUMERIC_ACCEPTED")
        self.assertIsNone(payload["review"]["first_violation_timestamp"])
        self.assertFalse(payload["pnu"]["g07_owner_human_detector_attested"])
        self.assertEqual(len(payload["stages"]),7)
        self.assertEqual(len(payload["cases"]),5)
        self.assertTrue(all(x["detected"] and x["not_accepted"] for x in payload["cases"]))
    def test_cli_reports_three_original_paths_unchanged(self):
        with tempfile.TemporaryDirectory() as temp:
            p=subprocess.run([sys.executable,str(DAY/"run_lab.py"),"--out",temp],
                             capture_output=True,text=True,timeout=20)
            self.assertEqual(p.returncode,0,p.stderr)
            for f in ("d15_evidence_review.json","d15_counterexamples.json","d15_offline_replay.html"):
                self.assertTrue((Path(temp)/f).stat().st_size>100)
            rendered=(Path(temp)/"d15_offline_replay.html").read_text(encoding="utf-8")
            self.assertIn("FAULT CHALLENGE",rendered)
            self.assertIn("EVIDENCE THEATER",rendered)
            self.assertIn("D15_SYNTHETIC_NEGATIVE_DETECTION=5/5",p.stdout)
    def test_provenance_and_safe_educational_scope(self):
        self.assertIn("D13",self.html)
        self.assertIn("D14",self.html)
        self.assertIn("S04",self.html)
        self.assertIn("G07",self.html)
        self.assertIn("NO_NEW_ROS_GAZEBO",self.html)

if __name__=="__main__": unittest.main()
