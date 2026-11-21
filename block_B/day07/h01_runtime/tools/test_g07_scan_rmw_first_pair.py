"""RED: original Gazebo preGoal #44863792399 first Scan 424.373ms, the
exact same Scan header pair reached independent rosbag in 101.297ms.
Require native Jazzy rclpy RMW source/receive/seq at the local subscriber
before deciding DDS-receipt vs Python Executor/take. No safety release.
"""
import unittest
from pathlib import Path
from p2_g07_scan_rmw_first_pair import (
    normalize_scan_message_info, first_scan_rmw_pair)

HERE=Path(__file__).parent

class ScanExactFirstRmwPair(unittest.TestCase):
    def sample(self):
        return {"topic":"scan","previous_rx_host_monotonic":146.083134869,
                "current_rx_host_monotonic":146.507508325,
                "previous_header_sim":45.402,"current_header_sim":45.501,
                "header_sim_gap_ms":99.,"gap_ms":424.373456}

    def test_exact_jazzy_info_dict_preserves_source_received_and_seq(self):
        src=1_795_000_000_000_000_000
        self.assertEqual(
            normalize_scan_message_info({
                "source_timestamp":src,
                "received_timestamp":src+500_000,
                "publication_sequence_number":900}),
            (src,src+500_000,900))
        self.assertEqual(normalize_scan_message_info(None),(-1,-1,-1))
        self.assertEqual(normalize_scan_message_info({}),(-1,-1,-1))

    def test_100ms_source_receive_but_424ms_callback_is_not_publisher_stall(self):
        src=1_795_000_000_000_000_000
        rows=[
          {"topic":"scan","at":146.083134869,"header_sim":45.402,
           "rmw_source_ns":src,"rmw_received_ns":src+500_000,
           "rmw_publication_seq":900},
          {"topic":"scan","at":146.507508325,"header_sim":45.501,
           "rmw_source_ns":src+99_000_000,
           "rmw_received_ns":src+100_500_000,
           "rmw_publication_seq":901}
        ]
        r=first_scan_rmw_pair(self.sample(),rows)
        self.assertEqual(r["status"],"SCAN_OBSERVER_TAKE_OR_EXECUTOR_DELAY_CANDIDATE_HOLD")
        self.assertAlmostEqual(r["source_gap_ms"],99.0)
        self.assertAlmostEqual(r["received_gap_ms"],100.0)
        self.assertAlmostEqual(r["observer_gap_ms"],424.373456,places=4)
        self.assertEqual(r["publication_seq_gap"],1)
        self.assertEqual(r["release"],"HOLD")
        self.assertFalse(r["root_cause_proven"])

    def test_100ms_source_and_424ms_received_is_per_subscriber_rmw_candidate(self):
        src=1_795_000_000_000_000_000
        rows=[
          {"topic":"scan","at":146.083134869,"header_sim":45.402,
           "rmw_source_ns":src,"rmw_received_ns":src+100_000,
           "rmw_publication_seq":90},
          {"topic":"scan","at":146.507508325,"header_sim":45.501,
           "rmw_source_ns":src+99_000_000,
           "rmw_received_ns":src+424_100_000,
           "rmw_publication_seq":91}
        ]
        r=first_scan_rmw_pair(self.sample(),rows)
        self.assertEqual(r["status"],"SCAN_SUBSCRIBER_RMW_RECEIVE_OR_TAKE_DELAY_CANDIDATE_HOLD")
        self.assertEqual(r["release"],"HOLD")

    def test_missing_rmw_or_seq_never_infers_root_cause(self):
        rows=[
          {"topic":"scan","at":146.083134869,"header_sim":45.402,
           "rmw_source_ns":-1,"rmw_received_ns":-1,"rmw_publication_seq":-1},
          {"topic":"scan","at":146.507508325,"header_sim":45.501,
           "rmw_source_ns":-1,"rmw_received_ns":-1,"rmw_publication_seq":-1}
        ]
        r=first_scan_rmw_pair(self.sample(),rows)
        self.assertEqual(r["status"],"SCAN_EXACT_RMW_METADATA_UNAVAILABLE_HOLD")
        self.assertIsNone(r["source_gap_ms"])
        self.assertFalse(r["root_cause_proven"])
        self.assertEqual(r["release"],"HOLD")

    def test_runtime_records_scan_metadata_without_writing_in_callback(self):
        src=(HERE/"p2_g07_scan_wall_pregoal.py").read_text()
        self.assertIn("normalize_scan_message_info(info)",src)
        self.assertIn("scan_rmw_rows",src)
        self.assertIn("first_scan_rmw_pair(report.get(",src)
        self.assertIn('report["first_scan_rmw_pair"]',src)
        self.assertIn("SCAN_LIMIT_MS=300.0",src)
        self.assertIn("HEADER_SIM_LIMIT_MS=150.0",src)
        self.assertIn("WINDOW_SEC=12.0",src)

if __name__=="__main__":
    unittest.main()
