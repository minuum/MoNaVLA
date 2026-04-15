# 데이터셋 증강 (Augmentation) 전략

**작성일**: 2025-12-04
**목표**: 250 episodes → 5,000+ episodes (시뮬레이션 증강)

---

## 🎯 **교수님 요구사항**

> **증강을 해서 마무리**하는 게 좋을 듯함
> 
> VLM 파인튜닝 → 500여 개 데이터셋 파인튜닝한 VLM으로 inference test
> 
> **데이터셋 증강 여부 파악 (500 → 5,000개)**
> 
> **시뮬레이션으로 증강하기**

---

## 📊 **현재 상황**

### **보유 데이터**
```
Real-world episodes: 250
평균 길이: ~18 프레임
총 데이터 포인트: ~4,500
```

### **목표**
```
증강 후: 5,000 episodes
총 데이터 포인트: ~90,000
배율: 20x
```

---

## 🔧 **증강 전략**

### **Strategy 1: 시뮬레이션 증강 (추천, 교수님 요구사항)**

#### **Gazebo/PyBullet 시뮬레이션**

```python
# 시뮬레이션 환경 구축
import pybullet as p
import pybullet_data

class MobileVLASimulation:
    def __init__(self):
        # PyBullet 초기화
        p.connect(p.GUI)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        
        # 환경 로드
        self.plane = p.loadURDF("plane.urdf")
        self.robot = self.load_serbot_omniwheel()
        
    def randomize_env(self):
        # 박스 랜덤화
        box_pos = [
            np.random.uniform(-1, 1),  # x
            np.random.uniform(-0.5, 0.5),  # y
            0.5  # z (고정)
        ]
        box_size = np.random.uniform(0.3, 0.6)
        box_color = np.random.rand(3)
        
        # 병 랜덤화
        bottle_pos = [
            np.random.uniform(1.5, 2.5),
            np.random.uniform(-0.3, 0.3),
            0.3
        ]
        
        # 조명 랜덤화
        light_intensity = np.random.uniform(0.5, 1.5)
        
        # 카메라 위치 약간 변경
        camera_height = np.random.uniform(0.3, 0.4)
        camera_pitch = np.random.uniform(-10, 10)
        
        return box_pos, bottle_pos, light_intensity
    
    def collect_episode(self, episode_id):
        # 환경 랜덤화
        box_pos, bottle_pos, light = self.randomize_env()
        
        # 초기 위치
        p.resetBasePositionAndOrientation(
            self.robot, [0, 0, 0], [0, 0, 0, 1]
        )
        
        # 에피소드 수집
        frames = []
        actions = []
        
        for step in range(100):  # 평균 18 프레임보다 길게
            # 카메라 이미지
            img = self.get_camera_image()
            
            # Action (간단한 경로 계획)
            action = self.compute_action(box_pos, bottle_pos)
            
            # 실행
            self.robot.set_velocity(action)
            p.stepSimulation()
            
            frames.append(img)
            actions.append(action)
            
            # 종료 조건
            if self.reached(bottle_pos):
                break
        
        # H5 저장
        self.save_h5(episode_id, frames, actions)
```

---

#### **증강 파라미터**

| 파라미터 | 범위 | 목적 |
| :--- | :--- | :--- |
| **Box Position** | x: [-1, 1], y: [-0.5, 0.5] | 다양한 장애물 위치 |
| **Box Size** | [0.3, 0.6]m | 크기 변화 |
| **Box Color** | RGB random | 색상 불변성 |
| **Bottle Position** | x: [1.5, 2.5], y: [-0.3, 0.3] | 목표 다변화 |
| **Lighting** | intensity [0.5, 1.5] | 조명 조건 |
| **Camera Pose** | pitch: [-10°, 10°] | 카메라 각도 |

---

#### **구현 계획**

```bash
# Step 1: 시뮬레이션 환경 구축
## Serbot-omniwheel URDF 생성
## Gazebo world 설정
Time: ~1 day

# Step 2: 랜덤화 로직 구현
## Domain randomization
## 데이터 수집 파이프라인
Time: ~0.5 day

# Step 3: 대량 데이터 생성
## 5,000 episodes 수집
## Headless mode (GUI 없이)
Time: ~1-2 days (자동)

# Step 4: Sim2Real 검증
## 10% Real data로 fine-tune
## Sim data로 pre-train → Real data로 adapt
Time: ~0.5 day
```

---

### **Strategy 2: Real-world 증강 (제한적)**

#### **Image-level Augmentation**
```python
import albumentations as A

transform = A.Compose([
    # Color augmentation
    A.ColorJitter(brightness=0.2, contrast=0.2, 
                  saturation=0.2, hue=0.1, p=0.8),
    
    # Noise
    A.GaussNoise(var_limit=(10, 50), p=0.5),
    
    # Blur
    A.GaussianBlur(blur_limit=(3, 7), p=0.3),
    
    # Lighting
    A.RandomBrightnessContrast(p=0.8),
    
    # Geometric (조심해서!)
    A.ShiftScaleRotate(shift_limit=0.05, scale_limit=0.05, 
                       rotate_limit=5, p=0.5),
])

# 적용
for episode in real_episodes:
    for frame in episode:
        # Original
        dataset.add(frame, action)
        
        # Augmented (5x)
        for _ in range(5):
            aug_frame = transform(image=frame)['image']
            dataset.add(aug_frame, action)  # action은 동일

# 결과: 250 → 1,500 episodes
```

**한계**:
- ⚠️ Action은 그대로 → Geometric aug 사용 제한적
- ⚠️ 실제 변화 제한적 (박스 위치 등은 못 바꿈)
- ⚠️ 1,500도 부족 (VLM 파인튜닝 필요: ~10,000)

---

