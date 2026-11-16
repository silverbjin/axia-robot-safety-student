"""Student distribution contract: no completed teacher code in public scaffold."""
import importlib.util
import json
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
MAPPING={
    'day09': ('student_eda_todo.py','make_features'),
    'day10': ('student_if_todo.py','fit_evaluate_if'),
    'day11': ('student_ae_todo.py','fit_evaluate_ae'),
    'day12': ('student_event_todo.py','make_event_jsonl'),
}


def test_public_course_has_four_days_and_safe_exercises():
    for day,(filename,name) in MAPPING.items():
        f=ROOT/day/filename
        assert f.is_file()
        content=f.read_text(encoding='utf-8')
        assert 'TODO' in content and 'NotImplementedError' in content
        assert 'from eda_pipeline import' not in content
        assert 'IsolationForest(' not in content
        assert 'torch.save(' not in content
        assert 'create_publisher(' not in content and 'send_goal_async(' not in content


def test_student_todo_contract_intentional_red_not_hidden_solution():
    for day,(filename,name) in MAPPING.items():
        f=ROOT/day/filename
        spec=importlib.util.spec_from_file_location(f'{day}_todo',f)
        mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        function=getattr(mod,name)
        with pytest.raises(NotImplementedError,match='TODO'):
            function(Path('/dummy/fixture'),Path('/dummy/result'))


def test_student_public_readme_and_rubric():
    readme=(ROOT/'README_KO.md').read_text()
    rubric=(ROOT/'LEARNER_RUBRIC_KO.md').read_text()
    assert 'EXPECTED_RED' in readme
    assert 'SYNTHETIC_COURSE_FIXTURE' in readme
    assert all(f'D{num}' in rubric for num in ('09','10','11','12'))
    assert '100' in rubric


def test_student_does_not_leak_private_assets():
    for p in ROOT.rglob('*'):
        if not p.is_file():continue
        name=str(p.relative_to(ROOT)).lower()
        assert not any(k in name for k in ('hidden_tests','teacher_solution','instructor/','ae_checkpoint.pt','private_key','.env'))
    assert (ROOT/'fixtures'/'SHA256SUMS').is_file()


def test_student_release_candidate_without_owner_signoff():
    if (ROOT/'release'/'PUBLIC_STUDENT_MANIFEST.json').exists():
        m=json.loads((ROOT/'release'/'PUBLIC_STUDENT_MANIFEST.json').read_text())
        assert m['release_approved'] is False
        assert m['owner_wsl2_verified'] is False
        assert m['data_source']=='SYNTHETIC_COURSE_FIXTURE'
