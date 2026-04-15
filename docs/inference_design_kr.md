# VLA 추론 시스템 설계 문서

## 1. 개요

본 문서는 Mobile VLA(Vision-Language-Action) 모델의 추론 시스템 설계를 다룹니다. 실시간 로봇 제어를 위한 효율적인 추론 파이프라인과 액션 청크 기반 제어 전략을 제시합니다.

**작성일**: 2025-12-09  
**버전**: 1.0

---

## 2. 시스템 요구사항

### 2.1 타이밍 제약사항

| 항목 | 주기 | 설명 |
|------|------|------|
| 2DOF 입력 | 0.4초 (400ms) | 로봇의 속도 명령 입력 주기 |
| 액션 예측 | 0.2초 (200ms) | 모델 추론 실행 주기 |
| 액션 실행 | 0.02초 (20ms) | 개별 액션 실행 주기 |
| 장기 태스크 예측 | 20초 | 복잡한 태스크의 재계획 주기 |

### 2.2 입력 데이터

1. **초기 입력** (에피소드 시작 시)
   - 거리 측정값 (초기 위치)
   - RGB 카메라 이미지
   - 고정 텍스트 명령 (예: "1box_hori_right")

2. **연속 입력** (0.4초마다)
   - 2DOF 속도 명령 (linear_x, angular_z)
   - 현재 로봇 상태

### 2.3 출력 데이터

- **액션 청크**: 10개의 2DOF 액션 (2초 분량)
- **각 액션**: (x, y) 또는 (linear_x, angular_z)

---

## 3. 액션 청크 메커니즘

### 3.1 개념

**문제**: 20ms마다 모델 추론을 수행하면 계산 부하가 과도함

**해결**: Action Chunking - 한 번의 추론으로 미래의 여러 액션을 예측

```
추론 주기: 200ms
액션 실행 주기: 20ms
청크 크기: 10개 액션

┌─────────────────────────────────────────────────┐
│ t=0ms: 추론 → [a0, a1, a2, ..., a9]            │
│ t=0~20ms: 실행 a0                               │
│ t=20~40ms: 실행 a1                              │
│ t=40~60ms: 실행 a2                              │
│ ...                                             │
│ t=180~200ms: 실행 a9                            │
│ t=200ms: 재추론 → [a10, a11, ..., a19]         │
└─────────────────────────────────────────────────┘
```

### 3.2 윈도우 프레임 전략

**초기 프레임**: 추론 시간이 길어질 수 있음 (모델 초기화)
**이후 프레임**: 기존 액션 청크를 따라 이동하며 안정적인 제어

```python
# 의사 코드
if is_first_inference:
    # 초기 추론은 시간이 오래 걸릴 수 있음
    action_chunk = model.predict(image, text, state)
    # 필요시 대기 또는 안전 동작
else:
    # 기존 청크 실행 중
    if chunk_index < len(action_chunk):
        execute_action(action_chunk[chunk_index])
    else:
        # 새로운 청크 예측
        action_chunk = model.predict(current_image, text, state)
        chunk_index = 0
```

---

## 4. 추론 파이프라인 설계

### 4.1 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                   추론 시스템                            │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐      ┌──────────────┐                │
│  │ 센서 입력    │      │ 모델 추론    │                │
│  │ - 카메라     │─────▶│ - VLA 모델   │                │
│  │ - 거리       │      │ - 액션 청크  │                │
│  │ - 텍스트     │      │   생성       │                │
│  └──────────────┘      └──────┬───────┘                │
│                               │                         │
│                               ▼                         │
│                    ┌──────────────────┐                │
│                    │ 액션 스케줄러    │                │
│                    │ - 청크 관리      │                │
│                    │ - 타이밍 제어    │                │
│                    └────────┬─────────┘                │
│                             │                           │
│                             ▼                           │
│                    ┌──────────────────┐                │
│                    │ 로봇 제어기      │                │
│                    │ - 2DOF 명령      │                │
│                    │ - 안전 체크      │                │
│                    └──────────────────┘                │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 4.2 주요 컴포넌트