### **Strategy 3: Hybrid (Sim + Real)**

```python
# Step 1: Sim으로 대량 생성 (4,750 episodes)
sim_data = generate_sim_data(n=4750)

# Step 2: Real데이터 유지 (250 episodes)
real_data = load_real_data()

# Step 3: 혼합 학습
## Phase 1: Sim data로 pre-train
model_pretrain = train(sim_data, epochs=5)

## Phase 2: Real data로 fine-tune
model_final = train(real_data, init_weights=model_pretrain, epochs=10)

# Step 4: Domain adaptation
## CycleGAN으로 Sim → Real 스타일 변환
## 또는 simple style transfer
```

---

## 📊 **데이터 요구량 재분석**

### **목표별 필요 데이터**

| 목표 | 필요 Episodes | 현재 | 증강 후 | 가능성 |
| :--- | :---: | :---: | :---: | :---: |
| **Action Head만** | ~500 | 250 | 5,000 | ✅ 충분 |
| **VLM 파인튜닝** | ~10,000 | 250 | 5,000 | ⚠️ 부족 |
| **VLM Pretrain** | ~100,000 | 250 | 5,000 | ❌ 불가능 |

---

### **교수님 목표 (500 → 5,000)**

```python
# 500 episodes로 VLM 파인튜닝?
실제 필요: ~10,000 episodes
증강 목표: 5,000 episodes

→ 여전히 부족!

# 대안
Option 1: 5,000으로 VLM "일부" 파인튜닝
   - 최상위 레이어만 (Top 2-3 layers)
   - LoRA 적용 (r=16 이하)
   
Option 2: Action Head만 집중
   - VLM 여전히 Frozen
   - 5,000이면 Action Head 충분
```

---

## 🔬 **Sim2Real Gap 해결**

### **문제: Sim ≠ Real**
```
시뮬레이션의 문제:
- 물리 엔진 부정확 (마찰, 관성)
- 렌더링 Quality 차이
- 센서 노이즈 없음
```

### **해결책**

#### **1. Domain Randomization**
```python
# 시뮬레이션에서 극단적으로 랜덤화
- 조명: 0.2 ~ 2.0 (매우 넓게)
- 색상: HSV 전체 범위
- 텍스처: 다양한 패턴
- 카메라 노이즈 추가

→ Real이 Sim의 subset이 되도록
```

#### **2. Domain Adaptation**
```python
# CycleGAN: Sim ←→ Real 스타일 변환
from torchvision.models import CycleGAN

# Sim 이미지를 Real 스타일로 변환
sim_image_real_style = cyclegan(sim_image)

# 이걸로 학습
```

#### **3. Real data 소량 mixing**
```python
# 90% Sim + 10% Real
train_data = concat(
    sim_data[4500],  # 90%
    real_data[250]   # 10%
)

# Real data에 높은 가중치
loss = 0.9 * loss_sim + 1.1 * loss_real
```

---

## 📝 **구현 로드맵**

### **Phase 1: 시뮬레이션 구축 (1주)**
```bash
Day 1-2: Gazebo/PyBullet 환경 설정
Day 3-4: Serbot-omniwheel 모델링
Day 5-6: 랜덤화 로직 구현
Day 7: 테스트 및 검증
```

### **Phase 2: 데이터 생성 (3일)**
```bash
Day 1: 1,000 episodes 생성 (테스트)
Day 2-3: 5,000 episodes 생성 (자동)
```

### **Phase 3: 학습 및 검증 (1주)**
```bash
Day 1-3: Sim data로 학습
Day 4-5: Real data로 fine-tune
Day 6-7: 실제 로봇 테스트
```

---

## 🎯 **현실적 목표**

### **단기 (2주 내)**
1. ✅ **Image augmentation으로 1,500 episodes**
   - Real data만 사용
   - 빠르게 가능
   - Sim2Real gap 없음

2. ⏳ **학습 및 성능 비교**
   - Baseline (250) vs Augmented (1,500)
   - 성능 향상 확인

### **중기 (1개월)**
1. ⏳ **Simulation 환경 구축**
   - PyBullet/Gazebo
   - 5,000 episodes 생성

2. ⏳ **Sim2Real 학습**
   - Domain adaptation
   - Fine-tuning

3. ⏳ **VLM 일부 파인튜닝**
   - Top layers만 (LoRA)
   - 5,000 episodes 활용

---

## 📊 **예상 성능**

| 데이터 | Episodes | VLM 상태 | 예상 성능 | Sim2Real |
| :--- | :---: | :--- | :--- | :--- |
| **현재** | 250 | Frozen | Loss 0.013 | N/A |
| **Image Aug** | 1,500 | Frozen | Loss 0.010 | ✅ 없음 |
| **Sim** | 5,000 | Frozen | Loss 0.008 | ⚠️ Gap 있음 |
| **Sim + Adapt** | 5,000 | Frozen | Loss 0.009 | ✅ 완화 |
| **Sim + Fine-tune** | 5,000 | Top layers | Loss 0.007 | ⚠️ Gap 있음 |

---

## 📝 **결론**

### ✅ **즉시 가능**
- Image augmentation (1,500 episodes, 1일)
- 학습 및 비교 (1일)

### ⏳ **단기 가능 (2주)**
- Simulation 환경 구축
- 5,000 episodes 생성

### ⚠️ **VLM 파인튜닝 제한적**
- 5,000도 부족 (이상적: ~10,000)
- Top layers만 또는 LoRA 권장

### 🎯 **추천 순서**
1. Image augmentation (즉시)
2. Simulation 구축 (2주)
3. Hybrid 학습 (Sim + Real)
4. VLM 일부 파인튜닝 (선택)

---

*다음: Image augmentation 구현 및 학습*
