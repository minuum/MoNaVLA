# 6-7 DoF Manipulation vs 2 DoF Navigation: Action Space 비교

**작성일**: 2026-01-12 01:05  
**목적**: Manipulation task의 실제 액션값과 우리 navigation task 비교

---

## 📊 Action Space 비교

### 1. 6-7 DoF Manipulation (RoboVLMs, OpenVLA, RT-2)

#### Action Representation

```python
# 일반적인 7-DoF manipulation action
action = [
    delta_x,      # End-effector position change (m)
    delta_y,      # End-effector position change (m)
    delta_z,      # End-effector position change (m)
    delta_roll,   # Orientation change (rad)
    delta_pitch,  # Orientation change (rad)
    delta_yaw,    # Orientation change (rad)
    gripper       # Gripper state (binary or continuous)
]

# 또는 absolute position
action = [
    x,      # Absolute position (m)
    y,      # Absolute position (m)
    z,      # Absolute position (m)
    roll,   # Absolute orientation (rad)
    pitch,  # Absolute orientation (rad)
    yaw,    # Absolute orientation (rad)
    gripper # 0 (open) or 1 (close)
]
```

#### 실제 값 범위 (CALVIN/Open X-Embodiment 기준)

```python
# Delta position (relative)
delta_position:
  - x, y, z: [-0.05, +0.05] m  (±5cm per step)
  - Common range: [-0.02, +0.02] m

# Delta orientation
delta_orientation:
  - roll, pitch, yaw: [-0.1, +0.1] rad  (±5.7°)
  
# Gripper
gripper:
  - Binary: {0, 1}
  - Or continuous: [-1, +1]

# Normalization
norm_min: -1.0
norm_max: +1.0
```

#### 실제 데이터 예시 (CALVIN)

```python
# Pick and place task
Episode:
  t=0: [0.00, 0.00, 0.02, 0.0, 0.0, 0.0, 0.0]  # Move up
  t=1: [0.01, 0.00, 0.00, 0.0, 0.0, 0.0, 0.0]  # Move forward
  t=2: [0.00, 0.00, -0.02, 0.0, 0.0, 0.0, 0.0] # Move down
  t=3: [0.00, 0.00, 0.00, 0.0, 0.0, 0.0, 1.0]  # Close gripper
  t=4: [0.00, 0.00, 0.02, 0.0, 0.0, 0.0, 1.0]  # Lift up
  ...

특징:
  - Continuous values (delta movements)
  - Small incremental changes
  - Smooth trajectories
  - Fine-grained control
```

---

### 2. 2 DoF Navigation (우리)

#### Action Representation

```python
# Velocity-based control
action = [
    linear_x,  # Forward velocity (m/s)
    linear_y   # Lateral velocity (m/s)
]

# 실제 값 (우리 데이터)
linear_x: {0.00, 1.15} m/s  ← 2개 값만!
linear_y: {-1.15, 0.00, +1.15} m/s  ← 3개 값만!

# Combinations: 2×3 = 6 discrete actions
```

#### 실제 데이터 분석 결과

```python
# LEFT episodes (1800 frames)
Linear X distribution:
  - 0.00 m/s:  11.1% (정지)
  - 1.15 m/s:  88.9% (전진)

Linear Y distribution:
  - -1.15 m/s: 16.7% (오른쪽)
  -  0.00 m/s: 38.9% (중립)
  - +1.15 m/s: 44.4% (왼쪽)

Coverage: 100% discrete!
```

---

## 🔍 핵심 차이점

### Position vs Velocity

| 측면 | 6-7 DoF (Position) | 2 DoF (Velocity) |
|------|-------------------|------------------|
| **Type** | Delta Position | Velocity |
| **Unit** | Meters (m) | Meters/Second (m/s) |
| **Control** | Position control | Velocity control |
| **Integration** | Position → absolute | Velocity → position (적분) |
| **Feedback** | End-effector pose | Odometry/IMU |

#### Position-based (Manipulation)

