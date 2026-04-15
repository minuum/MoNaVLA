# 긴급 미팅 준비 (오늘 16:00 - 2시간 10분!)

**현재**: 2025-12-10 13:44  
**미팅**: 2025-12-10 16:00  
**남은 시간**: 2시간 16분 ⏰

---

## ✅ 확인된 사실 (환각 없음)

### 사용 가능한 Checkpoint 쌍

**Case 9 (No Chunk + Aug + Abs)**:
- ✅ **Epoch 0** (FT 안됨): `epoch_epoch=00-val_loss=0.022.ckpt`
- ✅ **Epoch 1** (진행 중): 현재 학습 중

**Case 5 (No Chunk - Best)**:
- ✅ **Epoch 3**: `epoch_epoch=03-val_loss=0.001.ckpt`
- ✅ **Epoch 4**: `epoch_epoch=04-val_loss=0.001.ckpt` (best)
- ✅ **Epoch 5**: `epoch_epoch=05-val_loss=0.001.ckpt`

**Case 8 (No Chunk + Abs)**:
- ✅ **Epoch 2**: `epoch_epoch=02-val_loss=0.004.ckpt`
- ✅ **Epoch 4**: `epoch_epoch=04-val_loss=0.002.ckpt`

**Case 3 (Aug+Abs, Chunk=10)**:
- ✅ **Epoch 6**: `epoch_epoch=06-val_loss=0.050.ckpt`
- ✅ **Epoch 8**: `epoch_epoch=08-val_loss=0.050.ckpt`

---

## 🎯 비교 전략

### Option A: Same Model, Different Epochs (권장)
**Case 9 비교**:
- **NoFT**: Epoch 0 (val_loss=0.022) - 거의 학습 안됨
- **FT**: Epoch 1+ (진행 중) - 학습 진행

**장점**: 같은 config, 순수 FT 효과만 측정

### Option B: Different Cases
**No Chunk 계열 비교**:
- Case 5 Epoch 0 (없음) vs Epoch 4 (best)
- Case 8 Epoch 0 (없음) vs Epoch 4

**문제**: Epoch 0 checkpoint 없음

---

## 📊 비교 Metrics (표준 지표)

### 1. Representation Similarity
**CKA (Centered Kernel Alignment)** ⭐ 추천
- 논문: Kornblith et al. (2019) "Similarity of Neural Network Representations"
- 표준 지표, 많이 사용됨
- Layer-wise comparison

**CCA (Canonical Correlation Analysis)**
- 고전적 방법
- Neural representation 비교

**Cosine Similarity**
- 간단하고 직관적
- 이미 구현됨

### 2. Distribution Metrics
**Fréchet Distance**
- GAN 평가에서 많이 사용
- Distribution similarity

**MMD (Maximum Mean Discrepancy)**
- Two-sample test
- Distribution 차이 측정

**Wasserstein Distance** ⭐
- 이미 구현됨
- Earth Mover's Distance

### 3. Clustering Metrics
**Silhouette Score**
- Clustering quality
- -1 ~ +1

**Davies-Bouldin Index**
- Cluster separation

---

## ⚡ 긴급 실행 계획 (2시간)

### 13:45-14:15 (30분): Checkpoint 로딩 및 추출
```bash
# Case 9 Epoch 0 vs 진행중
python3 scripts/extract_epoch_comparison.py \
  --case9-epoch0 runs/.../epoch_epoch=00*.ckpt \
  --case9-current (학습 중단 후 last.ckpt)
```

### 14:15-14:45 (30분): 비교 분석
```bash
python3 scripts/analyze_ft_effect.py \
  --metrics cka,cosine,wasserstein \
  --output docs/meeting/
```

### 14:45-15:15 (30분): 시각화
```bash
python3 scripts/visualize_meeting.py
# - t-SNE
# - CKA matrix
# - Similarity plot
```

### 15:15-15:45 (30분): 표 정리 및 슬라이드
- FT vs NoFT 비교표
- 핵심 발견 3가지
- 시각화 3장

### 15:45-16:00 (15분): 리허설

---

## 📋 표 형식 (table_experiment_config.md 스타일)

| Checkpoint | Case | Epoch | Fine-Tuned | Val Loss | Train Loss | Description |
|:---|:---:|:---:|:---:|---:|---:|:---|
| **NoFT** | 9 | 0 | ❌ No | 0.022 | - | Initial state |
| **FT** | 9 | 1 | ✅ Yes | TBD | TBD | After 1 epoch |
| **FT** | 5 | 4 | ✅ Yes | 0.000532 | ~0.0001 | Best model |

---

## 🎓 예상 결과

**Hypothesis**:
- Epoch 0: Random/초기 representation
- Epoch 1+: Task-specific representation

**Metrics**:
- CKA: ~0.3-0.5 (다름)
- Cosine: ~0.6 (moderate)
- t-SNE: 명확한 clustering 차이

---

**상태**: 급하게 진행 중 ⚡  
**우선순위**: Epoch 0 vs 진행중 비교
