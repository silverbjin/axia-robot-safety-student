# AXIA Robot Safety — 학생용 실습 후보 (Block A + Block B)

**상태: G12 통합 검토 브랜치. 정식 배포·라이선스 인수 미승인.** 기존 학생 `main`은 변경하지 않습니다.

## 학생용 실습
- [D03 진단·Safe Mode TODO](docs/D03/README_KO.md) — `block_A/day03/p1_adapter_todo.py` 및 `todo_safety.py`의 학생 구현 과제. 기존 D03 공개 시험은 **의도한 초기 RED**를 확인합니다.
- [Block B/D04~D07](block_B/README_KO.md) — 사람 검출, RGB-D 거리, 안전 버블, 경로 기반 실습. 기존 Block B 자료·워크플로를 그대로 유지합니다.
- [D03 환경 준비](docs/D03/02_WINDOWS_WSL_NATIVE_KO.md), [버전 잠금 범위](VERSION_LOCK.md), [권리·공지 상태](LICENSES.md), [외부 자산 원장](THIRD_PARTY_ATTRIBUTION.md).

## D03 최소 실행 (Python 합성 데이터 전용)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install 'pytest==8.3.5'
bash block_A/day03/scripts/run_lab.sh preflight
bash block_A/day03/scripts/run_lab.sh inspect
bash block_A/day03/scripts/run_lab.sh red
```

**주의:** 학생이 TODO를 구현하기 전 RED는 기대 결과입니다. `green`은 학생이 직접 구현한 뒤 실행합니다. 공개 저장소에는 강사 정답·hidden tests를 포함하지 않습니다.

ROS 2 Jazzy·Gazebo Harmonic 시각 실습은 선택이며, D03 합성 시험이나 D04~D07 Python TODO의 통과를 실제 로봇 안전 인증·자동 주행 승인으로 해석하지 않습니다. SW Stop은 인증된 하드웨어 E-Stop이 아닙니다.

## 공개 배포 보류

이 브랜치는 기존 학생용 D03(고정 소스 `4f74916a09f726ffd6978926adfc83ee9f528298`)의 33개 **기존 파일 객체**와 기존 Block B 학생 `main` (`d2f16eaf5b5fb60ad9b8009fe1532fa75363e971`)를 통합한 검토용입니다. `main` 병합·태그·배포 전에는 라이선스 및 모든 배포 자산의 권리 검토, 강사 승인, 최신 학생 인수 테스트가 필요합니다.