#### 4.2.1 입력 관리자 (InputManager)

```python
class InputManager:
    """센서 입력 수집 및 전처리"""
    
    def __init__(self):
        self.camera = Camera()
        self.distance_sensor = DistanceSensor()
        self.text_command = ""
        
    def get_initial_input(self):
        """초기 입력 수집"""
        return {
            'image': self.camera.capture(),
            'distance': self.distance_sensor.measure(),
            'text': self.text_command
        }
    
    def get_continuous_input(self):
        """연속 입력 수집 (0.4초마다)"""
        return {
            'velocity': self.get_current_velocity(),
            'state': self.get_robot_state()
        }
```

#### 4.2.2 모델 추론기 (ModelInference)

```python
class ModelInference:
    """VLA 모델 추론 엔진"""
    
    def __init__(self, model_path, device='cuda'):
        self.model = self.load_model(model_path)
        self.device = device
        self.chunk_size = 10
        
    def predict_action_chunk(self, image, text, state):
        """
        액션 청크 예측
        
        Returns:
            action_chunk: shape (10, 2) - 10개의 2DOF 액션
        """
        # 입력 전처리
        image_tensor = self.preprocess_image(image)
        text_embedding = self.encode_text(text)
        state_tensor = self.preprocess_state(state)
        
        # 모델 추론
        with torch.no_grad():
            action_chunk = self.model(
                image_tensor,
                text_embedding,
                state_tensor
            )
        
        return action_chunk.cpu().numpy()
    
    def load_model(self, model_path):
        """파인튜닝된 모델 로드"""
        # 체크포인트에서 모델 로드
        checkpoint = torch.load(model_path)
        model = VLAModel(...)
        model.load_state_dict(checkpoint['model_state_dict'])
        model.eval()
        return model
```

#### 4.2.3 액션 스케줄러 (ActionScheduler)

```python
class ActionScheduler:
    """액션 청크 관리 및 스케줄링"""
    
    def __init__(self):
        self.action_chunk = None
        self.chunk_index = 0
        self.last_inference_time = 0
        self.inference_interval = 0.2  # 200ms
        self.action_interval = 0.02    # 20ms
        
    def should_infer(self, current_time):
        """추론이 필요한지 확인"""
        return (current_time - self.last_inference_time) >= self.inference_interval
    
    def get_current_action(self):
        """현재 실행할 액션 반환"""
        if self.action_chunk is None or self.chunk_index >= len(self.action_chunk):
            return None
        
        action = self.action_chunk[self.chunk_index]
        self.chunk_index += 1
        return action
    
    def update_chunk(self, new_chunk):
        """새로운 액션 청크로 업데이트"""
        self.action_chunk = new_chunk
        self.chunk_index = 0
        self.last_inference_time = time.time()
```

#### 4.2.4 로봇 제어기 (RobotController)

```python
class RobotController:
    """로봇 제어 명령 실행"""
    
    def __init__(self):
        self.cmd_vel_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)
        self.safety_checker = SafetyChecker()
        
    def execute_action(self, action):
        """
        2DOF 액션 실행
        
        Args:
            action: (linear_x, angular_z) 또는 (x, y)
        """
        # 안전 체크
        if not self.safety_checker.is_safe(action):
            rospy.logwarn("Unsafe action detected, stopping")
            self.stop()
            return
        
        # 액션 실행
        cmd = Twist()
        cmd.linear.x = action[0]
        cmd.angular.z = action[1]
        self.cmd_vel_pub.publish(cmd)
    
    def stop(self):
        """긴급 정지"""
        cmd = Twist()
        self.cmd_vel_pub.publish(cmd)
```

---

## 5. 추론 루프 구현

### 5.1 메인 추론 루프

