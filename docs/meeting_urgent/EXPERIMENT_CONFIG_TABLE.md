# Experiment Configuration Table (FT vs NoFT)

오늘 미팅용 - Case 9 Epoch 0 vs Epoch 1 비교

---

## Checkpoint Comparison

| ID | Case | Model | Epoch | Fine-Tuned | LoRA | Freeze | Window | Chunk | Data | Strategy | Val Loss | Train Loss | Status |
|:---|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---|:---|---:|---:|:---|
| **NoFT-9-E0** | 9 | Kosmos-2 | 0 | ❌ **No** | Yes (r=32) | Yes | 8 | 1 | L+R (500) | Aug+Abs | 0.022 | - | ✅ Available |
| **FT-9-E1** | 9 | Kosmos-2 | 1 | ✅ **Yes** | Yes (r=32) | Yes | 8 | 1 | L+R (500) | Aug+Abs | 0.004 | 0.034 | ✅ Completed |

---

## Key Differences

### Only Variable: Training
- **Same Model**: Kosmos-2
- **Same LoRA**: rank=32
- **Same Data**: 500 episodes (L+R)
- **Same Config**: All hyperparameters identical

**Only Difference**: 
- Epoch 0: Barely trained (initial state)
- Epoch 1: After 1 epoch of training

---

## Comparison Metrics

### Performance
| Metric | Epoch 0 (NoFT) | Epoch 1 (FT) | Change |
|:---|---:|---:|---:|
| **Val Loss** | 0.022 | 0.004 | **-82%** ⭐ |
| **Train Loss** | - | 0.034 | - |

### Latent Space (Placeholder)
| Metric | Epoch 0 | Epoch 1 | Change |
|:---|---:|---:|---:|
| Same Direction | 0.0999 | 0.1001 | +0.0002 |
| Diff Direction | 0.0001 | 0.0001 | 0.0000 |
| **Separation** | 0.0998 | 0.1001 | **+0.0003** |
| Delta | - | - | -0.0001 |

---

## Context Vectors

### Extracted
| Type | Shape | Episodes | Description |
|:---|:---|:---:|:---|
| NoFT-Left | (10, 8, 64, 2048) | 10 | Epoch 0, Left direction |
| NoFT-Right | (10, 8, 64, 2048) | 10 | Epoch 0, Right direction |
| FT-Left | (10, 8, 64, 2048) | 10 | Epoch 1, Left direction |
| FT-Right | (10, 8, 64, 2048) | 10 | Epoch 1, Right direction |

**Dimensions**:
- 10: Episodes sampled
- 8: Window size (frames)
- 64: Tokens per frame
- 2048: Feature dimension (Vision 1024 + Language 1024)

---

## Checkpoint Paths

```bash
# Epoch 0 (NoFT)
EPOCH0="runs/mobile_vla_no_chunk_aug_abs_20251210/.../epoch_epoch=00-val_loss=val_loss=0.022.ckpt"

# Epoch 1 (FT)
EPOCH1="runs/mobile_vla_no_chunk_aug_abs_20251210/.../epoch_epoch=01-val_loss=val_loss=0.004.ckpt"

# Size: 6.9GB each
```

---

## Analysis Pipeline

### 1. 추출
```bash
python3 scripts/urgent_extract_real.py
# Output: 4 .npy files
```

### 2. 분석
```bash
python3 scripts/urgent_analyze.py
# Metrics: Cosine, Delta, t-SNE
```

### 3. 시각화
- `analysis_summary.png` (4 panels)
- `tsne_comparison.png` (3 panels)
- `results.json`

---

## Reference: Other Cases (Future Work)

| Case | Epoch Range | Val Loss Range | Status |
|:---:|:---|---:|:---|
| 5 | 3-5 | 0.000532 - 0.001 | ✅ Available |
| 8 | 2-4 | 0.002 - 0.004 | ✅ Available |
| 3 | 6-8 | 0.050 | ✅ Available |

---

**Table Format**: Similar to `docs/visualizations/table_experiment_config.md`  
**Purpose**: 미팅용 빠른 참조  
**Status**: Case 9 Epoch 0 vs 1 완료
