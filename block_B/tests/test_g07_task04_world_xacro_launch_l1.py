"""L1 real ROS 2 Launch event-handler contract, no Gazebo/Goal.
Run after source /opt/ros/jazzy/setup.bash on exact CI Student SHA.
"""
import importlib.util
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from launch import LaunchDescription, LaunchContext
from launch.actions import ExecuteProcess, RegisterEventHandler, EmitEvent
from launch.events.process import ProcessExited

LAUNCH_FILE=(Path(__file__).resolve().parents[1]/"day07/h01_runtime/ros2_ws/src/"
             "axia_safety_bringup/launch/axia_tb3_p2.launch.py")


def load_real_launch():
    import sys
    sys.path.insert(0,str(LAUNCH_FILE.parent))
    spec=importlib.util.spec_from_file_location("axia_tb3_l1_test",LAUNCH_FILE)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestRealLaunchHandler(unittest.TestCase):
    def _process_exit(self,rc,sdf):
        world=ExecuteProcess(cmd=['xacro','-o',str(sdf),
                                  'headless:=True','fixture_world.sdf.xacro'])
        server=ExecuteProcess(cmd=['gz','sim','-r','-s',str(sdf)])
        d=LaunchDescription([world,server])
        scope={'AXIA_G07_TASK04_OWNER_MOVING_L3':'1',
               'AXIA_G07_OWNER_STARTUP_PARITY':'1',
               'AXIA_G07_CI_SIM_GOAL_ALLOWED':'0',
               'AXIA_P0_SIM_ONLY':'1'}
        mod=load_real_launch()
        with patch.dict(os.environ,scope,clear=True):
            mod._order_world_xacro_before_gazebo(d)
        self.assertNotIn(server,d.entities,
                         "Gazebo process must not be scheduled before xacro")
        handlers=[x for x in d.entities if isinstance(x,RegisterEventHandler)]
        self.assertEqual(len(handlers),1)
        event=ProcessExited(returncode=rc,action=world,name='xacro',
                            cmd=['xacro','-o',str(sdf),'headless:=True',
                                 'fixture_world.sdf.xacro'],
                            cwd='/',env={},pid=1234)
        actions=handlers[0].event_handler.handle(event,LaunchContext())
        return server,actions

    def test_success_generates_exactly_one_server_action_after_valid_sdf(self):
        with TemporaryDirectory() as td:
            sdf=Path(td)/'nav2_test.sdf'
            sdf.write_text("<sdf version='1.9'><world name='default'/></sdf>")
            server,actions=self._process_exit(0,sdf)
            self.assertEqual(actions,[server])

    def test_xacro_nonzero_does_not_start_gazebo(self):
        with TemporaryDirectory() as td:
            server,actions=self._process_exit(7,Path(td)/'missing.sdf')
            self.assertNotIn(server,actions)
            self.assertTrue(any(isinstance(a,EmitEvent) for a in actions))

    def test_missing_and_invalid_sdf_fail_closed(self):
        with TemporaryDirectory() as td:
            sdf=Path(td)/'nav2_test.sdf'
            for value in (None,"<sdf><world", "<sdf><model/></sdf>"):
                with self.subTest(value=value):
                    if value is None:
                        sdf.unlink(missing_ok=True)
                    else:
                        sdf.write_text(value)
                    server,actions=self._process_exit(0,sdf)
                    self.assertNotIn(server,actions)
                    self.assertTrue(any(isinstance(a,EmitEvent) for a in actions))


if __name__=="__main__":
    unittest.main()
