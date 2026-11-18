# D02 — SW Stop·Nav2 취소·재승인 (2026-11-10, 19:00–22:00)
**이론 3시간, 필수 코딩 없음.** SW_STOP_LATCHED는 안전 인증된 물리 E-Stop이 아니다.

## 학습목표
- 하드웨어 E-Stop과 ROS Software Stop의 안전 경계를 구별한다.
- Nav2 Cancel ACK와 최종 terminal CANCELED를 구별한다.
- reset != rearm, 새 Goal 승인 후에만 주행 가능한 상태도를 완성한다.

```text
BOOT_SAFE --(1.____)--> NORMAL (Goal 없으면 disarmed)
NORMAL --(2.____)--> SW_STOP_LATCHED
SW_STOP_LATCHED --(3.____ + 4.____)--> RECOVERY_REQUIRED
RECOVERY_REQUIRED --(5.____)--> NORMAL (아직 Goal 없음)
NORMAL --(6.____)--> 새 Goal 권한 부여 가능
```

## 사례 판정
A. Cancel ACK만 확인된 상태.
B. Goal terminal 상태 SUCCEEDED가 수신된 상태.
C. reset 직후 기존 Goal이 남아 있는 상태.
D. 재부팅 후 과거 Goal ID/epoch 토큰을 재사용하는 상태.

각 사례를 허용/차단/증거 부족으로 판정하고 근거를 설명한다. **주행 명령 발행 실습 금지**.
