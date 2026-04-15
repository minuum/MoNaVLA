# 학습 vs 추론 과정 환각 없는 분석 (2026-01-07)

## 🔍 핵심 발견: 학습과 추론의 차이

### 문제의 본질
**Ablation test 실패 원인**: 학습 시와 추론 시의 **input 처리 방식이 다름**

---

## 📊 Training vs Inference 비교표

| 항목 | Training (학습 시) | Inference (추론 시) | 차이점 분석 |
|------|-------------------|---------------------|------------|
| **Input 구조** | `(B, seq_len, latent, feature)` | `(1, window_size, 3, 224, 224)` | ✅ 동일 구조 |
| **Instruction 처리** | `lang_x` tokenized → VLM embedding | `instruction` tokenized → VLM embedding | ✅ 동일 |
| **VLM Forward** | `forward_continuous()` | `forward_continuous(mode="inference")` | ⚠️ **Mode 차이** |
| **Action Token** | Inserted at last position | Inserted at last position | ✅ 동일 |
| **History** | `history_type="post"` | 설정 동일 | ✅ 동일 |
| **LSTM Input** | `(B*seq_len, latent, feature)` | Training과 동일 처리 | ✅ 동일 |
| **Output Shape** | `(B, seq_len, chunk, 2)` | `(1, 8, 5, 2)` → `(8, 5, 2)` | ⚠️ **Batch reshape** |
| **Loss 계산** | Huber Loss with attention_mask | **Loss 없음** | ❌ **학습 필요** |

---

## 🎯 핵심 문제 발견

### 1. **Mode="inference"의 의미**
```python
# forward_continuous()에서
prediction["action"] = self.forward_continuous(
    vision_x, lang_x, attention_mask,
    vision_gripper=vision_gripper,
    mode="inference",  # ← 이 부분!
)
```

**의미**: Mode가 "inference"일 때는 **loss를 계산하지 않고** action만 반환

### 2. **학습 시 실제로 사용되는 값**

#### Training Step에서:
```python
# Mobile_VLA_trainer.py _process_batch()
velocity_chunck = action_chunck  # (B, seq_len, chunk_size, 2)

# forward_continuous()
output = self.model(
    input_ids=None,
    inputs_embeds=multimodal_embeds,  # ← VLM + instruction embedding
    ...
)

# Action head (MobileVLALSTMDecoder)
velocities, None = self.rnn -> self.velocities(x)
# velocities: (B, seq_len, chunk_size, 2)

# Loss 계산
loss_velocity = huber_loss(velocities, velocity_labels)
```

#### Inference Step에서:
```python
# inference_pipeline.py predict()
encoded = processor.tokenizer(instruction, ...)  # ← Instruction tokenize

outputs = self.trainer.model.inference(
    vision_x=image_tensor,
    lang_x=encoded['input_ids'],  # ← Instruction 전달
    attention_mask=encoded['attention_mask']
)

action_pred = outputs['action']  # (1, window_size, chunk, 2)
# Loss 계산 없음!
```

---

## 🔴 **문제 발견: Instruction이 Loss에 반영 안 됨**

### 현재 Loss 계산 구조

```python
# MobileVLALSTMDecoder.loss()
def loss(self, pred_action, labels, attention_mask=None):
    velocities = pred_action[0]  # 모델 출력
    velocity_labels = labels[0]   # Ground truth
    
    loss_velocity = huber_loss(velocities, velocity_labels)
    # ← Instruction이 여기서 사용되지 않음!
```

### 문제점
1. **Instruction은 VLM embedding에만 사용됨**
2. **Loss는 velocity vs velocity_labels만 비교**
3. **Instruction → Action 연결이 약함**

---

## 📋 **Training 과정 상세 분석**

### Step 1: Data Preparation
```python
# Dataset에서
task_description = "Navigate around the obstacle on the left side..."  # English
images = [...]  # (window_size, H, W, 3)
action_chunck = [...]  # (window_size, chunk_size, 2)
```

### Step 2: Tokenization
```python
# VLM tokenizer
lang_x = tokenizer(task_description)  # (B, max_text_len)
```

### Step 3: VLM Forward
```python
# Embed instruction
input_embeds = self.word_embedding(lang_x)

# Merge vision + language
multimodal_embeds = merge(vision_embeds, input_embeds)

# Add action token
action_tokens = self.action_token  # Learnable token
multimodal_embeds = concat(multimodal_embeds, action_tokens)

# VLM forward
output_hs = self.model(inputs_embeds=multimodal_embeds)
# output_hs: (B*seq_len, num_tokens, hidden_dim)
```

