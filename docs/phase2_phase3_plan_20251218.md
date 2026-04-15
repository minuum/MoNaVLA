# 2단계: 추론 테스트 & 3단계: 실제 로봇 주행 계획

**작성일**: 2025-12-18 13:37  
**참고**: OpenVLA, RT-2, RoboFlamingo 최신 연구  
**목표**: Best Model (Left Chunk10) 배포 및 로봇 테스트

---

## 📋 전체 로드맵

```
Phase 1: 학습 (완료 ✅)
└─ Left Chunk10 (Val Loss 0.0100) 🥇

Phase 2: 추론 테스트 (현재)
├─ 2.1 오프라인 추론 테스트
├─ 2.2 API 서버 배포
├─ 2.3 Latency 측정
└─ 2.4 ROS2 통합

Phase 3: 실제 로봇 주행
├─ 3.1 로봇 하드웨어 준비
├─ 3.2 Closed-loop 제어 테스트
├─ 3.3 Success Rate 측정
└─ 3.4 성능 벤치마크
```

---

# Phase 2: 추론 테스트

## 2.1 오프라인 추론 테스트 (GPU 사용)

### 목적
- Best Model의 추론 기능 검증
- Latency 기준치 확인
- Action 출력 정상 확인

### 테스트 방법

#### A. 단일 이미지 추론
```python
# scripts/test_best_model_inference.py
from Mobile_VLA.inference_pipeline import MobileVLAInferencePipeline
import numpy as np
from PIL import Image
import time

# Left Chunk10 Best Model 로드
checkpoint_path = "runs/mobile_vla_no_chunk_20251209/kosmos/mobile_vla_finetune/2025-12-18/mobile_vla_left_chunk10_20251218/epoch_epoch=09-val_loss=val_loss=0.010.ckpt"
config_path = "Mobile_VLA/configs/mobile_vla_left_chunk10_20251218.json"

pipeline = MobileVLAInferencePipeline(
    checkpoint_path=checkpoint_path,
    config_path=config_path,
    device="cuda"
)

# 테스트 이미지 로드 (실제 로봇 카메라 이미지)
test_image = Image.open("test_data/robot_view_001.jpg")

# 추론 실행
instruction = "Navigate around obstacles and reach the front of the beverage bottle on the left"

start_time = time.time()
action, latency_ms = pipeline.predict(test_image, instruction)
total_time = (time.time() - start_time) * 1000

print(f"Action: {action}")  # [linear_x, linear_y]
print(f"Model Latency: {latency_ms:.1f} ms")
print(f"Total Latency: {total_time:.1f} ms")
```

#### B. 배치 추론 테스트
```python
# 10개 연속 이미지로 테스트
test_images = [...]  # 10 images
latencies = []

for img in test_images:
    action, latency = pipeline.predict(img, instruction)
    latencies.append(latency)

print(f"Avg Latency: {np.mean(latencies):.1f} ms")
print(f"Max Latency: {np.max(latencies):.1f} ms")
print(f"Min Latency: {np.min(latencies):.1f} ms")
```

### 평가 지표 (참고: OpenVLA 연구)

| 지표 | 목표 | 근거 |
|------|------|------|
| **Average Latency** | < 100 ms | OpenVLA: 3-5Hz (200-333ms) |
| **Max Latency** | < 150 ms | Real-time 제어 여유 |
| **Action Range** | [-1, 1] | Normalized action space |
| **GPU Memory** | < 10GB | A5000 (24GB) 여유 |

---

## 2.2 API 서버 배포

### API 서버 아키텍처
```
[Jetson Robot] --HTTP--> [Billy Server:8000] --GPU--> [VLA Model]
     ↓                           ↓                         ↓
  Camera                    FastAPI                  Left Chunk10
  ROS2                   Authentication              Inference
```

### 배포 절차

#### Step 1: Best Model을 API 서버에 설정
```bash
# Mobile_VLA/inference_server.py 수정
# Line 180-184: checkpoint_path 업데이트

export VLA_CHECKPOINT_PATH="runs/mobile_vla_no_chunk_20251209/kosmos/mobile_vla_finetune/2025-12-18/mobile_vla_left_chunk10_20251218/epoch_epoch=09-val_loss=val_loss=0.010.ckpt"
export VLA_CONFIG_PATH="Mobile_VLA/configs/mobile_vla_left_chunk10_20251218.json"
```

#### Step 2: API 서버 실행
```bash
# API Key 설정
export VLA_API_KEY="your-secure-api-key"

# 서버 시작
nohup python3 Mobile_VLA/inference_server.py > logs/api_server_left_chunk10.log 2>&1 &

# Health Check
curl http://localhost:8000/health
```

