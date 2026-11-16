# Block C 학생 평가표 — 총 100점

| 과목 | 평가 | 점수 | 증거 |
|---|---|---:|---|
| D09 | 스키마·해시·출처 | 10 | SHA256 / 3 split |
| D09 | trace 경계 / UNKNOWN / EDA | 15 | features.csv / plot / report |
| D10 | train-only / valid threshold | 15 | if_metrics.json |
| D10 | 혼동행렬 / FP·FN | 10 | trace ID·precision·recall·FPR·FNR |
| D11 | CPU AE, scaler, seed/checkpoint | 15 | weights SHA/epoch/loss |
| D11 | IF 비교와 오탐 분석 | 10 | model_comparison.md |
| D12 | JSONL schema/quality/stale | 15 | anomaly_events.jsonl / timeline |
| D12 | ROS 상태 및 검증 수준 | 10 | Jazzy L1 evidence 또는 JSONL fallback |

Test로 scaler/threshold를 재학습하거나 INVALID를 정상으로 분류하면 해당 점수는 0점. cmd_vel·Goal 제어권 연결 또는 인증 E-Stop 표기는 전체 D12 인수 보류입니다. 제출시 Git SHA, 명령, 실제 출력, 미검증 범위를 구분합니다.
