"""Small pure T07 acceptance gates; real ROS observations must supply inputs.

The pure numerical result is intentionally never final Owner acceptance.
"""
import math


def before_moving_fault(snapshot):
    if not isinstance(snapshot,dict): return False,'NO_SNAPSHOT'
    if snapshot.get('final_publishers') != [('axia_base_command_guard','geometry_msgs/msg/Twist')]:
        return False,'FINAL_GRAPH_NOT_PROVEN'
    if snapshot.get('goal_uuid') is None or len(str(snapshot['goal_uuid'])) != 32:
        return False,'NO_OWNED_GOAL_UUID'
    if snapshot.get('action_status') != 2:
        return False,'GOAL_NOT_EXECUTING'
    if snapshot.get('guard',{}).get('latched') is not False or snapshot['guard'].get('reason') != 'FORWARDING_MONITORED_CM':
        return False,'GUARD_NOT_FORWARDING'
    now = snapshot.get('mono')
    if type(now) not in (float,int) or not math.isfinite(now):return False,'NO_MONOTONIC_TIME'
    for source in ('scan','odom','guard','supervisor','clock','final','pre_guard'):
        at=snapshot.get(source+'_at')
        if type(at) not in (int,float) or not math.isfinite(at) or not (0<=now-at<=.5):
            return False,'STALE_'+source.upper()
    # An Action status message is published on transitions, not at 20Hz.
    # The currently executing Goal UUID is cross-checked against a fresh
    # Supervisor state and continuous actual odometry, Guard and commands.
    action_at=snapshot.get('action_at')
    if type(action_at) not in (float,int) or not math.isfinite(action_at) or not (0 <= now-action_at<=15):
        return False,'ACTION_TRANSITION_UNVERIFIED'
    if not snapshot.get('clock_advancing'):return False,'CLOCK_FROZEN'
    for name in ('odom_speed','final_speed','pre_guard_speed'):
        speed=snapshot.get(name)
        if type(speed) not in (int,float) or not math.isfinite(speed) or abs(speed)<.05:
            return False,'MOTION_NOT_PROVEN_'+name.upper()
    return True,'LIVE_P2_MOVEMENT_CANDIDATE'


def check_case_result(result):
    if not isinstance(result,dict):return False,'MISSING_CASE_RESULT'
    if result.get('gate_accepted') is not False:
        return False,'PREMATURE_GATE_ACCEPTANCE'
    if result.get('certified_estop') is not False:
        return False,'CERTIFIED_ESTOP_MISLABEL'
    if result.get('status') not in ('NUMERICAL_CANDIDATE','BLOCKED'):
        return False,'UNRECOGNIZED_VERDICT'
    return True,'RAW_OWNER_REVIEW_REQUIRED'


def zone_phase_sample(phase, observed, snap, move_at):
    """Return only a fresh physically observed G07 zone response.

    Pure L0 helper; inputs MUST come from actual ROS Observer + Gazebo move.
    It does not certify collisions, odometry, or a real-world E-Stop.
    """
    if phase not in ('clear', 'slowdown', 'stop') or not isinstance(observed, dict) or not isinstance(snap, dict):
        return None
    def number(n):
        return type(n) in (int, float) and math.isfinite(n)
    if not number(move_at):
        return None
    for key in ('scan_at', 'supervised_at', 'pre_guard_at'):
        at=snap.get(key)
        if not number(at) or at < move_at:
            return None
        now=snap.get('mono')
        if number(now) and not (0 <= now-at <= .3):
            return None
    front=observed.get('scan')
    sup=observed.get('vin')
    cm=observed.get('pre')
    if (not number(front) or not isinstance(sup,list) or not sup
            or not isinstance(cm,list) or not cm):
        return None
    vin= sup[-1];out= cm[-1]
    if not isinstance(vin,dict) or not isinstance(out,dict):
        return None
    if any(not number(x.get(key)) for x,key in (
        (vin,'t'),(vin,'vx'),(vin,'wz'),(out,'t'),(out,'vx'),(out,'wz')
    )):
        return None
    if vin['t'] < move_at or out['t'] < move_at or vin['vx'] <= .03:
        return None
    if phase == 'clear' and not (front > .75 and out['vx'] > .03):
        return None
    if phase == 'slowdown' and not (.4 < front < .75
                                    and 0.0 < out['vx'] <= .30 * vin['vx'] + .01):
        return None
    if phase == 'stop' and not (front < .4
                                and abs(out['vx']) < .01
                                and abs(out['wz']) < .02):
        return None
    return {'phase':phase,'distance':front,
            'vin':vin['vx'],'vout':out['vx'],
            'win':vin['wz'],'wout':out['wz']}


