"""Mock IF/AE producer. This executable is not a ROS node."""
import argparse
import json
from pathlib import Path
from .events import parse_event


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--file', required=True, type=Path)
    parser.add_argument('--id', required=True)
    parser.add_argument('--level', required=True, choices=['OK', 'WARN', 'ERROR', 'STALE'])
    parser.add_argument('--model', default='AE', choices=['IF', 'AE'])
    parser.add_argument('--score', required=True, type=float)
    parser.add_argument('--cutoff', required=True, type=float)
    args = parser.parse_args()
    event = dict(event_id=args.id, level=args.level, model=args.model,
                 score=args.score, cutoff=args.cutoff)
    raw = json.dumps(event, ensure_ascii=False)
    try:
        parse_event(raw)
    except ValueError as exc:
        parser.error(str(exc))
    args.file.parent.mkdir(parents=True, exist_ok=True)
    with args.file.open('a', encoding='utf-8') as stream:
        stream.write(raw + '\n')
    print(f'APPEND: {raw}')


if __name__ == '__main__':
    main()
