# Visualizations

**작성**: 2025-12-10  
**목적**: 케이스별 시각화 자료 정리

---

## 📁 구조

```
docs/visualizations/
├── case1/           # Case 1: Baseline (Chunk=10)
├── case2/           # Case 2: Xavier Init (Chunk=10)
├── case3/           # Case 3: Aug+Abs (Chunk=10)
├── case4/           # Case 4: Right Only (Chunk=10)
├── case5/           # Case 5: No Chunk ⭐ (BEST)
├── case8/           # Case 8: No Chunk + Abs
├── case9/           # Case 9: No Chunk + Aug+Abs
└── summary/         # 전체 비교 시각화
```

---

## 📊 케이스별 시각화

### Case 1: Baseline (Chunk=10)
**파일**: `case1/summary.png`
- Val Loss: 0.027
- Training curve
- Config summary

### Case 2: Xavier Init (Chunk=10)
**파일**: `case2/summary.png`
- Val Loss: 0.048
- Training curve
- Config summary

### Case 3: Aug+Abs (Chunk=10)
**파일**: `case3/summary.png`
- Val Loss: 0.050
- Training curve
- Config summary

### Case 4: Right Only (Chunk=10)
**파일**: `case4/summary.png`
- Val Loss: 0.016
- Training curve
- Config summary

### Case 5: No Chunk ⭐ (BEST)
**파일**: `case5/summary.png`
- **Val Loss: 0.000532** 🏆
- Training curve
- Config summary

### Case 8: No Chunk + Abs
**파일**: `case8/summary.png`
- Val Loss: 0.00243
- Training curve
- Config summary

### Case 9: No Chunk + Aug+Abs
**파일**: `case9/summary.png`
- Val Loss: 0.004
- Training curve
- Config summary

---

## 📈 Summary 시각화

### 1. All Cases Comparison
**파일**: `summary/all_cases_comparison.png`
- 모든 케이스 Val Loss 비교
- Log scale bar chart
- Case 5 highlighted (gold border)

### 2. Chunk Strategy Comparison
**파일**: `summary/chunk_comparison.png`
- Chunk=1 vs Chunk=10 평균 비교
- 98% improvement 표시

---

## 🎯 미팅 발표용 추천

**Main slides**:
1. `summary/all_cases_comparison.png` - 전체 개요
2. `summary/chunk_comparison.png` - 핵심 발견
3. `case5/summary.png` - Best model

**Backup slides** (질문 시):
- `case1/summary.png` - Baseline 설명
- `case8/summary.png`, `case9/summary.png` - Strategy 비교

---

**생성 스크립트**: `scripts/generate_case_visualizations.py`  
**데이터 출처**: `docs/MASTER_EXPERIMENT_TABLE.md`
