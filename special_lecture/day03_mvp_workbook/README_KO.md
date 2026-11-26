# DAY 3 — 실제 G07 완성 MVP 기반 AI Native 디버깅 워크북 (기획 후보)

본 디렉터리는 **완성 워크북이 아니라 제작 기획·프롬프트 초안**입니다.
DAY 2에서 이미 공개된 완성 MVP 코드 전체를 그대로 활용하고, 개발 → 통합 → 인수 오류를 해결하는 프롬프트 방법을 학습합니다.

- [실제 공개 MVP 소스 및 빌드](../day02_mvp_sources/README_KO.md)
- [DAY 3 상세 제작 계획](DAY3_MVP_WORKBOOK_PLAN_KO.md)
- [DAY 3 완성형 마스터 프롬프트 초안](MASTER_PROMPT_DAY3_MVP_KO.txt)
- [공개 원본 출처 검증기](../day02_mvp_sources/scripts/verify_dual_source.py)
- [DAY 3 L0 계획/원본 검증](test_workbook_contract.py)

```bash
# 공개 소스 release에서 원본 서명 확인 (새 Goal/Gazebo 없음)
python3 special_lecture/day02_mvp_sources/scripts/verify_dual_source.py
# 교재 기획 구성 L0 테스트
python3 -m unittest discover -s special_lecture/day03_mvp_workbook -p 'test_*.py' -v
```

**원본 기준 고정**: `release/day02-dual-mvp-full-source-build-20261126` @ `96be43164fab3f15025edd59279bcfd50b6232cd`.

**공개 범위**: 기존 공개된 실제 MVP 소스, 학습 계획, 공개 진단 테스트만. 강사 정답 및 hidden tests는 비공개. `main` 병합에는 사용자 별도 승인이 필요합니다.
**검증 경계**: 문서·소스 SHA L0 PASS는 실제 Gazebo L2/Owner WSL2 L3의 신규 PASS가 아닙니다. 현재 신규 L2/L3는 `NOT_RUN`입니다.
