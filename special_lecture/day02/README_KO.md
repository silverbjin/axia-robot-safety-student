# AXIA DAY 02 — Advanced FAILED G07 MVP snapshot (0/2 actual Native L2)

**경고:** 이 브랜치는 고장 원인 분석을 위한 **미인수 실패 코드**입니다. 2026-11-21 실제 Moving Gazebo Native L2 두 번 모두 FAIL했습니다. 이 자료는 강사 WSL2 인수 또는 실제 로봇 제어 출고물이 아닙니다.

| 구분 | 소스 |
|---|---|
| 학생 실패 원본 | `a04f9a7da8d54bbd9f944d05388792cb706adf28` |
| 당시 Public Native workflow | `8e03ac0a912ca9b81bdddda70212e52e6d804389` |
| 당시 원본 CI | [#44914827138 · 0/2 FAIL](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/44914827138) |
| 현재 완성본 | Student `f7edb2d126502eeeed58ae014adadc7a2096d41b`, Public [#44965035965 · 2/2 PASS](https://github.com/silverbjin/axia-robot-safety-ci-public/actions/runs/44965035965) |
| 과제 | [ADVANCED_FAILURE_ANALYSIS_KO.md](workbook/ADVANCED_FAILURE_ANALYSIS_KO.md) |

## 오프라인 안전한 실행

```bash
python3 special_lecture/day02/scripts/verify_failed_case.py \
  --out /tmp/axia-day02-failed/check.json
python3 -m unittest discover -s special_lecture/day02/tests -p 'test_*.py' -v
```

**예상:** `L0_FAILED_CASE_SOURCE_AND_EVIDENCE_PASS`와 6개 공개 계약 테스트 OK. 이는 **실패본이 성공했다**는 뜻이 아니라, 실제 실패한 코드 및 증거와 교육 자료가 일치한다는 뜻입니다.

**분석 기본:** 수정 없이 관찰 → 첫 위반 재구성 → 가설/반증 설계 → 격리 브랜치에서 RED→GREEN → 리뷰·CI. Goal 자동 실행, TTL 완화, 실제 WSL2 반복 재시도 금지. 독립 GUI 화면 검증·FastDDS 원인·E-Stop 인증은 해당되지 않습니다. 강사 정답과 원본 개인 rosbag은 포함하지 않습니다.
