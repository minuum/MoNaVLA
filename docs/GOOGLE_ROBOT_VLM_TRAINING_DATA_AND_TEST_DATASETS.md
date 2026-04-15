# Google Robot VLM - 학습 데이터 및 테스트 가능 데이터셋 가이드

**작성 일시**: 2026-01-14 13:01  
**목적**: Google Robot pretrained VLM이 어떤 데이터로 학습되었는지 확인하고, 테스트 가능한 실제 데이터셋 이미지를 찾

는 방법 제시

---

## 🤖 Google Robot Pretrained VLM 정보

### 우리가 사용하는 Checkpoint

```
파일: pretrained_ckpts/checkpoints/kosmos_ph_google-robot-post-train.pt

이름 분석:
  - kosmos: Kosmos-2 VLM backbone
  - ph: Policy Head
  - google-robot: Google Robot 환경
  - post-train: Post-training (fine-tuning)

크기: ~1.2GB
```

---

### RoboVLMs 공식 Checkpoints (HuggingFace)

**URL**: https://huggingface.co/robovlms/RoboVLMs

**제공 Checkpoints**:
1. `kosmos_ph_calvin_abcd` - CALVIN dataset (split ABCD)
2. `kosmos_ph_calvin_abc` - CALVIN dataset (split ABC)
3. `kosmos_ph_oxe-pretrain` - OXE-magic-soup dataset

**우리 checkpoint**: 위 3개에 없음 → 별도로 제공 (Google Robot 특화)

---

### 학습 데이터 추정 (RoboVLMs 논문 기반)

