"""AXIA D12: execute the released Notebook in a genuinely fresh kernel.

The verification scope is Python offline only. This does NOT run ROS, Gazebo,
Nav2, a certified E-Stop or physical safety systems.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient

BASE = Path(__file__).resolve().parents[1]
NB_PATH = BASE / "lesson12-risk-state-monitoring.ipynb"
OUTPUTS = BASE / "outputs"


def main():
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    source = nbformat.read(NB_PATH, as_version=4)
    assert len(source.cells) == 54
    code = [c for c in source.cells if c.cell_type == "code"]
    assert len(code) == 11
    client = NotebookClient(
        source, timeout=180, kernel_name="python3", allow_errors=False,
        resources={"metadata": {"path": str(BASE)}},
    )
    executed = client.execute()
    cells = [c for c in executed.cells if c.cell_type == "code"]
    assert [c.execution_count for c in cells] == list(range(1, 12))
    assert all(not any(o.output_type == "error" for o in c.outputs) for c in cells)
    stdout = [
        "".join(o.get("text", "") for o in c.outputs if o.output_type == "stream")
        for c in cells
    ]
    assert all("[PASS]" in s for s in stdout)
    assert sum(s.count("[PASS]") for s in stdout) == 11
    feedback = OUTPUTS / "operator_feedback.jsonl"
    records = [json.loads(x) for x in feedback.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(records) == 2
    assert {x["event_id"] for x in records} == {
        "DEMO:TST_N_00:002", "DEMO:TST_N_00:003"}
    assert all(x["control_authority"] is False for x in records)
    for name in ("d12_event_timeline.png", "d12_level_distribution.png"):
        assert (OUTPUTS / name).is_file()
    dest = OUTPUTS / "lesson12-ci-reexecuted.ipynb"
    nbformat.write(executed, dest)
    info = {
        "python": sys.version.split()[0],
        "notebook_cells": len(executed.cells),
        "code_cells": len(cells),
        "passed_code_cells": 11,
        "feedback_records": len(records),
        "execution_scope": "PYTHON_OFFLINE_ONLY",
        "ros_actual": False,
        "gazebo_actual": False,
        "certified_estop": False,
    }
    (OUTPUTS / "ci-verdict.json").write_text(
        json.dumps(info, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("D12_NOTEBOOK_FRESH_KERNEL_GREEN 11/11 code_cells")
    print("D12_NOTEBOOK_FEEDBACK_ROUNDTRIP_GREEN count=2 no_control=true")
    print("D12_NOTEBOOK_ROS_GAZEBO_NOT_RUN")
    print(json.dumps(info, ensure_ascii=False))


if __name__ == "__main__":
    main()
