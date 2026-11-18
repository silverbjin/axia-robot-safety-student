"""Task03 formal public Gazebo release evidence, ROS-free negative test.
Actual ROS/Gazebo/ECM only runs in public Actions; no mock can pass L2.
"""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from p2_g07_task03_contract import (REQ_TOPICS, audit_bag_14,
    audit_goal_terminal, audit_guard_internal_cm_age, audit_native_ecm_contact)


class FormalEvidenceContract(unittest.TestCase):
    def create_bag(self, root, *, absent=None, empty=None):
        bag=root/"rosbag2"
        bag.mkdir()
        (bag/"metadata.yaml").write_text("rosbag2_bagfile_information:\n  storage_identifier: sqlite3\n")
        con=sqlite3.connect(str(bag/"proof.db3"))
        con.execute("create table topics(id integer primary key,name text,type text)")
        con.execute("create table messages(id integer primary key,topic_id integer,timestamp integer,data blob)")
        for idx, topic in enumerate(REQ_TOPICS,1):
            if topic==absent: continue
            con.execute("insert into topics values(?,?,?)",(idx,topic,"std_msgs/msg/String"))
            if topic!=empty:
                con.execute("insert into messages(topic_id,timestamp,data) values(?,?,?)",
                    (idx,1_000_000_000+idx,b"real-case-fixture"))
        con.commit()
        con.close()
        return bag

    def test_bag_14_topic_counts_and_sha256_and_negative(self):
        with tempfile.TemporaryDirectory() as tmp:
            bag=self.create_bag(Path(tmp))
            result=audit_bag_14(bag)
            self.assertEqual(result["status"],"ACTUAL_SQLITE_14_TOPIC_CUSTODY_PASS")
            self.assertEqual(len(result["topic_message_counts"]),14)
            self.assertEqual(len(result["sqlite_sha256"]),64)
            self.assertGreater(result["total_messages"],0)
        for keyword in ("absent","empty"):
            with self.subTest(keyword=keyword),tempfile.TemporaryDirectory() as tmp:
                name=REQ_TOPICS[7]
                bag=self.create_bag(Path(tmp),**{keyword:name})
                self.assertNotEqual(audit_bag_14(bag)["status"],
                                    "ACTUAL_SQLITE_14_TOPIC_CUSTODY_PASS")

    def test_exact_uuid_terminal_cancel_only(self):
        uuid="f"*32
        ok=audit_goal_terminal(uuid,0,[uuid],5,False)
        self.assertEqual(ok["status"],"EXACT_GOAL_UUID_TERMINAL_CANCELED_PASS")
        for status,rc,ids,latched in [(2,0,[uuid],False),(5,1,[uuid],False),
                                        (5,0,["e"*32],False),(5,0,[uuid],True)]:
            with self.subTest(status=status,rc=rc,ids=ids,latched=latched):
                self.assertNotEqual(audit_goal_terminal(uuid,rc,ids,status,latched)["status"],
                                    "EXACT_GOAL_UUID_TERMINAL_CANCELED_PASS")

    def test_guard_cm_internal_age_in_same_motion_window(self):
        events=[{"kind":"owner_goal_published","t":1.0}]
        events.extend({"kind":"guard","t":1.01+i*.05,
             "data":{"latched":False,"cm_age_sec":.049,"supervisor_age_sec":.045}}
             for i in range(20))
        v=audit_guard_internal_cm_age(events,goal_start=1.0,window_end=2.01)
        self.assertEqual(v["status"],"GUARD_NATIVE_CM_AGE_TTL150_PASS")
        events[9]["data"]["cm_age_sec"]=.151
        self.assertNotEqual(audit_guard_internal_cm_age(events,goal_start=1.0,window_end=2.01)["status"],
                            "GUARD_NATIVE_CM_AGE_TTL150_PASS")
        del events[9]["data"]["cm_age_sec"]
        self.assertNotEqual(audit_guard_internal_cm_age(events,goal_start=1.0,window_end=2.01)["status"],
                            "GUARD_NATIVE_CM_AGE_TTL150_PASS")

    def test_native_ecm_contact_one_positive_control_and_motion_zero(self):
        positive={"source_sha":"same_witness_binary",
                  "sensor_found":True,"observed_iterations":100,
                  "missing_iterations":0,"positive_contacts":5,"report_complete":True,
                  "first_sim_ns":0,"last_sim_ns":10_000_000_000}
        motion={**positive,"positive_contacts":0,"first_sim_ns":0,"last_sim_ns":20_000_000_000}
        v=audit_native_ecm_contact(positive,motion,goal_sim_ns=5_000_000_000,
                                   stop_sim_ns=15_000_000_000)
        self.assertEqual(v["status"],"S02_NATIVE_ECM_GOAL_WINDOW_CONTACT_ZERO_PASS")
        motion["missing_iterations"]=1
        self.assertNotEqual(audit_native_ecm_contact(positive,motion,goal_sim_ns=5_000_000_000,
                                 stop_sim_ns=15_000_000_000)["status"],
                            "S02_NATIVE_ECM_GOAL_WINDOW_CONTACT_ZERO_PASS")
        motion["missing_iterations"]=0
        motion["last_sim_ns"]=6_000_000_000
        self.assertNotEqual(audit_native_ecm_contact(positive,motion,goal_sim_ns=5_000_000_000,
                                 stop_sim_ns=15_000_000_000)["status"],
                            "S02_NATIVE_ECM_GOAL_WINDOW_CONTACT_ZERO_PASS")


if __name__=="__main__":
    unittest.main()
