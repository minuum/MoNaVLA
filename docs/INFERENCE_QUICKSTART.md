# VLA 추론 시스템 빠른 시작 가이드

## 개요
이 가이드는 Case 5 (aug_abs) 모델을 사용한 VLA 추론 시스템의 빠른 시작 방법을 제공합니다.

**핵심 특징**:
- ✅ abs_action 전략: 방향 정확도 100%
- ✅ Frozen Kosmos-2 VLM: Catastrophic Forgetting 방지
- ✅ 메모리 최적화: window_size=2 (75% 감소)
- ✅ FastAPI 서버: REST API 제공
- ✅ ROS2 통합: TurtleBot4 연동 준비

---

## 1. 설치

### 필수 패키지
```bash
pip install fastapi uvicorn pydantic torch torchvision transformers pillow pyyaml numpy
```

### 체크포인트 준비
Case 5 체크포인트가 필요합니다:
```bash
# 체크포인트 경로 확인
find RoboVLMs_upstream/runs -name "mobile_vla_kosmos2_aug_abs*" -type d

# 또는 Case 4 사용
find RoboVLMs_upstream/runs -name "mobile_vla_kosmos2_abs_action*" -type d
```

---

## 2. 로컬 추론 테스트

### 방법 1: Python 스크립트
```python
import sys
sys.path.insert(0, 'src')

from robovlms_mobile_vla_inference import MobileVLAConfig, MobileVLAInferenceSystem
import numpy as np
from PIL import Image

# 설정
config = MobileVLAConfig(
    checkpoint_path="RoboVLMs_upstream/runs/mobile_vla_kosmos2_aug_abs_20251209/.../last.ckpt",
    use_abs_action=True  # 필수!
)

# 시스템 초기화
system = MobileVLAInferenceSystem(config)
system.inference_engine.load_model()

# 이미지 로드
image = np.array(Image.open("test_image.jpg"))
system.image_buffer.clear()
for _ in range(2):  # window_size=2
    system.image_buffer.add_image(image)

# 추론 실행
actions, info = system.inference_engine.predict_action(
    system.image_buffer.get_images(),
    "Navigate to the left bottle",  # Left → +1.0
    use_abs_action=True
)

print(f"🔍 방향: Left → {info['direction']}")
print(f"🤖 예측 액션 (10개): {actions}")
print(f"⏱️  추론 시간: {info['inference_time']*1000:.2f}ms")
```

### 방법 2: CLI 도구
```bash
python scripts/inference_abs_action.py \
    --checkpoint RoboVLMs_upstream/runs/mobile_vla_kosmos2_aug_abs_20251209/.../last.ckpt \
    --image test_images/sample_left.jpg \
    --text "Navigate to the left bottle"
```

**예상 출력**:
```
Instruction: 'Navigate to the left bottle' → Direction Multiplier: 1.0
==============================
Raw Prediction (Abs): [0.25, 0.15]
Final Action: linear_x=0.250, linear_y=0.150
==============================
```

---

## 3. API 서버 구축

### 서버 시작
```bash
# 환경 변수로 체크포인트 경로 설정
export VLA_CHECKPOINT_PATH="RoboVLMs_upstream/runs/mobile_vla_kosmos2_aug_abs_20251209/.../last.ckpt"

# 서버 실행
python api_server.py
```

서버가 `http://0.0.0.0:8000`에서 실행됩니다.

### API 테스트

#### 헬스 체크
```bash
curl http://localhost:8000/health
```

**응답**:
```json
{
  "status": "healthy",
  "model_loaded": true
}
```

#### 추론 요청 (curl)
```bash
# Base64 인코딩된 이미지 사용
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "images": ["<base64_encoded_image>"],
    "instruction": "Navigate to the left bottle"
  }'
```

