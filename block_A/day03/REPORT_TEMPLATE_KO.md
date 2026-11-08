# D03 학생 실습 제출 보고서

- 학습자/조: (작성)
- 날짜:
- 실습 Repo: `silverbjin/axia-robot-safety-student` / 기준 브랜치 `D03`
- 본인 Fork URL:
- 본인 HEAD SHA: (`git rev-parse HEAD`)
- 실행 환경: Ubuntu/Python 버전, WSL2·Docker 여부:

## 1. 학습 목표 확인

- LO1 ROS Diagnostics 구조와 `DiagnosticStatus`의 레벨 0/1/2/3 설명:
- LO2 Safe Mode 우선순위, 수동 복구 필요 이유:

## 2. 테스트 증거

| 단계 | 명령 | 실제 출력 요약 | Exit Code |
|---|---|---|---|
| Fixture inspect | `bash block_A/day03/scripts/run_lab.sh inspect` | | |
| 처음 RED | `bash block_A/day03/scripts/run_lab.sh red` | Original pytest exit 1 / | |
| 구현 후 GREEN | `bash block_A/day03/scripts/run_lab.sh green` | | |
| 상태 합성 재생 | `bash block_A/day03/scripts/run_lab.sh run` | | |
| 선택 응용 | `bash block_A/day03/scripts/run_lab.sh challenges` | | |

- GitHub Actions URL (본인 Fork 또는 PR):
- `results/d03/green.log`, `results/d03/green.xml` 제출 여부:

## 3. 판정 근거

- `NORMAL`이 실제 주행 승인과 다른 이유:
- Scan 소실과 `DiagnosticStatus.STALE`의 차이:
- Stop 후 정상 데이터가 돌아와도 자동 재주행을 막는 이유:

## 4. 검증 수준과 미검증 항목

- Python 공개 단위시험: 실제 결과 기입
- ROS 2 Jazzy 실제 `/diagnostics` 발행: PASS/FAIL/NOT_RUN (실행했다면 명령/증거)
- Gazebo 통합 실행: PASS/FAIL/NOT_RUN
- 인증 HW E-Stop: NOT_VERIFIED

## 5. 문제 해결 기록

실패 증상 → 원인 가설 → 수정 파일/라인 → 재실행 증거: