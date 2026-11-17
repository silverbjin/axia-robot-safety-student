#!/usr/bin/env python3
"""P2 numerical evidence screening (L0). Raw Gazebo/SQLite review still needed.

Never elevates arbitrary JSON to G05/G06/G07 acceptance. To PASS, actual
Gazebo odom, source topic provenance, collision ground truth, Goal UUID and
raw evidence must be independently examined at the exact SHA.
"""
import argparse
import json
import math
from pathlib import Path

MAX_STOP_LATENCY = 1.5
MIN_DWELL = 1.0
MAX_ODOM_V = 0.03
MAX_ODOM_W = 0.05
MAX_SAMPLE_GAP = 0.30


def _number(x):
    return type(x) in (int, float) and math.isfinite(x)


def _samples(raw):
    if not isinstance(raw, list) or not raw or any(
        not isinstance(x, dict) or not all(k in x and _number(x[k])
            for k in ('t','vx','wz')) for x in raw
    ):
        return False
    times = [x['t'] for x in raw]
    return all(a < b and b-a <= MAX_SAMPLE_GAP
               for a,b in zip(times,times[1:]))


def _stop(odom, event_t):
    if not _samples(odom) or not _number(event_t):
        return False, 'ODOM_MISSING_INVALID_OR_GAPPED', None
    moving = [x for x in odom if event_t-0.5 <= x['t'] <= event_t and
              (abs(x['vx']) > MAX_ODOM_V or abs(x['wz']) > MAX_ODOM_W)]
    if not moving:
        return False, 'MOVING_AT_EVENT_NOT_PROVEN', None
    after = [x for x in odom if x['t'] >= event_t]
    if not after or after[-1]['t'] < event_t + MIN_DWELL:
        return False, 'POST_EVENT_DWELL_MISSING', None
    for i,s in enumerate(after):
        if s['t']-event_t > MAX_STOP_LATENCY:
            break
        if (abs(s['vx']) < MAX_ODOM_V and abs(s['wz']) < MAX_ODOM_W
                and after[-1]['t']-s['t'] >= MIN_DWELL
                and all(abs(x['vx']) < MAX_ODOM_V and abs(x['wz']) < MAX_ODOM_W
                        for x in after[i:])):
            return True, 'ODOM_ZERO_DWELL_NUMERICAL_CANDIDATE', round(s['t']-event_t,6)
    return False, 'ODOM_STOP_OR_DWELL_NOT_PROVEN', None


def _decision(case, reason, valid=False, **more):
    return {'gate':case,'status': 'NUMERICAL_CANDIDATE' if valid else 'BLOCKED',
            'reason':reason,'numerical_candidate':valid,
            'gate_accepted':False,'verified_gazebo_e2e':False,
            'certified_estop':False, **more}


def assess_process_fault(raw):
    if not isinstance(raw,dict) or raw.get('case') not in ('G05','G06'):
        return _decision('G05/G06','UNSUPPORTED_FAULT_CASE')
    case=raw['case']
    for field in ('source_sha','goal_uuid','gz_partition','ros_domain_id'):
        if not raw.get(field):
            return _decision(case,'PROVENANCE_MISSING_'+field)
    if raw.get('fault_target_verified') is not True or raw.get('guard_alive') is not True:
        return _decision(case,'FAULT_OR_GUARD_NOT_VERIFIED')
    if raw.get('guard_latched') is not True:
        return _decision(case,'GUARD_NOT_LATCHED')
    if raw.get('terminal_status') not in ('CANCELED','ABORTED') or raw.get('old_goal_reactivated') is not False:
        return _decision(case,'GOAL_TERMINAL_OR_NO_AUTO_RESUME_UNVERIFIED')
    event_t=raw.get('fault_mono')
    ok,reason,latency=_stop(raw.get('odom'),event_t)
    if not ok:
        return _decision(case,reason)
    cmds=raw.get('cmd_after_latch')
    if not isinstance(cmds,list) or not cmds or any(
        not isinstance(x,dict) or not _number(x.get('vx')) or not _number(x.get('wz'))
        or abs(x['vx'])>=.01 or abs(x['wz'])>=.02 for x in cmds
    ):
        return _decision(case,'NONZERO_OR_MISSING_FINAL_COMMAND')
    return _decision(case,'NUMERICAL_ONLY_RAW_REVIEW_REQUIRED',True,
                     measured_stop_latency_sec=latency)


