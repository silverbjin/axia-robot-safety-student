"""BLOCK_D integrated release contract — RED until final one-shot auditor exists."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from block_D.tools.verify_student_release import verify_release, git_blob_sha1, EXPECTED_G07_BLOBS

class BlockDFinalStudentAcceptance(unittest.TestCase):
    def test_old_g07_hash_manifest_is_unmodified(self):
        for p,sha in EXPECTED_G07_BLOBS.items():
            self.assertEqual(git_blob_sha1(ROOT/p),sha)
    def test_unfinished_student_TODOs_stay_public_no_teacher_solutions(self):
        self.assertIn('return "U"',(ROOT/"block_D/day13/reachability_student.py").read_text())
        self.assertIn("D14_TODO_NOT_IMPLEMENTED",(ROOT/"block_D/day14/risk_policy_student.py").read_text())
        for filename in ("p3_oracles.py","p3_g09_risk_policy.py","p3_g10_compound.py",
                         "INSTRUCTOR_ANSWER_KEY_KO.md"):
            self.assertEqual(list((ROOT/"block_D").rglob(filename)),[],filename)
    def test_main_entrypoints_for_all_three_days(self):
        for day in ("13","14","15"):
            guide=(ROOT/f"block_D/day{day}/STUDENT_LAB_GUIDE_KO.md").read_text()
            self.assertIn("git clone --branch main",guide)
    def test_stage1_release_manifest_persists(self):
        x=json.loads((ROOT/"block_D/release/RELEASE_MANIFEST.json").read_text())
        self.assertEqual(x["stage"],"STAGE1_METADATA_ONLY")
        self.assertFalse(x["runtime_modified"])
    def test_one_shot_3_days_expected_red_red_green(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=verify_release(ROOT,Path(tmp))
            self.assertEqual(result["status"],"BLOCK_D_RELEASE_STUDENT_CONTRACT_PASS")
            self.assertEqual(result["D13"]["test_count"],10)
            self.assertEqual(result["D13"]["expected_failures"],2)
            self.assertEqual(result["D14"]["test_count"],20)
            self.assertEqual(result["D14"]["expected_failures"],11)
            self.assertEqual(result["D15"]["test_count"],24)
            self.assertEqual(result["D15"]["expected_failures"],0)
            self.assertEqual(result["D15"]["negative_mutations_detected"],5)
            self.assertFalse(result["new_ros_gazebo_goal_executed"])
            self.assertFalse(result["teacher_answer_published"])
            self.assertTrue((Path(tmp)/"BLOCK_D_RELEASE_RESULT.json").is_file())
if __name__=="__main__":
    unittest.main()
