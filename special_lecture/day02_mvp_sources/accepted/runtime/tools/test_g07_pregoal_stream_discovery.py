"""G07 real native #44859905000 cycle1: /safety/scan start late.

The strict 12s Scan/Clock/Odom wall window must begin AFTER all 4 read-only
topics have actually delivered two fresh callbacks. Never shorten window,
relax 300ms TTL or fabricate a source.
"""
import unittest
from pathlib import Path
from p2_g07_scan_wall_pregoal import preflight_streams_ready


class PregoalDiscovery(unittest.TestCase):
    def rows(self,t=10.0):
        return {key:[(t-.16,1.0),(t-.04,1.1)]
                for key in ("scan","safety_scan","clock","odom")}

    def test_all_four_actual_topics_fresh_before_starting_12s_window(self):
        self.assertTrue(preflight_streams_ready(self.rows(),now=10.0))
        row=self.rows()
        row["safety_scan"]=[]
        self.assertFalse(preflight_streams_ready(row,now=10.0))
        row=self.rows()
        row["safety_scan"]=[(9.20,1.0),(9.35,1.1)]
        self.assertFalse(preflight_streams_ready(row,now=10.0))

    def test_future_backward_or_duplicate_callbacks_never_admit(self):
        for values in ([(10.02,1.0),(10.03,1.1)],
                       [(9.95,1.0),(9.94,1.1)],
                       [(9.96,1.0),(9.96,1.1)]):
            row=self.rows()
            row["clock"]=values
            with self.subTest(values=values):
                self.assertFalse(preflight_streams_ready(row,now=10.0))

    def test_existing_12s_strict_window_not_shortened_or_bypassed(self):
        p=Path(__file__).with_name("p2_g07_scan_wall_pregoal.py").read_text()
        self.assertIn("DISCOVERY_WARMUP_MAX_SEC=8.0",p)
        self.assertIn("WARMUP_SEC=2.0",p)
        self.assertIn("WINDOW_SEC=12.0",p)
        self.assertIn("preflight_streams_ready(records,now=time.monotonic())",p)
        self.assertIn("SCAN_PREFLIGHT_STREAM_DISCOVERY_TIMEOUT",p)
        self.assertIn("records.values():rows.clear()",p)
        self.assertIn("while time.monotonic()-t1<window_sec",p)
        self.assertIn("SCAN_LIMIT_MS=300.0",p)
        self.assertIn("HEADER_SIM_LIMIT_MS=150.0",p)


if __name__=="__main__":
    unittest.main()
