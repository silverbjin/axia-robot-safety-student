"""D07-H01 *pure* native Gazebo Contacts evidence contract, never ROS Goal.

The TouchPlugin /touched is a one-shot Boolean, not a complete stream of
gz.msgs.Contacts. This oracle alone cannot attest physical sensor operation:
runtime must supply independently captured topic/type/collision and a
stationary positive-control event before H01 motion.
"""
from __future__ import annotations
import math

NATIVE_CONTACT_TOPIC=(
    "/world/default/model/axia_p2_g07_obstacle/"
    "link/obstacle_link/sensor/axia_contact/contact")


def _valid_time(value):
    return type(value) in (int,float) and math.isfinite(value) and value>=0


def assess_contact_source(topic: str, message_type: str,
                          positive_control_proven: bool,
                          capture_window: dict,
                          event_ledger: list)->dict:
    """Classify actual externally captured Contact events; NO goal authority."""
    fail={"status":"CONTACT_PROVENANCE_HOLD_NO_GOAL",
          "reason":"NATIVE_CONTACT_PROVENANCE_OR_MONITOR_NOT_PROVEN",
          "contact_ground_truth_ready":False,"robot_obstacle_contact_count":None,
          "source_verified":False,"positive_control_verified":False,
          "monitor_window_covered":False,
          "motion_admitted":False,"goal_sent":False,
          "certified_estop":False}
    if (topic!=NATIVE_CONTACT_TOPIC or message_type!="gz.msgs.Contacts"
        or positive_control_proven is not True
        or not isinstance(capture_window,dict)
        or not isinstance(event_ledger,(list,tuple))):
        return fail
    w=capture_window
    keys=("start","end","subscribed_at","alive_until")
    if (any(not _valid_time(w.get(k)) for k in keys)
        or not(w["subscribed_at"]<=w["start"]<w["end"]<=w["alive_until"])
        or any(w.get(k) is not True for k in
               ("stream_source_verified","no_restart","clock_advancing"))):
        return {**fail,"reason":"CONTACT_CAPTURE_WINDOW_NOT_CONTINUOUS"}
    calibrations=0
    contact_count=0
    for item in event_ledger:
        if not isinstance(item,dict) or item.get("topic")!=topic:
            return {**fail,"reason":"CONTACT_EVENT_PROVENANCE_MISMATCH"}
        tm=item.get("received_at")
        count=item.get("contacts")
        a=item.get("collision1")
        b=item.get("collision2")
        phase=item.get("phase")
        if (not _valid_time(tm) or type(count) is not int or count<0
            or not isinstance(a,str) or not isinstance(b,str)
            or phase not in ("calibration","motion")):
            return {**fail,"reason":"INVALID_CONTACT_NATIVE_EVENT"}
        if phase=="calibration":
            if (tm>=w["start"] or count<=0 or
                not ("axia_p2_g07_obstacle" in a or
                     "axia_p2_g07_obstacle" in b)):
                continue
            calibrations+=1
        else:
            if not w["start"]<=tm<=w["end"]:
                return {**fail,"reason":"MOTION_CONTACT_OUTSIDE_CAPTURE_WINDOW"}
            if count>0:
                contact_count+=count
    if calibrations==0:
        return {**fail,"reason":"CONTACT_POSITIVE_CONTROL_NOT_OBSERVED"}
    validated={**fail,"source_verified":True,
               "positive_control_verified":True,
               "monitor_window_covered":True,
               "robot_obstacle_contact_count":contact_count}
    if contact_count>0:
        return {**validated,"status":"CONTACT_POSITIVE_BLOCKED_NO_GOAL",
                "reason":"ACTUAL_CONTACT_EVENT_DURING_H01"}
    return {**validated,"status":"CONTACT_WINDOW_VALIDATED_NO_GOAL",
            "reason":"CALIBRATED_NATIVE_GZ_CONTACT_AND_CONTINUOUS_MONITOR_WINDOW",
            "contact_ground_truth_ready":True}


