# 케이스 세분화: FT vs No FT

**업데이트**: 2025-12-10 13:21  
**목적**: Option 1 (FT) vs Option 2 (No FT) 비교

---

## 🔄 케이스 재분류

### Option 1: Fine-Tuned (LoRA) ✅
**설정**: Frozen Backbone + LoRA **Trained**

| New ID | Old ID | Description | Val Loss | Status |
|:---:|:---:|:---|---:|:---|
| **FT-1** | Case 1 | Baseline (Chunk=10) | 0.027 | ✅ 완료 |
| **FT-2** | Case 2 | Xavier Init (Chunk=10) | 0.048 | ✅ 완료 |
| **FT-3** | Case 3 | Aug+Abs (Chunk=10) | 0.050 | ✅ 완료 |
| **FT-4** | Case 4 | Right Only (Chunk=10) | 0.016 | ✅ 완료 |
| **FT-5** | Case 5 | No Chunk | **0.000532** | ✅ 완료 ⭐ |
| **FT-8** | Case 8 | No Chunk+Abs | 0.00243 | ✅ 완료 |
| **FT-9** | Case 9 | No Chunk+Aug+Abs | TBD | 🔄 진행중 |

---

### Option 2: No Fine-Tuning (Pre-trained) ❌
**설정**: Frozen Backbone + LoRA **Not Trained** (초기 상태)

| New ID | Description | Status | Priority |
|:---:|:---|:---:|:---:|
| **NoFT-0** | Pre-trained Kosmos-2 (baseline) | ❌ 미수행 | ⭐⭐⭐ |
| **NoFT-1** | Pre-trained + Chunk=10 | ❌ 미수행 | - |
| **NoFT-5** | Pre-trained + Chunk=1 | ❌ 미수행 | ⭐⭐ |

---

## 🎯 비교 매트릭스

### Comparison A: Baseline (Chunk=10)
- **FT-1** (trained) vs **NoFT-0** (pre-trained)
- 질문: "LoRA 학습이 Chunk=10에서 효과있는가?"

### Comparison B: Best Model (Chunk=1)
- **FT-5** (trained, best) vs **NoFT-5** (pre-trained)
- 질문: "LoRA 학습이 No Chunk에서 효과있는가?" ⭐

### Comparison C: Direction Analysis
- **FT-5 Left** vs **FT-5 Right** (trained)
- **NoFT-0 Left** vs **NoFT-0 Right** (pre-trained)
- 질문: "학습 전후로 방향 구분 능력이 생겼는가?"

---

## 📊 우선순위 작업

### Priority 1: NoFT-0 Context 추출 ⭐⭐⭐
**목표**: Pre-trained Kosmos-2의 context vectors

```python
# 1. Load pre-trained Kosmos-2 (No LoRA weights)
# 2. Extract contexts for Left (50 eps)
# 3. Extract contexts for Right (50 eps)
# Output:
#   - noFT_baseline_left.npy
#   - noFT_baseline_right.npy
```

**예상 결과**:
- Left-Left similarity: ~0.85
- Right-Right similarity: ~0.85
- **Left-Right similarity: ~0.82** (구분 안됨)

---

### Priority 2: FT-5 Context 추출 ⭐⭐⭐
**목표**: Fine-tuned Case 5의 context vectors

```python
# 1. Load Case 5, Epoch 4 checkpoint
# 2. Extract contexts for Left (50 eps)
# 3. Extract contexts for Right (50 eps)
# Output:
#   - FT5_left.npy
#   - FT5_right.npy
```

**예상 결과**:
- Left-Left similarity: ~0.95
- Right-Right similarity: ~0.95
- **Left-Right similarity: ~0.70** (명확히 구분!)

---

### Priority 3: 비교 분석 ⭐⭐
**측정**:
1. **Before FT**: NoFT Left vs Right
2. **After FT**: FT-5 Left vs Right
3. **Delta**: NoFT vs FT-5 (같은 input)

**출력**:
```
Comparison Report
================

Before Fine-Tuning (NoFT-0):
  Left-Left: 0.85 ± 0.03
  Right-Right: 0.85 ± 0.04
  Left-Right: 0.82 ± 0.05
  → No clear separation

After Fine-Tuning (FT-5):
  Left-Left: 0.95 ± 0.02
  Right-Right: 0.95 ± 0.02
  Left-Right: 0.70 ± 0.08
  → Clear clustering!

Fine-Tuning Effect:
  Same input delta: 0.68
  → LoRA significantly changed latent space
```

---

### Priority 4: 시각화 ⭐⭐
1. **t-SNE (Before)**: NoFT-0 Left/Right 섞임
2. **t-SNE (After)**: FT-5 Left/Right 분리
3. **Similarity Matrix**: Before vs After

---

## 📋 실행 계획

### Step 1: Pre-trained 모델 준비 (1시간)
```bash
# Load Kosmos-2 without any fine-tuning
# Or: Initialize RoboVLMs with random LoRA weights
```

### Step 2: Context 추출 (2시간)
```bash
# Run extraction script
python3 scripts/extract_ft_vs_noFT_contexts.py

# Output 확인
ls -lh docs/latent_space_analysis/
```

### Step 3: 유사도 분석 (1시간)
```bash
# Run comparison
python3 scripts/compare_ft_noFT.py

# 결과:
# - comparison_report.txt
# - similarity_matrix.png
```

### Step 4: 시각화 (1시간)
```bash
# Generate t-SNE plots
python3 scripts/visualize_ft_noFT.py

# 결과:
# - tsne_before_FT.png
# - tsne_after_FT.png
# - delta_heatmap.png
```

---

## 🎯 Expected Deliverables (수요일 미팅)

### 1. Context Vectors (4 files)
- ✅ noFT_baseline_left.npy
- ✅ noFT_baseline_right.npy
- ✅ FT5_left.npy
- ✅ FT5_right.npy

### 2. Analysis Report
- ✅ Cosine similarity (before/after)
- ✅ Statistical comparison
- ✅ Feature analysis

### 3. Visualizations (3 images)
- ✅ t-SNE before FT
- ✅ t-SNE after FT
- ✅ Delta/change visualization

### 4. Conclusion
**"LoRA Fine-Tuning이 효과적으로 작동함을 증명"**
- Before: 방향 구분 못함 (0.82)
- After: 명확히 구분 (0.70)
- Effect: Latent space 재구성 (delta 0.68)

---

**작성**: 2025-12-10 13:21  
**상태**: 케이스 세분화 완료, 실행 준비
