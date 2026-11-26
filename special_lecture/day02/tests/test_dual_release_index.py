"""DAY02 v4 dual snapshot policies; offline L0 only."""
import json
from pathlib import Path
import unittest

D=Path(__file__).resolve().parents[1]
class DualRelease(unittest.TestCase):
    def test_source_and_history_pair(self):
        x=json.loads((D/"DUAL_RELEASE_INDEX.json").read_text())
        self.assertEqual(x["accepted"]["source_sha"],"f7edb2d126502eeeed58ae014adadc7a2096d41b")
        self.assertEqual(x["advanced_failed"]["source_sha"],"a04f9a7da8d54bbd9f944d05388792cb706adf28")
        self.assertEqual(x["advanced_failed"]["release_commit_sha"],"d9ba3f78ae701697a5986a2bc856e4d856a73dd9")
        self.assertEqual(x["accepted"]["native_status"],"2_OF_2_PASS")
        self.assertEqual(x["advanced_failed"]["native_status"],"0_OF_2_FAIL")
        self.assertIs(x["advanced_failed"]["owner_release_authorized"],False)
    def test_safe_scope(self):
        x=json.loads((D/"DUAL_RELEASE_INDEX.json").read_text())
        self.assertIs(x["policy"]["main_merge_requires_user_approval"],True)
        self.assertIs(x["policy"]["certified_estop"],False)
        self.assertIs(x["course"]["new_gazebo_goal_by_default"],False)
    def test_checkout_script_is_safe(self):
        s=(D/"scripts/prepare_dual_mvp.sh").read_text()
        self.assertIn("worktree add --detach",s)
        self.assertIn("d9ba3f78ae701697a5986a2bc856e4d856a73dd9",s)
        self.assertIn("REFUSE_OVERWRITE",s)
        self.assertNotIn("ros2 launch",s)
        self.assertNotIn("gz sim",s)
    def test_master_first_units(self):
        p=(D/"workbook/DUAL_MVP_WORKBOOK_PLAN_v4_KO.md").read_text()
        m=(D/"workbook/MASTER_PROMPT_DAY02_DUAL_MVP_KO.txt").read_text()
        for i in range(14): self.assertIn("U%02d"%i,p)
        for i in range(1,7): self.assertIn("A%02d"%i,p)
        self.assertIn("Run 44914827138",m)
        self.assertIn("Run 44965035965",m)
if __name__=="__main__":unittest.main()
