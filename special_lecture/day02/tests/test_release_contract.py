"""DAY02 public L0 release contract; no ROS or Gazebo launched."""
import importlib.util, json, subprocess, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
DAY02=Path(__file__).resolve().parents[1]
SCRIPT=DAY02/"scripts/verify_release.py"
MANIFEST=DAY02/"COURSE_RELEASE_MANIFEST.json"
class Day02Release(unittest.TestCase):
    def test_01_manifest_pins_and_scope(self):
        self.assertTrue(MANIFEST.is_file(),"DAY02_MANIFEST_MISSING_RED")
        data=json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(data["source_commit_sha"],"f7edb2d126502eeeed58ae014adadc7a2096d41b")
        self.assertEqual(data["proven_ci"]["run_id"],44965035965)
        self.assertEqual(data["owner_raw_review"]["original_auto_verdict"],"HOLD_RAW_REVIEW_AND_VISUAL_PENDING")
        self.assertIs(data["scope_limits"]["certified_estop"],False)
    def test_02_existing_mvp_runtime_blob_hashes(self):
        self.assertTrue(SCRIPT.is_file(),"DAY02_VERIFIER_MISSING_RED")
        with tempfile.TemporaryDirectory(prefix="axia_d02_") as td:
            output=Path(td)/"result.json"
            p=subprocess.run([sys.executable,str(SCRIPT),"--out",str(output)],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stdout+"\n"+p.stderr)
            result=json.loads(output.read_text())
            self.assertEqual(result["status"],"L0_RELEASE_CONTRACT_PASS")
            self.assertEqual(result["checked_runtime_blobs"],8)
            self.assertFalse(result["ros_gazebo_run"])
            self.assertFalse(result["goal_sent"])
    def test_03_missing_manifest_fails_closed(self):
        spec=importlib.util.spec_from_file_location("axia_day02_verify",SCRIPT)
        mod=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        with tempfile.TemporaryDirectory() as td:
            res=mod.validate(root=ROOT,manifest_path=Path(td)/"missing.json")
            self.assertEqual(res["status"],"FAIL_L0_RELEASE_MANIFEST")
    def test_04_mutated_source_blob_fails_closed(self):
        import copy
        spec=importlib.util.spec_from_file_location("axia_day02_verify",SCRIPT)
        mod=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        data=json.loads(MANIFEST.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            clone=copy.deepcopy(data)
            expected={}
            for rel in data["locked_runtime_blobs"]:
                f=root/rel
                f.parent.mkdir(parents=True,exist_ok=True)
                f.write_text("fixture "+rel)
                expected[rel]=mod.blob_sha(f)
            clone["locked_runtime_blobs"]=expected
            m=root/"manifest.json"
            m.write_text(json.dumps(clone))
            self.assertEqual(mod.validate(root=root,manifest_path=m)["status"],"L0_RELEASE_CONTRACT_PASS")
            (root/next(iter(expected))).write_text("TAMPERED")
            res=mod.validate(root=root,manifest_path=m)
            self.assertEqual(res["status"],"FAIL_L0_RELEASE_CONTRACT")
            self.assertTrue(any("RUNTIME_BLOB_DRIFT:" in x for x in res["errors"]))
    def test_05_no_private_payloads(self):
        leaked=[str(p.relative_to(DAY02)) for p in DAY02.rglob("*") if p.is_file()
                and (p.name.lower().startswith(("solution","hidden_test"))
                or p.suffix.lower() in (".db3",".onnx",".pt"))]
        self.assertFalse(leaked,leaked)
if __name__=="__main__": unittest.main()
