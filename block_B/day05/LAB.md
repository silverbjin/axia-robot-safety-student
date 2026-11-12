# D05 · 11/13 19:00~22:00 — RGB bbox와 정렬 Depth ROI

> **D05 상세 학생 실습 가이드:** [D05_STUDENT_LAB_GUIDE_KO.md](D05_STUDENT_LAB_GUIDE_KO.md) — 3시간 운영, 터미널 1개, 기존 TODO RED→GREEN, expected CSV, 실제 공개 CI 범위 및 종료 절차. 현재 문서의 기존 계약/fixture를 변경하지 않는다.

## 2026-11-13 수업 시작 링크

1. [D05 학생 데모 가이드](D05_STUDENT_DEMO_GUIDE_KO.md) — 1분 1.30m, 접근 변화율 −0.50m/s, invalid→UNKNOWN을 먼저 관찰
2. [D05 학생 실습 가이드](D05_STUDENT_LAB_GUIDE_KO.md) — 터미널/환경, RED→GREEN, 실습 코드 계약, 예상 CSV/JSON 및 종료

**강사 정답은 비공개**, 신규 ROS/Gazebo/Goal 실행은 학생 D05 Python 필수 과제에 포함되지 않는다. 아래 기존 120분 실습 개요는 보존한다.

## 목표
1. RGB bbox에서 동일 좌표계의 정렬 Depth ROI를 선택한다.
2. 0/NaN/Inf/누락·범위 외 거리값과 타임스탬프 불일치를 처리한다.
3. 관측 불가를 "안전"으로 오판하지 않는다.

## 준비 / 터미널
전날 D04 TODO를 완료한 상태, 기존 Python 가상환경 활성화. **새 터미널 불필요**.

## 실습 120분 (이론 60분 별도)
1. (15분) `depth_samples.json` 세 프레임과 `aligned_to_rgb=true`, `unit=m` 확인.
2. (15분) `test_f001_median_depth`와 `test_depth_stamp_mismatch_returns_unknown` RED 실행.
3. (55분) `measure_person_range` 구현: 정합성·ROI 경계 검증, 적어도 ROI 절반이 유효해야 중앙값 산출, 시간차 0.05s 이하.
4. (20분) 0/NaN/Inf, ragged grid, skew 경계 공개 테스트.
5. (15분) `python -m pytest -q block_B/tests` 및 `python -m block_B.run_lab --out results/d04_d05_run1`.

## 기대 데이터(합성 기록 입력에서의 결과)
`f001: 1.30m`, `f002: 미검출`, `f003: Depth 불충분`. 수치는 센서 정확도나 인증 임계값이 아닙니다.

## 장애 대응
- `LAB_BLOCKED ... TODO...`: D04/D05 중 미완성 함수 확인.
- `LAB_BLOCKED ... Output directory must not exist`: 새 출력 경로 사용.
- 시간차가 크면 `None`이 정상; 0m/Inf를 안전한 거리로 치환하지 않습니다.
- RGB-D ROS 토픽이 없더라도 이 수업은 정상 진행 가능합니다. Gazebo/ROS 검증은 별개입니다.

## 제출
TODO 두 함수, 공개 테스트 출력, `person_range.csv`, 의도된 invalid/stale 반례 설명, Git SHA 및 실제 검증 수준.
