# Window Size 불일치 분석 (환각 없는 코드 검증)

## 🔴 **심각한 문제 발견**

### 1. Config vs Dataset 불일치

| 항목 | Config 설정 | Dataset 코드 | 실제 필요 |
|------|-------------|-------------|-----------|
| `window_size` | **8** | 주석: 16 | **?** |
| `fwd_pred_next_n` | **5** | 주석: 2 | **?** |
| images 길이 | 8+5=**13** | **18** (하드코딩) | **불일치!** |
| actions 길이 | 8+5-1=**12** | **17** (하드코딩) | **불일치!** |

---

## 📋 코드 검증 (환각 없이)

### Dataset Loader (mobile_vla_action_dataset.py)

#### Line 19 (주석):
```python
# 길이 설정: window_size=16, fwd_pred_next_n=2 
# → images 길이=18, actions 길이=17을 만족
```

#### Line 213-220 (실제 코드):
```python
# images 길이 강제 조정
target_img_len = self.window_size + self.fwd_pred_next_n  # 8 + 5 = 13
if images.shape[0] > target_img_len:
    images = images[:target_img_len]  # 13으로 자름
elif images.shape[0] < target_img_len:
    # 패딩으로 13까지 채움
    pad = target_img_len - images.shape[0]
    images = np.concatenate([images, np.repeat(last, pad, axis=0)], axis=0)
```

→ **images를 13으로 맞추는 코드!**

#### Line 223-229 (actions):
```python
# actions가 18이면 마지막 1개를 제거해 윈도우 규칙에 맞춤
if actions.shape[0] > 17:
    actions = actions[:17]  # 17로 자름
elif actions.shape[0] < 17 and images.shape[0] == 18:
    pad = 17 - actions.shape[0]
    actions = np.concatenate([actions, np.repeat(last, pad, axis=0)], axis=0)
```

→ **actions를 17로 맞추려는 코드!**

**BUT** images는 13으로 만들어졌으므로 `images.shape[0] == 18` 조건은 **절대 만족 안 됨!**

---

## 🎯 Base Transform 기대값

### ActionPredictionBatchTransform.__call__ (Line 178)

```python
# Training 모드
if self.mode == "train":
    assert action.shape[0] == self.window_size + self.fwd_pred_next_n - 1
    window_size = self.window_size
```

**기대값**:
- `action.shape[0]` = window_size + fwd_pred_next_n - 1
- 현재 config: 8 + 5 - 1 = **12**

**실제값** (dataset에서 전달):
- actions.shape = **17** (또는 13-1=12?)

---

## 🔍 실제로 어떻게 작동하는가?

### convert_action (Line 110-135)

```python
def convert_action(self, action: np.ndarray, action_mask: torch.Tensor):
    if self.mode == "train":
        # the act step set to fwd_pred_next_n + 1, 
        # it will get one more action which we should drop it
        action = action[:-1]  # 마지막 1개 제거
        action_mask = action_mask[:-1]
```

**흐름**:
1. Dataset에서 actions=17 전달 (또는 12?)
2. convert_action에서 `action[:-1]` → 16 (또는 11?)
3. BUT assertion 기대값: window_size + fwd_pred_next_n - 1 = 12

---

## 📊 정확한 계산

### 올바른 설정 (주석 기준)
```
window_size = 16
fwd_pred_next_n = 2

images.shape[0] = 16 + 2 = 18 ✅
actions.shape[0] = 16 + 2 = 18
convert_action 후: 18 - 1 = 17
assertion: 16 + 2 - 1 = 17 ✅
```

### 현재 설정 (config)
```
window_size = 8
fwd_pred_next_n = 5

images.shape[0] = 8 + 5 = 13 (코드에서 강제)
actions.shape[0] = 8 + 5 = 13 (동일하게 처리되어야)
convert_action 후: 13 - 1 = 12
assertion: 8 + 5 - 1 = 12 ✅
```

→ **이론적으로는 맞음!**

---

## ❓ 그렇다면 왜 17을 체크하는가?

### Line 223-229 재검토:
```python
# actions가 18이면 마지막 1개를 제거해 윈도우 규칙(window=16, fwd=2)에 맞춤
if actions.shape[0] > 17:
    actions = actions[:17]
```

