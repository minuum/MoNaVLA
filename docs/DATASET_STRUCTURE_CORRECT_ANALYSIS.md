# Mobile VLA 데이터셋 구조 및 학습 방법 완전 분석

**작성일**: 2026-01-11  
**목적**: Window-based Sequential Prediction의 정확한 이해

---

## 1. 데이터셋 구조

### 1.1 H5 파일 구조

```python
episode_20251119_080007_1box_hori_right_core_medium.h5
{
    'images': (18, 720, 1280, 3),  # T timesteps
    'actions': (18, 3),             # [linear_x, linear_y, angular_z]
    'language_instruction': "Navigate around the obstacle on the right side and move forward"
}
```

**핵심**: 각 episode는 **시간 순서대로** 연속된 (image, action) 쌍을 가짐

---

### 1.2 Timestep별 구조

```python
t=0: image[0] → action[0] = [0.00, 0.00, 0.0]  # 정지
t=1: image[1] → action[1] = [1.15, 0.00, 0.0]  # 직진
t=2: image[2] → action[2] = [1.15, 0.00, 0.0]  # 직진
t=3: image[3] → action[3] = [1.15, 0.00, 0.0]  # 직진
t=4: image[4] → action[4] = [0.00, -1.15, 0.0]  # 오른쪽
t=5: image[5] → action[5] = [1.15, -1.15, 0.0]  # 직진+오른쪽
...
```

**의미**: 
- **순차적 task**: 장애물을 피해서 목표로 이동
- **Action은 context-dependent**: 현재 위치와 지금까지의 trajectory에 의존

---

## 2. Window-based Prediction 방식

### 2.1 설정

```python
window_size = 8  # History window
fwd_pred_next_n = 5  # Future action prediction
```

**총 필요 프레임**: `8 + 5 = 13` frames

---

### 2.2 Sample 생성 방식

#### Example Window

```python
# Episode에서 start_frame=3으로 샘플 생성

[History: 8 frames]
t=3: image[3], action[3] = [1.15, 0.00, 0.0]
t=4: image[4], action[4] = [0.00, -1.15, 0.0]
t=5: image[5], action[5] = [1.15, -1.15, 0.0]
t=6: image[6], action[6] = [1.15, -1.15, 0.0]
t=7: image[7], action[7] = [1.15, -1.15, 0.0]
t=8: image[8], action[8] = [1.15, -1.15, 0.0]
t=9: image[9], action[9] = [1.15, -1.15, 0.0]
t=10: image[10], action[10] = [1.15, -1.15, 0.0]

[Future: 5 frames - Prediction Target]
t=11: image[11], action[11] = [?, ?]  ← 예측!
t=12: image[12], action[12] = [?, ?]  ← 예측!
t=13: image[13], action[13] = [?, ?]  ← 예측!
t=14: image[14], action[14] = [?, ?]  ← 예측!
t=15: image[15], action[15] = [?, ?]  ← 예측!
```

---

### 2.3 모델 Input/Output

#### Input

```python
{
    'rgb': images[3:11],  # 8 frames (window_size)
    'text': "Navigate RIGHT",  # Language instruction
    'action': actions[3:16],  # 13 actions (context)
}
```

#### Output (Prediction Target)

```python
# Action Chunk Prediction
action_chunck: [
    actions[11:16],  # Chunk at t=11
    actions[12:17],  # Chunk at t=12
    actions[13:18],  # Chunk at t=13
    ...
]
```

**핵심**: 
- **단일 action이 아님**
- **여러 timestep의 action chunk를 예측**
- **Sliding window 방식**

---

## 3. Dataset Loader 동작 방식

### 3.1 Random Sampling

```python
# __getitem__(idx)
1. Random episode 선택
   ep_idx = random.choice(episodes)

2. Random start frame 선택  
   start_frame = random.randint(0, len(episode) - 13)

3. Window 생성
   images = episode[start_frame : start_frame+13]
   actions = episode[start_frame : start_frame+13]
   
4. Instruction 로드
   lang = episode['language_instruction']
```

**목적**: 
- **Temporal diversity** 확보
- **Overfitting 방지**
- **모든 timestep에서 학습**

---

### 3.2 Collater: Chunk 생성

```python
# collater(batch)

# Input tensors
images: (B, 13, C, H, W)
actions: (B, 13, 2)

# Process
1. Split into history + future
   history_images = images[:, :8]  # (B, 8, C, H, W)
   
2. Create action chunks using unfold
   action_chunck = actions.unfold(1, fwd_pred_next_n, 1)
   # (B, T-5+1, 5, 2) = (B, 9, 5, 2)
   
3. Output
   {
       'rgb': history_images,  # (B, 8, C, H, W)
       'action_chunck': action_chunck,  # (B, 9, 5, 2)
       'text': text_tokens
   }
```

---

## 4. 학습 목표: Action Chunk Prediction

### 4.1 모델이 학습하는 것

```python
Given:
  - Images[t-7:t]  (8 frames of history)
  - Instruction: "Navigate RIGHT"
  - Action history[t-7:t]

Predict:
  - Actions[t+1:t+6]  (5 future actions)
```

**NOT**:
```python
# ❌ 잘못된 이해 (제 실수)
Given: Random image + instruction
Predict: Single average action
```

**Correct**:
```python
# ✅ 올바른 이해
Given: 8-frame history + instruction
Predict: 5-frame future action sequence
```

---

### 4.2 Instruction의 역할

**Episode-level guidance**:

```
Instruction: "Navigate RIGHT"

→ Episode 전체의 고수준 의도
→ 각 timestep에서:
   - t=0: 직진 시작
   - t=1-3: 계속 직진
   - t=4: 오른쪽 회전 시작 ← Instruction 반영!
   - t=5-18: 오른쪽으로 이동
```

