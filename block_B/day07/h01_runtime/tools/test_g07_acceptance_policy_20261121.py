"""G07 acceptance policy RED→GREEN without ROS or fake Goal.

Scoped instructor release change: GUI is diagnostic, localization STARTUP
ACK may be missing only with independent ACTIVE + later real pose/TF gates;
depth sensor absent in session-only Waffle SDF; scan wall>300ms diagnostic
while missing/out-of-order Scan and Clock/Odom hard limits remain.
"""
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"scripts/p2_no_goal_smoke_ci.sh"
OWNER_LAUNCH=ROOT/"ros2_ws/src/axia_safety_bringup/launch/axia_tb3_p2.launch.py"

class G07AcceptancePolicy(unittest.TestCase):
    @staticmethod
    def _samples(*,slow_scan=True,missing=False,odom_slow=False):
        # 12s real monotonic in one session. One Scan callback gap is 450ms,
        # but laser Header simulated 100ms => no dropped/out-of-order evidence.
        clocks=[(i*.05,i*.05) for i in range(271)]
        odom=[(i*(.35 if odom_slow else .1),i*.1) for i in range(141 if not odom_slow else 43)]
        scan=[]
        for i in range(120):
            t=i*.1+(0.35 if slow_scan and i>=55 else 0)
            stamp=i*.1+(0.20 if missing and i>=55 else 0)
            scan.append((t,stamp))
        return dict(clock=clocks,odom=odom,scan=scan,safety_scan=list(scan))

    def test_scan_450ms_is_diagnostic_not_formal_timeout(self):
        from p2_g07_scan_wall_pregoal import assess_pregoal_samples
        result=assess_pregoal_samples(self._samples())
        self.assertEqual(result["status"],"PASS_SCOPED_RECEIVED_SCAN_ONLY",result)
        self.assertGreater(result["topic_results"]["scan"]["max_wall_gap_ms"],300)
        self.assertTrue(result["scan_wall_gap_diagnostic_only"])
        self.assertIsNotNone(result["first_scan_timing_boundary"])
        self.assertFalse(result["goal_sent"])
        self.assertFalse(result["certified_estop"])

    def test_scan_header_missing_and_clock_or_odom_gap_still_block(self):
        from p2_g07_scan_wall_pregoal import assess_pregoal_samples
        self.assertEqual(assess_pregoal_samples(
            self._samples(missing=True))["status"],"HOLD")
        self.assertEqual(assess_pregoal_samples(
            self._samples(odom_slow=True))["status"],"HOLD")

    def test_g07_localization_lost_startup_ack_readonly_state_not_spoofed(self):
        from d07_h01_lifecycle_reconcile import assess_reconciliation
        native={"schema":"axia_g07_native_lifecycle_service_v1",
                "manager":"localization","command":"startup",
                "service":"/lifecycle_manager_localization/manage_nodes",
                "status":"SERVICE_TIMEOUT","success":False,
                "request_sent":True,"goal_sent":False}
        env={"ROS_DISTRO":"jazzy","AXIA_P0_SIM_ONLY":"1",
             "AXIA_G07_OWNER_STARTUP_PARITY":"1",
             "AXIA_G07_STARTUP_READONLY_RECONCILE":"1",
             "GZ_PARTITION":"axia_p2_acceptance_123",
             "GITHUB_ACTIONS":"true",
             "AXIA_G07_CI_SIM_GOAL_ALLOWED":"1"}
        sample={"manager_active":True,
                "map_server":{"id":3,"label":"active"},
                "amcl":{"id":3,"label":"active"}}
        accepted=assess_reconciliation(native,[sample,sample],env)
        self.assertTrue(accepted["admitted_for_g07_startup_state_only"])
        self.assertFalse(accepted["lifecycle_ack_received"])
        self.assertFalse(accepted["startup_resent"])
        self.assertFalse(accepted["moving_goal_admitted"])
        self.assertFalse(assess_reconciliation(native,[sample,{"manager_active":False}],env)
                         ["admitted_for_g07_startup_state_only"])

    def test_g07_default_waffle_temp_sdf_excludes_depth_but_keeps_lidar(self):
        from p2_g07_demo_lidar_overlay import generate
        source=(b'<?xml version="1.0"?>\n<robot>\n' +
          b'<sensor name="hls_lfcd_lds" type="gpu_lidar">'
          b'<always_on>true</always_on><update_rate>5</update_rate></sensor>\n'
          b'<sensor name="intel_realsense_r200_depth" type="depth">'
          b'<always_on>1</always_on><update_rate>5</update_rate>'
          b'<camera name="realsense_depth_camera"/></sensor>\n'
          b'<joint name="camera_joint" type="fixed"/>\n</robot>\n')
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            model=root/"gz_waffle.sdf.xacro";model.write_bytes(source)
            target=root/"g07.sdf.xacro"
            report=generate(model,target,disable_depth=True)
            out=target.read_bytes()
            self.assertIn(b'hls_lfcd_lds',out)
            self.assertIn(b'<update_rate>10</update_rate>',out)
            self.assertNotIn(b'intel_realsense_r200_depth',out)
            self.assertIn(b'camera_joint',out)
            self.assertEqual(model.read_bytes(),source)
            self.assertTrue(report["depth_sensor_disabled_in_session"])
            target2=root/"g07_depth_optin.sdf.xacro"
            report2=generate(model,target2,disable_depth=False)
            self.assertIn(b'intel_realsense_r200_depth',target2.read_bytes())
            self.assertFalse(report2["depth_sensor_disabled_in_session"])

    def test_g07_script_selects_depth_off_gui_optional_with_existing_entry(self):
        source=SCRIPT.read_text()
        self.assertIn("AXIA_G07_DEPTH_SENSOR_ENABLED",source)
        self.assertIn("--disable-depth",source)
        self.assertIn("AXIA_G07_OWNER_GUI_OPTIONAL",source)
        self.assertIn("AXIA_G07_GUI_DIAGNOSTIC_ONLY",source)
        self.assertIn('LAUNCH="$ROOT/ros2_ws/src/axia_safety_bringup/launch/axia_tb3_p2.launch.py"',source)
        self.assertNotIn("CERTIFIED_ESTOP=true",source)

    def test_bringup_package_installed_without_source_relative_only(self):
        package=ROOT/"ros2_ws/src/axia_safety_bringup"
        self.assertTrue((package/"package.xml").is_file())
        self.assertTrue((package/"setup.py").is_file())
        setup=(package/"setup.py").read_text()
        self.assertIn("axia_tb3_p2.launch.py",setup)
        self.assertIn("resource_index/packages",setup)
        self.assertIn("launch",setup)
        self.assertIn("config",setup)

if __name__=="__main__":
    unittest.main()
