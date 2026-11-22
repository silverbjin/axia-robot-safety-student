"""D15 초심자 실습 핸드북 출고 계약: docs L0 only, never run robot."""
import hashlib
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
DAY=ROOT/"block_D"/"day15"
GUIDE=DAY/"STUDENT_BEGINNER_HANDS_ON_GUIDE_KO.md"

class D15BeginnerWorkbookContract(unittest.TestCase):
    def test_beginner_guide_exists_and_stages(self):
        self.assertTrue(GUIDE.is_file(), "상세 초심자 D15 가이드가 아직 없음")
        s=GUIDE.read_text(encoding="utf-8")
        for token in (
            "Human-aware Safety AMR 통합 MVP 구현",
            "통합 안전제어 시나리오 검증 및 결과정리",
            "git clone --branch main",
            "git rev-parse HEAD",
            "python3 -m unittest discover",
            "block_D/day15/run_lab.py --out /tmp/axia-d15",
            "d15_evidence_review.json",
            "d15_counterexamples.json",
            "d15_offline_replay.html",
            "CLEAR", "SLOW", "STOP", "CANCEL", "ODOM_DWELL",
            "SAFETY_TTL", "PNU_AND_SCOPE",
            "first_violation_timestamp",
            "HOLD_RAW_REVIEW_AND_VISUAL_PENDING",
            "D15_SYNTHETIC_NEGATIVE_DETECTION=5/5",
            "STUDENT_EVIDENCE_WORKSHEET_KO.md",
            "FINAL_EVALUATION_RUBRIC_KO.md",
            "NOT_RUN",
        ):
            with self.subTest(token=token):
                self.assertIn(token,s)
    def test_code_and_system_explanations(self):
        s=GUIDE.read_text(encoding="utf-8")
        for token in (
            "load_evidence()", "review_baseline()", "negative_counterexamples()",
            "validate_g09_g10_separation()", "ordered_snapshots()",
            "/cmd_vel_supervised", "/cmd_vel_pre_guard", "/cmd_vel",
            "SCAN_301MS", "GUARD_151MS", "GOAL_WRONG",
            "DWELL_0_5S", "FALSE_CERTIFICATION",
            "입력", "처리", "출력", "TTL", "Goal UUID",
            "Nav2", "Collision Monitor", "Base Guard",
        ):
            with self.subTest(token=token):
                self.assertIn(token,s)
    def test_no_private_leak_or_fake_acceptance(self):
        s=GUIDE.read_text(encoding="utf-8")
        for forbidden in (
            "training/block_D/day15/INSTRUCTOR_ANSWER_KEY_KO.md",
            "BEGIN PRIVATE KEY", "G11_FORMAL_ACCEPTED=true",
            "CERTIFIED_ESTOP=true",
        ):
            self.assertNotIn(forbidden,s)
        self.assertIn("실제 Gazebo",s)
        self.assertIn("합성",s)
    def test_existing_fixture_not_changed(self):
        p=DAY/"fixtures"/"jrcigogl_public_derived.json"
        b=p.read_bytes()
        gitblob=hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
        self.assertEqual(gitblob,"ae7d594b5452d96cc8802bc53bc8ad578fe99fb7")
    def test_entrypoint_links_beginner_guide(self):
        s=(DAY/"STUDENT_LAB_GUIDE_KO.md").read_text(encoding="utf-8")
        self.assertIn("STUDENT_BEGINNER_HANDS_ON_GUIDE_KO.md",s)

if __name__=="__main__":
    unittest.main()