### Step 4: Action Extraction
```python
# Extract action token 위치의 hidden states
action_hs = output_hs[action_token_mask]  # (B*seq_len, latent, hidden_dim)
```

### Step 5: LSTM Decoder
```python
# LSTM forward
x, h_n = self.rnn(action_hs, hidden_state)

# Velocity head
velocities = self.velocities(x)  # MLP + Tanh
# velocities: (B, seq_len, chunk_size, 2)
```

### Step 6: Loss Calculation
```python
loss_velocity = huber_loss(
    velocities,        # 예측 (instruction 기반)
    velocity_labels    # GT (파일명 기반)
)
```

---

## 🎯 **왜 Instruction이 무시되는가?**

### 가설 1: **Frozen VLM의 한계** ⭐ 가장 유력
```
VLM Frozen 
→ Instruction encoding 고정
→ Action token의 hidden state가 instruction 정보를 잘 담지 못함
→ LSTM이 instruction과 무관하게 학습됨
```

**증거**:
- Epoch 1에서 LEFT/RIGHT 모두 동일한 출력 (-0.3274)
- Instruction이 달라도 action이 동일

### 가설 2: **Instruction-Action Alignment 부족**
```
Training Loss = huber(pred_velocity, gt_velocity)
→ Instruction 정보가 loss에 직접 반영 안 됨
→ 모델이 instruction을 무시하고 평균적인 action 학습
```

### 가설 3: **Learning Rate 또는 Epoch 부족**
```
Epoch 1 = 너무 이름
→ Instruction grounding 학습 부족
→ 더 많은 epoch 필요
```

---

## 📊 **3가지 Loss 값 분석**

학습 로그에서 나타나는 3가지 값:

| Loss 이름 | 의미 | 계산 방법 | 현재 값 (Epoch 1) |
|-----------|------|-----------|-------------------|
| `train_loss` | 전체 loss | `loss_velocity` (gripper 없음) | 0.0885 |
| `train_loss_velocity_act` | Velocity loss | `huber_loss(pred, gt)` | 0.0885 |
| `train_rmse_velocity_act` | RMSE | `sqrt(MSE(pred, gt))` | 0.297 |

**현재 상태**:
- Loss가 낮음 (0.0885) → 모델이 평균적인 action 학습
- **BUT** instruction 구분 못함 → Instruction grounding 실패

---

## 🔍 **추가 검증 필요 사항**

### 1. VLM Output 확인
```python
# Training 중 VLM의 action_hs 확인
# LEFT instruction vs RIGHT instruction의 hidden state 차이 있는지?
```

### 2. Action Token의 역할
```python
# self.action_token이 instruction 정보를 받고 있는지?
# Frozen VLM이라서 못 받는 것 아닌지?
```

### 3. Gradient Flow 확인
```python
# VLM이 frozen이지만 action_token은 learnable
# action_token → LSTM으로의 gradient flow 정상인지?
```

---

## 💡 **해결 방안**

### 방안 1: VLM LoRA Fine-tuning (강력 추천)
```json
{
  "train_setup": {
    "freeze_backbone": false,
    "lora_enable": true,
    "lora_r": 32,
    "lora_alpha": 16
  }
}
```

**장점**:
- VLM이 instruction에 따라 다른 embedding 생성 가능
- Instruction grounding 성능 향상

### 방안 2: Contrastive Loss 추가
```python
# LEFT vs RIGHT instruction의 hidden state 차이를 명시적으로 학습
loss_contrastive = contrastive_loss(
    action_hs_left,
    action_hs_right,
    target=different
)
```

### 방안 3: 더 많은 Epoch 학습
- Epoch 1은 너무 이름
- Epoch 5-7에서 재테스트

---

## 🎯 **결론**

### 1. **학습 과정은 올바름** ✅
- Instruction이 VLM에 전달됨
- Action head가 정상적으로 작동함
- Loss 계산 정상

### 2. **BUT Frozen VLM의 한계** ❌
- VLM이 frozen이라 instruction에 따른 다른 embedding 생성 못함
- Action token의 hidden state가 instruction 정보 부족
- LSTM이 instruction 무시하고 평균 action 학습

### 3. **해결책**
**우선순위**:
1. **Epoch 3-5에서 재테스트** (먼저 시도)
2. 실패 시 **VLM LoRA fine-tuning**
3. 또는 **Contrastive loss** 추가

---

**Updated**: 2026-01-07 09:50
