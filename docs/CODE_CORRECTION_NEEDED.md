# 코드 수정 되돌리기 및 재분석 보고서

## 📅 2025-12-17 21:44

## 🚨 중요한 정정

### ❌ 이전 잘못된 이해:
- DOF: linear_x, **angular_z** (틀림!)
- Action: 첫 번째만 사용 (틀림!)

### ✅ 올바른 이해 (데이터셋 코드 기준):

#### 1. **DOF**: 2 DOF = **linear_x, linear_y**
```python
# mobile_vla_h5_dataset.py Line 186-187
# Mobile VLA는 2D 액션만 사용 (linear_x, linear_y)
actions = actions[:, :2]  # (T, 2)
```

**이유**:
- 우리는 mobile robot의 **2D 평면 이동** 제어
- linear_x: 전진/후진
- linear_y: 좌/우 (holonomic robot인 경우) 또는 측면 속도

#### 2. **Action Chunk**: fwd_pred_next_n 만큼 생성
```python
# mobile_vla_h5_dataset.py Line 184
actions = f['actions'][
    start_idx + window_size:
    start_idx + window_size + action_chunk_size
]  # (T, 3) → (T, 2)
```

**의미**:
- `fwd_pred_next_n=1` → 1개 액션
- `fwd_pred_next_n=5` → 5개 액션
- `fwd_pred_next_n=10` → 10개 액션

#### 3. **추론 시 사용**:
- 모델은 `fwd_pred_next_n`개의 액션 시퀀스를 예측
- 실제 실행은 **첫 번째 액션만** 사용 (Reactive control)
- 나머지는 버림 (이것이 교수님 실험의 핵심)

---

## 📊 교수님 실험 다시 해석

### Chunk=1 (No Chunk) - Best Model
```
fwd_pred_next_n=1
→ 모델이 1개 액션 예측
→ 그 1개를 바로 실행
→ Reactive control (98% 성능 개선)
```

### Chunk=10 - Baseline
```
fwd_pred_next_n=10
→ 모델이 10개 액션 예측
→ 첫 번째만 실행, 나머지 9개 버림
→ 낭비 + 느린 반응
```

---

## 🔧 올바른 코드 수정 방향

### 1. **Action Output**: 2 DOF (linear_x, linear_y)
```python
# ✅ 올바른 코드
twist.linear.x = float(action[0])  # linear_x
twist.linear.y = float(action[1])  # linear_y  
twist.angular.z = 0.0  # Mobile VLA는 angular 사용 안 함
```

### 2. **Action Prediction**: fwd_pred_next_n개 예측
```python
# 모델 출력
action_logits = outputs.action_logits  # [batch_size, fwd_pred_next_n, 2]

# fwd_pred_next_n=1이면 [1, 1, 2]
# fwd_pred_next_n=10이면 [1, 10, 2]
```

### 3. **Action Execution**: 첫 번째만 실행
```python
# 첫 번째 액션 추출
first_action = action_logits[0, 0, :]  # [2] - [linear_x, linear_y]

# 실행
execute_action(first_action)  # 2 DOF
```

---

## 📝 데이터셋 구조 (실제 학습 코드 기준)

### HDF5 Structure:
```
- images: (T, 720, 1280, 3) RGB
- actions: (T, 3) [linear_x, linear_y, angular_z]
  → 학습 시 [:, :2]만 사용 (linear_x, linear_y)
```

### Training:
```python
# Input
images: [batch, window_size, 3, 224, 224]  # 8 frames
language: "Navigate to the left box"

# Output
actions: [batch, fwd_pred_next_n, 2]  # [linear_x, linear_y]
```

### Config Examples:
```json
{
  "fwd_pred_next_n": 1,   // Chunk=1
  "act_head": {
    "action_dim": 2       // linear_x, linear_y
  }
}
```

---

## ✅ 결론

### 제가 잘못 이해했던 부분:
1. ❌ DOF가 linear_x, angular_z라고 착각
2. ❌ Action chunk를 완전히 제거해야 한다고 착각

### 실제:
1. ✅ DOF는 **linear_x, linear_y**
2. ✅ Action chunk는 모델이 생성 (fwd_pred_next_n개)
3. ✅ **실행은 첫 번째만** (Reactive control의 핵심)

---

## 🔄 다음 단계

1. **코드 재수정 필요**
   - linear_y로 변경
   - angular_z = 0으로 설정
   
2. **이전 수정 되돌리기**
   - 잘못된 angular_z 코드 제거

3. **올바른 코드 작성**
   - 데이터셋 코드 기준으로 수정

---

**작성**: 2025-12-17 21:44  
**기준**: `Mobile_VLA/src/data/mobile_vla_h5_dataset.py`  
**상태**: 재분석 완료, 재수정 대기
