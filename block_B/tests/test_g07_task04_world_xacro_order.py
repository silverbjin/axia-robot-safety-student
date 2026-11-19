"""Owner oZGSnDD1: minimum ROS-free world-xacro/Gazebo start regression.
RED: Owner and public Moving modes lack H01's existing startup ordering.
No ROS, Gazebo or hardware is started by this module.
"""
import ast
import os
from pathlib import Path
import tempfile
import unittest

SOURCE=(Path(__file__).resolve().parents[1]/"day07/h01_runtime/ros2_ws/src/"
        "axia_safety_bringup/launch/axia_tb3_p2.launch.py")


def load_helpers():
    tree=ast.parse(SOURCE.read_text(encoding="utf-8"))
    wanted={"_world_xacro_sync_scope","_check_world_sdf_after_xacro_exit"}
    defs=[node for node in tree.body
          if isinstance(node,ast.FunctionDef) and node.name in wanted]
    if {n.name for n in defs}!=wanted:
        raise AssertionError("G07_TASK04_XACRO_WORLD_SYNC_HELPER_MISSING")
    import hashlib
    import xml.etree.ElementTree as ET
    ns={"os":os,"Path":Path,"hashlib":hashlib,"ET":ET}
    exec(compile(ast.Module(body=defs,type_ignores=[]),str(SOURCE),"exec"),ns)
    return ns


class TestG07OwnerWorldXacroRace(unittest.TestCase):
    def test_three_explicit_simulation_modes_only(self):
        scope=load_helpers()["_world_xacro_sync_scope"]
        self.assertEqual(scope({"AXIA_D07_H01_GUI_NO_GOAL":"1","AXIA_P0_SIM_ONLY":"1",
                                "AXIA_G07_CI_SIM_GOAL_ALLOWED":"0"}),"h01")
        self.assertEqual(scope({"AXIA_G07_TASK04_OWNER_MOVING_L3":"1","AXIA_P0_SIM_ONLY":"1",
                                "AXIA_G07_OWNER_STARTUP_PARITY":"1",
                                "AXIA_G07_CI_SIM_GOAL_ALLOWED":"0"}),"owner")
        self.assertEqual(scope({"AXIA_G07_TASK04_CI_GUI_MOVING":"1","AXIA_P0_SIM_ONLY":"1",
                                "AXIA_G07_TASK03_FORMAL_CI":"1",
                                "AXIA_G07_CI_SIM_GOAL_ALLOWED":"1",
                                "GITHUB_ACTIONS":"true"}),"ci_moving")
        for env in ({},{"AXIA_P0_SIM_ONLY":"1"},
                    {"AXIA_G07_TASK04_OWNER_MOVING_L3":"1"},
                    {"AXIA_G07_TASK04_OWNER_MOVING_L3":"1","AXIA_P0_SIM_ONLY":"1"},
                    {"AXIA_G07_TASK04_CI_GUI_MOVING":"1","AXIA_P0_SIM_ONLY":"1"},
                    {"AXIA_G07_TASK04_OWNER_MOVING_L3":"1","AXIA_P0_SIM_ONLY":"1",
                     "AXIA_G07_OWNER_STARTUP_PARITY":"1",
                     "AXIA_G07_CI_SIM_GOAL_ALLOWED":"1"},
                    {"AXIA_G07_TASK04_OWNER_MOVING_L3":"1","AXIA_P0_SIM_ONLY":"1",
                     "AXIA_G07_OWNER_STARTUP_PARITY":"1",
                     "AXIA_G07_CI_SIM_GOAL_ALLOWED":"0","GITHUB_ACTIONS":"true"}):
            with self.subTest(env=env):
                self.assertIsNone(scope(env))

    def test_actual_xacro_exit_status_and_world_sdf(self):
        check=load_helpers()["_check_world_sdf_after_xacro_exit"]
        with tempfile.TemporaryDirectory() as td:
            sdf=Path(td)/"nav2_fake.sdf"
            cmd=["xacro","-o",str(sdf),"headless:=True","official_world.sdf.xacro"]
            self.assertEqual(check(7,cmd)[0],"GAZEBO_WORLD_XACRO_FAILED")
            self.assertEqual(check(0,cmd)[0],"GAZEBO_WORLD_SDF_MISSING")
            sdf.write_text("")
            self.assertEqual(check(0,cmd)[0],"GAZEBO_WORLD_SDF_INVALID")
            sdf.write_text("<sdf version='1.9'><world")
            self.assertEqual(check(0,cmd)[0],"GAZEBO_WORLD_SDF_INVALID")
            sdf.write_text("<sdf version='1.9'><model name='bad'/></sdf>")
            self.assertEqual(check(0,cmd)[0],"GAZEBO_WORLD_SDF_INVALID")
            sdf.write_text("<sdf version='1.9'><world name='default'/></sdf>")
            verdict, evidence=check(0,cmd)
            self.assertEqual(verdict,"WORLD_SDF_READY")
            self.assertEqual(evidence["bytes"],sdf.stat().st_size)
            self.assertEqual(len(evidence["sha256"]),64)

    def test_delayed_sdf_writer_never_unlocks_gazebo_early(self):
        import threading
        import time
        check=load_helpers()["_check_world_sdf_after_xacro_exit"]
        with tempfile.TemporaryDirectory() as td:
            sdf=Path(td)/"nav2_delayed.sdf"
            cmd=["xacro","-o",str(sdf),"headless:=True","world.sdf.xacro"]
            generated=threading.Event()
            def writer():
                time.sleep(0.08)  # synthetic delay ONLY in unit test
                sdf.write_text("<sdf version='1.9'><world name='test'/></sdf>")
                generated.set()
            t=threading.Thread(target=writer)
            t.start()
            try:
                self.assertEqual(check(0,cmd)[0],"GAZEBO_WORLD_SDF_MISSING")
                self.assertTrue(generated.wait(timeout=1))
                self.assertEqual(check(0,cmd)[0],"WORLD_SDF_READY")
            finally:
                t.join(timeout=1)

    def test_unexpected_upstream_shape_fails_closed(self):
        check=load_helpers()["_check_world_sdf_after_xacro_exit"]
        for cmd in ([],["python","-o","/tmp/world.sdf"],["xacro","--bad"]):
            with self.subTest(cmd=cmd):
                self.assertEqual(check(0,cmd)[0],"GAZEBO_WORLD_XACRO_COMMAND_CHANGED")

    def test_registered_order_excludes_unconditional_server_start(self):
        s=SOURCE.read_text()
        self.assertIn("_order_world_xacro_before_gazebo(d)",s)
        self.assertIn("OnProcessExit(",s)
        self.assertIn("_check_world_sdf_after_xacro_exit",s)
        self.assertIn("event.returncode",s)
        self.assertIn("d.entities.remove(gazebo_server)",s)


if __name__=="__main__":
    unittest.main()
