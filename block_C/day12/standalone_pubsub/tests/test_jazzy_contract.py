import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'src' / 'axia_json_diagnostics' / 'axia_json_diagnostics'


def test_char_wire_encoding_and_decoding():
    # Exercise actual functions with a strict stand-in, not ROS middleware.
    class Status:
        @property
        def level(self):
            return self._level

        @level.setter
        def level(self, value):
            assert type(value) is bytes and len(value) == 1
            self._level = value

    class Array:
        def __init__(self):
            self.header = type('Header', (), {})()

    from axia_json_diagnostics.events import diagnostic_fields
    ns = dict(DiagnosticStatus=Status, DiagnosticArray=Array,
              KeyValue=lambda **kw: type('KV', (), kw)(), diagnostic_fields=diagnostic_fields)
    for name, target in [('diagnostic_publisher.py', 'to_message'), ('diagnostic_subscriber.py', 'level_number')]:
        tree = ast.parse((ROOT / name).read_text())
        funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == target]
        exec(compile(ast.Module(body=funcs, type_ignores=[]), name, 'exec'), ns)
    for i, label in enumerate(('OK', 'WARN', 'ERROR', 'STALE')):
        msg = ns['to_message']({'event_id': 'E1', 'level': label}, None)
        assert msg.status[0].level == bytes([i])
        assert ns['level_number'](msg.status[0].level) == i