def recent_stop_dwell(odom):
    """Consecutive, gap-bounded odom zero dwell at the latest sample."""
    if not isinstance(odom,list) or len(odom)<2:
        return 0.0
    previous=None
    earliest=None
    latest=None
    for row in reversed(odom):
        if not isinstance(row,dict) or any(
            type(row.get(k)) not in (int,float) or not math.isfinite(row[k])
            for k in ('t','vx','wz')
        ):
            return 0.0
        if previous is not None and not (0 < previous-row['t'] <= .3):
            return 0.0
        if abs(row['vx']) >= .03 or abs(row['wz']) >= .05:
            break
        if latest is None:
            latest=row['t']
        earliest=row['t']
        previous=row['t']
    return max(0.0, latest-earliest) if latest is not None and earliest is not None else 0.0


def before_moving_g07_slowdown(snapshot):
    """Actual movement in *G07 MVP slow zone*; not the strict G05/G06 gate.

    The verified Owner trace QrDCwq8W shows supervised 0.130 m/s and
    official Collision Monitor output and odom max 0.039 m/s (30%).
    The strict fault admission's >=0.05 m/s on ALL signals is impossible
    under correct 30% CM slowdown. This helper checks real, fresh,
    positive *reduced* motion without changing any fault or formal gate.
    """
    if not isinstance(snapshot, dict):
        return False, 'NO_SNAPSHOT'
    if snapshot.get('final_publishers') != [
        ('axia_base_command_guard', 'geometry_msgs/msg/Twist')
    ]:
        return False, 'FINAL_GRAPH_NOT_PROVEN'
    goal = snapshot.get('goal_uuid')
    if not isinstance(goal, str) or len(goal) != 32:
        return False, 'NO_OWNED_GOAL_UUID'
    if snapshot.get('action_status') != 2:
        return False, 'GOAL_NOT_EXECUTING'
    guard = snapshot.get('guard')
    if not isinstance(guard, dict) or guard.get('latched') is not False or (
        guard.get('reason') != 'FORWARDING_MONITORED_CM'
    ):
        return False, 'GUARD_NOT_FORWARDING'
    now = snapshot.get('mono')
    if type(now) not in (int, float) or not math.isfinite(now):
        return False, 'NO_MONOTONIC_TIME'
    for src in ('scan', 'odom', 'guard', 'supervisor', 'clock',
                'final', 'pre_guard', 'supervised'):
        at = snapshot.get(src + '_at')
        if type(at) not in (int, float) or not math.isfinite(at) or not (
            0 <= now - at <= .5
        ):
            return False, 'STALE_' + src.upper()
    action_at = snapshot.get('action_at')
    if type(action_at) not in (int, float) or not math.isfinite(action_at) or not (
        0 <= now - action_at <= 15
    ):
        return False, 'ACTION_TRANSITION_UNVERIFIED'
    if not snapshot.get('clock_advancing'):
        return False, 'CLOCK_FROZEN'

    def measured(name):
        value = snapshot.get(name)
        if type(value) not in (int, float) or not math.isfinite(value):
            return None
        return value

    vin = measured('supervised_speed')
    pre = measured('pre_guard_speed')
    final = measured('final_speed')
    odom = measured('odom_speed')
    if vin is None or vin <= .06:
        return False, 'SUPERVISED_MOTION_NOT_PROVEN'
    if pre is None or pre <= .01:
        return False, 'CM_SLOWDOWN_MOTION_NOT_PROVEN'
    if final is None or final <= .01:
        return False, 'FINAL_FORWARD_MOTION_NOT_PROVEN'
    if odom is None or odom <= .01:
        return False, 'ACTUAL_ODOM_MOTION_NOT_PROVEN'
    if pre > .35 * vin or final > .35 * vin:
        return False, 'CM_REDUCTION_NOT_PROVEN'
    return True, 'LIVE_G07_SLOWDOWN_MOTION_CANDIDATE'
