"""D13 public student tests: exactly P/N are expected to fail for the TODO stub."""
import sys, unittest
from pathlib import Path
DAY13 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DAY13))
from reachability_student import classify_time_indexed

def trace():
    return [{"t_sec": round(10.1 + .2*i, 8), "x": round(.2*i,8),
             "y":0.0, "radius":.15} for i in range(16)]
def person(**kwargs):
    p={"x":2.1,"y":0.0,"vx":-1.0,"vy":0.0,"radius":.2,
       "confidence":.9,"observed_sec":10.0}
    p.update(kwargs)
    return p

class D13TimeIndexedPublic(unittest.TestCase):
    def test_P_same_time_overlap(self):
        self.assertEqual(classify_time_indexed(trace(),person(),now_sec=10.1),"P")
    def test_N_same_path_different_time(self):
        self.assertEqual(classify_time_indexed(
            trace(),person(x=.9,vx=1.0),now_sec=10.1),"N")
    def test_U_stale_future_low_confidence(self):
        for x in (person(observed_sec=9.5),person(observed_sec=10.2),
                  person(confidence=.05)):
            with self.subTest(x=x):
                self.assertEqual(classify_time_indexed(trace(),x,now_sec=10.1),"U")
    def test_U_incomplete_or_time_jump(self):
        t=trace()
        self.assertEqual(classify_time_indexed(t[:-1],person(),now_sec=10.1),"U")
        t[7]["t_sec"]+=.04
        self.assertEqual(classify_time_indexed(t,person(),now_sec=10.1),"U")
    def test_U_non_finite(self):
        t=trace()
        t[5]["x"]=float("nan")
        self.assertEqual(classify_time_indexed(t,person(),now_sec=10.1),"U")

if __name__=="__main__":
    unittest.main()
