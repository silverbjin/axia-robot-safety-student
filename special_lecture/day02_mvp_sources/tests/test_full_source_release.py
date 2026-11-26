"""AXIA DAY02 dual G07 source release: RED contracts before snapshot import.

Only static/L0 checks. The separate public Jazzy container CI proves colcon builds.
"""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parents[1]
MANIFEST=HERE/"DUAL_SOURCE_MANIFEST.json"
VERIFIER=HERE/"scripts/verify_dual_source.py"
BUILDER=HERE/"scripts/build_dual_mvp.sh"
PACKAGE_NAMES=("axia_fault_injector","axia_safety_bringup","axia_safety_supervisor","axia_scenario_verifier")
PINS={
    "accepted":("f7edb2d126502eeeed58ae014adadc7a2096d41b","1ad1d424358345420b8bfc67a6a7ca44d634a974"),
    "failed":("a04f9a7da8d54bbd9f944d05388792cb706adf28","0d44f39c8f5927d21411c33e7a793ca1a3f6f368"),
}

class DualMvpSourceRelease(unittest.TestCase):
    def test_01_manifest_and_historical_results(self):
        self.assertTrue(MANIFEST.is_file(),"RED: dual source manifest missing")
        d=json.loads(MANIFEST.read_text())
        self.assertEqual(d["schema"],"axia.day02.dual_g07_full_source_build.v1")
        self.assertEqual(d["accepted"]["native_moving_l2"],"2_OF_2_PASS")
        self.assertEqual(d["failed"]["native_moving_l2"],"0_OF_2_FAIL")
        self.assertEqual(d["failed"]["owner_l3"],"NOT_RUN")
        self.assertFalse(d["certified_estop"])

    def test_02_full_runtime_tree_sha_custody(self):
        for label,(commit,tree) in PINS.items():
            with self.subTest(label=label):
                runtime=HERE/label/"runtime"
                self.assertTrue((runtime/"ros2_ws/src").is_dir(),"RED: full runtime snapshot missing")
                got=subprocess.check_output(["git","-C",str(ROOT),"rev-parse",
                    "HEAD:special_lecture/day02_mvp_sources/"+label+"/runtime"],text=True).strip()
                self.assertEqual(got,tree,"whole runtime tree must match actual proven Student SHA")

    def test_03_four_actual_ament_python_packages_each(self):
        for label in PINS:
            with self.subTest(label=label):
                src=HERE/label/"runtime/ros2_ws/src"
                actual={p.name for p in src.iterdir() if (p/"package.xml").exists()}
                self.assertEqual(actual,set(PACKAGE_NAMES))
                for name in PACKAGE_NAMES:
                    root=ET.parse(src/name/"package.xml").getroot()
                    self.assertEqual(root.findtext("name"),name)
                    self.assertEqual(root.find("export").findtext("build_type"),"ament_python")
                    self.assertTrue((src/name/"setup.py").is_file())

    def test_04_failed_and_accepted_sources_are_not_mislabeled(self):
        d=json.loads(MANIFEST.read_text())
        self.assertEqual(d["accepted"]["runtime_source_sha"],PINS["accepted"][0])
        self.assertEqual(d["failed"]["runtime_source_sha"],PINS["failed"][0])
        self.assertNotEqual(d["accepted"]["runtime_tree_sha"],d["failed"]["runtime_tree_sha"])
        self.assertEqual(d["accepted"]["ros2_src_tree_sha"],"767c3d10187280303f5226a90ede205eb0059033")
        self.assertEqual(d["failed"]["ros2_src_tree_sha"],"767c3d10187280303f5226a90ede205eb0059033")

    def test_05_verifier_catches_mutated_manifest(self):
        self.assertTrue(VERIFIER.is_file(),"RED: offline verification script missing")
        spec=importlib.util.spec_from_file_location("axia_dual_source_verifier",VERIFIER)
        mod=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertEqual(mod.verify(root=ROOT,manifest_path=MANIFEST)["status"],"DUAL_G07_SOURCE_CUSTODY_L0_PASS")
        with tempfile.TemporaryDirectory() as tmp:
            broken=json.loads(MANIFEST.read_text())
            broken["failed"]["native_moving_l2"]="2_OF_2_PASS"
            f=Path(tmp)/"manifest.json"
            f.write_text(json.dumps(broken))
            self.assertEqual(mod.verify(root=ROOT,manifest_path=f)["status"],"DUAL_G07_SOURCE_CUSTODY_L0_FAIL")

    def test_06_script_is_safe_and_separate_colcon_build(self):
        self.assertTrue(BUILDER.is_file(),"RED: one-shot builder missing")
        s=BUILDER.read_text()
        self.assertIn("colcon build",s)
        self.assertIn("--build-base",s)
        self.assertIn("--install-base",s)
        self.assertIn("cp -a",s)
        self.assertIn("--verify",s)
        self.assertNotIn("ros2 launch",s)
        self.assertNotIn("gz sim",s)
        self.assertNotIn("--run-goal",s)

    def test_07_original_source_private_payload_check(self):
        forbidden=[]
        for label in PINS:
            for p in (HERE/label/"runtime").rglob("*"):
                if p.is_file() and (p.name.lower().startswith(("solution","hidden_test","private_key"))
                  or p.suffix.lower() in (".db3",".tar",".gz",".zip",".pt",".onnx")):
                    forbidden.append(str(p))
        self.assertFalse(forbidden,forbidden)

if __name__=="__main__":
    unittest.main()