#### 추론 요청 (Python)
```python
import requests
import base64
import numpy as np
from PIL import Image

# 이미지 로드 및 인코딩
image = Image.open("test_image.jpg").resize((224, 224))
img_bytes = np.array(image).tobytes()
img_b64 = base64.b64encode(img_bytes).decode()

# API 호출
response = requests.post(
    "http://localhost:8000/predict",
    json={
        "images": [img_b64],
        "instruction": "Navigate to the right bottle"
    }
)

result = response.json()
print(f"액션: {result['actions']}")
print(f"추론 시간: {result['inference_time']:.3f}s")
print(f"FPS: {result['fps']:.2f}")
```

---

## 4. ROS2 통합

### ROS2 패키지 빌드
```bash
cd ROS_action
colcon build --packages-select mobile_vla_package
source install/setup.bash
```

### API 클라이언트 노드 실행
```bash
# 터미널 1: API 서버 시작
export VLA_CHECKPOINT_PATH="<체크포인트 경로>"
python api_server.py

# 터미널 2: ROS2 노드 시작
ros2 run mobile_vla_package api_client_node \
    --ros-args -p server_url:=http://localhost:8000
```

**노드 동작**:
1. 카메라 이미지 구독 (`/camera/image_raw`)
2. API 서버로 추론 요청 (300ms마다)
3. 로봇 제어 명령 발행 (`/cmd_vel`)

---

## 5. 체크포인트 경로 찾기

Case 5 체크포인트가 없다면:

### Option 1: Case 4 사용
```bash
# Case 4 체크포인트 찾기
find RoboVLMs_upstream/runs -path "*mobile_vla_kosmos2_right_only*" -name "last.ckpt"

# 설정 업데이트
export VLA_CHECKPOINT_PATH="<찾은 경로>"
```

### Option 2: Case 5 학습 실행
```bash
# Case 5 학습 설정 확인
ls Mobile_VLA/configs/mobile_vla_kosmos2_aug_abs_20251209.json

# 학습 실행 (필요시)
# (기존 학습 스크립트 참조)
```

---

## 6. 성능 벤치마크

```bash
python src/robovlms_mobile_vla_inference.py \
    --checkpoint <체크포인트 경로> \
    --benchmark
```

**예상 결과**:
```
⏱️ 벤치마크 시작 (100회)...
✅ 벤치마크 완료:
  - 평균 지연 시간: 150.23 ms
  - 최대 지연 시간: 180.45 ms
  - FPS: 6.66
```

---

## 7. 트러블슈팅

### Q1: 체크포인트를 찾을 수 없습니다
```bash
# 모든 체크포인트 확인
find RoboVLMs_upstream/runs -name "*.ckpt" | head -10

# 가장 최근 체크포인트 사용
find RoboVLMs_upstream/runs -name "last.ckpt" -type f -printf '%T@ %p\n' | sort -n | tail -1
```

### Q2: 메모리 부족
```python
# window_size 줄이기
config = MobileVLAConfig(
    window_size=1,  # 2→1 (추가 50% 감소)
    ...
)
```

### Q3: 추론 속도가 느림
- GPU 사용 확인: `torch.cuda.is_available()`
- FP16 사용 확인: 코드에 이미 적용됨
- batch_size=1 유지 (이미 최적화됨)

### Q4: 방향이 반대로 나옴
체크포인트가 abs_action이 아닐 수 있습니다:
```python
# abs_action 비활성화
config = MobileVLAConfig(
    use_abs_action=False,
    ...
)
```

---

## 8. 다음 단계

1. **로컬 테스트**: scripts/inference_abs_action.py로 샘플 이미지 테스트
2. **API 서버**: FastAPI 서버 구동 및 헬스 체크
3. **ROS2 통합**: TurtleBot4에서 실제 테스트
4. **시나리오 테스트**: 10회 반복 실행 및 성공률 측정

---

**작성일**: 2025-12-09  
**버전**: 1.0  
**기반 모델**: Case 5 (aug_abs) - Direction Accuracy 100%
