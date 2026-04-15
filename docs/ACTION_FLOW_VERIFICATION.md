# Action Flow 검증: 데이터 → 학습 → Inference → ROS2

**작성일**: 2026-01-12 00:55  
**목적**: 실제 액션 값의 전체 flow가 올바른지 검증

---

## 📊 실제 데이터 분석 결과

### LEFT Episodes (100개, 1800 frames)

```
linear_x: [0.000, 1.150] m/s
  - mean: 1.022 m/s
  - std: 0.361 m/s

linear_y: [-1.150, 1.150] m/s
  - mean: +0.319 m/s  ← 왼쪽으로!
  - std: 0.840 m/s
```

### RIGHT Episodes (100개, 1800 frames)

```
linear_x: [0.000, 1.150] m/s
  - mean: 1.022 m/s
  - std: 0.361 m/s

linear_y: [-1.150, 1.150] m/s
  - mean: -0.383 m/s  ← 오른쪽으로!
  - std: 0.767 m/s
```

### LEFT vs RIGHT 차이

```
linear_x: 동일 (1.022 m/s)
linear_y: 0.702 m/s 차이! ✅

LEFT:  [1.02, +0.32] → 직진 + 왼쪽
RIGHT: [1.02, -0.38] → 직진 + 오른쪽
```

**결론**: 데이터에 명확한 차이 있음! ✅

---

## 🔄 전체 Flow

### 1️⃣ 데이터 수집 (ROS2)

```python
# ROS2 Twist 메시지
geometry_msgs/Twist:
  linear:
    x: 1.15    # Forward speed (m/s)
    y: 0.50    # Lateral speed (m/s)  ← 왼쪽(+) / 오른쪽(-)
    z: 0.0
  angular:
    x: 0.0
    y: 0.0
    z: 0.0

# H5 파일 저장
actions: (18, 3)  # [linear_x, linear_y, angular_z]
```

**범위**:
- linear_x: [0, 1.15] m/s
- linear_y: [-1.15, +1.15] m/s

---

### 2️⃣ 학습 시 Normalization

```python
# Config 설정
{
  "norm_action": true,
  "norm_min": -1.0,
  "norm_max": 1.0
}

# Dataset에서 normalization (추정)
# 정확한 공식은 MobileVLAH5Dataset 코드 확인 필요
normalized = (action - mean) / std
또는
normalized = (action - min) / (max - min) * 2 - 1

# 결과
학습 데이터: normalized actions in [-1, 1] 범위
```

**Model 학습**:
- Input: Images
- Output: Normalized actions [-1, 1]

---

### 3️⃣ 모델 Inference

```python
# Model forward
image = preprocess(raw_image)
action_normalized = model(image)  # [-1, 1] 범위

# 예상 출력 (normalized)
LEFT model:
  action_normalized ≈ [0.5, +0.3]  # forward + left

RIGHT model:
  action_normalized ≈ [0.5, -0.3]  # forward + right
```

---

### 4️⃣ Denormalization (Inference Pipeline)

```python
# inference_pipeline.py Line 113-134
def denormalize_action(
    self,
    action_norm: torch.Tensor,
    source_min: float = -1.0,
    source_max: float = 1.0,
    target_min: float = -1.0,
    target_max: float = 1.0
) -> np.ndarray:
    """
    Denormalize action from [source_min, source_max] 
    to [target_min, target_max]
    """
    from robovlms.data.data_utils import unnoramalize_action
    
    action_denorm = unnoramalize_action(
        action_norm,
        action_min=target_min,
        action_max=target_max
    )
    
    return action_denorm
```

**기본 설정**:
- source_min/max: -1.0, 1.0 (모델 출력)
- target_min/max: -1.0, 1.0 (기본값)

**⚠️ 문제**: 
```
현재 denormalization이 [-1, 1] → [-1, 1]
→ 실제 값으로 복원 안됨!
```

---

### 5️⃣ ROS2로 전달

```python
# vla_api_client.py 또는 inference node

# Denormalized action (현재)
action = [0.5, 0.3]  # 여전히 normalized?

# Twist 메시지 publish
twist_msg = Twist()
twist_msg.linear.x = action[0]  # 0.5 (?)
twist_msg.linear.y = action[1]  # 0.3 (?)
```

---

## ⚠️ 발견된 문제

### 문제: Denormalization 안되고 있음!

```python
# 현재 inference_pipeline.py
target_min = -1.0  # 기본값
target_max = 1.0   # 기본값

→ Normalization된 값 그대로 사용 중!
```

**예상 문제**:
```
Model 출력: [0.5, 0.3] (normalized)
Denormalize: [0.5, 0.3] (변화 없음!)
ROS2로 전달: [0.5, 0.3] m/s

실제 필요: [1.0, 0.3] m/s
```

---

## ✅ 해결 방법

### Option 1: Target 범위 수정

