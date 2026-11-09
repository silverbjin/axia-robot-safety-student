"""D03 v3 STUDENT delivery gate. Offline tests; no ROS/Gazebo needed.

The two student TODO functions intentionally remain incomplete. These tests check
distribution integrity and fail-closed launch infrastructure, NOT student GREEN.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "block_A/day03/v3/scripts/classroom.sh"
LAB = ROOT / "block_A/day03/v3"
PKG = ROOT / "ros2_ws/src"
MANIFEST = LAB / "P1_RUNTIME_SOURCE_MANIFEST.json"
REQUIRED_PKG = ("axia_safety_supervisor", "axia_fault_injector",
                "axia_scenario_verifier", "axia_d3_demo")


def git_blob_hash(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


class D03V3DeliveryTests(unittest.TestCase):
    def test_manifest_from_pinned_source(self):
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(data["source_repo"], "silverbjin/axia-robot-safety-instructor")
        self.assertEqual(data["source_sha"], "0be687ee033233fcd53be1190e0b2f9e86730fc9")
        self.assertGreaterEqual(len(data["source_blobs"]), 40)
        for item in data["source_blobs"]:
            path = ROOT / item["path"]
            self.assertTrue(path.is_file(), item["path"])
            self.assertEqual(git_blob_hash(path.read_bytes()), item["sha"], item["path"])
            self.assertTrue(item["path"].startswith("ros2_ws/src/"))

    def test_runtime_packages_and_launch_present(self):
        for name in REQUIRED_PKG:
            p = PKG / name / "package.xml"
            self.assertTrue(p.exists(), str(p))
            self.assertEqual(ET.parse(p).getroot().findtext("name"), name)
            self.assertTrue((PKG / name / "setup.py").is_file())
        self.assertTrue((PKG / "axia_safety_bringup/launch/axia_tb3_p1.launch.py").is_file())
        self.assertTrue((PKG / "axia_d3_demo/models/pedestrian_proxy.sdf").is_file())

    def test_no_teacher_solutions_or_hidden_tests(self):
        banned = ("instructor/solutions", "hidden_tests", "age-key", "secret_token")
        for path in (LAB, PKG):
            for f in path.rglob("*"):
                if not f.is_file() or f.suffix not in {".sh",".py",".md",".json",".xml",".sdf"}:
                    continue
                s = f.read_text(encoding="utf-8")
                # Provenance doc can mention repository namespace but never paths
                for x in banned:
                    self.assertNotIn(x, s.lower(), str(f))
        self.assertFalse((ROOT/"training/d03/instructor").exists())

    def test_launcher_parses_and_has_no_goal_authority(self):
        self.assertTrue(SCRIPT.is_file())
        subprocess.run(["bash", "-n", str(SCRIPT)], check=True)
        content = SCRIPT.read_text(encoding="utf-8")
        for phrase in ("reset --hard", "git clean -fd", "rm -rf",
                       "ros2 action send_goal", "ros2 topic pub /cmd_vel",
                       "ros2 service call /axia/safety/start"):
            self.assertNotIn(phrase, content)
        self.assertIn("YES-D3-SIM", content)
        self.assertIn("YES-D3-FAULT", content)
        self.assertIn("AXIA_D3_V3_SIM_ONLY", content)

    def _run(self, home: Path, *args):
        env = dict(os.environ, HOME=str(home))
        env.pop("AXIA_D3_V3_SESSION", None)
        return subprocess.run(["bash", str(SCRIPT), *args],
                              text=True, capture_output=True, timeout=12, env=env)

    def test_help_without_ros(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._run(Path(tmp), "--help")
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn("session", p.stdout)
            self.assertIn("preview", p.stdout)
            self.assertIn("live", p.stdout)

    def test_session_no_ros_and_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp)
            first=self._run(home,"session")
            self.assertEqual(first.returncode,0,first.stderr+first.stdout)
            env=home/"axia_d3_v3_classroom"/"session.env"
            self.assertTrue(env.is_file())
            self.assertEqual(env.stat().st_mode & 0o777,0o600)
            before=env.read_bytes()
            again=self._run(home,"session")
            self.assertEqual(again.returncode,0,again.stderr+again.stdout)
            self.assertEqual(env.read_bytes(),before)
            self.assertIn("ROS_DOMAIN_ID", env.read_text())
            self.assertIn("GZ_PARTITION", env.read_text())

    def test_rejects_symlinked_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp)
            folder=home/"axia_d3_v3_classroom"
            folder.mkdir()
            target=home/"KEEP"
            target.write_text("DO_NOT_CHANGE")
            (folder/"session.env").symlink_to(target)
            p=self._run(home,"session")
            self.assertNotEqual(p.returncode,0)
            self.assertEqual(target.read_text(),"DO_NOT_CHANGE")

    def test_route_validated_offline_and_saved(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp)
            self.assertEqual(self._run(home,"session").returncode,0)
            good=self._run(home,"route","demo_world","1","2","2","2")
            self.assertEqual(good.returncode,0,good.stderr+good.stdout)
            self.assertIn("[ROUTE_SAVED]",good.stdout)
            self.assertTrue((home/"axia_d3_v3_classroom"/"route.env").exists())
            bad=self._run(home,"route","../../wrong","0","0","1","0")
            self.assertNotEqual(bad.returncode,0)
            bad2=self._run(home,"route","demo_world","0","0","12","12")
            self.assertNotEqual(bad2.returncode,0)

    def test_new_evidence_keeps_domain_and_partition(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp)
            self.assertEqual(self._run(home,"session").returncode,0)
            env=home/"axia_d3_v3_classroom"/"session.env"
            old=env.read_text()
            p=self._run(home,"new-evidence")
            self.assertEqual(p.returncode,0,p.stderr)
            now=env.read_text()
            for name in ("ROS_DOMAIN_ID","GZ_PARTITION"):
                oldline=next(s for s in old.splitlines() if s.startswith("export "+name+"="))
                self.assertIn(oldline,now)
            self.assertNotEqual(old,now)

    def test_live_without_session_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=self._run(Path(tmp),"live")
            self.assertNotEqual(p.returncode,0)
            self.assertIn("[BLOCKED]",p.stderr+p.stdout)

    def test_student_bridge_is_readonly(self):
        bridge=(ROOT/"block_A/day03/ros_diagnostics_bridge.py").read_text()
        self.assertIn('"/diagnostics"',bridge)
        self.assertIn('"/axia/safety/state"',bridge)
        self.assertNotIn("ros2 service call",bridge)

    def test_student_todo_remains_unimplemented(self):
        for name in ("p1_adapter_todo.py","todo_safety.py"):
            text=(ROOT/"block_A/day03"/name).read_text()
            self.assertIn("TODO_NOT_IMPLEMENTED",text)

    def test_guides_and_ci_present(self):
        for path in ("README.md", "block_A/day03/v3/README_D03_V3_LAB_KO.md",
                     "block_A/day03/v3/DESIGN_D03_V3_KO.md",
                     "block_A/day03/v3/REPORT_D03_V3_KO.md",
                     ".github/workflows/d03-v3-public-ci.yml"):
            self.assertTrue((ROOT/path).is_file(), path)


if __name__ == "__main__":
    unittest.main()
