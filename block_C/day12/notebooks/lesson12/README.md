# AXIA Block C D12 — 이상탐지 기반 위험상태 모니터링

**3시간 교육용 Jupyter Notebook (54셀 / 코드 11셀 / 실습 6단계).**

Notebook: [lesson12-risk-state-monitoring.ipynb](lesson12-risk-state-monitoring.ipynb). 데이터는 공개 `SYNTHETIC_COURSE_FIXTURE` 합성 사건 12건이며, 실제 AE 추론·센서·ROS DDS·Gazebo 동작이 아닙니다.

## Git clone부터 실행

```bash
git clone https://github.com/silverbjin/axia-robot-safety-student.git
cd axia-robot-safety-student/block_C/day12/notebooks/lesson12
python3 --version
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
# 설치된 VS Code/Jupyter/Colab에서 Notebook을 열고 Restart & Run All
# CLI에서 독립 검증: 다음 명령은 새 Python kernel을 실제 실행
python assets/run_and_verify.py
```

Notebook을 실행하는 현재 작업 폴더는 반드시 **이 README가 있는 lesson12/**여야 합니다. `assets/event_contract.py` 및 `assets/sample_events.jsonl`을 함께 보관하며, `outputs/.gitkeep`은 출력 디렉터리를 Git clone 후에도 보존합니다. Notebook에는 고해상도 개념도 PNG가 Markdown attachment로 내장되어 있어 별도 파일 참조 없이 그림이 보입니다.

## 자료

- [학생용 단계별 실습](student_guide.md)
- [원본 제작 시점 QA 기록](QA_REPORT.md) — Linux Python 3.13.5에서 11/11 코드 셀과 1920×1080 브라우저 렌더링 검증, **현재 GitHub CI 인수 결과와는 구별**합니다.
- [requirements.txt](requirements.txt), [fresh kernel 실행기](assets/run_and_verify.py)

**안전:** 교육 WARNING ≠ SW Stop ≠ 인증된 E-Stop. 관제·운영자 피드백은 데이터 실습이며 `/cmd_vel` 또는 Goal 전송이 없습니다. 실제 ROS 2 Jazzy, Gazebo Harmonic, Windows WSL2, Colab 새 실행은 검증되지 않았다면 PASS로 쓰지 않습니다.

**배포 분리:** 강사 정답·hidden tests·체크포인트는 학생 공개 저장소에 포함하지 않습니다. 학생 TODO 패키지는 기존과 같이 독립 유지합니다.
