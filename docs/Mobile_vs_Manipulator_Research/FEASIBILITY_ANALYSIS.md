# Mobile vs Manipulator 연구 타당성 분석

**작성일**: 2025-12-04
**핵심 질문**: Mobile-VLA 연구가 Manipulator 대비 실현 가능한가?

---

## 🎯 **교수님 핵심 우려사항**

> Mobile 부분 연구가 아닌 Manipulator 연구가 대부분인데, 실현 가능한 문제인가?
> 
> Action head 파인튜닝해서 원하는 성능을 뽑아낼 수 있는가? (현재 데이터셋 양 기준)
> 
> Serbot-omniwheel 같은 연구가 없을 텐데 의미가 있으려면 파인튜닝에 몇만 장 필요할 듯

---

## 📚 **기존 연구 현황**

### **Manipulator VLA 연구 (주류)**

| 논문/프로젝트 | 로봇 | Task | 데이터 규모 |
| :--- | :--- | :--- | :--- |
| **RoboVLMs** | WidowX, Franka, UR5 | Pick, Place, Push | ~100K+ episodes |
| **RT-2** | Google Robot | Manipulation | ~130K episodes |
| **OpenVLA** | 7 manipulators | General manipulation | ~970K episodes |
| **Octo** | Multiple arms | Dexterous manipulation | ~800K episodes |

**공통점**:
- ✅ **팔 로봇 (Manipulator)** 중심
- ✅ **물체 조작 (Manipulation)** Task
- ✅ **수십만~백만 데이터**

---

### **Mobile VLA 연구 (소수)**

| 논문/프로젝트 | 로봇 | Task | 데이터 규모 | 비고 |
| :--- | :--- | :--- | :--- | :--- |
| **MOSAIC** | TurtleBot | Navigation | ~50K+ episodes | Sim2Real |
| **ViNT** | Mobile base | Visual navigation | ~100K trajectories | Multi-env |
| **NoMaD** | Various mobile | Navigation | ~50K+ | Diffusion |

**특징**:
- ⚠️ **연구 적음**
- ⚠️ **대부분 Simulation 중심**
- ⚠️ **Real-world deployment 사례 적음**

---

## 🔍 **우리 연구의 독특성**

### **Serbot-Omniwheel (우리 로봇)**
```python
특징:
- Omni-directional mobile base
- 카메라 기반 인식
- 2DOF velocity control
- Real-world deployment
```

### **기존 Mobile VLA와의 차이**
| 항목 | 기존 연구 | 우리 |
| :--- | :--- | :--- |
| **데이터** | Sim + Real 혼합 | Real only |
| **환경** | 다양한 환경 | 단일 환경 (실험실) |
| **태스크** | 여러 목적지 | 단일 목적지 (병) |
| **데이터 규모** | ~50K+ | **250** episodes |

---

## ⚠️ **실현 가능성 분석**

### **문제 1: 데이터 부족**

#### 기존 Mobile VLA 연구 요구량
```
MOSAIC: ~50,000 episodes (Sim2Real)
ViNT: ~100,000 trajectories
NoMaD: ~50,000+ episodes

우리: 250 episodes ❌
→ 기존 연구 대비 0.5% 수준
```

#### 교수님 예측 (정확함!)
> 의미 있으려면 파인튜닝에 몇만 장 필요

**현실**:
- VLM 파인튜닝: ~10,000 episodes 필요
- Action Head만: ~500-1,000 episodes 필요
- **우리: 250 episodes (Action Head도 부족)**

---

### **문제 2: 태스크 단순성**

#### 우리 태스크
```
Task: "Navigate around box to reach bottle"
Complexity: 단순 (회피 → 도착)
Variations: 거의 없음 (박스 위치만 변경)
```

#### 일반적 Mobile VLA
```
Task: "Go to kitchen", "Find the red chair"
Complexity: 복잡 (경로 계획, 장애물 회피, 목표 인식)
Variations: 많음 (다양한 환경, 목표, 장애물)
```

**→ 우리 태스크는 "VLA"가 필요한 복잡도가 아님!**

---

### **문제 3: VLM Pretrain 불일치**

```python
# RoboVLMs Pretrain
로봇: Manipulator (팔)
Task: Pick, Place, Open, Close
Action: 7DOF pose

# 우리 로봇
로봇: Mobile Base (팔 없음)
Task: Navigate
Action: 2DOF velocity

→ Pretrain 지식 활용 불가!
```

---

## 📊 **현재 성과 재평가**

### 우리가 달성한 것
```
✅ Frozen VLM + Action Head 학습 성공
✅ Loss 0.0131 달성
✅ RMSE 0.114 (82% 개선)
```

### 하지만 실제로는...

#### **실험 1: VLM의 실제 기여도**
```python
# 가설
Frozen VLM (Manipulator pretrain) ≈ Random VLM (no pretrain)

# 이유
1. Manipulator 지식 쓸모없음 (Mobile task)
2. 실질적으로 ImageNet-level feature만 사용
3. Transfer learning 효과 미미
```

