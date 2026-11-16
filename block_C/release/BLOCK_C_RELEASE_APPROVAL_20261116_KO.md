# AXIA Block C 학생용 D09–D12 — 정식 교육 자료 출고 기록

**사용자 승인:** 2026-11-16, 교육용 Block C MVP 정식 출고 및 독립 학생 저장소 `main` 병합.

## 범위

- C01 재현 가능한 **합성 시계열** fixture(46 traces, 4599 rows), D09~D12 학생용 `TODO` 실습·평가표 및 교육용 ROS 진단 코드.
- 고정 학생용 인수 소스 SHA: `dff7b4a2710525a72287f5416b7b613a9d979f1e`.
- Owner WSL2: 학생 스캐폴드 계약 **5 passed**, 학생 과제 기능 `4 expected RED`(학생 구현 전), 진단 Jazzy DDS L1 8건 수신. 출고 승인 근거는 Instructor 비공개 인수 증거에 보관.
- 공개 CI 출고 계약 [Run #43725720019](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/43725720019) PASS.

**학생용 TODO는 의도적으로 미완성이다.** `4 expected RED`는 제품 실패나 강사 답안 공개가 아니다. 비공개 강사 정답·Hidden Test·모델 가중치를 이 저장소에 포함하지 않는다.

## 안전·감사

`PUBLIC_STUDENT_MANIFEST.json`의 `release_approved=false`는 **출고 이전 증거 스냅샷**이므로 변경하지 않는다. 이 파일이 사용자 승인 이후 릴리스 기록이다.

실제 로봇 제어 권한, Gazebo 실제 주행, 생산 Safety Guard TTL 및 인증 E-Stop은 **검증/승인 대상이 아니다**. `BLOCK_C_STUDENT_EDUCATION_RELEASE_APPROVED=true`.
