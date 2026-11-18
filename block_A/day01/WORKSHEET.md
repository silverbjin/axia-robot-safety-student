# D01 — Fail-Safe 위험분석 (2026-11-09, 19:00–22:00)
**이론 3시간, 필수 코딩 없음.** TurtleBot3 Waffle/Jazzy/Harmonic 설계 사례를 읽고 토의한다.

## 학습목표
- Hazard/Fault/Failure와 fail-safe를 구분한다.
- /scan → Supervisor → Collision Monitor → /cmd_vel의 신뢰 경계를 설명한다.
- 0 Twist, Nav2 Goal cancel, 실제 odom 정지, 인증 하드웨어 E-Stop을 구별한다.

## 분석 카드
1. /safety/scan이 사라졌으나 Nav2는 기존 경로를 보유한다.
2. /clock이 멈추지만 host monotonic clock은 진행한다.
3. Supervisor 프로세스가 종료되어 최종 Twist 0이 더 이상 발행되지 않는다.
4. /cmd_vel에 의도치 않은 두 번째 발행자가 나타난다.

| hazard_id | 고장 원인 | 심각도와 이유 | 신뢰 경계 | 검출 증거 | 요구 안전상태 | 미검증 가정 |
|---|---|---|---|---|---|---|
| H-01 | | | | | | |
| H-02 | | | | | | |

**제출:** 위험분석 2개, 위험 우선순위 토의, 안전 증거 제안. 임계값은 교육용 제안이지 인증값이 아니다.
