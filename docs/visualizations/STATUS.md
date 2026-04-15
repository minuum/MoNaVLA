# Visualization Status

**시각**: 2025-12-10 09:16

## 문제

matplotlib이 현재 SSH/non-interactive 환경에서 응답하지 않습니다.

## 준비 완료

**스크립트**: `scripts/create_professional_visualizations.py`
- 논문 스타일 시각화 3개 생성
- 영어 레이블만 사용 (한글 깨짐 방지)
- 실제 데이터만 사용 (환각 없음)

## 실행 방법

### Option 1: GUI 환경에서 실행
```bash
python3 scripts/create_professional_visualizations.py
```

### Option 2: Jupyter Notebook
```bash
jupyter notebook
# 스크립트 내용을 notebook에 복사하여 실행
```

### Option 3: X11 forwarding
```bash
ssh -X user@host
python3 scripts/create_professional_visualizations.py
```

## 생성될 파일

1. `docs/visualizations/fig_loss_comparison.png`
   - 케이스별 Val Loss 비교 (막대 그래프)
   - Case 5 강조

2. `docs/visualizations/fig_case5_progress.png`
   - Case 5 학습 진행 (라인 그래프)
   - Epoch 4 최적점 표시

3. `docs/visualizations/fig_strategy_comparison.png`
   - Chunking 전략 비교
   - No Chunk vs Chunk

## 데이터 (검증됨)

- Case 1: 0.027
- Case 2: 0.048
- Case 3: 0.050
- Case 4: 0.016
- Case 5: 0.000532 (최고)
- Case 8: 0.004

---

**다음**: GUI 환경 또는 로컬에서 실행 필요
