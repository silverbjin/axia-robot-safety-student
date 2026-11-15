"""Student TDD task tests — RED until learners implement all four TODOs.
Do not include these in ordinary CI acceptance; CI checks expected RED separately.
"""
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def task(day,filename,func):
    path=ROOT/day/filename
    spec=importlib.util.spec_from_file_location('student_task_'+day,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module,func)


def test_d09_should_build_trace_safe_features(tmp_path):
    assert isinstance(task('day09','student_eda_todo.py','make_features')(ROOT/'fixtures',tmp_path),dict)


def test_d10_should_evaluate_isolation_forest(tmp_path):
    assert isinstance(task('day10','student_if_todo.py','fit_evaluate_if')(tmp_path,tmp_path/'if'),dict)


def test_d11_should_evaluate_cpu_autoencoder(tmp_path):
    assert isinstance(task('day11','student_ae_todo.py','fit_evaluate_ae')(tmp_path,tmp_path/'ae'),dict)


def test_d12_should_write_jsonl_timeline(tmp_path):
    assert isinstance(task('day12','student_event_todo.py','make_event_jsonl')(tmp_path/'scores.csv',tmp_path/'events'),dict)
