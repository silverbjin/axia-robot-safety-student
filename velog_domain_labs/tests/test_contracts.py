"""공개 표준 라이브러리 테스트: 강사 솔루션은 포함되지 않습니다."""
import math
import unittest
class Lab01(unittest.TestCase):
    def test_pass(self):
        from axia_command_chain_lab.core import check_final_owner as f
        self.assertEqual(f(["p2_base_guard"]),"PASS")
    def test_missing(self):
        from axia_command_chain_lab.core import check_final_owner as f
        self.assertEqual(f([]),"FAIL_MISSING")
    def test_duplicate(self):
        from axia_command_chain_lab.core import check_final_owner as f
        self.assertEqual(f(["p2_base_guard","unknown"]),"FAIL_DUPLICATE")
    def test_wrong(self):
        from axia_command_chain_lab.core import check_final_owner as f
        self.assertEqual(f(["nav2"]),"FAIL_WRONG_OWNER")

class Lab02(unittest.TestCase):
    def test_transform(self):
        from axia_tf_scan_lab.core import transform_point
        x,y=transform_point(1,0,2,3,math.pi/2)
        self.assertAlmostEqual(x,2);self.assertAlmostEqual(y,4)
    def test_slow(self):
        from axia_tf_scan_lab.core import front_distance,classify_zone
        self.assertEqual(classify_zone(front_distance(-0.1,0.1,[2.0,0.65,0.9])),"SLOW")
    def test_stop(self):
        from axia_tf_scan_lab.core import classify_zone
        self.assertEqual(classify_zone(0.40),"STOP")
    def test_unknown(self):
        from axia_tf_scan_lab.core import front_distance,classify_zone
        self.assertEqual(classify_zone(front_distance(-0.1,0.1,[float("nan"),float("inf"),0.01])),"UNKNOWN")
    def test_invalid_increment(self):
        from axia_tf_scan_lab.core import front_distance
        with self.assertRaises(ValueError): front_distance(0,0,[1.0])

class Lab03(unittest.TestCase):
    def test_ack_not_terminal(self):
        from axia_nav2_goal_lab.core import GoalLifecycle
        g=GoalLifecycle("old");g.request_sw_stop();g.on_cancel_ack("old")
        self.assertFalse(g.can_drive());self.assertEqual(g.state,"SW_STOP_LATCHED")
    def test_wrong_uuid(self):
        from axia_nav2_goal_lab.core import GoalLifecycle
        g=GoalLifecycle("old");g.request_sw_stop();g.on_cancel_ack("old")
        with self.assertRaises(ValueError):g.on_terminal("wrong",5)
    def test_new_goal_only(self):
        from axia_nav2_goal_lab.core import GoalLifecycle
        g=GoalLifecycle("old");g.request_sw_stop();g.on_cancel_ack("old");g.on_terminal("old",5)
        g.reset(True);g.rearm();self.assertFalse(g.can_drive())
        with self.assertRaises(ValueError):g.accept_new_goal("old")
        g.accept_new_goal("new");self.assertTrue(g.can_drive())
    def test_no_reset_if_unhealthy(self):
        from axia_nav2_goal_lab.core import GoalLifecycle
        g=GoalLifecycle("old");g.request_sw_stop();g.on_cancel_ack("old");g.on_terminal("old",5)
        with self.assertRaises(ValueError):g.reset(False)

class Lab04(unittest.TestCase):
    def test_valid_slow(self):
        from axia_async_guard_lab.core import SupervisorCommand,guard_decision
        x=guard_decision(10,9.95,0.013,[SupervisorCommand(9.94,0.05)])
        self.assertEqual(x.reason,"ALLOW_MATCHED")
        self.assertAlmostEqual(x.velocity,0.013)
    def test_stale_zero(self):
        from axia_async_guard_lab.core import SupervisorCommand,guard_decision
        x=guard_decision(10,9.80,0.01,[SupervisorCommand(9.95,0.05)])
        self.assertEqual((x.reason,x.velocity),("ZERO_STALE",0.0))
    def test_history_expiry(self):
        from axia_async_guard_lab.core import SupervisorCommand,guard_decision
        self.assertEqual(guard_decision(10,9.99,0.01,[SupervisorCommand(9.7,0.05)]).velocity,0)
    def test_reversal(self):
        from axia_async_guard_lab.core import SupervisorCommand,guard_decision
        self.assertEqual(guard_decision(10,9.99,0.01,[SupervisorCommand(9.95,-0.05)]).reason,"ZERO_UNPROVEN")
    def test_nan(self):
        from axia_async_guard_lab.core import guard_decision
        self.assertEqual(guard_decision(10,9.99,float("nan"),[]).velocity,0)

class Lab05(unittest.TestCase):
    def good(self):
        return dict(actual_gazebo_executed=True,raw_evidence_verified=True,
            source_sha="a"*40,goal_terminal="CANCELED",
            odom_stop_dwell_sec=1.03,collision_count=0,first_timing_violation=None)
    def test_good(self):
        from axia_evidence_oracle_lab.core import evaluate_stop_evidence
        self.assertEqual(evaluate_stop_evidence(self.good()),"PASS")
    def test_missing_raw(self):
        from axia_evidence_oracle_lab.core import evaluate_stop_evidence
        e=self.good();e["raw_evidence_verified"]=False
        self.assertEqual(evaluate_stop_evidence(e),"INCONCLUSIVE")
    def test_timing_violation(self):
        from axia_evidence_oracle_lab.core import evaluate_stop_evidence
        e=self.good();e["first_timing_violation"]="CM_150MS"
        self.assertEqual(evaluate_stop_evidence(e),"FAIL")
    def test_active_goal(self):
        from axia_evidence_oracle_lab.core import evaluate_stop_evidence
        e=self.good();e["goal_terminal"]="ACTIVE"
        self.assertEqual(evaluate_stop_evidence(e),"FAIL")
    def test_collision(self):
        from axia_evidence_oracle_lab.core import evaluate_stop_evidence
        e=self.good();e["collision_count"]=1
        self.assertEqual(evaluate_stop_evidence(e),"FAIL")
    def test_sha256(self):
        from axia_evidence_oracle_lab.core import sha256_file
        import tempfile,os,hashlib
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"AXIA");path=f.name
        try:self.assertEqual(sha256_file(path),hashlib.sha256(b"AXIA").hexdigest())
        finally:os.unlink(path)
if __name__=="__main__":unittest.main()