```python
class VLAInferenceSystem:
    """VLA 추론 시스템 메인 클래스"""
    
    def __init__(self, model_path):
        self.input_manager = InputManager()
        self.model = ModelInference(model_path)
        self.scheduler = ActionScheduler()
        self.controller = RobotController()
        
        self.is_initialized = False
        
    def run(self):
        """메인 추론 루프"""
        rate = rospy.Rate(50)  # 20ms 주기
        
        # 초기화
        initial_input = self.input_manager.get_initial_input()
        self.text_command = initial_input['text']
        
        while not rospy.is_shutdown():
            current_time = time.time()
            
            # 추론이 필요한 경우
            if self.scheduler.should_infer(current_time):
                self._perform_inference()
            
            # 현재 액션 실행
            action = self.scheduler.get_current_action()
            if action is not None:
                self.controller.execute_action(action)
            
            rate.sleep()
    
    def _perform_inference(self):
        """모델 추론 수행"""
        # 현재 상태 수집
        current_input = self.input_manager.get_continuous_input()
        image = self.input_manager.camera.capture()
        
        # 액션 청크 예측
        start_time = time.time()
        action_chunk = self.model.predict_action_chunk(
            image,
            self.text_command,
            current_input['state']
        )
        inference_time = time.time() - start_time
        
        # 로깅
        rospy.loginfo(f"Inference time: {inference_time*1000:.2f}ms")
        
        # 스케줄러 업데이트
        self.scheduler.update_chunk(action_chunk)
        
        # 첫 추론 완료
        if not self.is_initialized:
            self.is_initialized = True
            rospy.loginfo("First inference completed")
```

### 5.2 0.4초 주기 입력 처리

```python
class ContinuousInputHandler:
    """0.4초 주기 입력 처리"""
    
    def __init__(self):
        self.input_buffer = []
        self.last_update_time = 0
        self.update_interval = 0.4  # 400ms
        
    def update(self):
        """0.4초마다 2DOF 입력 수집"""
        current_time = time.time()
        
        if (current_time - self.last_update_time) >= self.update_interval:
            velocity = self.get_velocity_command()
            self.input_buffer.append({
                'timestamp': current_time,
                'velocity': velocity
            })
            self.last_update_time = current_time
            
            # 버퍼 크기 제한 (최근 10개만 유지)
            if len(self.input_buffer) > 10:
                self.input_buffer.pop(0)
    
    def get_recent_velocities(self):
        """최근 속도 명령 반환"""
        return [item['velocity'] for item in self.input_buffer]
```

---

## 6. 장기 태스크 처리

### 6.1 20초 주기 재계획

일부 복잡한 태스크는 20초마다 전체 계획을 재수립해야 합니다.

```python
class LongTermPlanner:
    """장기 태스크 계획기"""
    
    def __init__(self):
        self.replan_interval = 20.0  # 20초
        self.last_replan_time = 0
        
    def should_replan(self, current_time):
        """재계획이 필요한지 확인"""
        return (current_time - self.last_replan_time) >= self.replan_interval
    
    def replan(self, current_state, goal):
        """전체 계획 재수립"""
        # 현재 상태에서 목표까지의 새로운 계획 생성
        # 환경 변화, 장애물 등을 고려
        new_plan = self.generate_plan(current_state, goal)
        self.last_replan_time = time.time()
        return new_plan
```

---

## 7. 검증 및 테스트

### 7.1 출력 검증

올바른 x, y 값이 출력되는지 확인하는 테스트 코드:

