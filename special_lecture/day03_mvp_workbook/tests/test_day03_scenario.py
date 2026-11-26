"""L0-only regression for DAY3 scenario wrapper and guide; no ROS, no Goal."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'scripts/day03_g07_scenario_once.sh'
GUIDE=ROOT/'DAY3_G07_MVP_SCENARIO_USE_GUIDE_KO.md'

class Day3ScenarioContract(unittest.TestCase):
    def invoke(self,*args,env=None):
        return subprocess.run(['bash',str(SCRIPT),*args],capture_output=True,text=True,env=env)

    def test_shell_syntax(self):
        self.assertEqual(subprocess.run(['bash','-n',str(SCRIPT)]).returncode,0)

    def test_doctor_is_offline_and_never_runs_goal(self):
        result=self.invoke('--doctor')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('NO_NETWORK_NO_ROS_NO_GAZEBO_NO_GOAL',result.stdout)
        self.assertIn('f43df3132c8c1dac29f7c980274cd85bcdda02fc',result.stdout)

    def test_default_stays_doctor(self):
        result=self.invoke()
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('DOCTOR_L0_PASS',result.stdout)

    def test_no_moving_goal_mode(self):
        for mode in ('--run','--goal','--fault','--bad'):
            with self.subTest(mode=mode):
                result=self.invoke(mode)
                self.assertEqual(result.returncode,2)
                self.assertIn('USAGE=',result.stderr)

    def test_non_git_cache_fails_closed_without_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache=Path(tmp)/'cache';cache.mkdir()
            env={**os.environ,'AXIA_DAY3_SCENARIO_CACHE_DIR':str(cache)}
            result=self.invoke('--compare',env=env)
            self.assertEqual(result.returncode,3)
            self.assertIn('CACHE_NOT_GIT_HOLD',result.stderr)

    def test_source_is_sha_and_blob_pinned(self):
        content=SCRIPT.read_text()
        for value in ('f43df3132c8c1dac29f7c980274cd85bcdda02fc',
                      '7c40f7a51b1ff6504be7bd4f16acbead185ebf55',
                      '4a6212555ba58d93e06a165477ad1f973dc8992d',
                      'status --porcelain','NO_ROS_NO_GAZEBO_NO_GOAL'):
            self.assertIn(value,content)
        self.assertNotIn('ros2 launch',content)
        self.assertNotIn('killall',content)

    def test_guide_has_sources_safety_and_unit_mapping(self):
        g=GUIDE.read_text(encoding='utf-8')
        for value in ('S01','S02','S03','S04','S05','S06','F01','F04',
                      'U00','U13','/scan','/safety/scan','RED','GREEN',
                      'first_safety_transition','first_timing_violation',
                      'L0','L2','L3','NOT_RUN','HOLD','300ms','120ms','150ms',
                      '44965035965','44914827138','NO_GOAL','E-Stop',
                      'day03_g07_scenario_once.sh'):
            self.assertIn(value,g,value)

if __name__=='__main__':
    unittest.main()