def _assess_zone_motion(raw, success_reason, **metadata):
    """Identical physical slowdown, stop, dwell criteria for full vs demo."""
    case='G07'
    samples=raw.get('zones')
    if not isinstance(samples,list) or len(samples)<3:
        return _decision(case,'ZONE_SAMPLES_MISSING')
    phases={}
    for x in samples:
        if not isinstance(x,dict) or x.get('phase') not in ('clear','slowdown','stop'):
            return _decision(case,'UNKNOWN_ZONE_PHASE')
        if not all(k in x and _number(x[k]) for k in ('distance','vin','vout','win','wout')):
            return _decision(case,'INVALID_ZONE_SAMPLE')
        phases[x['phase']]=x
    if set(phases)!=set(('clear','slowdown','stop')):
        return _decision(case,'INCOMPLETE_ZONE_PHASES')
    clear,slow,stop=(phases[k] for k in ('clear','slowdown','stop'))
    if not (clear['distance']>0.75 and 0.4<slow['distance']<0.75
            and stop['distance']<0.4 and clear['vin']>0.03 and slow['vin']>0.03):
        return _decision(case,'DISTANCE_OR_INPUT_NOT_DEMONSTRATIVE')
    if abs(slow['vout']) > .30*abs(slow['vin']) + .01:
        return _decision(case,'SLOWDOWN_RATIO_VIOLATED')
    if abs(stop['vout']) >= .01 or abs(stop['wout']) >= .02:
        return _decision(case,'STOP_COMMAND_VIOLATED')
    if not _number(raw.get('odom_stop_dwell_sec')) or raw['odom_stop_dwell_sec']<1.0:
        return _decision(case,'ODOM_STOP_DWELL_MISSING')
    return _decision(case,success_reason,True,**metadata)


def assess_zone(raw):
    """Full acceptance screening, unchanged: native collision truth required."""
    case='G07'
    if not isinstance(raw,dict) or any(not raw.get(k) for k in
        ('source_sha','gz_partition','goal_uuid')):
        return _decision(case,'PROVENANCE_MISSING')
    if raw.get('physical_obstacle_scan') is not True or (
            raw.get('collision_ground_truth') is not True
            or type(raw.get('collision_count')) is not int
            or raw['collision_count'] != 0):
        return _decision(case,'PHYSICAL_SCAN_OR_CONTACT_UNVERIFIED')
    return _assess_zone_motion(raw,'NUMERICAL_ONLY_GAZEBO_CONTACT_RAW_REVIEW_REQUIRED')


def assess_zone_demo(raw):
    """MVP sim demonstration ONLY; no native collision proof or full gate PASS.

    Require same actual scan/CM speed/stop and odom dwell thresholds. Never
    convert unobserved contacts into a fabricated collision_count=0.
    """
    case='G07'
    if not isinstance(raw,dict) or any(not raw.get(k) for k in
        ('source_sha','gz_partition','goal_uuid')):
        return _decision(case,'PROVENANCE_MISSING')
    if (raw.get('demo_scope')!='SIMULATED_MVP_NO_CONTACT_CERTIFICATION'
            or raw.get('collision_ground_truth') is not False
            or raw.get('collision_count') is not None):
        return _decision(case,'DEMO_SCOPE_CONTACT_TRUTH_CONTRADICTION')
    if (raw.get('physical_obstacle_scan') is not True
            or raw.get('entity_preloaded_world') is not True
            or raw.get('set_pose_ack') is not True):
        return _decision(case,'DEMO_PHYSICAL_OBSTACLE_NOT_PROVEN')
    return _assess_zone_motion(
        raw,'MVP_DEMO_ONLY_CONTACT_GROUND_TRUTH_UNAVAILABLE',
        scope='MVP_DEMO_ONLY',collision_ground_truth=False)


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--case',choices=['G05','G06','G07'],required=True)
    p.add_argument('--json',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(argv)
    try:
        data=json.loads(a.json.read_text())
        result=assess_zone(data) if a.case=='G07' else assess_process_fault(data)
        if result['gate'] != a.case:
            result=_decision(a.case,'CASE_MISMATCH')
        a.output.parent.mkdir(parents=True,exist_ok=True)
        with a.output.open('x') as fp:
            json.dump(result,fp,indent=2,sort_keys=True)
            fp.write('\n')
        print(json.dumps(result,sort_keys=True))
        return 3 if result['numerical_candidate'] else 2
    except (ValueError,OSError,TypeError) as e:
        print('P2_ORACLE_BLOCKED '+type(e).__name__)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
