# Mobile VLA 핵심 하이퍼파라미터 브리핑 (대학원생용)

**작성일**: 2026-01-11  
**목적**: Model_LEFT 학습을 위한 하이퍼파라미터 완전 이해

---

## 📋 목차

1. [데이터 관련](#1-데이터-관련-파라미터)
2. [모델 구조](#2-모델-구조-파라미터)
3. [학습 전략](#3-학습-전략-파라미터)
4. [Optimization](#4-optimization-파라미터)
5. [정규화](#5-정규화-파라미터)
6. [실전 가이드](#6-실전-가이드)

---

## 1. 데이터 관련 파라미터

### 1.1 `episode_pattern`: 데이터 필터링

```json
{
    "train_dataset": {
        "episode_pattern": "episode_202512*left*.h5"
    }
}
```

**역할**: 
- 어떤 episode를 학습에 사용할지 결정
- Glob pattern 사용

**Model_LEFT 설정**:
```
"episode_202512*left*.h5"
→ 20251203, 20251204의 LEFT episodes만 선택
→ ~250 episodes
```

**Model_RIGHT 설정** (나중에):
```
"episode_202512*right*.h5"
→ RIGHT episodes만
```

**영향**:
- ✅ LEFT-specific policy 학습
- ✅ Instruction grounding 문제 우회
- ⚠️ 데이터 양 50% 감소 (500 → 250)

---

### 1.2 `window_size`: History Length

```json
{
    "window_size": 8
}
```

**역할**:
- 몇 프레임의 history를 사용할지
- LSTM에 입력되는 sequence 길이

**메커니즘**:
```python
# window_size = 8
Input: images[t-7:t+1]  # 8 frames
       actions[t-7:t+1]  # 8 past actions

LSTM processes:
  hidden_states = LSTM(images, actions)
  
Output: action[t+1]  # Next action
```

**영향**:
- **크면** (e.g., 16):
  - ✅ 더 많은 context
  - ✅ 더 긴 history로 판단
  - ❌ 메모리 많이 사용
  - ❌ 학습 느림

- **작으면** (e.g., 4):
  - ✅ 빠른 학습
  - ✅ 메모리 적게 사용
  - ❌ Context 부족
  - ❌ Reactive policy (근시안적)

**우리 선택**: 8 (RoboVLMs 표준)
- Navigation에 적절한 history
- 약 2-3초의 과거 정보

---

### 1.3 `fwd_pred_next_n`: Future Prediction Horizon

```json
{
    "fwd_pred_next_n": 5
}
```

**역할**:
- 몇 개의 future actions를 예측할지
- Action chunking size

**메커니즘**:
```python
# fwd_pred_next_n = 5
Model predicts:
  actions[t+1:t+6]  # 5 future actions
  
실제로는 t+1만 실행, 나머지는 planning
```

**영향**:
- **크면** (e.g., 10):
  - ✅ 더 먼 미래 고려 (planning)
  - ✅ Smooth trajectory
  - ❌ 학습 어려움
  - ❌ Computation 많음

- **작으면** (e.g., 1):
  - ✅ 단순, 빠름
  - ✅ Reactive
  - ❌ Jerky motion
  - ❌ Short-sighted

**우리 선택**: 5
- Balance between reactivity and planning
- ~1.5초 미래 예측

---

### 1.4 `train_split`: Train/Val 비율

```json
{
    "train_split": 0.8
}
```

**역할**:
- 데이터를 train/val로 분할

**계산**:
```python
LEFT episodes: 250 total

train_split = 0.8:
  - Train: 250 * 0.8 = 200 episodes
  - Val: 250 * 0.2 = 50 episodes
```

**영향**:
- **높으면** (e.g., 0.9):
  - ✅ 더 많은 학습 데이터
  - ❌ Val set 작음 → validation 불안정

- **낮으면** (e.g., 0.7):
  - ✅ 큰 val set → 신뢰성 높음
  - ❌ 학습 데이터 부족

**우리 선택**: 0.8 (표준)
- 200 train / 50 val
- 적절한 balance

---

## 2. 모델 구조 파라미터

### 2.1 `freeze_backbone`: VLM Frozen 여부

```json
{
    "train_setup": {
        "freeze_backbone": true
    }
}
```

**역할**:
- VLM (1.66B params)을 frozen할지 학습할지

**Frozen (true)** - 우리 선택:
```
VLM: 1.66B params → FROZEN ❄️
Action Head: 12.7M params → TRAINABLE 🔥

장점:
  ✅ 메모리 적게 사용 (~4GB)
  ✅ 빠른 학습
  ✅ Stable gradients

단점:
  ❌ Instruction grounding 안됨
  ❌ Task-specific adaptation 제한
```

**Trainable (false)**:
```
VLM: 1.66B params → TRAINABLE 🔥
Action Head: 12.7M params → TRAINABLE 🔥

장점:
  ✅ VLM을 task에 맞게 fine-tune
  ✅ Better instruction grounding

단점:
  ❌ 메모리 많이 필요 (~20GB+)
  ❌ 학습 느림
  ❌ 250 episodes로는 부족
```

**우리 전략**: 
- Model_LEFT/RIGHT는 instruction 필요 없음
- **Frozen 유지** → 빠르고 효율적

---

### 2.2 `action_dim`: Action Space Dimension

```json
{
    "act_head": {
        "action_dim": 2
    }
}
```

**역할**:
- 출력 action의 dimension

**우리 Task**:
```python
action_dim = 2:
  - action[0]: linear_x (forward/backward)
  - action[1]: linear_y (left/right strafe)

Mobile robot 2-DoF
```

**RoboVLMs 기본**: 7-DoF
```python
action_dim = 7:
  - [0:3]: position (x, y, z)
  - [3:6]: orientation (roll, pitch, yaw)
  - [6]: gripper (open/close)
```

**영향**:
- Action space가 작음
  → 학습 쉬움
  → 250 episodes로 충분할 가능성

---

### 2.3 `hidden_size`: LSTM Hidden Dimension

```json
{
    "act_head": {
        "hidden_size": 512
    }
}
```

**역할**:
- LSTM의 hidden state 크기
- 모델의 capacity

**메커니즘**:
```python
LSTM:
  input: VLM features (2048 dim)
  hidden: 512 dim  ← 이 파라미터
  output: 512 dim → MLP → 2 dim (action)
```

**영향**:
- **크면** (e.g., 1024):
  - ✅ 더 많은 capacity
  - ✅ 복잡한 pattern 학습 가능
  - ❌ Overfitting 위험 (250 ep)
  - ❌ 메모리 많이 사용

- **작으면** (e.g., 256):
  - ✅ 빠름
  - ✅ Overfitting 덜함
  - ❌ Capacity 부족
  - ❌ 복잡한 policy 못 배움

**우리 선택**: 512
- 2-DoF task에 적절
- 250 episodes에 맞는 크기

---

## 3. 학습 전략 파라미터

### 3.1 `batch_size` & `accumulate_grad_batches`

```json
{
    "batch_size": 2,
    "trainer": {
        "accumulate_grad_batches": 4
    }
}
```

**역할**:
- Effective batch size 결정

**계산**:
```python
Effective batch size = batch_size × accumulate_grad_batches
                     = 2 × 4
                     = 8
```

**메커니즘**:
```python
# batch_size = 2
- GPU에 한 번에 2 samples 로드
- Forward pass: 2 samples

# accumulate_grad_batches = 4
- Gradient 4번 누적
- 8 samples 분의 gradient 모인 후 update

Total: 8 samples per update (effective)
```

**영향**:

**Effective batch size 크면** (e.g., 16):
- ✅ Stable gradients
- ✅ Better generalization
- ❌ 학습 느림 (fewer updates)
- ❌ GPU 메모리 많이 필요

**Effective batch size 작으면** (e.g., 2):
- ✅ 빠른 iteration
- ✅ GPU 메모리 적게
- ❌ Noisy gradients
- ❌ 불안정한 학습

**우리 선택**: 8 (2×4)
- RTX A5000 24GB에 적합
- Navigation task에 충분

---

### 3.2 `max_epochs`: 학습 기간

```json
{
    "trainer": {
        "max_epochs": 20
    }
}
```

**역할**:
- 전체 dataset을 몇 번 순회할지

**계산**:
```python
Train episodes: 200
Effective batch size: 8

Steps per epoch = 200 / 8 = 25 steps

Total training:
  20 epochs × 25 steps = 500 updates
```

**영향**:
- **많으면** (e.g., 50):
  - ✅ 충분히 학습
  - ❌ Overfitting 위험 (250 ep로)
  - ❌ 시간 오래 걸림

- **적으면** (e.g., 10):
  - ✅ 빠름
  - ❌ Underfitting 가능성

**우리 선택**: 20
- Single task (LEFT only)
- 250 episodes에 적절
- Early stopping으로 조절

---

### 3.3 `precision`: 연산 정밀도

```json
{
    "train_setup": {
        "precision": "16-mixed"
    }
}
```

**역할**:
- FP16 mixed precision training 사용 여부

**메커니즘**:
```
16-mixed:
  - Forward pass: FP16 (빠름)
  - Backward pass: FP16
  - Weight update: FP32 (정확함)
  - Loss scaling 자동
```

**영향**:
- **16-mixed** (우리):
  - ✅ 2배 빠름
  - ✅ 메모리 50% 절약
  - ⚠️ 수치 불안정 가능 (rare)

- **32** (full precision):
  - ✅ 수치 안정
  - ❌ 느림
  - ❌ 메모리 많이 사용

**우리 선택**: 16-mixed
- Navigation task는 안정적
- 속도/메모리 이득 큼

---

## 4. Optimization 파라미터

### 4.1 `learning_rate`: 학습률

```json
{
    "learning_rate": 1e-4
}
```

**역할**:
- Gradient descent의 step size

**메커니즘**:
```python
# 학습 과정
loss = compute_loss(pred, target)
grad = backward(loss)

# Weight update
weights = weights - learning_rate * grad
                    ↑
                    이 크기
```

**영향**:
- **크면** (e.g., 1e-3):
  - ✅ 빠른 수렴
  - ❌ Overshooting (발산)
  - ❌ 불안정

- **작으면** (e.g., 1e-5):
  - ✅ 안정적
  - ❌ 매우 느린 수렴
  - ❌ Local minima에 빠짐

**우리 선택**: 1e-4 (0.0001)
- VLM frozen + Action Head 학습
- 표준적인 값
- Stable convergence

**실험 가이드**:
```
처음 학습:
  - 1e-4로 시작
  - Loss 관찰

Loss 감소 안되면:
  - 1e-3으로 증가 (더 aggressive)

Loss 발산하면:
  - 1e-5로 감소 (더 conservative)
```

---

### 4.2 `warmup_epochs`: Learning Rate Warmup

```json
{
    "warmup_epochs": 1
}
```

**역할**:
- 처음 몇 epoch 동안 LR을 서서히 증가

**메커니즘**:
```python
# Warmup schedule
Epoch 0-1 (warmup):
  LR: 0 → 1e-4 (linear increase)

Epoch 1+ (normal):
  LR: 1e-4 (constant or decay)
```

**시각화**:
```
LR
 |
 |         1e-4 _____________ (normal)
 |        /
 |       /
 |      / (warmup)
 | ___/
 |_____________________ Epochs
     0   1   2   3  ...
```

**영향**:
- **Warmup 있음**:
  - ✅ 안정적인 시작
  - ✅ Large gradient 방지
  - ✅ Better final performance

- **Warmup 없음**:
  - ⚠️ 초기 불안정 가능
  - ⚠️ 큰 gradient로 시작

**우리 선택**: 1 epoch
- Frozen VLM이라 안정적
- 간단한 warmup으로 충분

---

### 4.3 `weight_decay`: L2 Regularization

```json
{
    "weight_decay": 0.01
}
```

**역할**:
- Weight의 크기를 제한 (L2 regularization)

**메커니즘**:
```python
# Loss with weight decay
total_loss = task_loss + weight_decay * ||weights||²

Example:
  task_loss = 0.1
  ||weights||² = 100
  weight_decay = 0.01
  
  total_loss = 0.1 + 0.01 * 100 = 1.1
                      ↑
                      weight들이 작아지도록 penalty
```

**영향**:
- **크면** (e.g., 0.1):
  - ✅ Strong regularization
  - ✅ Overfitting 방지
  - ❌ Underfitting 위험
  - ❌ 학습 느림

- **작으면** (e.g., 0.001):
  - ✅ 더 많이 학습 가능
  - ❌ Overfitting 위험

**우리 선택**: 0.01
- 250 episodes에 적절
- Moderate regularization

---

### 4.4 `optimizer`: Optimization Algorithm

```json
{
    "optimizer": "adamw"
}
```

**역할**:
- Gradient descent 알고리즘 선택

**옵션**:

**AdamW** (우리):
```
- Adam + Weight decay decoupling
- Adaptive learning rate per parameter
- Momentum 사용

장점:
  ✅ Fast convergence
  ✅ Robust
  ✅ VLM에서 표준

단점:
  ⚠️ 메모리 조금 더 사용
```

**SGD**:
```
- Stochastic Gradient Descent
- Simple

장점:
  ✅ Simple
  ✅ 메모리 적게
  
단점:
  ❌ 느린 수렴
  ❌ Tuning 어려움
```

**우리 선택**: AdamW
- VLM finetuning 표준
- Proven to work

---

## 5. 정규화 파라미터

### 5.1 `gradient_clip_val`: Gradient Clipping

```json
{
    "trainer": {
        "gradient_clip_val": 1.0
    }
}
```

**역할**:
- Gradient exploding 방지

**메커니즘**:
```python
# Without clipping
grad = compute_gradient(loss)
# grad could be very large → unstable

# With clipping
grad = compute_gradient(loss)
if ||grad|| > gradient_clip_val:
    grad = grad * (gradient_clip_val / ||grad||)
    # Normalize to max 1.0
```

**시각화**:
```
Gradient norm
 |
 |    ×  Without clipping (explode!)
 |   /|
 | _/ |_____ With clipping (capped at 1.0)
 |__________ 
     Steps
```

**영향**:
- **있음** (e.g., 1.0):
  - ✅ 안정적 학습
  - ✅ Exploding gradient 방지

- **없음** (None):
  - ⚠️ 불안정할 수 있음
  - ⚠️ NaN 발생 가능

**우리 선택**: 1.0
- RNN (LSTM) 사용 → gradient exploding 가능
- **필수**

---

### 5.2 `norm_action`: Action Normalization

```json
{
    "norm_action": true,
    "norm_min": -1.0,
    "norm_max": 1.0
}
```

**역할**:
- Action 값을 [-1, 1] 범위로 정규화

**메커니즘**:
```python
# Raw action from dataset
action_raw = [1.15, -0.5]  # Mobile robot velocity

# Normalization
action_norm = (action_raw - mean) / (max - min) * 2 - 1
# Result: [-1, 1] range

# Model predicts
pred = model(image)  # [-0.8, 0.3] (normalized)

# Denormalization (inference)
action_real = (pred + 1) / 2 * (max - min) + min
```

**영향**:
- **정규화함** (true):
  - ✅ 학습 안정
  - ✅ Gradient 균등
  - ✅ 다른 dim 간 balance

- **안함** (false):
  - ❌ 특정 dim dominant
  - ❌ 학습 불균형

**우리 선택**: true
- **항상 권장**
- Neural network 표준

---

## 6. 실전 가이드

### 6.1 학습 시작 전 체크리스트

```bash
# 1. 데이터 확인
cd /home/billy/25-1kp/vla/ROS_action/mobile_vla_dataset
ls -1 episode_202512*left*.h5 | wc -l
# 예상: ~250

# 2. Config 확인
cat Mobile_VLA/configs/mobile_vla_left_only.json | grep -A 5 "episode_pattern"

# 3. GPU 메모리 확인
nvidia-smi

# 4. 이전 runs 정리 (optional)
rm -rf runs/mobile_vla_left_only
```

---

### 6.2 학습 시작

```bash
# Model_LEFT 학습
cd /home/billy/25-1kp/vla

python RoboVLMs_upstream/robovlms/train/train.py \
    --config Mobile_VLA/configs/mobile_vla_left_only.json \
    2>&1 | tee logs/train_left_$(date +%Y%m%d_%H%M%S).log
```

---

### 6.3 모니터링 포인트

#### Epoch 0-2 (초기)
```
Watch:
  - Train loss 감소하는지
  - Val loss 감소하는지
  - NaN 발생 안하는지

Expected:
  - Train: 0.5 → 0.3
  - Val: 0.6 → 0.4
```

#### Epoch 3-10 (중기)
```
Watch:
  - Train/Val gap
  - Overfitting 징후

Expected:
  - Train: 0.3 → 0.1
  - Val: 0.4 → 0.2
  - Gap < 0.1 (good)
```

#### Epoch 11-20 (후기)
```
Watch:
  - Val loss plateau
  - Best checkpoint epoch

Expected:
  - Val loss 최저점 찾기
  - Early stopping 고려
```

---

### 6.4 하이퍼파라미터 Tuning 전략

#### 문제별 해결책

**Problem 1: Loss 감소 안됨**
```
Symptoms:
  - Epoch 5 이후에도 loss > 0.5
  - Val loss 정체

Solutions:
  1. Learning rate 증가 (1e-4 → 1e-3)
  2. Accumulate_grad_batches 감소 (4 → 2)
  3. Hidden_size 증가 (512 → 768)
```

**Problem 2: Overfitting**
```
Symptoms:
  - Train loss < 0.05
  - Val loss > 0.3
  - Gap > 0.2

Solutions:
  1. Weight_decay 증가 (0.01 → 0.05)
  2. Hidden_size 감소 (512 → 256)
  3. Early stopping (best epoch 사용)
  4. Data augmentation 추가
```

**Problem 3: NaN loss**
```
Symptoms:
  - Loss suddenly → NaN
  - Training crash

Solutions:
  1. Learning rate 감소 (1e-4 → 1e-5)
  2. Gradient_clip_val 감소 (1.0 → 0.5)
  3. Precision 변경 (16-mixed → 32)
```

**Problem 4: 학습 너무 느림**
```
Symptoms:
  - 1 epoch > 10분
  
Solutions:
  1. Batch_size 증가 (2 → 4)
  2. Num_workers 증가 (4 → 8)
  3. Precision 유지 (16-mixed)
```

---

### 6.5 핵심 파라미터 우선순위

| 우선순위 | 파라미터 | 언제 조정? |
|---------|---------|----------|
| **1** | `learning_rate` | Loss 감소 안될 때 |
| **2** | `weight_decay` | Overfitting 발생 시 |
| **3** | `max_epochs` | 항상 Early stopping 고려 |
| **4** | `batch_size` | GPU 메모리 부족/여유 있을 때 |
| **5** | `hidden_size` | Capacity 조절 필요 시 |
| **6** | `warmup_epochs` | 초기 불안정할 때 |

---

## 7. 예상 결과

### Model_LEFT (250 episodes, 20 epochs)

```
Best case (Epoch 10-15):
  Train loss: 0.05-0.10
  Val loss: 0.10-0.15
  
  의미:
    - LEFT navigation 잘 학습
    - [linear_x, +linear_y] policy
    - 일관성 높음

Realistic (Epoch 15):
  Train loss: 0.10
  Val loss: 0.15
  
  충분히 좋음!
```

---

## 8. 최종 체크

### 학습 전

- [ ] Config에서 `episode_pattern` 확인
- [ ] `train_split=0.8` 확인
- [ ] GPU 메모리 충분한지 확인
- [ ] 로그 디렉토리 준비

### 학습 중

- [ ] Epoch 1-2에서 loss 감소 확인
- [ ] NaN 없는지 확인
- [ ] TensorBoard 모니터링
- [ ] GPU 사용률 확인

### 학습 후

- [ ] Best checkpoint 저장 확인
- [ ] Val loss curve 확인
- [ ] Overfitting 정도 확인
- [ ] Test 준비 (LEFT vs RIGHT 비교)

---

## 요약

### 필수 이해 파라미터 Top 5

1. **`window_size=8`**: History 길이 (2-3초)
2. **`learning_rate=1e-4`**: 학습 속도
3. **`weight_decay=0.01`**: Overfitting 방지
4. **`max_epochs=20`**: 학습 기간
5. **`episode_pattern`**: 데이터 필터 (LEFT only!)

### 안전한 기본값 (250 episodes)

```json
{
    "batch_size": 2,
    "accumulate_grad_batches": 4,
    "learning_rate": 1e-4,
    "weight_decay": 0.01,
    "max_epochs": 20,
    "gradient_clip_val": 1.0,
    "hidden_size": 512
}
```

**이 값으로 시작해서 조정!**

---

**준비 완료!** 학습 시작하시겠습니까? 🚀