def discover_contact_advertisement(topic_listing: str, topic_info: str)->dict:
    """Validate native Harmonic topic *metadata*, never collision-free health.

    gz-sim may ignore <sensor><topic> and expose the fully scoped contact
    sensor path. Even a real gz.msgs.Contacts publisher is not a positive
    collision calibration and cannot prove zero physical contacts.
    """
    fail={"status":"NATIVE_CONTACT_METADATA_HOLD_NO_GOAL",
          "reason":"NATIVE_TOPIC_OR_TYPE_NOT_ADVERTISED",
          "native_topic_discovered":False,"topic_type_proven":False,
          "source_verified":False,"sensor_health_proven":False,
          "contact_ground_truth_ready":False,"positive_control_proven":False,
          "motion_admitted":False,"goal_sent":False,"certified_estop":False}
    if not isinstance(topic_listing,str) or not isinstance(topic_info,str):
        return fail
    names=[t.strip() for t in topic_listing.splitlines()]
    if NATIVE_CONTACT_TOPIC not in names:
        return fail
    if ("gz.msgs.Contacts" not in topic_info
        or "Publishers" not in topic_info
        or "Publishers: 0" in topic_info):
        return {**fail,"native_topic_discovered":True}
    return {**fail,"status":"NATIVE_CONTACT_TYPE_ADVERTISED_ONLY_NO_GOAL",
            "reason":"REAL_SENSOR_CALIBRATION_AND_WINDOW_STILL_REQUIRED",
            "native_topic_discovered":True,"topic_type_proven":True}


def parse_positive_contact_calibration(topic_listing: str, topic_info: str,
                                       raw_echo: str)->dict:
    """Require an actual Gazebo collision1/collision2 pair in native echo.

    One real stationary positive-control sensor event proves only calibration
    at that instant; a later moving-Goal window still needs uninterrupted
    capture, negative Contact evidence, scan/odom and safety TTL.
    """
    import re
    advertised=discover_contact_advertisement(topic_listing,topic_info)
    fail={"status":"CONTACT_POSITIVE_CONTROL_HOLD_NO_GOAL",
          "reason":"NATIVE_POSITIVE_COLLISION_PAIR_MISSING",
          "topic_type_proven":advertised["topic_type_proven"],
          "positive_control_observed":False,"calibration_event_count":0,
          "contact_ground_truth_ready":False,"sensor_health_proven":False,
          "motion_admitted":False,"goal_sent":False,"certified_estop":False}
    if not advertised["topic_type_proven"] or not isinstance(raw_echo,str):
        return fail
    count=0
    for block in re.split(r"(?m)^\s*contact\s*\{",raw_echo)[1:]:
        # Gazebo Harmonic protobuf TEXT uses nested collision objects:
        # collision1 { id: 44 name: "..." }, not always collision1:"...".
        # Match each collision field independently inside this contact block.
        def collision_name(label):
            legacy=re.search(r'\b'+label+r'\s*:\s*"([^"]+)"',block)
            if legacy:
                return legacy.group(1)
            nested=re.search(r'\b'+label+r'\s*\{([^{}]*)\}',block,re.S)
            if not nested:
                return None
            value=re.search(r'\bname\s*:\s*"([^"]+)"',nested.group(1))
            return value.group(1) if value else None
        names=(collision_name("collision1"),collision_name("collision2"))
        if any(x is None for x in names):
            continue
        if (any("axia_p2_g07_obstacle" in x for x in names)
            and any("turtlebot3_waffle" in x for x in names)):
            count+=1
    if count==0:
        return fail
    return {**fail,
            "status":"CONTACT_STATIONARY_POSITIVE_CONTROL_OBSERVED_NO_GOAL",
            "reason":"POSITIVE_SENSOR_ONLY_MOTION_WINDOW_UNVERIFIED",
            "positive_control_observed":True,"calibration_event_count":count,
            "sensor_health_proven":True}