```python
# Control loop
current_pos = get_end_effector_pos()  # [x, y, z, ...]
target_pos = current_pos + action     # Add delta
move_to(target_pos)                   # Move to target

# 특징
- Absolute positioning
- Precise endpoint control
- No drift (closed-loop)
```

#### Velocity-based (Navigation)

```python
# Control loop
velocity = action  # [linear_x, linear_y]
publish_velocity(velocity)  # Continuous command
# Robot integrates velocity over time

# 특징
- Open-loop (without odometry feedback)
- Position = ∫ velocity dt
- Potential drift
- Simpler control
```

---

### Continuous vs Discrete

| 측면 | 6-7 DoF | 2 DoF |
|------|---------|-------|
| **Data** | Continuous | **Discrete** |
| **Values** | 무한 (실수) | 6개 (2×3) |
| **Learning** | Regression | Classification 가능 |
| **Resolution** | Fine-grained | Coarse-grained |

#### Manipulation: Continuous가 필수

```python
# Pick object at (0.35, 0.12, 0.05)
action = [+0.015, +0.003, -0.008, ...]

# 왜 continuous?
- 물체 위치가 continuous
- Fine manipulation 필요
- Smooth trajectory 중요
- 0.01m 단위로 제어

→ Regression 필수!
```

#### Navigation: Discrete로 충분

```python
# Navigate around obstacle
action = [1.15, +1.15]  # Forward + Left

# 왜 discrete?
- 속도 명령만 필요
- Coarse control로 충분
- Binary decisions (left/right)
- 1.15 m/s 고정 속도

→ Classification 가능!
```

---

## 📈 실제 데이터 비교

### CALVIN (Manipulation)

```python
# Episode statistics (추정)
Action distribution:
  delta_x: Gaussian(-0.02, 0.02) → Continuous!
  delta_y: Gaussian(-0.02, 0.02) → Continuous!
  delta_z: Gaussian(-0.02, 0.02) → Continuous!
  gripper: {0, 1}                → Binary!

Unique values per dimension: 1000+
Continuous ratio: 99%+
```

### Our Data (Navigation)

```python
# Episode statistics (실제)
Action distribution:
  linear_x: {0.00, 1.15}           → Discrete!
  linear_y: {-1.15, 0.00, +1.15}  → Discrete!

Unique values: 6 (2×3)
Continuous ratio: 0%!
```

---

## 🎯 설계 비교

### Manipulation Task 설계 (RoboVLMs)

```python
# Model
class ManipulationHead(nn.Module):
    def forward(self, hidden):
        action = self.mlp(hidden)  # (B, 7)
        return action  # Continuous output

# Loss
loss = MSELoss(action_pred, action_target)
# or HuberLoss for robustness

# 이유
- Data is continuous
- Regression is optimal
- Fine control needed
```

**정당성**: ✅ Data가 continuous → Regression 적합

---

### Navigation Task 설계 (우리 - 현재)

```python
# Model (현재)
class NavigationHead(nn.Module):
    def forward(self, hidden):
        action = self.mlp(hidden)  # (B, 2)
        return action  # Continuous output

# Loss
loss = MSELoss(action_pred, action_target)

# 문제
- Data is discrete (100%)
- But using regression
- Mismatch!
```

**문제**: ❌ Data가 discrete → Classification이 더 적합

---

### Navigation Task 설계 (제안)

```python
# Model (제안)
class NavigationHead(nn.Module):
    def forward(self, hidden):
        logits = self.classifier(hidden)  # (B, 6)
        return logits  # 6-class classification

# Loss
loss = CrossEntropyLoss(logits, target_class)

# 장점
- Data is discrete
- Classification is optimal
- Perfect alignment
```

**정당성**: ✅ Data가 discrete → Classification 적합

---

## 💡 왜 Manipulation은 Continuous인가?

### 이유 1: Task 특성