```python
class InferenceValidator:
    """추론 결과 검증"""
    
    def __init__(self):
        self.action_history = []
        
    def validate_action_chunk(self, action_chunk):
        """액션 청크 유효성 검사"""
        # 형태 확인
        assert action_chunk.shape == (10, 2), \
            f"Expected shape (10, 2), got {action_chunk.shape}"
        
        # 값 범위 확인
        for i, action in enumerate(action_chunk):
            x, y = action
            
            # 속도 제한 확인
            assert -1.0 <= x <= 1.0, \
                f"Action {i}: x={x} out of range [-1.0, 1.0]"
            assert -1.0 <= y <= 1.0, \
                f"Action {i}: y={y} out of range [-1.0, 1.0]"
            
            # NaN/Inf 확인
            assert not np.isnan(x) and not np.isnan(y), \
                f"Action {i}: NaN detected"
            assert not np.isinf(x) and not np.isinf(y), \
                f"Action {i}: Inf detected"
        
        return True
    
    def log_action(self, action, timestamp):
        """액션 로깅"""
        self.action_history.append({
            'timestamp': timestamp,
            'action': action.tolist()
        })
    
    def save_action_log(self, filepath):
        """액션 로그 저장"""
        with open(filepath, 'w') as f:
            json.dump(self.action_history, f, indent=2)
```

### 7.2 단위 테스트

```python
import unittest

class TestInferenceSystem(unittest.TestCase):
    """추론 시스템 테스트"""
    
    def setUp(self):
        self.model = ModelInference('path/to/model.pth')
        self.validator = InferenceValidator()
    
    def test_action_chunk_shape(self):
        """액션 청크 형태 테스트"""
        dummy_image = np.random.rand(224, 224, 3)
        dummy_text = "1box_hori_right"
        dummy_state = np.zeros(10)
        
        action_chunk = self.model.predict_action_chunk(
            dummy_image, dummy_text, dummy_state
        )
        
        self.assertEqual(action_chunk.shape, (10, 2))
    
    def test_action_value_range(self):
        """액션 값 범위 테스트"""
        dummy_image = np.random.rand(224, 224, 3)
        dummy_text = "1box_hori_right"
        dummy_state = np.zeros(10)
        
        action_chunk = self.model.predict_action_chunk(
            dummy_image, dummy_text, dummy_state
        )
        
        self.assertTrue(self.validator.validate_action_chunk(action_chunk))
    
    def test_inference_time(self):
        """추론 시간 테스트"""
        dummy_image = np.random.rand(224, 224, 3)
        dummy_text = "1box_hori_right"
        dummy_state = np.zeros(10)
        
        start_time = time.time()
        action_chunk = self.model.predict_action_chunk(
            dummy_image, dummy_text, dummy_state
        )
        inference_time = time.time() - start_time
        
        # 200ms 이내에 추론 완료되어야 함
        self.assertLess(inference_time, 0.2)
```

---

## 8. 파인튜닝 모델 통합

### 8.1 모델 로딩

```python
def load_finetuned_model(checkpoint_path, config):
    """파인튜닝된 모델 로드"""
    # 설정 로드
    model_config = config['model']
    
    # 모델 초기화
    model = VLAModel(
        vision_encoder=model_config['vision_encoder'],
        language_encoder=model_config['language_encoder'],
        action_dim=2,
        chunk_size=10
    )
    
    # 체크포인트 로드
    checkpoint = torch.load(checkpoint_path, map_location='cuda')
    model.load_state_dict(checkpoint['model_state_dict'])
    
    # 평가 모드
    model.eval()
    
    # GPU로 이동
    model = model.cuda()
    
    print(f"Model loaded from {checkpoint_path}")
    print(f"Training epoch: {checkpoint.get('epoch', 'unknown')}")
    print(f"Training loss: {checkpoint.get('loss', 'unknown')}")
    
    return model
```

### 8.2 모델 최적화

추론 속도 향상을 위한 최적화:

```python
def optimize_model_for_inference(model):
    """추론 최적화"""
    # 1. TorchScript 컴파일
    model = torch.jit.script(model)
    
    # 2. 반정밀도 (FP16) 사용
    model = model.half()
    
    # 3. CUDA 그래프 사용 (선택적)
    # model = torch.cuda.make_graphed_callables(model, ...)
    
    return model
```

---

## 9. 실행 예제

### 9.1 기본 실행

