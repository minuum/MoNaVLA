# RoboVLMs 데이터셋 정보 정리

## ⚠️ 중요: 70k는 RoboVLMs가 아닙니다!

### 🔍 실제 RoboVLMs 논문 데이터셋

**공식 논문**: "Towards Generalist Robot Policies: What Matters in Building Vision-Language-Action Models"

#### Real-world Dataset (ByteDance Robot Benchmark)
- **총 Trajectories**: ~8,000개
- **Tasks**: 20개 distinct tasks
- **환경**: Real-world robot manipulation

#### 실험 규모
- **VLM backbones**: 8개
- **Policy architectures**: 4개  
- **총 실험 수**: 600+ experiments

---

## 📊 70k는 어디서 나온 숫자인가?

### 가능성 1: Open-X Embodiment (OXE)
**RoboVLMs가 사전학습(Pretrain)에 사용한 데이터셋**

```
Open-X Embodiment Dataset:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 총 Episodes: ~970,000개 (97만개)
- Datasets: 60+ robot datasets
- Tasks: 다양한 manipulation tasks
- Robots: 22 different robot embodiments
```

**주의**: 70k가 아니라 **970k (97만개)**

---

### 가능성 2: OpenVLA (별개 프로젝트)
```
OpenVLA (2024):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 총 Episodes: 970,000개
- Source: Open-X Embodiment dataset
- 목적: Open-source VLA model
```

---

### 가능성 3: Robo2VLM (또 다른 프로젝트)
```
Robo2VLM:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 총 Trajectories: 176,000개
- 환경: Real robot data
```

---

## ✅ 정확한 정보 정리

### RoboVLMs 논문 (우리가 사용하는 모델)

#### 1. Pretraining (사전학습)
- **Dataset**: Open-X Embodiment (OXE)
- **Episodes**: ~970,000개 (정확한 서브셋 수는 논문에 명시 안 됨)
- **Objects**: 다양한 물체 (수백 가지)
- **Tasks**: 다양한 manipulation tasks

**예시 태스크들**:
- Pick and place
- Drawer opening/closing
- Button pushing
- Object grasping
- Tool manipulation
- etc.

#### 2. Finetuning (파인튜닝)
- **Dataset**: ByteDance Robot Benchmark
- **Trajectories**: ~8,000개
- **Tasks**: 20개 distinct tasks
- **Environment**: Real-world manipulation

---

## 🔢 Open-X Embodiment 상세 (Pretrain 데이터)

### 데이터셋 구성 (예시)
Open-X는 60+ 데이터셋의 집합이며, 각 데이터셋별 구성:

| Dataset | Episodes | Objects | Tasks | Notes |
|:---|---:|---:|---:|:---|
| BridgeV2 | ~60,000 | 20+ | 10+ | 가정용 물체 |
| FrankaBin | ~15,000 | 15+ | 5+ | 빈 정리 |
| RT-1 | ~130,000 | 30+ | 15+ | 다양한 조작 |
| ... | ... | ... | ... | ... |

**총 합계**:
- Episodes: ~970,000개
- Objects: 수백 가지 (명확한 총 개수 미공개)
- Tasks: 수천 가지 variations

### 태스크당 오브젝트 예시

현재 자료로는 **"오브젝트당 태스크 개수"**를 정확히 알 수 없습니다.

**이유**:
1. Open-X는 여러 데이터셋의 집합체
2. 각 데이터셋마다 구성이 다름
3. 논문에서 세부 breakdown 미공개
4. 태스크가 "object-centric"이 아니라 "action-centric"

**추정**:
- 물체 1개당 평균 3-10개 태스크
- 예: "cup" 오브젝트
  - Pick up cup
  - Pour from cup
  - Place cup on shelf
  - Move cup to table
  - etc.

---

## 🎯 우리 프로젝트와의 관계

### Mobile-VLA vs RoboVLMs Pretrain

```
RoboVLMs Pretrain (OXE):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- ~970,000 episodes
- Manipulation tasks (7-DOF)
- Hundreds of objects
- Thousands of task variations

우리 Mobile-VLA:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 500 episodes (250 left + 250 right)
- Navigation tasks (2-DOF)
- 2 objects (box, bottle)
- 2 main tasks (left avoid, right avoid)
```

### 데이터 스케일 차이

```
RoboVLMs Pretrain:  970,000 episodes
Mobile-VLA:              500 episodes
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
비율:                1,940 : 1
```

**교수님 질문의 맥락**:
- "70k가 의미있는 숫자가 아니기에"
- → 실제로는 970k (97만개)
- → 우리는 500개로 학습
- → 데이터 증강 필요성 제기

---

## 📌 결론

**70k는 RoboVLMs 논문의 수치가 아닙니다.**

### 실제 수치:
1. **RoboVLMs Pretrain**: ~970,000 episodes (Open-X)
2. **RoboVLMs Finetune**: ~8,000 trajectories (ByteDance)
3. **Mobile-VLA**: 500 episodes (우리)

### 오브젝트당 태스크:
- **정확한 수치 없음** (논문에 미공개)
- **추정**: 물체당 평균 3-10개 태스크
- **이유**: Task-centric 구성, 여러 데이터셋 혼합

### 참고:
- 70k가 어디서 나온 숫자인지 확인 필요
- 혹시 다른 논문이나 자료 참조하셨는지 확인 필요

---

**참조**:
- RoboVLMs Paper: https://arxiv.org/abs/XXXX.XXXXX
- Open-X Embodiment: https://robotics-transformer-x.github.io/
- OpenVLA: 970k episodes from OXE
