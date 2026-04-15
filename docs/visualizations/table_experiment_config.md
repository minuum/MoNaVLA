# Experiment Configuration (Complete)

| Case   | Model    | Backbone | LoRA | LoRA Rank |   Window |   Chunk | Data         |   Batch |     LR | Strategy     |   Epochs |
|:-------|:---------|:---------|:-----|----------:|---------:|--------:|:-------------|--------:|-------:|:-------------|---------:|
| Case 1 | Kosmos-2 | Frozen   | Yes  |        32 |        8 |      10 | L+R (500)    |       1 | 0.0001 | Baseline     |       10 |
| Case 2 | Kosmos-2 | Frozen   | Yes  |        32 |        8 |      10 | L+R (500)    |       1 | 0.0001 | Xavier Init  |       10 |
| Case 3 | Kosmos-2 | Frozen   | Yes  |        32 |        8 |      10 | L+R (500)    |       1 | 0.0001 | Aug+Abs      |       10 |
| Case 4 | Kosmos-2 | Frozen   | Yes  |        32 |        8 |      10 | R only (250) |       1 | 0.0001 | Baseline     |       10 |
| Case 5 | Kosmos-2 | Frozen   | Yes  |        32 |        8 |       1 | L+R (500)    |       1 | 0.0001 | No Chunk     |        7 |
| Case 8 | Kosmos-2 | Frozen   | Yes  |        32 |        8 |       1 | L+R (500)    |       1 | 0.0001 | No Chunk+Abs |        5 |

## 설정 설명

### 공통 설정 (모든 케이스 동일)

**Model Architecture**:
- **Model**: Kosmos-2 (Microsoft VLM)
- **Backbone**: **Frozen** (freeze_backbone=True)
  - VLM의 vision encoder와 language model은 학습하지 않음
  - Pre-trained weights 그대로 사용
- **LoRA**: **Enabled** (lora_enable=True)
  - Low-Rank Adaptation 사용
  - LoRA Rank: 32
  - LoRA Alpha: 16
  - LoRA Dropout: 0.1
- **Train Vision**: False
  - Vision encoder도 freeze

**Training Setup**:
- Window Size: 8 (8개 이미지 history)
- Batch Size: 1
- Learning Rate: 0.0001 (1e-4)
- Optimizer: AdamW
- Precision: 16-bit mixed precision

### 케이스별 차이점

**차이점은 3가지만**:
1. **Chunk (fwd_pred_next_n)**:
   - Case 1-4: 10 (Action Chunking)
   - Case 5, 8: 1 (No Chunk)

2. **Data**:
   - Case 1, 2, 3, 5, 8: L+R (500 episodes)
   - Case 4: R only (250 episodes)

3. **Strategy**:
   - Baseline: 기본 설정
   - Xavier Init: Action head initialization 변경
   - Aug+Abs: Data augmentation + Absolute action
   - No Chunk: Action chunking 제거
   - No Chunk+Abs: No chunk + Absolute action

## LoRA 상세 설정

**모든 케이스 공통**:
```json
{
  "freeze_backbone": true,
  "lora_enable": true,
  "lora_r": 32,
  "lora_alpha": 16,
  "lora_dropout": 0.1,
  "lora_bias": "none",
  "train_vision": false
}
```

**LoRA가 학습하는 부분**:
- Language model의 attention layers
- Action head (MobileVLALSTMDecoder)

**Frozen 부분**:
- Vision encoder (Kosmos-2 vision backbone)
- Language model의 FFN layers (LoRA 없는 부분)

## 왜 모든 케이스가 동일한 LoRA/Frozen 설정?

**이유**:
1. **공정한 비교**: 모델 구조는 동일하게 유지
2. **변수 통제**: Strategy 효과만 측정
3. **효율성**: LoRA는 빠르고 효과적
4. **안정성**: Frozen backbone으로 catastrophic forgetting 방지

**실험 설계**:
- 독립 변수: Strategy, Chunk, Data
- 통제 변수: Model, LoRA, Frozen, Batch, LR
- 종속 변수: Val Loss, Train Loss

---

**작성**: 2025-12-10 12:20  
**업데이트**: LoRA/Frozen 정보 추가