#### Step 3: 테스트
```python
import requests
import base64

# 이미지를 base64로 인코딩
with open("test_image.jpg", "rb") as f:
    img_base64 = base64.b64encode(f.read()).decode()

# API 호출
response = requests.post(
    "http://localhost:8000/predict",
    json={
        "image": img_base64,
        "instruction": "Navigate to left bottle"
    },
    headers={"X-API-Key": "your-secure-api-key"}
)

result = response.json()
print(f"Action: {result['action']}")
print(f"Latency: {result['latency_ms']} ms")
```

---

## 2.3 Latency 벤치마크 (참고: 최신 VLA 연구)

### 목표 Latency (Real-time 제어)
- **30 FPS 비디오**: < 33 ms (이상적)
- **10 Hz 제어**: < 100 ms (실용적)
- **3-5 Hz 제어**: < 200-333 ms (OpenVLA 수준)

### 최적화 방법 (참고: π0 VLA 연구)

#### A. 모델 최적화
```python
# TensorRT 변환 (선택)
import torch_tensorrt

model_trt = torch_tensorrt.compile(
    model,
    inputs=[torch_tensorrt.Input((1, 3, 224, 224))],
    enabled_precisions={torch.float16}
)
```

#### B. CUDA Graph 사용
```python
# CUDA graph로 오버헤드 제거
static_input = torch.randn(1, 3, 224, 224).cuda()
s = torch.cuda.Stream()
s.wait_stream(torch.cuda.current_stream())
with torch.cuda.stream(s):
    for _ in range(3):  # warmup
        output = model(static_input)
s.synchronize()

# Graph 캡처
g = torch.cuda.CUDAGraph()
with torch.cuda.graph(g):
    static_output = model(static_input)

# 빠른 실행
g.replay()
```

### Latency 측정 스크립트
```python
# scripts/benchmark_latency.py
import torch
import time
import numpy as np

def benchmark_latency(model, num_iterations=100):
    device = "cuda"
    model = model.to(device).eval()
    
    # Dummy input
    dummy_image = torch.randn(1, 3, 224, 224).to(device)
    dummy_text = "Navigate to left bottle"
    
    # Warmup
    with torch.no_grad():
        for _ in range(10):
            _ = model(dummy_image, dummy_text)
    
    # Measure
    latencies = []
    with torch.no_grad():
        for _ in range(num_iterations):
            start = time.time()
            _ = model(dummy_image, dummy_text)
            torch.cuda.synchronize()
            latency = (time.time() - start) * 1000
            latencies.append(latency)
    
    return {
        'mean': np.mean(latencies),
        'std': np.std(latencies),
        'min': np.min(latencies),
        'max': np.max(latencies),
        'p50': np.percentile(latencies, 50),
        'p95': np.percentile(latencies, 95),
        'p99': np.percentile(latencies, 99)
    }
```

---

## 2.4 ROS2 통합 테스트

### ROS2 Client 설정
```bash
# Jetson에서 실행
cd ~/vla/ros2_client

# SSH Tunnel 설정 (이미 완료)
bash ~/vla/scripts/jetson_ssh_tunnel.sh

# API 연결 테스트
python3 vla_api_client.py --test
```

### 테스트 시나리오
1. **API Connection Test**: Health check
2. **Single Prediction Test**: 1개 이미지
3. **Continuous Prediction Test**: 10개 연속
4. **Latency Distribution**: 100회 측정

---

# Phase 3: 실제 로봇 주행

## 3.1 로봇 하드웨어 준비

### 하드웨어 체크리스트
- [ ] 로봇 베이스 (Mecanum wheel)
- [ ] 카메라 (720x1280, RGB)
- [ ] Jetson 컴퓨터
- [ ] Billy Server (A5000) 연결
- [ ] 배터리 충전
- [ ] 안전 장비 (E-stop)

### 소프트웨어 체크리스트
- [x] SSH Tunnel 설정
- [x] ROS2 Client 구현
- [ ] 로봇 제어 인터페이스
- [ ] 안전 제어 로직
- [ ] 데이터 로깅 시스템

---

## 3.2 Closed-loop 제어 테스트

### 제어 루프 아키텍처 (참고: RT-2, OpenVLA)