```bash
# 추론 시스템 실행
python scripts/run_inference.py \
    --model checkpoints/mobile_vla_finetuned.pth \
    --config configs/inference_config.yaml \
    --text "1box_hori_right"
```

### 9.2 설정 파일 예제

```yaml
# configs/inference_config.yaml
model:
  vision_encoder: "resnet50"
  language_encoder: "clip"
  checkpoint: "checkpoints/mobile_vla_finetuned.pth"

inference:
  chunk_size: 10
  inference_interval: 0.2  # 200ms
  action_interval: 0.02    # 20ms
  
input:
  velocity_interval: 0.4   # 400ms
  camera_topic: "/camera/rgb/image_raw"
  distance_topic: "/distance"

output:
  cmd_vel_topic: "/cmd_vel"
  log_actions: true
  log_path: "logs/inference_actions.json"

safety:
  max_linear_vel: 1.0
  max_angular_vel: 1.0
  emergency_stop_distance: 0.3
```

---

## 10. 성능 모니터링

### 10.1 메트릭 수집

```python
class PerformanceMonitor:
    """성능 모니터링"""
    
    def __init__(self):
        self.metrics = {
            'inference_times': [],
            'action_execution_times': [],
            'total_actions': 0,
            'failed_actions': 0
        }
    
    def record_inference_time(self, time_ms):
        """추론 시간 기록"""
        self.metrics['inference_times'].append(time_ms)
    
    def get_statistics(self):
        """통계 계산"""
        inference_times = self.metrics['inference_times']
        
        return {
            'avg_inference_time': np.mean(inference_times),
            'max_inference_time': np.max(inference_times),
            'min_inference_time': np.min(inference_times),
            'std_inference_time': np.std(inference_times),
            'total_actions': self.metrics['total_actions'],
            'success_rate': 1 - (self.metrics['failed_actions'] / 
                                 max(self.metrics['total_actions'], 1))
        }
    
    def print_report(self):
        """성능 보고서 출력"""
        stats = self.get_statistics()
        print("\n=== Performance Report ===")
        print(f"Average inference time: {stats['avg_inference_time']:.2f}ms")
        print(f"Max inference time: {stats['max_inference_time']:.2f}ms")
        print(f"Min inference time: {stats['min_inference_time']:.2f}ms")
        print(f"Total actions: {stats['total_actions']}")
        print(f"Success rate: {stats['success_rate']*100:.2f}%")
```

---

## 11. 향후 개선 사항

### 11.1 단기 개선

1. **모델 양자화**: INT8 양자화로 추론 속도 향상
2. **배치 처리**: 여러 입력을 배치로 처리
3. **비동기 추론**: 추론과 실행을 병렬화

### 11.2 장기 개선

1. **온라인 학습**: 실시간 데이터로 모델 업데이트
2. **다중 모델 앙상블**: 여러 모델의 예측 결합
3. **적응형 청크 크기**: 상황에 따라 청크 크기 조정

---

## 12. 참고 자료

- [OpenVLA Paper](https://openvla.github.io/)
- [Action Chunking Transformer](https://arxiv.org/abs/2304.13705)
- [ROS Navigation Stack](http://wiki.ros.org/navigation)

---

## 부록 A: 전체 코드 구조

```
vla/
├── scripts/
│   ├── run_inference.py          # 메인 실행 스크립트
│   └── test_inference.py         # 테스트 스크립트
├── src/
│   └── mobile_vla/
│       ├── inference/
│       │   ├── __init__.py
│       │   ├── input_manager.py      # 입력 관리
│       │   ├── model_inference.py    # 모델 추론
│       │   ├── action_scheduler.py   # 액션 스케줄링
│       │   ├── robot_controller.py   # 로봇 제어
│       │   └── validator.py          # 검증
│       └── models/
│           └── vla_model.py          # VLA 모델 정의
├── configs/
│   └── inference_config.yaml     # 설정 파일
└── tests/
    └── test_inference_system.py  # 단위 테스트
```

---

**문서 끝**