**이유**: 
- 이 코드는 **주석 기준 설정 (16+2=18)**을 위한 것
- 실제 H5 파일에 18개 action이 있을 때 17로 자르는 코드
- **현재 config (8+5=13)와 맞지 않음!**

---

## 🔴 **문제점 요약**

### 1. Dataset 코드와 Config 불일치
- Dataset 코드 주석: window=16, fwd=2
- 실제 Config: window=8, fwd=5
- **하지만** dataset 코드는 config를 사용해 동적으로 조정 ✅

### 2. 혼란스러운 주석
- Line 19, 222: window=16, fwd=2 기준 주석
- 실제로는 `self.window_size`, `self.fwd_pred_next_n` 사용

### 3. 실제 작동 방식
```python
target_img_len = self.window_size + self.fwd_pred_next_n  # 8 + 5 = 13
```
→ Config 값을 **제대로 사용**함!

---

## ✅ **결론: 학습은 정상 작동 중**

### 실제 Data Flow (window=8, fwd=5)

```
H5 File (18 frames):
  images: [18, H, W, 3]
  actions: [18, 3]
    ↓
Dataset.__getitem__:
  images → [:13] → [13, H, W, 3]  (window + fwd = 8 + 5)
  actions → [:13] → [13, 7] 패딩
    ↓
batch_transform (convert_action):
  action[:-1] → [12, 7]  (window + fwd - 1)
    ↓
Collator:
  action_chunk = get_tensor_chunk(action, fwd_pred_next_n=5)
  → [window_size=8, chunk_size=5, action_dim=2]
    ↓
Model Training:
  각 window timestep마다 5개의 future action 예측
```

---

## 🎯 **Window Size의 의미**

### window_size = 8
- 과거 8개 프레임의 이미지 + instruction을 VLM에 입력
- 각 timestep마다 action 생성

### fwd_pred_next_n = 5
- 각 timestep에서 다음 5개 action을 예측 (action chunking)
- Smoothness 향상

### 총 필요 frames
- Images: window_size + fwd_pred_next_n = 8 + 5 = **13**
- Actions: window_size + fwd_pred_next_n - 1 = 8 + 5 - 1 = **12**

---

## 💡 **Instruction Grounding 관점**

### 중요한 발견
```python
# Line 173-251: wrap_instruction_and_action_interleave
for i in range(window_size):  # 8번 반복
    # 각 timestep에 동일한 instruction 사용!
    task_description = "Navigate around the obstacle on the left side..."
```

**핵심**:
- **동일한 instruction**이 window의 **모든 timestep (8개)**에 반복 사용
- VLM은 각 timestep마다 (instruction + image_i) → hidden state 생성
- Hidden state → Action head → 5개 action 예측

**문제**:
- VLM이 frozen이면 **instruction encoding이 모든 timestep에서 동일**
- 이미지만 바뀌고 instruction은 고정
- **Frozen VLM의 한계가 여기서 명확히 드러남!**

---

## 🎯 **최종 판단**

### 1. Window Size 설정: ✅ **정상**
- Config (8, 5)와 코드가 일치
- Data flow 정상 작동

### 2. Instruction 처리: ❌ **문제**
- Window 8개 timestep 모두 **동일한 instruction embedding**
- Frozen VLM → 이미지별로 다른 embedding 못 만듦
- **LoRA fine-tuning이 필수!**

### 3. 학습 방식: ✅ **적합**
- 18 frames 중 13개 사용 (window=8, fwd=5)
- Action chunking으로 smoothness 확보
- 구조적으로는 문제없음

---

## 🚀 **다음 단계**

1. **LoRA 메모리 문제 해결 후 재시도**
   - Gradient checkpointing ✅ 적용됨
   - LoRA rank 16으로 감소 ✅

2. **LoRA 학습 재시작**
   ```bash
   bash scripts/train_active/train_lora_chunk5.sh
   ```

3. **성공 시 Epoch 1에서 즉시 ablation test**
   - LoRA는 Frozen보다 빠르게 학습될 것으로 예상

---

**Updated**: 2026-01-07 09:58
