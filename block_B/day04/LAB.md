# D04 · 11/12 19:00~22:00 — YOLO 사람 검출의 입력 계약

## 목표
1. Bounding Box와 confidence의 차이를 설명한다.
2. 높은 confidence의 사람 검출 1개를 결정하고 경계 오류를 거부한다.
3. **모델 추론 증거**와 **합성 기록 데이터 재생**을 구분한다.

## 준비 / 터미널
기존 `block_B/README_KO.md`의 Python 환경; **새 터미널 1개**로 시작, 종료 시 `deactivate`.

## 실습 120분 (이론 60분 별도)
1. (20분) `detections.csv` 4행 확인: `f001` person+chair, `f002` 저신뢰, `f003` 정상 검출.
2. (20분) 공개 테스트 `test_block_b_public.py` 실행, TODO 미구현으로 RED 확인.
3. (50분) `block_B/block_b_todo.py::select_person` 구현: `[x1,y1,x2,y2)`, 이미지 크기, confidence 0~1과 min_confidence 포함 경계, 최고 score 선택.
4. (20분) `python -m pytest -q block_B/tests/test_block_b_public.py -k 'select_person or confidence or bbox'`로 표적 회귀.
5. (10분) 모델 출력 원본과 강사 합성 CSV의 출처·라이선스 차이 기록.

## 예상 출력 / 장애 대응
- TODO 상태 `NotImplementedError: TODO_D04_SELECT_PERSON`: **정상 RED**.
- `Fixture hash mismatch`: 데이터를 수정했거나 체크섬이 달라진 것. 원본을 다시 받으세요. 체크섬 재생성으로 오류를 숨기지 마세요.
- Bounding Box가 이미지 밖이면 함수는 `ValueError`를 내야 합니다. 결과를 조용히 clipping하지 않습니다.
- 모델/영상 설치 불가: CSV 재생으로 실습을 완성합니다(실제 YOLO 검증 아님).

## 제출
TODO D04 코드, 한 개의 누락/오류 사례 분석, `pytest` 출력 캡처. 정답·Hidden Test는 제공하지 않습니다.
