"""Owner vJpsc6Wy regression: actual map TF available, AMCL pose late subscriber absent.

Field bag: map->odom 832 and odom->base_footprint 2791 TF messages, but
Observer receives zero /amcl_pose in its 4s pre-Goal interval. Goal not sent.
Also Guard/Supervisor context wait-set traceback appears only after SIGINT.
These tests do not assert a successful live run; require public real L2.
"""
from pathlib import Path
from types import SimpleNamespace as NS
import sys
import unittest

TOOLS=Path(__file__).resolve().parent
SRC=TOOLS.parent/"ros2_ws/src/axia_safety_supervisor"
sys.path.insert(0,str(TOOLS))
sys.path.insert(0,str(SRC))
from p2_l3_coordinate_frames import verified_live_map_tf_pose
from axia_safety_supervisor.p2_shutdown_context import is_context_waitset_shutdown


def fake_tf(frame="map",child="base_link",stamp_sec=100,stamp_nsec=250000000,
            x=-2.0,y=-0.5):
    return NS(header=NS(frame_id=frame,stamp=NS(sec=stamp_sec,nanosec=stamp_nsec)),
              child_frame_id=child,transform=NS(
                 translation=NS(x=x,y=y,z=0.0),
                 rotation=NS(x=0.0,y=0.0,z=0.0,w=1.0)))


class FieldMapTfFallback(unittest.TestCase):
    def test_real_map_to_base_tf_is_verified_only_if_fresh(self):
        # Independent actual Nav2 TF chain used by TF2 Buffer.lookup_transform.
        pose=verified_live_map_tf_pose(fake_tf(),clock_ns=100_200_000_000)
        self.assertEqual(pose,(-2.0,-0.5,0.0))

    def test_tf_fails_closed_for_stale_future_or_wrong_frame(self):
        bad=[
            (fake_tf(stamp_sec=94),100_200_000_000),
            (fake_tf(stamp_sec=103),100_200_000_000),
            (fake_tf(frame="odom"),100_200_000_000),
            (fake_tf(child="base_footprint"),100_200_000_000),
            (fake_tf(x=7.0),100_200_000_000),
        ]
        for transform,clock in bad:
            with self.subTest(frame=transform.header.frame_id,child=transform.child_frame_id):
                with self.assertRaises(ValueError):
                    verified_live_map_tf_pose(transform,clock_ns=clock)

    def test_owner_uses_actual_existing_tf_if_amcl_held_pose_not_received(self):
        live=(TOOLS/"p2_l3_live_session.py").read_text()
        runner=(TOOLS/"p2_g07_ci_moving_goal.py").read_text()
        self.assertIn("verified_live_map_tf_pose(",live)
        self.assertIn("G07_LIVE_MAP_TF_VERIFIED_BEFORE_GOAL",live)
        self.assertIn("'tf_map_base_link'",live)
        self.assertIn("map_pose_source=getattr(obs,'map_pose_source'",runner)
        self.assertNotIn("map_pose=obs.data()['pose']",runner)

    def test_ci_can_force_real_tf_without_owner_fallback_override(self):
        source=(TOOLS/"p2_l3_live_session.py").read_text()
        self.assertIn("AXIA_G07_CI_FORCE_MAP_TF_FALLBACK",source)
        self.assertIn('GITHUB_ACTIONS',source)
        self.assertIn('AXIA_G07_CI_SIM_GOAL_ALLOWED',source)
        self.assertIn('G07_CI_REAL_MAP_TF_FALLBACK_REQUIRED',source)

    def test_no_map_tf_still_blocks_goal(self):
        live=(TOOLS/"p2_l3_live_session.py").read_text()
        self.assertIn("G07_AMCL_MAP_POSE_UNAVAILABLE_BEFORE_GOAL",live)
        self.assertIn("buf.can_transform('map','base_link'",live)
        self.assertIn("buf.lookup_transform('map','base_link'",live)


class FieldShutdownWaitset(unittest.TestCase):
    class RCLError(Exception):
        pass

    def test_only_invalid_context_waitset_after_shutdown_is_ignored(self):
        e=self.RCLError("failed to initialize wait set: the given context is not valid, either rcl_init() was not called or rcl_shutdown() was called.")
        self.assertTrue(is_context_waitset_shutdown(e,context_ok=False))
        self.assertFalse(is_context_waitset_shutdown(e,context_ok=True))
        self.assertFalse(is_context_waitset_shutdown(RuntimeError(str(e)),context_ok=False))
        self.assertFalse(is_context_waitset_shutdown(self.RCLError("failed to publish context invalid"),context_ok=False))

    def test_both_nodes_preserve_other_errors_and_cleanup(self):
        pkg=SRC/"axia_safety_supervisor"
        for name in ("p2_base_guard_node.py","p2_supervisor_node.py"):
            text=(pkg/name).read_text()
            with self.subTest(node=name):
                self.assertIn("is_context_waitset_shutdown(exc,context_ok=rclpy.ok())",text)
                self.assertIn("raise",text)
                self.assertIn("rclpy.try_shutdown()",text)

if __name__=="__main__":
    unittest.main()
