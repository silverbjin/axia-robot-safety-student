"""Use real Jazzy launch actions for Owner/CI Xacro=>Gazebo ordering.

No Goal/ROS graph in L0. Native L2 must subsequently prove actual /clock,
simulated motion, native CM/Guard timing and ordered shutdown.
"""
import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from launch import LaunchContext, LaunchDescription
from launch.actions import ExecuteProcess, RegisterEventHandler, Shutdown

ROOT=Path(__file__).resolve().parents[1]
LAUNCH=ROOT/"ros2_ws/src/axia_safety_bringup/launch/axia_tb3_p2.launch.py"
spec=importlib.util.spec_from_file_location("axia_g07_owner_clock_launch",LAUNCH)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class RealLaunchSequence(unittest.TestCase):
    def make_launch(self, output):
        xacro=ExecuteProcess(cmd=["xacro","-o",str(output),"dummy.sdf.xacro"])
        gazebo=ExecuteProcess(cmd=["gz","sim","-r","-s",str(output)])
        return LaunchDescription([xacro,gazebo]),xacro,gazebo

    def test_owner_only_ordering_and_unapproved_default_preservation(self):
        with tempfile.TemporaryDirectory() as td:
            d,x,g=self.make_launch(Path(td)/"world.sdf")
            with patch.dict(os.environ,{
                "AXIA_G07_TASK04_OWNER_MOVING_L3":"1",
                "AXIA_G07_CI_SIM_GOAL_ALLOWED":"0",
                "AXIA_P0_SIM_ONLY":"1",
                "AXIA_G07_OWNER_STARTUP_PARITY":"1",
                "AXIA_P2_G07_PHYSICAL_PREFLIGHT":"1",
                "AXIA_P2_G07_RELOCATED_OBSTACLE":"1",
                "GITHUB_ACTIONS":"false",
            },clear=True):
                module._order_h01_world_xacro_before_gazebo(d)
            entities=list(d.entities)
            self.assertNotIn(g,entities)
            self.assertLess(next(i for i,e in enumerate(entities)
                                 if isinstance(e,RegisterEventHandler)),
                            entities.index(x))
            untrusted,x2,g2=self.make_launch(Path(td)/"untouched.sdf")
            with patch.dict(os.environ,{},clear=True):
                module._order_h01_world_xacro_before_gazebo(untrusted)
            self.assertIn(g2,list(untrusted.entities))

    def test_ci_moving_same_order_without_owner_authority(self):
        with tempfile.TemporaryDirectory() as td:
            d,x,g=self.make_launch(Path(td)/"world.sdf")
            env={"AXIA_G07_TASK04_CI_GUI_MOVING":"1",
                 "GITHUB_ACTIONS":"true",
                 "AXIA_G07_CI_SIM_GOAL_ALLOWED":"1",
                 "AXIA_P0_SIM_ONLY":"1",
                 "AXIA_G07_OWNER_STARTUP_PARITY":"1",
                 "AXIA_P2_G07_PHYSICAL_PREFLIGHT":"1"}
            with patch.dict(os.environ,env,clear=True):
                module._order_h01_world_xacro_before_gazebo(d)
            self.assertNotIn(g,list(d.entities))

    def test_successful_real_sdf_gate_returns_only_gazebo(self):
        with tempfile.TemporaryDirectory() as td:
            output=Path(td)/"world.sdf"
            output.write_text('<sdf version="1.9"><world name="default"></world></sdf>')
            d,x,g=self.make_launch(output)
            out=module._on_world_xacro_exit(SimpleNamespace(returncode=0),LaunchContext(),g)
            self.assertEqual(out,[g])

    def test_missing_or_bad_sdf_cannot_start_gazebo(self):
        with tempfile.TemporaryDirectory() as td:
            output=Path(td)/"world.sdf"
            d,x,g=self.make_launch(output)
            for bad in (None,"",'<sdf version="1.9"><model name="oops"/></sdf>'):
                if bad is not None:
                    output.write_text(bad)
                out=module._on_world_xacro_exit(SimpleNamespace(returncode=0),LaunchContext(),g)
                self.assertEqual(len(out),1)
                self.assertIsInstance(out[0],Shutdown)
                self.assertNotIn(g,out)
            output.write_text('<sdf version="1.9"><world name="default"></world></sdf>')
            out=module._on_world_xacro_exit(SimpleNamespace(returncode=9),LaunchContext(),g)
            self.assertIsInstance(out[0],Shutdown)

if __name__=="__main__":
    unittest.main()