**Source**: [RoboVLMs Paper (arXiv:2412.14058)](https://arxiv.org/abs/2412.14058)

**논문 내용**:
> "We evaluate models on **Google Robot environments**"  
> "Post-Train on **tested RT tasks stage**"  
> "**SimplerEnv - Google Robot** benchmark"

**추론**:
```
1. Base: Kosmos-2 (일반 VLM)
   ↓
2. Pre-train: OXE dataset (cross-embodiment)
   ↓
3. Post-train: Google Robot / RT-1 tasks
   ↓
4. Result: kosmos_ph_google-robot-post-train.pt
```

**학습 데이터 (추정)**:
- **RT-1 dataset**: Google의 실제 robot manipulation data
  - 130K+ episodes
  - 700+ tasks
  - 13 robots over 17 months
  - Office kitchen environment
  
- **SimplerEnv - Google Robot scenarios**: 
  - Pick coke can
  - Open/close drawer
  - Move near object
  - Place in receptacle

---

## 📊 테스트 가능한 데이터셋

### 1. SimplerEnv - Google Robot ⭐⭐⭐⭐⭐ (최우선!)

**Source**: https://simpler-env.github.io/  
**GitHub**: https://github.com/simpler-env/SimplerEnv

**특징**:
- ✅ Google Robot manipulation tasks 시뮬레이션
- ✅ RT-1, RT-2 tasks 정확히 재현
- ✅ 설치 쉬움
- ✅ Real-time screenshot 가능
- ✅ **In-distribution for Google Robot VLM**

**Tasks**:
```
1. google_robot_pick_coke_can
2. google_robot_move_near
3. google_robot_open_drawer
4. google_robot_close_drawer
5. google_robot_place_in_receptacle
```

**설치**:
```bash
# MuJoCo 설치
conda install -c conda-forge mujoco

# SimplerEnv 설치
pip install simpler-env
```

**이미지 추출 코드**:
```python
from simpler_env.utils.env.env_builder import build_maniskill2_env
from PIL import Image
import numpy as np

# Create environment
env = build_maniskill2_env(
    "google_robot_pick_coke_can",
    obs_mode="rgbd",
    control_mode="pd_ee_delta_pose",
)

# Reset and get first observation
obs = env.reset()

# Extract RGB image
rgb_image = obs['image']['base_camera']['rgb']
img = Image.fromarray((rgb_image * 255).astype(np.uint8))
img.save('test_images/google_robot/simpler_env_sample.png')

print(f"Image size: {img.size}")
```

**장점**:
- 🟢 가장 쉬운 방법
- 🟢 정확한 Google Robot 환경
- 🟢 즉시 테스트 가능
- 🟢 In-distribution data

---

### 2. Open X-Embodiment (OXE) Dataset ⭐⭐⭐⭐

**Source**: https://robotics-transformer-x.github.io/  
**Dataset**: https://github.com/google-deepmind/open_x_embodiment

**특징**:
- ✅ 실제 robot 데이터 (real-world)
- ✅ Google Robot 데이터 포함
- ✅ 1M+ robot trajectories
- ✅ 22 robot embodiments
- ⚠️ Download 필요 (large ~TB)

**포함 데이터셋**:
```
1. fractal20220817_data - Google Robot
2. bridge_dataset - WidowX robot
3. austin_buds_dataset
4. ... (총 60개 datasets)
```

**설치**:
```bash
pip install tensorflow-datasets
```

**이미지 추출 코드**:
```python
import tensorflow_datasets as tfds
from PIL import Image
import numpy as np

# Load Google Robot dataset
dataset_name = 'fractal20220817_data'
ds = tfds.load(dataset_name, split='train[:10]')

for i, episode in enumerate(ds.take(5)):
    # Extract image from observation
    image = episode['observation']['image'].numpy()
    
    # Save as PNG
    img = Image.fromarray(image)
    img.save(f'test_images/google_robot/oxe_sample_{i}.png')
    
    # Print instruction
    instruction = episode['observation']['natural_language_instruction']
    print(f"Sample {i}: {instruction}")
```

**장점**:
- 🟢 실제 robot data
- 🟢 Google 공식 데이터
- 🟢 다양한 tasks

**단점**:
- 🔴 Download 크기 매우 큼
- 🔴 시간 오래 걸림

---

### 3. CALVIN Dataset ⭐⭐⭐

**Source**: http://calvin.cs.uni-freiburg.de/  
**Download**: http://calvin.cs.uni-freiburg.de/dataset/

**특징**:
- ✅ Table-top manipulation
- ✅ Long-horizon tasks
- ✅ ABCD 환경 variations
- ⚠️ Google Robot과 다름 (다른 setup)

**Download**:
```bash
# Task ABCD_D (가장 다양함)
wget http://calvin.cs.uni-freiburg.de/dataset/task_ABCD_D.zip
unzip task_ABCD_D.zip
```

**이미지 추출 코드**:
```python
import numpy as np
from PIL import Image

# Load CALVIN episode
data = np.load('task_ABCD_D/training/episode_0000000.npz')

# Extract RGB frames
rgb_static = data['rgb_static']  # (T, H, W, 3)

# Save first frame
img = Image.fromarray(rgb_static[0])
img.save('test_images/calvin/sample_0.png')
```

**장점**:
- 🟢 공개 download 쉬움
- 🟢 Manipulation tasks

**단점**:
- 🟡 Google Robot과 setup 다름
- 🟡 Robot embodiment 다름

---

### 4. Bridge Dataset ⭐⭐⭐

**Source**: https://rail-berkeley.github.io/bridgedata/

**특징**:
- ✅ WidowX robot
- ✅ Kitchen manipulation
- ✅ 60K+ trajectories

**설치**:
```bash
pip install tensorflow-datasets
```

**이미지 추출**:
```python
import tensorflow_datasets as tfds

ds = tfds.load('bridge_dataset', split='train[:10]')

for i, episode in enumerate(ds.take(5)):
    image = episode['observation']['image'].numpy()
    Image.fromarray(image).save(f'test_images/bridge/sample_{i}.png')
```

---

### 5. RT-1 Project Page Screenshots ⭐⭐

**Source**: https://robotics-transformer.github.io/

**방법**:
1. Project page 방문
2. Example images screenshot
3. YouTube videos → frame extraction

**장점**:
- 🟢 가장 빠름
- 🟢 Representative examples

**단점**:
- 🔴 Sample 제한적
- 🔴 다양성 부족

---

## 🎯 추천 접근 방법 (우선순위)

### 방법 1: SimplerEnv (최우선!) ⭐⭐⭐⭐⭐

**왜?**:
- ✅ 설치 가장 쉬움
- ✅ Google Robot tasks 정확히 재현
- ✅ In-distribution for Google Robot VLM
- ✅ 즉시 테스트 가능
- ✅ 다양한 tasks

**실행 계획**:
```bash
# 1. 설치
pip install simpler-env mujoco

# 2. 이미지 생성 스크립트 실행
python scripts/extract_simpler_env_images.py

# 3. Google Robot VLM 테스트
python scripts/test_google_robot_vlm_simpler_env.py
```

---

### 방법 2: OXE Dataset (실제 데이터 원하면) ⭐⭐⭐⭐

**왜?**:
- ✅ 실제 robot data
- ✅ Google 공식
- ⚠️ Download 크기 큼

**실행 계획**:
```bash
# 1. 설치
pip install tensorflow-datasets

# 2. Small subset만 다운로드
python -c "
import tensorflow_datasets as tfds
ds = tfds.load('fractal20220817_data', split='train[:10]')
# 첫 10개 episode만
"

# 3. 이미지 추출 및 테스트
python scripts/test_google_robot_vlm_oxe.py
```

---

### 방법 3: 생성 이미지 (빠른 프로토타입) ⭐⭐⭐

**이미 수행함**:
- manipulation task 이미지 생성
- Google Robot VLM 테스트 완료
- 결과: 약간 나음 (40% vs 20%)

**단점**:
- Real data 아님
- Domain gap 있을 수 있음

---

## 🔬 실험 계획

### Phase 1: SimplerEnv 이미지 테스트

```python
# 1. SimplerEnv 설치
pip install simpler-env

# 2. 5개 tasks에서 각 10장씩 추출
tasks = [
    'google_robot_pick_coke_can',
    'google_robot_move_near',
    'google_robot_open_drawer',
    'google_robot_close_drawer',
    'google_robot_place_in_receptacle',
]

# 3. Google Robot VLM 테스트
for task in tasks:
    images = extract_images(task, n=10)
    responses = test_vlm(images, prompts)
    analyze_results(responses)
```

---

### Phase 2: 비교 분석

**비교 대상**:
1. SimplerEnv (in-distribution) ← Google Robot tasks
2. 우리 Navigation (out-of-distribution) ← 복도 환경

**측정**:
- Scene recognition accuracy
- Object recognition accuracy
- Hallucination rate
- Robot understanding

**예상 결과**:
```
SimplerEnv (in-distribution):
  - Scene: 70-80% 정확
  - Objects: 50-60% 정확
  - Hallucination: 중간 정도
  - Robot: 명확히 인식
  
Navigation (out-of-distribution):
  - Scene: 0-20% 정확
  - Objects: 20-30% 정확
  - Hallucination: 매우 심각
  - Robot: 인식 못함
```

---

## 📋 다음 단계

### 즉시 실행 가능 (2-3시간)

```bash
# 1. SimplerEnv 설치
pip install simpler-env

# 2. 샘플 이미지 생성 스크립트 작성
# scripts/extract_simpler_env_images.py

# 3. Google Robot VLM 테스트
# scripts/test_google_robot_vlm_real_data.py

# 4. 결과 분석 및 문서화
```

### Optional (시간 있으면)

```bash
# OXE dataset small subset
pip install tensorflow-datasets
python scripts/extract_oxe_samples.py

# CALVIN dataset
wget http://calvin.cs.uni-freiburg.de/dataset/task_ABCD_D.zip
python scripts/extract_calvin_samples.py
```

---

## 🎊 요약

### Google Robot VLM 학습 데이터

```
1. Base: Kosmos-2 (일반 VLM)
2. Pre-train: OXE cross-embodiment data
3. Post-train: Google Robot / RT-1 tasks
   - Pick, place, move manipulation
   - Kitchen/lab environment
   - Table-top tasks
```

### 테스트 가능 데이터셋 (우선순위)

```
1. SimplerEnv ⭐⭐⭐⭐⭐
   - 가장 쉬움
   - Google Robot 정확
   - In-distribution
   
2. OXE Dataset ⭐⭐⭐⭐
   - 실제 data
   - Google 공식
   - Download 큼
   
3. CALVIN/Bridge ⭐⭐⭐
   - Manipulation tasks
   - Google Robot 아님
```

### 추천 행동

```
✅ SimplerEnv 설치 및 테스트 (최우선!)
✅ Google Robot VLM in-distribution 성능 확인
✅ Navigation vs Manipulation 비교
⚠️ OXE는 시간 있으면
```

---

**다음 문서**: Google Robot VLM SimplerEnv 테스트 결과 (예정)
