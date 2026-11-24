import json
import pytest
from axia_json_diagnostics.events import JsonlReader, parse_event, diagnostic_fields


def event(**kwargs):
    return dict(event_id='E001', level='WARN', model='AE', score=0.8, cutoff=0.5, **kwargs)


def test_mapping():
    fields = diagnostic_fields(parse_event(json.dumps(event())))
    assert fields['level'] == 1
    assert fields['values']['event_id'] == 'E001'
    assert fields['values']['score'] == '0.8'


@pytest.mark.parametrize('level,expected', [('OK', 0), ('WARN', 1), ('ERROR', 2), ('STALE', 3)])
def test_levels(level, expected):
    assert diagnostic_fields(parse_event(json.dumps(dict(event(), level=level))))['level'] == expected


@pytest.mark.parametrize('raw', ['{', '[]', '{}', '{"event_id":"X","level":"BAD"}', '{"event_id":"X","level":"OK","score":NaN}', '{"event_id":"X","level":"OK","score":true}'])
def test_invalid(raw):
    with pytest.raises(ValueError):
        parse_event(raw)


def test_append_partial_and_invalid(tmp_path):
    p = tmp_path / 'events.jsonl'
    reader = JsonlReader(p)
    assert reader.poll() == []
    raw = json.dumps(event())
    p.write_text(raw[:10])
    assert reader.poll() == []
    with p.open('a') as f:
        f.write(raw[10:] + '\n{bad}\n')
        f.write(json.dumps(dict(event(), event_id='E002')) + '\n')
    lines = reader.poll()
    assert len(lines) == 3
    assert parse_event(lines[0])['event_id'] == 'E001'
    with pytest.raises(ValueError):
        parse_event(lines[1])
    assert parse_event(lines[2])['event_id'] == 'E002'
    assert reader.poll() == []


def test_bounded_batch(tmp_path):
    p = tmp_path / 'events.jsonl'
    p.write_text('a\nb\nc\n')
    reader = JsonlReader(p)
    assert reader.poll(2) == ['a', 'b']
    assert reader.poll(2) == ['c']
