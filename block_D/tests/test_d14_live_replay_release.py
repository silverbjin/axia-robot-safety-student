"""D14 Control Room — independent offline education release contract (public L0).

RED before production. Student TODO, G07 ROS and the original run_lab are immutable.
No real controls, real odom, real Stop, actual E-Stop or Gazebo acceptance.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DAY = ROOT / "block_D" / "day14"
GEN = DAY / "live_replay.py"
TPL = DAY / "live_replay_template.html"
STUDENT = DAY / "risk_policy_student.py"

class D14LiveReplayRelease(unittest.TestCase):
    def test_generator_and_template_reuse_student_source(self):
        self.assertTrue(GEN.is_file())
        self.assertTrue(TPL.is_file())
        source = GEN.read_text(encoding="utf-8")
        self.assertIn("from run_lab import load_cases, load_g10_events, replay", source)
        self.assertNotIn("import rclpy",source)
        self.assertNotIn("send_goal_async(",source)
        self.assertNotIn("create_publisher(",source)
        self.assertNotIn("subprocess",source)
        self.assertNotIn("requests",source)

    @classmethod
    def run_demo(cls, out: Path):
        return subprocess.run([sys.executable, str(GEN), "--out", str(out)],
                              cwd=ROOT, text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=20)

    def test_full_generator_observes_student_red_without_false_green(self):
        with tempfile.TemporaryDirectory() as t:
            out = Path(t) / "demo"
            run = self.run_demo(out)
            self.assertEqual(run.returncode, 0, run.stdout)
            self.assertIn("D14_LIVE_GENERATOR_L0_PASS",run.stdout)
            self.assertIn("D14_LIVE_STUDENT_GREEN=0",run.stdout)
            self.assertIn("NO_ROS_GAZEBO_GOAL",run.stdout)
            p = out / "d14_live_manifest.json"
            h = out / "axia_d14_safety_control_room.html"
            self.assertTrue(p.is_file())
            self.assertTrue(h.is_file())
            j = json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual(j["scope"],"OFFLINE_SYNTHETIC_L0_NO_ROBOT_CONTROL")
            self.assertEqual(j["schema"],"axia.block_d.d14.control_room.v1")
            self.assertTrue(j["no_ros_gazebo_goal"])
            self.assertFalse(j["student_policy_green"])
            self.assertEqual(len(j["policy_cases"]),16)
            self.assertEqual(len(j["g10_events"]),15)
            self.assertEqual(sum(bool(i["result"]["pass"]) for i in j["policy_cases"]),2)
            self.assertEqual(j["policy_cases"][0]["id"],"N_fresh_keeps_normal")
            self.assertEqual(j["g10_events"][2]["event"],"SCAN_FAULT")
            self.assertEqual(j["g10_events"][3]["event"],"CM_LOST")
            self.assertEqual(j["g10_events"][4]["event"],"GUARD_LATCH")
            self.assertEqual(j["g10_events"][5]["event"],"FINAL_CMD")
            self.assertEqual(j["g10_events"][-1]["event"],"NO_AUTO_RESUME")
            self.assertEqual(j["g10_events"][6]["stop_t"],0.65)
            self.assertEqual(j["g10_events"][6]["dwell_sec"],1.05)
            self.assertEqual(j["intent_implementation"],"NOT_IMPLEMENTED")

    def test_observed_trace_is_exact_existing_replay_no_fabrication(self):
        # Separate interpreter is essential: D13 and D14 both call a file
        # 'run_lab.py' and can coexist in one unittest discover process.
        program = """
from run_lab import load_cases, replay
from live_replay import build_manifest, load_g10_events
cases=load_cases()
manifest=build_manifest(cases)
for original,item in zip(cases,manifest["policy_cases"]):
    assert item["id"]==original["id"]
    assert item["steps"]==original["steps"]
    assert item["expected_last_action"]==original["expected_last_action"]
    assert item["result"]==replay(original)
