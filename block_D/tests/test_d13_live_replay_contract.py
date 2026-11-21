"""D13 Live Replay: off-line public contract. Keeps 10 student TODO tests unchanged."""
import importlib.util
import json
import re
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
D13 = ROOT / "block_D" / "day13"
APP = D13 / "live_replay.py"
TEMPLATE = D13 / "live_replay_template.html"

class D13LiveReplayContract(unittest.TestCase):
    def test_generator_and_template_exist_without_ros_dependency(self):
        self.assertTrue(APP.is_file())
        self.assertTrue(TEMPLATE.is_file())
        source = APP.read_text(encoding="utf-8")
        self.assertIn("load_cases", source)
        self.assertIn("evaluate_case", source)
        self.assertNotIn("rclpy", source)
        self.assertNotIn("p3_oracles", source)

    def test_full_offline_output_and_8_case_manifest(self):
        with tempfile.TemporaryDirectory(prefix="d13-live-") as td:
            res = subprocess.run(
                [sys.executable, str(APP), "--out", td], cwd=ROOT,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=20, check=False)
            self.assertEqual(res.returncode, 0, res.stdout)
            self.assertIn("D13_LIVE_REPLAY_L0_PASS", res.stdout)
            html = (Path(td) / "axia_d13_live_replay.html").read_text(encoding="utf-8")
            m = json.loads((Path(td) / "live_replay_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(len(m["cases"]), 8)
            self.assertEqual(m["geometry"]["sample_count"], 16)
            self.assertEqual(m["geometry"]["t_first"], 10.1)
            self.assertEqual(m["geometry"]["t_last"], 13.1)
            self.assertEqual(m["scope"], "OFFLINE_SYNTHETIC_L0_NO_ROBOT_CONTROL")
            self.assertEqual(m["expected_distribution"], {"P": 1, "N": 1, "U": 6})
            self.assertIn("time_steps", html)
            for token in ('id="play"', 'id="timeline"', 'id="reset"',
                          'id="reveal"', 'id="faultSelect"', 'id="faultExplanation"',
                          'id="predictA"', 'id="predictB"', "Math.hypot",
                          "OFFLINE · 합성 데이터", "NO_ROS_GAZEBO_GOAL"):
                self.assertIn(token, html)
            for bad in ('<script src=', 'https://', "fetch(",
                        "WebSocket(", "rclpy", "p3_oracles"):
                self.assertNotIn(bad, html)
            # The SVG namespace is an identifier, not an outbound HTTP call.
            self.assertNotIn("http://", html.replace(
                "http://www.w3.org/2000/svg", ""))

    def test_embedded_javascript_syntax_with_node_when_available(self):
        """Parser-level browser script regression; no external dependencies downloaded."""
        node = shutil.which("node")
        if not node:
            self.skipTest("Node not available: browser JS parser NOT_RUN")
        sys.path.insert(0, str(D13))
        from live_replay import build_manifest, render_live_html
        from run_lab import load_cases
        html = render_live_html(build_manifest(load_cases()))
        blocks = re.findall(r"<script[^>]*>(.*?)</script>", html, re.S)
        self.assertEqual(len(blocks), 2)
        with tempfile.TemporaryDirectory(prefix="d13-js-") as td:
            script = Path(td) / "d13_viewer.js"
            script.write_text(blocks[1], encoding="utf-8")
            res = subprocess.run([node, "--check", str(script)],
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 text=True, timeout=15, check=False)
            self.assertEqual(res.returncode, 0, res.stdout)

    def test_first_invalid_is_fixture_evidence_not_learner_success(self):
        sys.path.insert(0, str(D13))
        from live_replay import fixture_first_issue, build_manifest
        from run_lab import load_cases
        cases = {c["id"]:c for c in load_cases()}
        expected = {
            "U_stale_track":"0.6",
            "U_future_stamp":"10.2",
            "U_low_confidence":"0.05",
            "U_frame_mismatch":"odom",
            "U_missing_last_sample":"15",
            "U_time_jump":"11.54",
        }
        for case, detail in expected.items():
            with self.subTest(case=case):
                item = fixture_first_issue(cases[case])
                self.assertEqual(item["status"], "FIXTURE_INPUT_INVALID")
                self.assertIn(detail, item["detail"])
                self.assertNotIn("VERIFIED_BY_STUDENT", str(item))
        summary = build_manifest(load_cases())
        self.assertEqual(summary["learner_verdicts"]["P_same_time_overlap"], "U")
        self.assertEqual(summary["learner_verdicts"]["N_same_route_different_time"], "U")
        self.assertFalse(summary["learner_algorithm_green"])

if __name__ == "__main__":
    unittest.main()