```python
# ROS2 Node: VLA Control Loop
class VLAControlNode(Node):
    def __init__(self):
        super().__init__('vla_control_node')
        
        # VLA Client
        self.vla_client = VLAClient(
            api_server="http://100.86.152.29:8000",
            api_key="your-key"
        )
        
        # ROS2 Publishers/Subscribers
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.camera_sub = self.create_subscription(
            Image, '/camera/image_raw', 
            self.camera_callback, 10
        )
        
        # Control parameters
        self.control_freq = 10  # Hz (OpenVLA: 3-5Hz)
        self.timer = self.create_timer(1.0/self.control_freq, self.control_loop)
        
        self.latest_image = None
        self.instruction = "Navigate to left bottle"
        
    def camera_callback(self, msg):
        # ROS Image -> NumPy
        self.latest_image = self.bridge.imgmsg_to_cv2(msg, "rgb8")
    
    def control_loop(self):
        if self.latest_image is None:
            return
        
        # VLA Prediction
        try:
            action, latency = self.vla_client.predict(
                self.latest_image, 
                self.instruction
            )
            
            # Action -> cmd_vel
            cmd = Twist()
            cmd.linear.x = float(action[0])  # forward/backward
            cmd.linear.y = float(action[1])  # left/right (mecanum)
            
            # Safety check
            cmd = self.apply_safety_limits(cmd)
            
            # Publish
            self.cmd_vel_pub.publish(cmd)
            
            # Log
            self.get_logger().info(
                f"Action: [{action[0]:.3f}, {action[1]:.3f}], "
                f"Latency: {latency:.1f}ms"
            )
            
        except Exception as e:
            self.get_logger().error(f"Control failed: {e}")
            self.emergency_stop()
    
    def apply_safety_limits(self, cmd):
        # Velocity limits
        MAX_LINEAR_VEL = 0.5  # m/s
        cmd.linear.x = np.clip(cmd.linear.x, -MAX_LINEAR_VEL, MAX_LINEAR_VEL)
        cmd.linear.y = np.clip(cmd.linear.y, -MAX_LINEAR_VEL, MAX_LINEAR_VEL)
        return cmd
    
    def emergency_stop(self):
        stop_cmd = Twist()  # All zeros
        self.cmd_vel_pub.publish(stop_cmd)
```

### 제어 주파수 설정 (VLA 연구 참고)

| 연구 | 제어 주파수 | Latency | 비고 |
|------|-------------|---------|------|
| **RT-2** | 10 Hz | ~100 ms | Google DeepMind |
| **OpenVLA** | 3-5 Hz | 200-333 ms | 7B params |
| **π0-VLA** | 30 Hz | 27-30 ms | 최적화 버전 |
| **우리 목표** | **10 Hz** | **< 100 ms** | 실용적 목표 |

---

## 3.3 Success Rate 측정 (VLA 평가 프로토콜)

### 테스트 프로토콜 (참고: OpenVLA, RT-2)

#### 테스트 환경 설정
```
Setup:
- 로봇 시작 위치: (0, 0) 고정
- 목표 물체: 음료수 병
  - Left position: (-2m, 1m)
  - Right position: (2m, 1m)
- 장애물: 박스 2-3개
- 조명: 실내 형광등
- 바닥: 평평한 타일
```

#### Success Criteria (참고: RT-2, RoboFlamingo)
```python
def is_success(robot_pos, goal_pos, threshold=0.5):
    """
    Success criteria:
    1. Distance to goal < 0.5m
    2. No collision
    3. Completed within time limit (60s)
    """
    distance = np.linalg.norm(robot_pos - goal_pos)
    return distance < threshold
```

### 평가 메트릭 (VLA 표준)

#### 1. Task Success Rate (주요 지표)
```python
success_rate = (successful_trials / total_trials) * 100

# 목표: > 80% (OpenVLA 수준)
# 비교: RT-2 ~90%, RoboFlamingo 97%
```

#### 2. Additional Metrics (참고: VLATest)

| Metric | 정의 | 목표 | 근거 |
|--------|------|------|------|
| **Success Rate** | Goal 도달 성공률 | > 80% | OpenVLA baseline |
| **Avg Completion Time** | 평균 태스크 완료 시간 | < 30s | 효율성 |
| **Path Efficiency** | 최단 경로 대비 실제 경로 | > 0.7 | Navigation 품질 |
| **Collision Rate** | 장애물 충돌 비율 | < 10% | 안전성 |
| **Inference Latency** | 평균 추론 시간 | < 100ms | Real-time 제어 |

#### 3. Robustness Test (참고: VLATest Framework)

**환경 변화 테스트**:
- [ ] 조명 변화 (밝음/어두움)
- [ ] 배경 변화 (다른 위치)
- [ ] 물체 변화 (다른 병)
- [ ] 장애물 배치 변화

---

