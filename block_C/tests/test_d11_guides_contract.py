"""AXIA D11 public docs/TOY contracts: NO private instructor import or model execution."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DAY = ROOT / "day11"
DEMO = DAY / "STUDENT_DEMO_GUIDE_KO.md"
LAB = DAY / "STUDENT_LAB_GUIDE_KO.md"
READ = DAY / "README_KO.md"
TOY = DAY / "mse_toy_practice.py"
TODO = DAY / "student_ae_todo.py"

class D11GuidesContract(unittest.TestCase):
    def test_all_docs_exist_and_learning_objectives(self):
        for p in (DEMO, LAB, READ):
            self.assertTrue(p.is_file(), p)
            t=p.read_text(encoding="utf-8")
            self.assertIn("AutoEncoder 기반 정상상태 재구성 원리 이해",t)
            self.assertIn("재구성 오차 기반 이상상태 판정 실습",t)
            self.assertIn("SYNTHETIC_COURSE_FIXTURE",t)
            self.assertIn("INSUFFICIENT_DATA",t)
            self.assertIn("인증",t)
    def test_student_guide_clones_and_runs_without_teacher_code(self):
        for p in (DEMO, LAB):
            t=p.read_text(encoding="utf-8")
            for s in ("git clone https://github.com/silverbjin/axia-robot-safety-student.git",
                      "block_C/scripts/block_c_once.sh --doctor",
                      "block_C/fixtures/generator.py --check",
                      "block_C/day11/mse_toy_practice.py",
                      "EXPECTED_RED", "120", "46", "240", "80", "100"):
                self.assertIn(s,t,(p,s))
            self.assertIn("4599",t.replace(",",""),p)
            for forbidden in ("from autoencoder_pipeline import", "torch.save(", "create_publisher(", "send_goal_async("):
                self.assertNotIn(forbidden,t)
    def test_todo_remains_intentionally_unimplemented(self):
        s=TODO.read_text(encoding="utf-8")
        self.assertIn("raise NotImplementedError('D11 TODO not implemented')",s)
        self.assertNotIn("nn.Sequential(",s)
        self.assertFalse((DAY/"ae_checkpoint.pt").exists())
        self.assertFalse((DAY/"D11_SOLUTION_GUIDE_KO.md").exists())
    def test_toy_stdout_and_quality(self):
        q=subprocess.run([sys.executable,str(TOY)],capture_output=True,text=True,check=True,timeout=15)
        self.assertIn("case=normal mse=0.010000 threshold=0.500000 prediction=NORMAL",q.stdout)
        self.assertIn("case=anomaly mse=1.000000 threshold=0.500000 prediction=WARNING",q.stdout)
        self.assertIn("case=missing mse=UNSCORED threshold=0.500000 prediction=INSUFFICIENT_DATA",q.stdout)
        self.assertIn("model_training=false robot_control=false",q.stdout)
        print("D11_PUBLIC_TOY_MSE_PASS")
    def test_public_fixture_manifest_count(self):
        m=json.loads((ROOT/"fixtures/scenario_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(sum(m["expected_rows"].values()),4599)
        self.assertEqual(sum(m["trace_counts"].values()),46)
    def test_readme_links_point_to_real_files(self):
        t=READ.read_text(encoding="utf-8")
        for p in ("STUDENT_DEMO_GUIDE_KO.md","STUDENT_LAB_GUIDE_KO.md","mse_toy_practice.py","student_ae_todo.py"):
            self.assertIn(f"({p})",t)
            self.assertTrue((DAY/p).exists())

if __name__=="__main__":
    unittest.main()
