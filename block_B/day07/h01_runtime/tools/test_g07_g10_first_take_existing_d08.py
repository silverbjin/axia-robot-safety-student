"""G10 reuse D08 first rclpy take-complete probe, no native timebase conflation."""
import unittest
from pathlib import Path
from p2_g07_scan_take_first_pair import summarize_first_take_pair

class TestFirstTake(unittest.TestCase):
    def test_original_600ms_gap_take_completes_late_with_other_clock_callbacks(self):
        items=[
          dict(stage="take_complete",source_stamp_ns=46800000000,at=357.6805),
          dict(stage="callback_dispatch",source_stamp_ns=46800000000,at=357.68144),
          dict(stage="take_complete",source_stamp_ns=46902000000,at=358.2818),
          dict(stage="callback_dispatch",source_stamp_ns=46902000000,at=358.28194768)]
        r=summarize_first_take_pair(dict(previous_header_sim=46.8,current_header_sim=46.902,
              gap_ms=600.502826,topic="scan",clock_callback_count_inside_gap=9),items)
        self.assertEqual(r["status"],"ORIGINAL_TAKE_COMPLETE_LATE_CANDIDATE_HOLD")
        self.assertTrue(r["clock_progress_inside_gap"])
        self.assertFalse(r["root_cause_proven"])
        self.assertEqual(r["release"],"HOLD")

    def test_late_callback_after_fast_take_is_distinct(self):
        items=[
          dict(stage="take_complete",source_stamp_ns=46800000000,at=357.68),
          dict(stage="callback_dispatch",source_stamp_ns=46800000000,at=357.681),
          dict(stage="take_complete",source_stamp_ns=46902000000,at=357.781),
          dict(stage="callback_dispatch",source_stamp_ns=46902000000,at=358.282)]
        r=summarize_first_take_pair(dict(previous_header_sim=46.8,current_header_sim=46.902,
                gap_ms=600.5,topic="scan",clock_callback_count_inside_gap=0),items)
        self.assertEqual(r["status"],"POST_TAKE_DISPATCH_LATE_CANDIDATE_HOLD")

    def test_unmatched_or_duplicate_stamps_hold(self):
        first=dict(previous_header_sim=46.8,current_header_sim=46.902,
                gap_ms=600.5,topic="scan",clock_callback_count_inside_gap=0)
        self.assertEqual(summarize_first_take_pair(first,[])["status"],
                         "D08_TAKE_EXACT_PAIR_UNAVAILABLE_HOLD")
        duplicate=[dict(stage="take_complete",source_stamp_ns=46800000000,at=1.),
                   dict(stage="take_complete",source_stamp_ns=46800000000,at=1.01)]
        self.assertEqual(summarize_first_take_pair(first,duplicate)["status"],
                         "D08_TAKE_EXACT_PAIR_UNAVAILABLE_HOLD")

    def test_runtime_must_only_reuse_d08_probe_under_ci_flag(self):
        s=(Path(__file__).parent/"p2_g07_scan_wall_pregoal.py").read_text()
        self.assertIn("AXIA_G07_G10_D08_TAKE_AB",s)
        self.assertIn("from d08_rcl_take_dispatch_probe import",s)
        self.assertIn("AXIA_G07_G10_TAKE_FIRST_PAIR",s)
        self.assertIn("GITHUB_ACTIONS",s)
        self.assertNotIn("def build_scan_take_executor(",s)

if __name__=="__main__":unittest.main()
