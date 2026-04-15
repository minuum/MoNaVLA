# FT vs NoFT 비교표 (table_experiment_config.md 형식)

## Experiment Comparison: Fine-Tuned vs No Fine-Tuning

| Checkpoint ID | Case | Model | Epoch | Fine-Tuned | Window | Chunk | Data | Val Loss | Train Loss | Status |
|:---|:---:|:---|:---:|:---:|:---:|:---:|:---|---:|---:|:---|
| **NoFT-9-E0** | 9 | Kosmos-2 (LoRA) | 0 | ❌ **No** | 8 | 1 | L+R (500) | 0.022 | - | ✅ Available |
| **FT-9-E1** | 9 | Kosmos-2 (LoRA) | 1 | ✅ **Yes** | 8 | 1 | L+R (500) | 0.0224 | 0.034 | 🔄 Training |
| **FT-5-E4** | 5 | Kosmos-2 (LoRA) | 4 | ✅ **Yes** | 8 | 1 | L+R (500) | 0.000532 | ~0.0001 | ✅ Best |
| **FT-8-E4** | 8 | Kosmos-2 (LoRA) | 4 | ✅ **Yes** | 8 | 1 | L+R (500) | 0.00243 | ~0.00005 | ✅ Available |

---

## Key Comparison

### Primary Comparison: Case 9 (Epoch 0 vs Epoch 1)

**Same Configuration, Different Training**:
- Backbone: Frozen Kosmos-2
- LoRA: Yes (rank=32)
- Data: L+R (500 episodes)
- Chunk: 1 (No Chunk)
- Strategy: Aug + Abs

**Only Difference**: Fine-Tuning
- NoFT-9-E0: Epoch 0 (초기 상태, 거의 학습 안됨)
- FT-9-E1: Epoch 1 (1 epoch 학습)

**Expected Delta**:
- Val Loss: 0.022 → 0.022 (작은 변화)
- Latent Space: 큰 변화 예상
- Direction Separation: 증가 예상

---

## Metrics to Measure

### Representation Similarity
1. **CKA (Centered Kernel Alignment)** ⭐
   - Range: 0~1
   - Higher = More similar
   - Expected: ~0.4-0.6 (moderate change)

2. **Cosine Similarity**
   - Range: -1~1
   - Expected: ~0.6-0.7

3. **Fréchet Distance**
   - Lower = More similar
   - Expected: Moderate value

### Distribution Metrics
1. **Wasserstein Distance**
   - Earth Mover's Distance
   - Expected: > 0

2. **KL Divergence**
   - Information distance
   - Expected: > 0

### Clustering Metrics
1. **Silhouette Score**
   - Range: -1~1
   - NoFT: Low (mixed)
   - FT: High (separated)

2. **t-SNE Visualization**
   - Visual inspection
   - Clustering quality

---

## Checkpoint Paths

```bash
# NoFT (Epoch 0)
NoFT_CKPT="runs/mobile_vla_no_chunk_aug_abs_20251210/kosmos/mobile_vla_finetune/2025-12-10/mobile_vla_no_chunk_aug_abs_20251210/epoch_epoch=00-val_loss=val_loss=0.022.ckpt"

# FT (Epoch 1 - in progress, use last.ckpt)
FT_CKPT="runs/mobile_vla_no_chunk_aug_abs_20251210/kosmos/mobile_vla_finetune/2025-12-10/mobile_vla_no_chunk_aug_abs_20251210/last.ckpt"

# Best reference (Case 5 Epoch 4)
BEST_CKPT="runs/mobile_vla_no_chunk_20251209/kosmos/mobile_vla_finetune/2025-12-09/mobile_vla_no_chunk_20251209/epoch_epoch=04-val_loss=val_loss=0.001.ckpt"
```

---

**작성**: 2025-12-10 13:44  
**미팅**: 오늘 16:00 (2시간 16분 후)  
**우선순위**: Case 9 Epoch 0 vs Epoch 1
