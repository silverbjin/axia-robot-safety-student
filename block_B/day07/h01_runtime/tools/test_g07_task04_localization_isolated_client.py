"""oZGSnDD1/public L2 first post-Goal boundary: localization service timeout.

Two public Gazebo runs reached valid Goal/STOP, then 30s localization
ManageLifecycleNodes SHUTDOWN timeout after navigation ACK. Freeze the
service-client reuse boundary before changing it. No ROS simulation here.
"""
import inspect
import unittest
from unittest.mock import patch
import p2_g07_ordered_shutdown as shutdown


class FakeNode:
    def __init__(self,name):
        self.name=name
        self.destroyed=False
    def destroy_node(self):
        self.destroyed=True


class FakeRclpy:
    def __init__(self):
        self.nodes=[]
    def create_node(self,name,**kwargs):
        n=FakeNode(name)
        self.nodes.append(n)
        return n


class IsolatedOrderedLocalizationShutdown(unittest.TestCase):
    def test_two_manager_service_requests_use_distinct_fresh_nodes(self):
        rclpy=FakeRclpy()
        calls=[]
        def native(node,*,manager,command,timeout_sec):
            calls.append((node,manager,command,timeout_sec))
            return {"status":"ACK","request_sent":True,"elapsed_sec":.05}
        with patch.object(shutdown,"call_native_manage",side_effect=native):
            a=shutdown._call_isolated_stage(rclpy,manager="navigation",
                                            timeout_sec=40.0)
            b=shutdown._call_isolated_stage(rclpy,manager="localization",
                                            timeout_sec=30.0)
        self.assertEqual((a["status"],b["status"]),("ACK","ACK"))
        self.assertEqual(len(calls),2)
        self.assertIsNot(calls[0][0],calls[1][0])
        self.assertEqual([x[1] for x in calls],["navigation","localization"])
        self.assertTrue(all(x.destroyed for x in rclpy.nodes))
        self.assertIn("_call_isolated_stage(rclpy, manager=key",
                      inspect.getsource(shutdown.run))

    def test_timeout_stays_fail_closed_without_duplicate_shutdown_request(self):
        rclpy=FakeRclpy()
        calls=[]
        def native(node,*,manager,command,timeout_sec):
            calls.append(manager)
            return {"status":"SERVICE_TIMEOUT",
                    "request_sent":True,"elapsed_sec":timeout_sec}
        with patch.object(shutdown,"call_native_manage",side_effect=native):
            result=shutdown._call_isolated_stage(
                rclpy,manager="localization",timeout_sec=30.0)
        self.assertEqual(result["status"],"SERVICE_TIMEOUT")
        self.assertEqual(calls,["localization"])
        self.assertTrue(rclpy.nodes[0].destroyed)

    def test_contract_preserves_nav_loc_budgets_and_actual_ack(self):
        self.assertEqual(shutdown.shutdown_stage_budget("localization",60),30)
        self.assertEqual(shutdown.shutdown_stage_budget("navigation",60),40)
        source=inspect.getsource(shutdown.run)
        self.assertIn('ack["status"]!="ACK"',source)
        self.assertIn('deadline = monotonic() + limit',source)


if __name__=="__main__":
    unittest.main()