assert manifest["g10_events"]==load_g10_events()
print("D14_LIVE_EXACT_REPLAY_INDEPENDENT_MODULE_PASS")
"""
        proc=subprocess.run([sys.executable,"-c",program],
                            cwd=DAY, capture_output=True,text=True,timeout=20)
        self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)
        self.assertIn("D14_LIVE_EXACT_REPLAY_INDEPENDENT_MODULE_PASS",proc.stdout)

    def test_html_has_live_controls_and_hidden_result_until_vote(self):
        with tempfile.TemporaryDirectory() as t:
            proc=self.run_demo(Path(t))
            self.assertEqual(proc.returncode,0,proc.stdout)
            html=(Path(t)/"axia_d14_safety_control_room.html").read_text(encoding="utf-8")
            for token in ('id="policySelect"','id="policyPlay"','id="policyPause"',
                          'id="policyTimeline"','id="policyVote"','id="policyReveal"',
                          'id="policyHide"','id="g10Play"','id="g10Pause"',
                          'id="g10Timeline"','id="g10Next"','id="intentSelect"',
                          'id="intentVote"','id="intentReveal"',
                          'id="learnerActual"','id="fixtureExpected"',
                          'id="firstFault"','id="screenScope"','id="axia-data"'):
                self.assertIn(token,html)
            self.assertIn('style="display:none"',html)
            self.assertIn("reduced-motion",html)
            self.assertIn('role="status"',html)
            self.assertIn('aria-label=',html)
            self.assertIn("SYNTHETIC",html)
            self.assertIn("E-Stop",html)
            self.assertIn("LIMITED_REQUEST",html)
            self.assertIn("NORMAL_POLICY",html)
            self.assertIn("NO_AUTO_RESUME",html)
            self.assertNotIn("<script src=",html)
            self.assertNotIn("<link rel=\"stylesheet\" href=",html)
            self.assertNotIn("https://",html)
            self.assertNotIn("http://",html)

    def test_html_json_injection_safety_and_template_single_placeholder(self):
        program = """
from live_replay import TEMPLATE, build_manifest, render_live_html, load_cases
template=TEMPLATE.read_text(encoding="utf-8")
assert template.count("__AXIA_DATA__")==1
manifest=build_manifest(load_cases())
manifest["teaching_text"]="</script><img src=x onerror=alert(1)>"
html=render_live_html(manifest)
assert "</script><img" not in html
assert chr(92)+"u003c" in html
assert html.count('id="axia-data"')==1
print("D14_LIVE_XSS_ESCAPING_PASS")
"""
        proc=subprocess.run([sys.executable,"-c",program],
                            cwd=DAY,capture_output=True,text=True,timeout=20)
        self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)
        self.assertIn("D14_LIVE_XSS_ESCAPING_PASS",proc.stdout)

    def test_scope_documentation_and_no_instructor_solution(self):
        guide=(DAY/"STUDENT_LIVE_REPLAY_GUIDE_KO.md").read_text(encoding="utf-8")
        for token in ("git clone --branch main","live_replay.py --out",
                      "axia_d14_safety_control_room.html","d14_live_manifest.json",
                      "explorer.exe","NO_ROS_GAZEBO","NOT_IMPLEMENTED",
                      "SLOW","AVOID","STOP","P_then_N_never_autoclears",
                      "RESET_REJECTED_ACTIVE_FAULT","HTML_BROWSER_NOT_RUN",
                      "student_policy_green","run_lab.py","11", "20", "16", "15",
                      "SW Stop","E-Stop","1920×1080"):
            self.assertIn(token,guide)
        for token in ("p3_g09_risk_policy.py","p3_g10_compound.py",
                      "training/block_D/day14/solution/","FORMAL_G10_PASS"):
            self.assertNotIn(token,guide)

    def test_browser_javascript_parses_without_external_dependencies(self):
        import re
        import shutil
        node=shutil.which("node")
        if not node:
            self.skipTest("Node unavailable: browser JS syntax not verified locally")
        with tempfile.TemporaryDirectory() as t:
            out=Path(t)
            run=self.run_demo(out)
            self.assertEqual(run.returncode,0,run.stdout)
            html=(out/"axia_d14_safety_control_room.html").read_text(encoding="utf-8")
            m=re.search(r"<script>\\s*([\\s\\S]*?)</script>",html)
            self.assertIsNotNone(m,"standalone inline JS not found")
            script=out/"d14_control_room.mjs"
            script.write_text(m.group(1),encoding="utf-8")
            check=subprocess.run([node,"--check",str(script)],cwd=out,
                                 capture_output=True,text=True,timeout=20)
            self.assertEqual(check.returncode,0,check.stdout+check.stderr)
            self.assertIn("initPolicy();initIntent();initG10();",m.group(1))

if __name__=="__main__":
    unittest.main()
