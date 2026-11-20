"""#163 intermittent SHUTDOWN ACK: the fresh *service client endpoint* must be
created before the already-responsive parameter service request.

Only client discovery is precreated: no ManageLifecycleNodes command/Goal,
new DDS participant, second request, TTL change, or Nav2 source change.
"""
import unittest
from unittest.mock import Mock,patch
import p2_g07_ordered_shutdown as shut
import p2_g07_lifecycle_service as svc

def ci_env():
    return dict(GITHUB_ACTIONS="true",AXIA_G07_NAV_WARM_PARTICIPANT_CI_AB="1",
        AXIA_G07_CI_SIM_GOAL_ALLOWED="1",AXIA_P0_SIM_ONLY="1",
        ROS_DISTRO="jazzy",GZ_PARTITION="axia_p2_scan300_early")

class NavigationEarlyClient(unittest.TestCase):
    def test_create_before_parameters_no_shutdown_request(self):
        n=Mock()
        kind=object()
        marker=object()
        n.create_client.return_value=marker
        prepared=shut.prepare_navigation_shutdown_client(
            n,kind=kind,scope_env=ci_env())
        self.assertIs(prepared,marker)
        n.create_client.assert_called_once_with(kind,shut.NAV_MANAGER)
        n.create_client.return_value.call_async.assert_not_called()

    def test_unopted_path_preserves_original_client_lifetime(self):
        n=Mock()
        self.assertIsNone(shut.prepare_navigation_shutdown_client(
            n,kind=object(),scope_env=dict(AXIA_G07_NAV_WARM_PARTICIPANT_CI_AB="0")))
        n.create_client.assert_not_called()

    def test_native_manage_reuses_precreated_client_and_never_destroys_it(self):
        fake=Mock()
        f=Mock()
        f.done.return_value=True
        f.result.return_value=type("Answer",(),{"success":True})()
        fake.call_async.return_value=f
        fake.wait_for_service.return_value=True
        n=Mock()
        # Import ROS stubs only at runtime; test does not require Jazzy.
        import sys,types
        mod=types.ModuleType("nav2_msgs")
        srv=types.ModuleType("nav2_msgs.srv")
        class Manage:
            class Request:
                SHUTDOWN=4
                STARTUP=0
                def __init__(self): self.command=None
        srv.ManageLifecycleNodes=Manage
        ros=types.ModuleType("rclpy")
        ros.spin_until_future_complete=Mock()
        with patch.dict(sys.modules,{"nav2_msgs":mod,"nav2_msgs.srv":srv,"rclpy":ros}):
            answer=svc.call_native_manage(n,manager="navigation",command="shutdown",
                                          timeout_sec=40,prewarmed_client=fake)
        self.assertEqual(answer["status"],"ACK")
        fake.call_async.assert_called_once()
        n.create_client.assert_not_called()
        n.destroy_client.assert_not_called()
        self.assertEqual(fake.call_async.call_args.args[0].command,4)

    def test_precreated_client_only_in_opt_in_nav_stage(self):
        e=ci_env()
        sentinel=object()
        with patch.object(shut,"call_native_manage",return_value={"status":"ACK"}) as call:
            shut._call_shutdown_stage_for_ab(object(),object(),
                  manager="navigation",timeout_sec=40,
                  scope_env=e,prewarmed_client=sentinel)
        self.assertIs(call.call_args.kwargs["prewarmed_client"],sentinel)

    def test_actual_run_precreates_before_parameter_ack(self):
        from pathlib import Path
        src=Path(shut.__file__).read_text()
        self.assertLess(
            src.index("nav_shutdown_client = prepare_navigation_shutdown_client("),
            src.index("response = call(\\n            GetParameters"))
        self.assertIn("prewarmed_client=nav_shutdown_client",src)
        self.assertIn("node.destroy_client(nav_shutdown_client)",src)

if __name__=="__main__": unittest.main()
