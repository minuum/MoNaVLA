# 문제 종합 분석: 순차적 진단 보고서

**작성일**: 2026-01-11  
**목적**: 현재 발생한 모든 문제를 순차적으로 파악하고 학습 과정 검증

---

## 📋 목차

1. [현재 발생한 모든 문제 정리](#1-현재-발생한-모든-문제-정리)
2. [학습 데이터 분석](#2-학습-데이터-분석)
3. [학습 과정 검증](#3-학습-과정-검증)
4. [모델 출력 vs 데이터 비교](#4-모델-출력-vs-데이터-비교)
5. [문제 원인 진단](#5-문제-원인-진단)
6. [해결 방안](#6-해결-방안)

---

## 1. 현재 발생한 모든 문제 정리

### 문제 1: Instruction Grounding 완전 실패

**현상**:
```python
# LEFT vs RIGHT instruction
action_left  = [0.234, -0.156]
action_right = [0.234, -0.156]  # 완전히 동일!

difference = 0.000000  # ❌
```

**심각도**: ⭐⭐⭐⭐⭐ (Critical)

---

### 문제 2: Vision 처리 약화

**현상**:
```python
# 다른 이미지
action_img1 = [0.234, -0.156]
action_img2 = [0.198, -0.089]

difference = 0.009378  # 매우 작음
```

**이전 대비**:
- 기존 Chunk5: 0.073
- Pretrained VLM: 0.009 (약 **8배 악화**)

**심각도**: ⭐⭐⭐⭐ (High)

---

### 문제 3: Val Loss는 낮지만 Grounding 실패

**현상**:
- Val Loss: 0.093 (수치상 양호)
- Val RMSE: 0.270 (수치상 양호)
- **하지만 Instruction grounding: 완전 실패**

**의문점**:
```
Val Loss가 낮다 = 모델이 validation set의 action을 잘 예측한다
그런데 instruction은 구분 못한다?
→ 학습 과정에 문제가 있을 가능성
```

**심각도**: ⭐⭐⭐⭐⭐ (Critical - 근본 문제)

---

## 2. 학습 데이터 분석

### 2.1 데이터셋 구성

```bash
# Episode 파일명 예시
episode_20251119_141903_1box_hori_left_core_medium.h5
episode_20251119_080007_1box_hori_right_core_medium.h5
```

**분포**:
- LEFT episodes: ~120개
- RIGHT episodes: ~120개  
- Total: ~240개

**데이터 형식**:
```python
# H5 파일 구조
{
  'images': (T, 720, 1280, 3),  # T = timesteps
  'actions': (T, 3),             # [linear_x, linear_y, angular_z]
  'action_event_types': (T,)
}
```

---

### 2.2 LEFT vs RIGHT 데이터 차이 (예상)

**LEFT episodes**:
```python
Mean action: [1.02, +0.50, 0.0]  # +y 방향 (왼쪽)
  linear_x: 1.02 (전진)
  linear_y: +0.50 (왼쪽)
```

**RIGHT episodes**:
```python
Mean action: [1.02, -0.50, 0.0]  # -y 방향 (오른쪽)
  linear_x: 1.02 (전진)
  linear_y: -0.50 (오른쪽)
```

**예상 차이**:
```python
|linear_y_left - linear_y_right| = |+0.50 - (-0.50)| = 1.0
```

**문제**: 
- 데이터에는 **분명한 차이**가 있음 (linear_y 차이 ~1.0)
- 하지만 모델은 **차이 = 0.000** 출력

---

## 3. 학습 과정 검증

### 3.1 학습 설정 확인

```json
{
  "pretrained_vlm_path": "kosmos_ph_google-robot-post-train.pt",
  "load_vlm_only": true,
  "train_setup": {
    "freeze_backbone": true,  // ← VLM Frozen
    "predict_action": true
  },
  "act_head": {
    "type": "MobileVLALSTMDecoder",
    "action_dim": 2,  // linear_x, linear_y
    "window_size": 8
  },
  "batch_size": 1,
  "accumulate_grad_batches": 8,
  "max_epochs": 10
}
```

---

### 3.2 학습 결과

| Epoch | Train Loss | Val Loss | Val RMSE |
|-------|------------|----------|----------|
| 0 | ... | ... | ... |
| 3 | 0.023 | **0.093** | 0.240 |
| 7 | 0.001 | 0.099 | ... |
| 9 (final) | 0.023 | 0.119 | 0.270 |

**관찰**:
- Epoch 3: Best (val_loss = 0.093)
- 이후 overfitting 조짐 (val_loss 증가)

---

### 3.3 Loss Function 분석

```python
# mobile_vla_trainer.py
def loss(self, pred, labels, attention_mask):
    # Velocity action loss (Huber Loss)
    velocity_loss = F.huber_loss(pred, labels[0])  
    
    # labels[0] = ground truth velocity [linear_x, linear_y]
    # pred = model prediction [linear_x, linear_y]
    
    return {
        'loss_velocity_act': velocity_loss,
        'rmse_velocity_act': rmse
    }
```

**문제점 의심**:

1. **Instruction이 loss에 포함되지 않음**
   - Loss는 단순히 `|pred - gt|`만 계산
   - Instruction이 맞는지는 체크 안함

2. **가능한 시나리오**:
   ```python
   # Epoch 0
   gt_left  = [1.0, +0.5]  # LEFT episode
   gt_right = [1.0, -0.5]  # RIGHT episode
   
   # 모델이 평균값 학습
   pred_all = [1.0, 0.0]  # 그냥 중간값
   
   # Loss 계산
   loss_left  = |[1.0, 0.0] - [1.0, +0.5]| = 0.5
   loss_right = |[1.0, 0.0] - [1.0, -0.5]| = 0.5
   avg_loss = 0.5  ← 낮은 loss!
   
   # 하지만 instruction grounding은 없음!
   ```

---

## 4. 모델 출력 vs 데이터 비교

### 4.1 데이터 기대값

**LEFT episodes**:
```python
Mean: [1.02, +0.50]  # 왼쪽 이동
Std:  [0.36, 0.82]
```

**RIGHT episodes**:
```python
Mean: [1.02, -0.50]  # 오른쪽 이동
Std:  [0.36, 0.82]
```

**Difference**: `1.0` (linear_y)

---

### 4.2 모델 실제 출력

**Test 결과**:
```python
# Random 이미지 + LEFT/RIGHT instruction
action_left  = [0.234, -0.156]
action_right = [0.234, -0.156]

Difference: 0.000000
```

**문제**:
- 데이터 평균 `[1.02, ±0.50]`과 **전혀 다름**
- 출력이 `[0.234, -0.156]`로 **고정됨**

---

### 4.3 가설: "Default Action" 학습

**의심되는 상황**:

```python
# 모델이 학습한 것
"Instruction 무관하게 안전한 default action 출력"

default_action = [0.234, -0.156]  # 약간 전진, 약간 오른쪽
→ 모든 상황에서 이 값 출력

Why?
- Frozen VLM → instruction embedding 동일
- Action Head → 구분할 수 없음  
- 결국 "평균적으로 안전한" action 학습
```

---

## 5. 문제 원인 진단

### 5.1 근본 원인: Frozen VLM

```
Frozen VLM Text Encoder
  ↓
emb("LEFT") ≈ emb("RIGHT")  # 0.998 similarity
  ↓
VLM hidden state 거의 동일
  ↓
Action Head가 구분 불가
  ↓
Default action 출력 [0.234, -0.156]
```

---

### 5.2 Loss가 낮은 이유

**가설 1: Collapse to Mean**

```python
# 데이터 분포
LEFT:  [1.0, +0.5]  (50%)
RIGHT: [1.0, -0.5]  (50%)

# 모델이 학습한 것
pred = [1.0, 0.0]  # 평균값!

# Loss (Huber)
loss_left  = |[1.0, 0.0] - [1.0, +0.5]| = 0.5
loss_right = |[1.0, 0.0] - [1.0, -0.5]| = 0.5
avg_loss = 0.5

# RMSE
rmse = sqrt(0.5) ≈ 0.27  ← 우리 val_rmse!
```

**검증**:
- Val RMSE = 0.270
- 예상 RMSE (평균값 예측) = sqrt(0.5² + 0.5²) = 0.707
- **아니면 데이터 std가 0.27?**

---

**가설 2: Random Image로 테스트**

```python
# 우리 테스트
image = random_image(seed=42)  # ← 학습 데이터와 다름!
instruction = "Navigate LEFT"

# 모델이 학습한 것
"학습 데이터의 특정 이미지 패턴 → action"

# Random image는 못 봤으니
→ Default action 출력 [0.234, -0.156]
```

---

### 5.3 Vision 처리 약화 원인

**가설**:

```python
# Pretrained VLM
Vision Encoder: 1.6B params (Frozen)
Text Encoder: 0.05B params (Frozen)

# 학습됨
Action Head: 12.7M params

# 문제
Vision/Text encoder가 frozen
→ Robot domain에 맞지 않음
→ Hidden state가 별로 유용하지 않음
→ Action Head가 제대로 학습 못함
```

---

## 6. 해결 방안

### 6.1 즉시 검증 필요 사항

#### Test 1: 실제 학습 이미지로 테스트

```python
# Random image 대신
image = load_from_h5("episode_left_001.h5")
instruction = "Navigate LEFT"

# 예상
action = [1.0, +0.5]  # 데이터와 유사?
또는
action = [0.234, -0.156]  # 여전히 default?
```

**목적**: 모델이 학습 이미지에 overfitting 되었는지 확인

---

#### Test 2: Validation Set으로 직접 테스트

```python
# Validation dataset 사용
for batch in val_dataloader:
    pred = model(batch['rgb'], batch['lang'])
    gt = batch['actions']
    
    # LEFT episodes만
    left_diff = |pred[left_idx] - gt[left_idx]|
    
    # RIGHT episodes만
    right_diff = |pred[right_idx] - gt[right_idx]|
```

**목적**: Val loss가 정말 낮은지, instruction별로 확인

---

### 6.2 근본 해결책: LoRA Fine-tuning

```json
{
  "train_setup": {
    "freeze_backbone": false,  // ← Unfreeze!
    "lora_enable": true,
    "lora_r": 16,
    "lora_alpha": 32
  }
}
```

**예상 효과**:
```
Frozen VLM:
  emb("LEFT") ≈ emb("RIGHT")
  → difference = 0.000

LoRA VLM:
  emb("LEFT") ≠ emb("RIGHT")
  → difference > 0.05  ✅
```

---

## 7. 학습 과정 문제 가능성

### 가능성 1: Instruction이 학습에 사용되지 않음 (낮음)

**검증**:
```python
# dataset loader 확인
dataset[i] = {
    'rgb': images,
    'lang': instruction,  # ← 있음
    'actions': actions
}

# trainer forward
output = model(rgb, lang)  # ← lang 사용됨
```

→ Instruction은 사용됨. 문제 아님.

---

### 가능성 2: Instruction이 항상 동일 (낮음)

**검증**:
```python
# dataset loader 확인
# LEFT episode → instruction = "Navigate LEFT"
# RIGHT episode → instruction = "Navigate RIGHT"
```

→ Instruction은 다름. 문제 아님.

---

### 가능성 3: Frozen VLM이 근본 문제 (높음) ⭐

**메커니즘**:
```
1. VLM frozen → text embedding 고정
2. "LEFT" ≈ "RIGHT" (robot 관점에서)
3. Action Head → 구분 불가
4. Default action 학습
5. Val loss는 낮지만 grounding 실패
```

→ **가장 가능성 높음**

---

## 8. 결론 및 다음 단계

### 현재 상태

| 항목 | 상태 | 근본 원인 |
|------|------|----------|
| Instruction Grounding | ❌ 완전 실패 (0.000) | Frozen VLM |
| Vision Processing | ⚠️ 약화 (0.009) | Frozen Vision Encoder |
| Val Loss | ✅ 낮음 (0.093) | Default action 학습? |

---

### 즉시 실행 가능한 검증

1. **실제 학습 이미지로 테스트** (30분)
2. **Validation set 직접 검증** (1시간)
3. **Loss 분포 분석** (1시간)

---

### 근본 해결책

**LoRA Fine-tuning 구현** (1일)

```
1. Config 작성
2. 재학습 (10 epochs, ~8시간)
3. 검증
   → 예상: difference > 0.05  ✅
```

---

**다음 액션**: 
1. 실제 학습 이미지로 재테스트
2. Validation set 직접 검증
3. 문제 확인되면 → LoRA 구현

**최종 판단**: Frozen VLM이 근본 문제, LoRA 필수!
