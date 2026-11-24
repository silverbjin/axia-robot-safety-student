"""Small, ROS-independent JSONL input contract for the D12 teaching lab."""
import json
import math
from pathlib import Path

LEVELS = {'OK': 0, 'WARN': 1, 'ERROR': 2, 'STALE': 3}


def parse_event(raw):
    event = json.loads(raw)
    if not isinstance(event, dict):
        raise ValueError('event must be an object')
    if not isinstance(event.get('event_id'), str) or not event['event_id'].strip():
        raise ValueError('event_id must be a nonempty string')
    if not isinstance(event.get('level'), str) or event['level'] not in LEVELS:
        raise ValueError('level must be OK, WARN, ERROR or STALE')
    for key in ('score', 'cutoff'):
        if key in event:
            value = event[key]
            if type(value) not in (int, float):
                raise ValueError(f'{key} must be a finite number')
            try:
                finite = math.isfinite(value)
            except OverflowError:
                finite = False
            if not finite:
                raise ValueError(f'{key} must be a finite number')
    for key in ('model', 'message'):
        if key in event and not isinstance(event[key], str):
            raise ValueError(f'{key} must be a string')
    return event


def diagnostic_fields(event):
    return {
        'level': LEVELS[event['level']],
        'name': 'axia/education/' + event.get('model', 'detector'),
        'message': event.get('message', event['level']),
        'hardware_id': 'SYNTHETIC_COURSE_FIXTURE',
        'values': {key: str(event[key]) for key in
                   ('event_id', 'level', 'model', 'score', 'cutoff') if key in event},
    }


class JsonlReader:
    """Read newly appended complete lines; do not consume a partial last line.

    Lab contract: one append-only file, one writer, no rotation/truncation.
    Offset is in memory only; a restart replays the file from the beginning.
    """
    def __init__(self, path):
        self.path = Path(path)
        self.offset = 0

    def poll(self, limit=100):
        lines = []
        try:
            stream = self.path.open('rb')
        except FileNotFoundError:
            return lines
        with stream:
            stream.seek(self.offset)
            for _ in range(limit):
                line = stream.readline()
                if not line.endswith(b'\n'):
                    break
                self.offset = stream.tell()
                try:
                    lines.append(line.decode('utf-8').rstrip('\r\n'))
                except UnicodeDecodeError:
                    lines.append('{invalid UTF-8}')  # report as invalid JSON
        return lines