```python
# Manipulation
"Pick the red cup at (x, y, z)"

→ Object position은 continuous
→ End-effector도 continuous로 제어
→ 무한한 가능성

# Navigation
"Navigate LEFT around obstacle"

→ Direction은 discrete (LEFT/RIGHT)
→ Speed는 고정 (1.15 m/s)
→ 6개 조합만
```

### 이유 2: Control 방식

```python
# Manipulation: Position control
set_position([0.35, 0.12, 0.05])
→ 0.001m 단위 정밀도
→ Continuous 필수

# Navigation: Velocity control
set_velocity([1.15, 0.0])
→ High-level command
→ Discrete로 충분
```

### 이유 3: Hardware

```python
# Robot arm
- Servo motors with encoders
- Position feedback
- High precision (0.1mm)
→ Continuous control

# Mobile base
- Wheel motors
- Velocity control
- Lower precision (10cm)
→ Discrete commands 가능
```

---

## 🔍 우리 Task의 특수성

### Navigation with Fixed Speeds

```python
# 일반적인 navigation
action = [v_linear, v_angular]  # Continuous
v_linear: [0, 1.0] m/s
v_angular: [-2.0, +2.0] rad/s

→ 여전히 continuous!

# 우리 data
action = [linear_x, linear_y]  # Discrete!
linear_x: {0.0, 1.15}
linear_y: {-1.15, 0.0, +1.15}

→ 완전히 discrete!
```

**차이점**: 
- 일반 navigation: Continuous velocity
- 우리: Pre-defined velocity levels
- **이유**: 데이터 수집 방식 (joystick or preset commands)

---

## 📊 종합 비교표

| 측면 | Manipulation (6-7 DoF) | Navigation (우리, 2 DoF) |
|------|------------------------|-------------------------|
| **Task** | Pick, place, manipulate | Navigate, avoid obstacles |
| **DoF** | 6-7 (arm + gripper) | 2 (forward + lateral) |
| **Control** | Position | Velocity |
| **Unit** | Meters (delta) | Meters/Second |
| **Range** | [-0.05, +0.05] m | {0, 1.15} × {-1.15, 0, +1.15} |
| **Data** | Continuous | **Discrete (100%)** |
| **Unique** | 1000+ values | **6 values (2×3)** |
| **Model** | Regression | **Classification 권장** |
| **Loss** | MSE/Huber | **CrossEntropy 권장** |
| **Precision** | High (mm) | Low (cm) |
| **Feedback** | Closed-loop | Open-loop |

---

## 🎊 최종 결론

### Manipulation (6-7 DoF)

```
✅ Continuous regression 정당화:
  1. Data is continuous
  2. Fine position control needed
  3. Object locations are continuous
  4. High precision required
  
→ MSE/Huber loss optimal
```

### Navigation (우리, 2 DoF)

```
⚠️ Continuous regression 문제:
  1. Data is 100% discrete
  2. Only 6 possible actions
  3. Fixed velocity levels
  4. Coarse control sufficient
  
→ Classification이 더 적합!

현재: Regression (mismatch)
제안: 6-class classification
```

---

## 💡 권장 사항

### Option A: Discrete Classification (최적)

```python
# Perfect for our discrete data
Classes: 6 (2×3)
Loss: CrossEntropyLoss
Output: Direct action selection
```

### Option B: Continuous + Quantization (현재 임시)

```python
# Works but suboptimal
Model: Regression
Post-process: Round to {0, 1.15} × {-1.15, 0, +1.15}
```

---

## 📈 다음 단계

1. **현재 Model_LEFT/RIGHT 사용**
   - Quantization으로 discrete 값 생성
   - 임시로 작동 가능

2. **다음 버전: Classification 재설계**
   - DiscreteActionHead 구현
   - 6-class classification
   - Perfect data alignment

---

**요약**:
- Manipulation: Continuous (위치 제어) ✅ Regression
- Navigation (우리): Discrete (속도 제어) ✅ Classification 권장
- **Task 특성에 따라 설계가 달라야 함!**