## 3.4 실험 프로토콜 (상세)

### Experiment Design (참고: OpenVLA 평가)

#### Trial 1: Left Navigation (N=10)
```python
for trial in range(10):
    # 1. Setup
    reset_robot_to_start()
    place_bottle_at_left_position()
    place_random_obstacles()
    
    # 2. Execute
    instruction = "Navigate around obstacles and reach the front of the beverage bottle on the left"
    start_time = time.time()
    
    success = False
    trajectory = []
    
    while time.time() - start_time < 60:  # 60s timeout
        # Get camera image
        image = get_camera_image()
        
        # VLA prediction
        action, latency = vla_client.predict(image, instruction)
        
        # Execute action
        robot.execute_action(action)
        
        # Record
        trajectory.append({
            'time': time.time() - start_time,
            'position': robot.get_position(),
            'action': action,
            'latency': latency
        })
        
        # Check success
        if is_success(robot.get_position(), left_bottle_position):
            success = True
            break
        
        # Check collision
        if robot.is_collision():
            break
    
    # 3. Record result
    results.append({
        'trial': trial,
        'success': success,
        'duration': time.time() - start_time,
        'trajectory': trajectory,
        'collision': robot.is_collision()
    })
```

#### Trial 2: Right Navigation (N=10)
- 동일한 프로토콜, instruction만 변경

### 데이터 수집

```python
# 각 trial마다 저장
{
    'trial_id': 'left_001',
    'model': 'Left_Chunk10',
    'instruction': '...',
    'success': True,
    'duration': 25.3,  # seconds
    'path_length': 3.2,  # meters
    'num_collisions': 0,
    'avg_latency': 45.2,  # ms
    'trajectory': [...],  # positions over time
    'actions': [...],  # predicted actions
    'camera_views': [...],  # saved images
}
```

---

## 3.5 예상 결과 및 비교

### 우리 모델 예상 성능

| Metric | Left Chunk10 (예상) | 근거 |
|--------|---------------------|------|
| **Success Rate** | 75-85% | Val Loss 0.010 (매우 우수) |
| **Avg Latency** | 50-80 ms | A5000 GPU, 최적화 전 |
| **Completion Time** | 20-30s | Navigation 거리 ~3m |
| **Collision Rate** | < 15% | 장애물 회피 학습됨 |

### VLA 모델 비교 (참고)

| Model | Success Rate | Latency | 비고 |
|-------|--------------|---------|------|
| **RT-2** | ~90% | 100ms | 55B params, Google |
| **OpenVLA** | 50-85% | 200-333ms | 7B params, Open-source |
| **RoboFlamingo** | 97% | - | CALVIN benchmark |
| **우리 (Left Chunk10)** | **75-85% (목표)** | **< 100ms** | 250 eps, Task-specific |

---

## 🎯 실행 순서

### Week 1: Phase 2 (추론 테스트)
- [x] Day 1: 오프라인 추론 테스트
- [ ] Day 2: API 서버 배포 및 테스트
- [ ] Day 3: Latency 벤치마크
- [ ] Day 4: ROS2 통합 테스트
- [ ] Day 5: 전체 시스템 검증

### Week 2: Phase 3 (로봇 주행)
- [ ] Day 1: 로봇 하드웨어 준비 및 안전 테스트
- [ ] Day 2: Open-loop 테스트 (수동 제어)
- [ ] Day 3: Closed-loop 테스트 (VLA 제어)
- [ ] Day 4-5: Success Rate 측정 (20 trials)

### Week 3: 분석 및 보고
- [ ] 데이터 분석 및 시각화
- [ ] 성능 벤치마크 리포트
- [ ] 논문/미팅 자료 준비

---

## 📚 참고 논문

1. **OpenVLA** (2024)
   - Success Rate: 50-85%
   - Open-source 7B VLA
   - LoRA fine-tuning 가능

2. **RT-2** (2023, Google DeepMind)
   - Success Rate: ~90%
   - 55B parameters
   - Semantic generalization 우수

3. **RoboFlamingo** (2024)
   - Success Rate: 97% (single task)
   - Cost-effective VLM adaptation
   - CALVIN benchmark

4. **π0-VLA** (2024)
   - Latency: 27ms (30Hz)
   - Real-time optimization
   - CUDA graph 활용

5. **VLATest** (2024)
   - Robustness testing framework
   - Fuzzing-based evaluation
   - Multi-condition testing

---

**작성 완료**: 2025-12-18 13:37  
**참고**: 최신 VLA 연구 (2023-2024)  
**다음 단계**: API 서버 배포 및 추론 테스트 시작
