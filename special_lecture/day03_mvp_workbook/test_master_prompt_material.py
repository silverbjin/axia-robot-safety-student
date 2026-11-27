"""DAY3 prompt teaching release contract: docs-only, no Gazebo/Goal."""
import re
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
DAY3=ROOT/"special_lecture/day03_mvp_workbook"
MASTER=DAY3/"DAY3_G07_MASTER_PROMPT_EXECUTION_AND_REVIEW_KO.md"
UNITS=DAY3/"DAY3_G07_U00_U13_UNIT_PROMPTS_KO.md"

class PromptMaterialContract(unittest.TestCase):
    def test_complete_master_has_copyable_prompt_and_boundaries(self):
        src=MASTER.read_text(encoding="utf-8")
        for marker in (
            "## 2. 복사하여 사용하는 완성형 마스터 프롬프트",
            "## 3. 프롬프트 구성요소와 설계 이유",
            "## 4. AI 응답 필수 검수",
            "## 5. 잘못된 응답에 대한 교정 프롬프트",
            "## 6. 학생 실습 절차",
            "## 7. 증거 제출 템플릿",
            "first_state_transition", "first_timing_violation",
            "source_gap_ms", "received_gap_ms", "observer_gap_ms",
            "RED", "GREEN", "REFACTOR", "REVIEW", "COMMIT",
            "NOT_RUN", "INCONCLUSIVE", "HOLD", "PASS_SCOPED",
            "Scan 300ms", "CM 120ms", "Guard 150ms",
            "CERTIFIED_ESTOP=false", "44965035965", "44914827138"
        ):
            self.assertIn(marker,src,marker)
        self.assertGreaterEqual(src.count("~~~"), 2)
    def test_units_cover_full_workbook(self):
        src=UNITS.read_text(encoding="utf-8")
        for i in range(14):
            self.assertIn(f"## U{i:02d} —",src)
        for marker in ("프롬프트 작성 이유","AI 응답 검수","다시 질문", "WORKBOOK", "사실","가설"):
            self.assertIn(marker,src,marker)
    def test_no_new_safety_claim_or_instructor_solution(self):
        texts=(MASTER.read_text(encoding="utf-8"),UNITS.read_text(encoding="utf-8"))
        for src in texts:
            self.assertNotIn("owner_l3_accepted=true",src.lower())
            self.assertNotIn("certified_estop=true",src.lower())
            self.assertNotIn("HIDDEN_SOLUTION",src)
            self.assertIn("원본",src)
            self.assertIn("SHA",src)
    def test_existing_mvp_files_are_real(self):
        root=ROOT/"special_lecture/day02_mvp_sources/accepted/runtime/tools"
        for filename in (
            "p2_g07_health_first_boundary.py",
            "p2_g07_scan_rmw_first_pair.py",
            "p2_g07_ci_moving_goal_oracle.py",
            "p2_g07_ordered_shutdown.py"):
            self.assertTrue((root/filename).is_file(),filename)

if __name__ == "__main__":
    unittest.main()
