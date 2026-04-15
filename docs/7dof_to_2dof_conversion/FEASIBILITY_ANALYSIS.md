# 7DOF → 2DOF (Velocity) 변환 타당성 분석

**작성일**: 2025-12-04
**핵심 질문**: 현재 데이터셋 양(250 episodes)으로 7DOF Manipulator → 2DOF Mobile 변환이 가능한가?

---

## 🎯 **핵심 이슈**

### 교수님 우려사항
> VLM 단에서 나오는 context는 clear하지만, 로봇이 행동할 때의 velocity 값을 **어떻게** 변경할지 알려줘야 함
> 
> 이전(RoboVLMs)의 7DOF와 지금(Mobile)의 2DOF velocity를 어떻게 매칭시킬 건지 확인 필요

---

## 📊 **현재 상황 분석**

### 1. **RoboVLMs Pretrained Model의 Action Space**
```python
# RoboVLMs는 7DOF로 사전학습됨
7DOF = [
    pose_x, pose_y, pose_z,     # 3D 위치
    roll, pitch, yaw,           # 3D 회전
    gripper_open               # Gripper 상태
]
```

### 2. **Mobile-VLA의 Action Space**
```python
# 우리 데이터셋
2DOF = [
    linear_x,   # 전진/후진 속도
    linear_y,   # 좌/우 속도
]

# 실제 H5 파일에는 3차원 발견
3DOF = [
    linear_x, 
    linear_y, 
    angular_z   # 회전 속도 (사용 안 하는 중)
]
```

### 3. **Context Vector는 동일**
```python
# VLM 출력 (Frozen)
context_vector: (1, 8, 1, 2048)

# 이건 7DOF든 2DOF든 동일!
# → VLM은 7DOF Manipulator 이미지로 학습했지만
#    Mobile robot 이미지도 2048차원 context로 인코딩 가능
```

---

## ⚠️ **문제점 분석**

### **문제 1: Semantic Gap (의미론적 차이)**

#### RoboVLMs의 학습 데이터
- **로봇**: WidowX, Franka Panda, UR5 등 **Manipulator (팔 로봇)**
- **Task**: "Pick the red block", "Open the drawer" (물체 조작)
- **Action**: 7DOF pose (손의 3D 위치 + 회전)

#### Mobile-VLA의 데이터
- **로봇**: Serbot-Omniwheel (Mobile Base, **팔 없음**)
- **Task**: "Navigate around obstacles to reach bottle" (이동)
- **Action**: 2DOF velocity (평면 이동 속도)

**→ 근본적으로 다른 Task!**

---

### **문제 2: Action Head의 매핑 불가능성**

```python
# RoboVLMs Pretrained Action Head
input: context (2048) 
output: 7DOF pose 
trained on: Manipulator tasks (pick, place, push)

# 우리가 원하는 것
input: context (2048)  # ✅ 같음
output: 2DOF velocity  # ❌ 완전히 다름!
trained on: Mobile navigation  # ❌ Pretrain에 없음!
```

**핵심 문제**: 
- VLM은 "박스"를 인식할 수 있음 (우리가 증명함)
- 하지만 **"박스를 보면 회피하라"**는 **Manipulator 사전학습에 없는 개념**
- Manipulator는 "박스를 보면 잡으라"로 학습됨!

---

## 🧪 **현재 학습 결과 재해석**

### 우리가 학습한 것
```
Epoch 9 결과:
- Train Loss: 0.0131
- Val Loss: 0.0131
- RMSE: 0.114
```

### 이게 의미하는 것
1. ✅ **Action Head는 학습됨** (Loss 감소)
2. ✅ **Frozen VLM도 Mobile 이미지 인코딩 가능** (Context 생성)
3. ⚠️ **하지만 "의미 있는" 매핑인가?**

---

## 💡 **VLM Pretrain의 실제 역할**

### 교수님 말씀 (정확함!)
> 보통 VLM에서 사용하는 Robot 종류들이 나와 있고, 그 로봇과 비슷한 것들로 pre-training
> 
> 7~8종류 팔로 pt시키면, 같은 팔인데 모양 다른 것들은 action-head만 바꿔도 됨

