"""L2 #44650103452: real Goal passed, post-Goal Nav2 param service did not
appear within the original 3 seconds. Do not turn service absence into ACK.
This isolated discovery budget is INSIDE existing 60s shutdown deadline,
and never alters Scan 300ms, CM 120ms or Guard 150ms.
"""
import unittest
from pathlib import Path
from p2_g07_ordered_shutdown import parameter_discovery_budget

SCRIPT=Path(__file__).with_name("p2_g07_ordered_shutdown.py")

class BoundedNavManagerParameterDiscovery(unittest.TestCase):
    def test_rmw_parameter_service_discovery_has_bounded_grace(self):
        self.assertEqual(
          parameter_discovery_budget("/lifecycle_manager_navigation/get_parameters",60.0),8.0)
        self.assertEqual(
          parameter_discovery_budget("/lifecycle_manager_navigation/get_parameters",2.0),2.0)
        self.assertEqual(
          parameter_discovery_budget("/lifecycle_manager_localization/get_parameters",60.0),3.0)
    def test_original_service_absence_still_blocks(self):
        src=SCRIPT.read_text()
        self.assertIn('raise RuntimeError("SERVICE_MISSING:" + name)',src)
        self.assertIn('client.wait_for_service(timeout_sec=parameter_discovery_budget(name, remaining))',src)
        self.assertIn('parameter_service_discovery_elapsed_sec',src)
        self.assertIn('deadline = monotonic() + limit',src)

if __name__=="__main__":
    unittest.main()