#### **실험 2: 태스크 복잡도**
```python
# 우리 태스크
if box_detected:
    velocity = avoid_velocity
else:
    velocity = approach_velocity

# 이건 간단한 Rule-based로도 가능!
# VLA가 필요한 복잡도가 아님
```

---

## 🎯 **연구 의미 분석**

### **긍정적 측면** ✅

1. **Frozen VLM 전략 검증**
   - 데이터 부족 시 VLM 고정이 효과적
   - 250 episodes로도 Action Head 학습 가능

2. **Real-world Mobile VLA 구현**
   - 대부분 Sim인데 우리는 Real
   - Serbot-omniwheel은 독특한 플랫폼

3. **2DOF Velocity Control 성공**
   - 기존 7DOF pose → 2DOF velocity 변환
   - 실시간 제어 가능

---

### **부정적 측면** ❌

1. **VLM Pretrain 미활용**
   - Manipulator 지식 쓸모없음
   - ImageNet-level feature만 사용
   - **굳이 RoboVLMs를 쓸 이유가 없음**

2. **데이터 규모 부족**
   - 250 episodes = 기존 연구 대비 0.5%
   - 일반화 성능 의문
   - **새로운 환경/목표에 적용 불가**

3. **태스크 단순성**
   - Rule-based로도 가능한 수준
   - **VLA의 장점 활용 못 함**
   - 언어 명령도 고정 (다양성 없음)

---

## 💡 **실현 가능한 방향**

### **Option A: 데이터 증강 (시뮬레이션)**

교수님 제안:
> 데이터셋 증강 여부 파악 (500 → 5,000개)
> 시뮬레이션으로 증강

**방법**:
```python
# Gazebo/PyBullet 시뮬레이션
1. 환경 랜덤화 (박스 위치, 크기, 색상)
2. 카메라 위치 변경
3. 조명 조건 변경
4. 목표물 다양화

목표: 5,000+ episodes
→ VLM 파인튜닝 가능
```

**but, 여전히 문제**:
- Sim2Real gap
- 태스크 여전히 단순
- Manipulator pretrain 불일치

---

### **Option B: Mobile-specific VLM Pretrain**

```python
# 새로운 VLM 사전학습
데이터: Mobile robot navigation episodes
로봇: TurtleBot, Serbot 등
Task: 다양한 navigation
규모: ~100,000+ episodes

→ Mobile에 특화된 VLM
→ 우리 로봇에 Transfer learning 가능
```

**현실**:
- ❌ 데이터 수집 불가능 (시간/비용)
- ❌ 현재 연구 범위 초과

---

### **Option C: End-to-end Learning (VLM 없이)**

```python
# VLM 버리고 간단한 CNN
CNN(image) → feature → LSTM → 2DOF velocity

장점:
✅ 데이터 요구량 적음 (~1,000 episodes)
✅ 학습 빠름
✅ 추론 빠름

단점:
❌ Language conditioning 없음
❌ Zero-shot generalization 없음
```

---

## 📝 **결론**

### **현재 연구의 한계**

1. **VLM Pretrain 미활용** ⚠️
   - Manipulator → Mobile 지식 전이 안 됨
   - 실질적으로 ImageNet-level

2. **데이터 부족** ❌
   - 250 episodes (필요량의 5%)
   - 일반화 불가능

3. **태스크 단순** ⚠️
   - "VLA" 필요 없는 복잡도
   - Rule-based도 가능

---

### **실현 가능한 목표**

| 목표 | 필요 데이터 | 현재 | 가능성 |
| :--- | :---: | :---: | :---: |
| **Action Head 학습** | ~500 | 250 | ⚠️ 부족하지만 작동 |
| **VLM 파인튜닝** | ~10,000 | 250 | ❌ 불가능 |
| **일반화 (다양한 환경)** | ~50,000 | 250 | ❌ 불가능 |
| **Sim 증강 후 학습** | 5,000 (Sim) | 250 | ⚠️ Sim2Real gap |

---

### **추천 방향**

#### **단기 (현재 가능)**
1. ✅ **현재 모델로 추론 테스트**
   - 실제 로봇에서 작동하는지 확인
   - 성능 측정 (성공률, latency)

2. ✅ **Sim 데이터 증강**
   - Gazebo로 5,000 episodes 생성
   - Sim2Real 성능 확인

3. ✅ **End-to-end CNN 비교**
   - VLM 없는 baseline
   - 성능/효율성 비교

#### **장기 (연구 확장)**
1. ⏳ **다양한 태스크 추가**
   - 여러 목표물 (병, 박스, 의자 등)
   - 복잡한 환경 (다중 장애물)

2. ⏳ **Mobile-specific Pretrain**
   - Mobile robot 데이터 수집
   - 새로운 VLM 사전학습

---

*결론: 현재 데이터로는 제한적. Sim 증강 또는 단순 CNN이 더 현실적*
