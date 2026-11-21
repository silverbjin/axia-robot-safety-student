"""D14 Student public risk policy contracts (initial RED is required)."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from risk_policy_student import RiskState, apply_verdict, expired_verdict

def msg(seq=0, verdict="N", **changes):
    d={"seq":seq, "verdict":verdict, "scope":"SYNTHETIC_ROS_L1_NO_MOTION",
       "gate_accepted":False, "goal_sent":False, "certified_estop":False}
    d.update(changes); return d

def handle(state=None, payload=None, **opts):
    return apply_verdict(RiskState() if state is None else state,
                         msg() if payload is None else payload,
                         now_mono=opts.pop("now_mono",5.0),
                         unique_source=opts.pop("unique_source",True),
                         owned_goal=opts.pop("owned_goal",True),
                         healthy=opts.pop("healthy",True))

class RiskPolicyStudent(unittest.TestCase):
    def test_N_initial_healthy_normal(self):
        s,a=handle()
        self.assertEqual(a,"NORMAL_UNCHANGED_NO_FALSE_RISK")
        self.assertFalse(s.limited_by_risk)
    def test_P_limits(self):
        s,a=handle(payload=msg(0,"P"))
        self.assertEqual(a,"LIMIT_ON_PREDICTED_P")
        self.assertTrue(s.limited_by_risk)
    def test_U_limits(self):
        s,a=handle(payload=msg(0,"U"))
        self.assertEqual(a,"LIMIT_ON_UNKNOWN_U")
        self.assertTrue(s.limited_by_risk)
    def test_N_never_clears_existing_limit(self):
        s,_=handle(payload=msg(0,"P"))
        s,a=handle(s,payload=msg(1,"N"),now_mono=5.1)
        self.assertEqual(a,"KEEP_LIMITED_NO_AUTOMATIC_CLEAR")
        self.assertTrue(s.limited_by_risk)
    def test_duplicate_or_reordered_N_rejected(self):
        s,_=handle(payload=msg(2,"P"))
        s,a=handle(s,payload=msg(2,"N"))
        self.assertEqual(a,"REJECT_REPLAY_OR_REORDERED")
        self.assertTrue(s.limited_by_risk)
    def test_bad_provenance_fail_closed(self):
        s,a=handle(payload=msg(0,"N",gate_accepted=True))
        self.assertEqual(a,"LIMIT_ON_INVALID_PROVENANCE")
        self.assertTrue(s.limited_by_risk)
    def test_multiple_sources_limit(self):
        s,a=handle(unique_source=False)
        self.assertEqual(a,"LIMIT_ON_UNTRUSTED")
        self.assertTrue(s.limited_by_risk)
    def test_invalid_sequence_limits(self):
        s,a=handle(payload=msg(-1,"N"))
        self.assertEqual(a,"LIMIT_ON_INVALID_SEQUENCE")
        self.assertTrue(s.limited_by_risk)
    def test_invalid_label_is_unknown(self):
        s,a=handle(payload=msg(0,"SAFE"))
        self.assertEqual(a,"LIMIT_ON_UNKNOWN_U")
        self.assertEqual(s.last_verdict,"U")
    def test_no_owned_goal_does_not_arm(self):
        s,a=handle(payload=msg(0,"P"),owned_goal=False)
        self.assertEqual(a,"NO_OWNED_HEALTHY_GOAL")
        self.assertFalse(s.ever_received)
    def test_unhealthy_does_not_arm(self):
        s,a=handle(payload=msg(0,"N"),healthy=False)
        self.assertEqual(a,"NO_OWNED_HEALTHY_GOAL")
        self.assertFalse(s.ever_received)
    def test_stale_fresh_boundary(self):
        s,_=handle()
        self.assertFalse(expired_verdict(s,now_mono=5.3))
        self.assertTrue(expired_verdict(s,now_mono=5.52))
    def test_clock_regression_expires(self):
        s,_=handle()
        self.assertTrue(expired_verdict(s,now_mono=4.0))
    def test_unseen_initial_boot_does_not_expire(self):
        self.assertFalse(expired_verdict(RiskState(),now_mono=100.0))
    def test_invalid_clock_is_rejected(self):
        with self.assertRaises(ValueError):
            handle(now_mono=float("nan"))

if __name__=="__main__":
    unittest.main()