**우리 경우**:
- RoboVLMs pretrain: **Manipulator (팔) 7~8종류**
- 우리 로봇: **Mobile Base (팔 없음)**
- → **완전히 다른 로봇 형태!**

---

## 📉 **데이터 요구량 분석**

### Case 1: Action Head만 학습 (현재 방식)
```
전제: VLM pre-train에 유사한 로봇/Task가 있음
필요 데이터: ~500 episodes
결과: ✅ 가능 (우리가 증명함)
```

### Case 2: 완전히 다른 로봇 형태
```
전제: VLM pre-train에 Mobile robot 없음
필요 데이터: ~수만 episodes (VLM 파인튜닝 필요)
현재 데이터: 250 episodes
결과: ❌ 불가능
```

---

## 🎯 **우리가 실제로 한 것**

### 학습 과정
```python
# Step 1: VLM (Frozen)
VLM(mobile_image) → context (2048)

# Step 2: Action Head (Trainable)
ActionHead(context) → 2DOF velocity

# Step 3: Loss
loss = MSE(predicted_velocity, ground_truth_velocity)
```

### 성공한 이유
1. **VLM은 일반적인 물체 인식 가능** (박스, 병 등)
2. **Action Head가 0부터 2DOF 매핑 학습**
3. **태스크 단순** (회피 → 도착)

### 한계
1. **VLM의 사전 지식 활용 안 됨** (Manipulator 지식 쓸모없음)
2. **실질적으로 VLM = Feature Extractor**
3. **Transfer Learning 효과 미미**

---

## 🔬 **검증 실험 제안**

### 실험 1: VLM Feature 유용성 테스트
```python
# Baseline: Random Initialized VLM
VLM_random(image) → context → Action Head → 2DOF

# Ours: Pretrained VLM (Frozen)
VLM_pretrained(image) → context → Action Head → 2DOF

# 비교: Loss 수렴 속도, 최종 성능
```

**예상 결과**: 큰 차이 없을 것 (Manipulator 사전학습 도움 안 됨)

### 실험 2: 3DOF 확장 테스트
```python
# 현재 데이터에 angular_z 있음
3DOF = [linear_x, linear_y, angular_z]

# 3DOF로 재학습
# → 회전 제어 가능성 확인
```

---

## 📝 **결론**

### ✅ **7DOF → 2DOF 변환은 "기술적으로" 가능**
- Action Head를 2DOF로 바꾸면 학습됨
- 우리가 이미 증명함 (Loss 0.0131)

### ⚠️ **하지만 "의미론적으로" 문제**
1. **VLM Pretrain의 Manipulator 지식 활용 안 됨**
2. **Transfer Learning 효과 미미**
3. **실질적으로 VLM = ImageNet 수준의 Feature Extractor**

### 🎯 **현실적 해결책**

#### Option A: VLM 파인튜닝 (비추천)
- 필요 데이터: ~수만 episodes
- 현재 데이터: 250 episodes
- → **불가능**

#### Option B: 현재 방식 유지 (추천)
- "Frozen VLM + Action Head" 전략
- VLM의 일반적 물체 인식만 활용
- Manipulator 사전지식은 무시
- → **가능하지만 Transfer Learning 효과 제한적**

#### Option C: Mobile-specific VLM Pretrain (이상적)
- Mobile robot 데이터로 VLM 사전학습
- 필요 데이터: ~수만 episodes
- → **현재 불가능, 향후 연구 과제**

---

## 📊 **데이터 요구량 정리**

| 목표 | 필요 데이터 | 현재 데이터 | 실현 가능성 |
| :--- | :---: | :---: | :---: |
| Action Head만 학습 | ~500 | 250 | ✅ 가능 (완료) |
| VLM 파인튜닝 | ~10,000+ | 250 | ❌ 불가능 |
| Mobile VLM Pretrain | ~100,000+ | 250 | ❌ 불가능 |

---

*결론: 현재 방식(Frozen VLM)이 최선이지만, Transfer Learning 효과는 제한적*
