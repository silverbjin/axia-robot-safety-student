"""D14 초심자 실습서의 학습 단계와 공개·안전 범위만 확인하는 L0 문서 테스트.

기존 policy TODO/fixture/ROS runtime는 불변. 본 테스트는 학생 풀이가 아니라
실습서의 명령·예상 출력·단계별 체크포인트가 빠지지 않도록 한다.
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DAY = ROOT / "block_D" / "day14"
GUIDE = DAY / "STUDENT_LAB_GUIDE_KO.md"

class BeginnerLabGuideContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = GUIDE.read_text(encoding="utf-8")

    def test_clone_to_single_working_directory(self):
        for token in ("git clone --branch main", "git rev-parse HEAD", "python3 --version",
                      "pwd", "cd ~/axia-d14-student", "git status --short"):
            self.assertIn(token, self.doc)
        self.assertIn("기존 폴더", self.doc)

    def test_actual_code_walking_and_types(self):
        for token in ("@dataclass(frozen=True)", "last_seq", "last_rx_mono",
                      "ever_received", "limited_by_risk", "apply_verdict()",
                      "expired_verdict()", "dict", "bool", "0.5", "0.52"):
            self.assertIn(token, self.doc)

    def test_checkpointed_red_green_and_exit_codes(self):
        for token in ("체크포인트 A", "체크포인트 B", "체크포인트 C", "체크포인트 D",
                      "PIPESTATUS[0]", "UNITTEST_RC=1", "RUNNER_RC=2",
                      "FAILED (failures=11)", "D14_STUDENT_RESULT=RED_EXPECTED_TODO",
                      "D14_STUDENT_RESULT=GREEN", "PASS_CASES=", "git diff --check"):
            self.assertIn(token, self.doc)

    def test_fixture_and_first_fault_explanation(self):
        for token in ("N_fresh_keeps_normal", "P_then_N_never_autoclears",
                      "N_receipt_stale_requests_limit", "no_owned_goal_cannot_arm",
                      "SCAN_FAULT", "CM_LOST", "GUARD_LATCH", "FINAL_CMD",
                      "ODOM_STOP_DWELL", "NO_AUTO_RESUME", "stop_t=0.65"):
            self.assertIn(token, self.doc)

    def test_practice_without_claimed_robot_motion(self):
        for token in ("SLOW", "AVOID", "STOP", "choose_action_intent()",
                      "NOT_IMPLEMENTED", "NORMAL_POLICY", "LIMITED_REQUEST",
                      "NO_ROS_GAZEBO", "E-Stop", "HTML_BROWSER_NOT_RUN"):
            self.assertIn(token, self.doc)
        for forbidden in ("training/block_D/day14/solution/", "p3_g09_risk_policy.py",
                          "p3_g10_compound.py", "FORMAL_G10_PASS"):
            self.assertNotIn(forbidden, self.doc)

if __name__ == "__main__":
    unittest.main()