```python
# inference_pipeline.py에서
action_real = self.denormalize_action(
    action_norm,
    source_min=-1.0,
    source_max=1.0,
    target_min=0.0,      # ← 실제 데이터 최소값
    target_max=1.15      # ← 실제 데이터 최대값
)

# 결과
action_real ≈ [1.0, 0.3] m/s ✅
```

### Option 2: Config에 실제 범위 저장

```json
{
  "norm_action": true,
  "norm_min": -1.0,
  "norm_max": 1.0,
  "action_min": [0.0, -1.15],    // ← 추가
  "action_max": [1.15, 1.15]     // ← 추가
}
```

---

## 🔍 우리 Flow가 맞는지 검증

### 현재 상태 (추정)

```
✅ 데이터 수집: [0, 1.15] × [-1.15, 1.15] m/s
✅ 학습: Normalized to [-1, 1]
✅ Model: Learns normalized
⚠️ Denormalization: 안되고 있음 (추정)
❓ ROS2 전달: Normalized 값 그대로? (확인 필요)
```

### 만약 Denormalization이 안되면?

```
ROS2로 전달되는 값:
  LEFT:  [0.5, +0.3] m/s  (normalized)
  RIGHT: [0.5, -0.3] m/s  (normalized)

실제 로봇:
  - 0.5 m/s forward (예상보다 느림)
  - 0.3 m/s lateral (예상보다 느림)
  
→ 작동은 하지만 속도가 느릴 수 있음
```

### 만약 Denormalization이 된다면?

```
ROS2로 전달되는 값:
  LEFT:  [1.0, +0.5] m/s  (real)
  RIGHT: [1.0, -0.5] m/s  (real)

실제 로봇:
  - 1.0 m/s forward (정상)
  - 0.5 m/s lateral (정상)
  
→ 정상 작동 ✅
```

---

## 💡 확인 필요 사항

### 1. Dataset Normalization 방식

```python
# MobileVLAH5Dataset 확인 필요
# 어떻게 normalize하는지?

Option A: Min-Max Normalization
  normalized = (action - min) / (max - min) * 2 - 1

Option B: Z-score Normalization
  normalized = (action - mean) / std

→ Config의 norm_min, norm_max와 연결
```

### 2. Inference Denormalization 확인

```python
# inference_pipeline.py predict() 메서드
# 실제로 denormalize되는지?

# 테스트 필요
model = MobileVLAInferencePipeline(checkpoint, config)
action = model.predict(image, "Navigate LEFT")

print(f"Action: {action}")
print(f"Range check: [{action.min()}, {action.max()}]")

Expected:
  - If normalized: [-1, 1] 범위
  - If denormalized: [0, 1.15] 범위
```

### 3. ROS2 Client 확인

```python
# vla_api_client.py
# Denormalization step이 있는지?

# API response
response = requests.post("/predict", json={...})
action = response.json()["action"]

# 이 action이 normalized인지 real인지?
```

---

## 🎯 권장 조치

### Immediate Check

```bash
# 1. Dataset normalization 방식 확인
grep -n "normalize" RoboVLMs_upstream/robovlms/data/mobile_vla_h5_dataset.py

# 2. Inference denormalization 확인
grep -n "denormalize\|unnormalize" Mobile_VLA/inference_pipeline.py

# 3. API client 확인
grep -n "action" ros2_client/vla_api_client.py
```

### Test Script

```python
# test_action_range.py

# Load model
model_left = load("left_best.ckpt")

# Test
image = load_test_image()
action = model_left.predict(image)

print(f"Action: {action}")
print(f"  linear_x: {action[0]:.3f}")
print(f"  linear_y: {action[1]:.3f}")

# Check range
if -1 <= action[0] <= 1:
    print("  → Normalized! Need denormalization")
elif 0 <= action[0] <= 1.15:
    print("  → Denormalized! Good!")
```

---

## 📋 최종 답변

### "실제 액션값이 몇인데 우리 플로우에 맞아?"

**실제 데이터 범위**:
```
linear_x: [0, 1.15] m/s
linear_y: [-1.15, 1.15] m/s

LEFT 평균:  [1.02, +0.32] m/s
RIGHT 평균: [1.02, -0.38] m/s
```

**학습 시**:
```
✅ Normalize to [-1, 1]
✅ Model learns normalized
```

**Inference 시** (확인 필요 ⚠️):
```
❓ Denormalization 되는지?
  - 안되면: [0.5, 0.3] (느림)
  - 되면: [1.0, 0.3] (정상) ✅
```

**Flow 검증 필요**:
1. Dataset normalization 공식
2. Inference denormalization 실행 여부
3. ROS2로 전달되는 실제 값

**결론**:
- 데이터 자체는 올바름 ✅
- Normalization은 작동 중 ✅
- **Denormalization 확인 필요** ⚠️
- 작동은 하겠지만 속도가 느릴 수 있음

---

**다음 단계**: 
1. Inference pipeline 테스트
2. 실제 출력 값 범위 확인
3. 필요시 denormalization 수정