**Timestep-level conditioning**:

```python
# History 보고 현재 상태 파악
if "이미 오른쪽으로 돌았다":
    action = [1.15, -1.15]  # 계속 오른쪽으로

# Instruction 보고 방향 확인  
if instruction == "Navigate RIGHT":
    # 오른쪽 맞음, 계속 진행
else:
    # 왼쪽이어야 함, 방향 조정
```

---

## 5. 잘못 이해했던 부분 vs 올바른 이해

### 5.1 Episode 평균 비교 (❌ 틀림)

```python
# 제가 했던 분석
LEFT episodes 평균:  [1.02, +0.64]
RIGHT episodes 평균: [1.02, -0.26]

→ "모델이 이거를 구분해야 한다"
```

**문제점**:
- Episode 평균은 **학습 목표가 아님**
- 각 timestep은 **다른 context**를 가짐
- **Sequential dependency 무시**

---

### 5.2 Window-based Sequential Prediction (✅ 맞음)

```python
# 올바른 이해
Sample 1:
  History: images[0:8] + actions[0:8]
  Instruction: "RIGHT"
  Target: actions[8:13]
  
Sample 2:
  History: images[5:13] + actions[5:13]
  Instruction: "RIGHT"  # 같은 instruction
  Target: actions[13:18]  # 다른 target! (다른 context)
```

**핵심**:
- **같은 instruction**이라도
- **다른 history**면
- **다른 action** 예측해야 함

---

## 6. Instruction Grounding 실패의 진짜 의미

### 6.1 기존 해석 (부분적으로만 맞음)

```python
"LEFT와 RIGHT instruction을 주면 동일한 action 출력"
difference = 0.000
```

**문제**: 
- Random 이미지로 테스트했음
- History가 없었음
- **Out-of-distribution test**

---

### 6.2 올바른 해석

**Test 조건**:
```python
image = random_image(seed=42)  # ← OOD!
history = None  # ← No context!
instruction_left = "Navigate LEFT"
instruction_right = "Navigate RIGHT"
```

**모델 입장**:
```python
# VLM이 frozen → instruction embedding 동일
emb_left ≈ emb_right

# History 없음 → context 없음
# Random image → 학습 데이터와 다름

# → Default action 출력
action = [0.234, -0.156]  # 모든 경우
```

---

### 6.3 올바른 테스트 방법

```python
# 실제 validation sample 사용
sample_left = dataset[left_episode_idx]
  history_images = sample['rgb'][:8]
  instruction = "Navigate LEFT"
  target = sample['action_chunck']

pred_left = model(history_images, instruction)

# 다른 sample
sample_right = dataset[right_episode_idx]
  history_images = sample['rgb'][:8]  # 다른 history!
  instruction = "Navigate RIGHT"
  target = sample['action_chunck']

pred_right = model(history_images, instruction)

# 비교
if instruction은 다르지만 history가 비슷하면:
  → pred도 달라야 함 (instruction grounding)
```

---

## 7. 학습이 잘 되었는지 확인하는 방법

### 7.1 Val Loss 분석 (현재)

```python
Val Loss = 0.093
Val RMSE = 0.270
```

**의미**:
- 모델이 **action chunk를 어느 정도 예측**함
- 하지만 **instruction grounding 여부는 모름**

---

### 7.2 Instruction Grounding 확인 (필요)

```python
# Test 1: 같은 history, 다른 instruction
sample = get_validation_sample(idx=42)
history = sample['rgb']  # 고정

pred_left = model(history, "Navigate LEFT")
pred_right = model(history, "Navigate RIGHT")

if |pred_left - pred_right| > threshold:
    print("✅ Instruction grounding 작동")
else:
    print("❌ Instruction 무시")
```

```python
# Test 2: Ablation by instruction type
left_samples = [s for s in val_dataset if 'left' in s['lang']]
right_samples = [s for s in val_dataset if 'right' in s['lang']]

# LEFT instruction samples에서 linear_y 예측값 분포
pred_left_y = [model(s)['action'][:, 1].mean() for s in left_samples]

# RIGHT instruction samples에서 linear_y 예측값 분포
pred_right_y = [model(s)['action'][:, 1].mean() for s in right_samples]

# 비교
if mean(pred_left_y) > mean(pred_right_y):
    print("✅ LEFT는 +y, RIGHT는 -y 예측 (맞음)")
else:
    print("❌ Instruction 구분 못함")
```

---

## 8. 결론 및 다음 단계

### 현재 이해 수정

| 항목 | 잘못된 이해 | 올바른 이해 |
|------|------------|----------|
| **학습 목표** | Episode 평균 맞히기 | **Window-based action sequence 예측** |
| **Instruction** | 단일 action 결정 | **Episode-level context conditioning** |
| **Test 방법** | Random image + inst | **Validation sample로 제대로 테스트** |

---

### 다음 단계

**1. 올바른 Instruction Grounding Test** (1시간)
```python
# Validation dataset 사용
# 실제 history로 테스트
# LEFT vs RIGHT 예측 비교
```

**2. Frozen VLM 문제 여전히 존재** (구조적)
```python
# History가 있어도
# VLM frozen → emb_left ≈ emb_right
# Action Head → 여전히 구분 어려움
```

**3. 해결책: LoRA Fine-tuning** (필수)
```python
# VLM의 text embedding 학습
# "LEFT" ≠ "RIGHT" in embedding space
# → Instruction grounding 향상
```

---

**최종 판단**:
- ✅ 데이터셋 구조 이해 완료
- ✅ Window-based prediction 이해 완료
- ⚠️ 테스트 방법 수정 필요 (Validation set으로)
- ❌ Frozen VLM 문제 여전히 존재 → LoRA 필수
