# VLA 추론 시스템 사용 가이드

## 개요

이 문서는 Action Chunk 기반 Mobile VLA 추론 시스템의 사용 방법을 설명합니다.

## 주요 특징

- **액션 청크 메커니즘**: 200ms마다 10개의 액션을 한 번에 예측하여 계산 효율성 향상
- **실시간 제어**: 20ms마다 개별 액션 실행
- **입력 관리**: 0.4초마다 2DOF 속도 명령 수집
- **검증 및 모니터링**: 액션 유효성 검사 및 성능 모니터링

## 설치

```bash
# 필요한 패키지 설치
pip install torch torchvision numpy opencv-python pillow pyyaml
```

## 빠른 시작

### 1. 기본 사용

```python
from src.action_chunk_inference import ActionChunkInferenceSystem
import numpy as np

# 설정
config = {
    'chunk_size': 10,
    'inference_interval': 0.2,  # 200ms
    'velocity_interval': 0.4,   # 400ms
}

# 시스템 초기화
system = ActionChunkInferenceSystem(
    checkpoint_path="checkpoints/mobile_vla_finetuned.pth",
    config=config
)

# 초기 입력으로 시스템 초기화
initial_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
text_command = "1box_hori_right"
initial_distance = 1.5

system.initialize(initial_image, text_command, initial_distance)

# 데모 실행 (5초)
system.run_demo(duration=5.0)
```

### 2. 설정 파일 사용

```python
import yaml

# 설정 로드
with open('configs/inference_config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# 시스템 초기화
system = ActionChunkInferenceSystem(
    checkpoint_path=config['model']['checkpoint'],
    config=config['inference']
)
```

### 3. 실시간 루프

```python
import time

# 초기화
system.initialize(initial_image, text_command, initial_distance)

# 메인 루프
while True:
    # 한 스텝 실행
    action = system.step()
    
    if action is not None:
        # 액션 실행 (예: 로봇 제어)
        print(f"Executing action: [{action[0]:.4f}, {action[1]:.4f}]")
        # execute_robot_command(action)
    
    # 20ms 대기
    time.sleep(0.02)
```

## 상세 사용법

### 컴포넌트별 사용

#### 1. ActionScheduler

액션 청크를 관리하고 스케줄링합니다.

```python
from src.action_chunk_inference import ActionScheduler

scheduler = ActionScheduler(chunk_size=10, inference_interval=0.2)

# 액션 청크 업데이트
action_chunk = np.random.randn(10, 2)
scheduler.update_chunk(action_chunk)

# 현재 액션 가져오기
action = scheduler.get_current_action()
```

#### 2. InputManager

센서 입력을 수집하고 관리합니다.

```python
from src.action_chunk_inference import InputManager

input_manager = InputManager(velocity_interval=0.4)

# 초기 입력 설정
input_manager.set_initial_input(image, text, distance)

# 속도 입력 추가
input_manager.add_velocity((0.5, 0.1))

# 최근 속도 가져오기
recent_velocities = input_manager.get_recent_velocities(n=5)
```

#### 3. InferenceValidator

추론 결과를 검증합니다.

```python
from src.action_chunk_inference import InferenceValidator

validator = InferenceValidator(max_linear_vel=1.0, max_angular_vel=1.0)

# 액션 청크 검증
is_valid = validator.validate_action_chunk(action_chunk)

# 액션 로깅
validator.log_action(action, timestamp)

# 로그 저장
validator.save_action_log("logs/actions.json")
```

#### 4. PerformanceMonitor

성능을 모니터링합니다.

```python
from src.action_chunk_inference import PerformanceMonitor

monitor = PerformanceMonitor()

# 추론 시간 기록
monitor.record_inference_time(50.0)  # ms

# 액션 실행 기록
monitor.record_action_execution(success=True)

# 통계 출력
monitor.print_report()
```

## 테스트

```bash
# 단위 테스트 실행
python tests/test_inference_system.py

# 특정 테스트만 실행
python -m unittest tests.test_inference_system.TestActionScheduler
```

## 성능 벤치마크

```python
# 추론 시간 측정
system.monitor.print_report()
```

예상 성능:
- 평균 추론 시간: < 200ms
- 최대 추론 시간: < 300ms
- 액션 실행 주기: 20ms

## 타이밍 다이어그램

```
시간 (ms)    0    20   40   60   80   100  120  140  160  180  200  220
            │    │    │    │    │    │    │    │    │    │    │    │
추론        ●─────────────────────────────────────────────────────●
            │                                                      │
액션 실행   ●────●────●────●────●────●────●────●────●────●────●────●
            a0   a1   a2   a3   a4   a5   a6   a7   a8   a9   a10  a11

속도 입력   ●────────────────────────────────────────────────────────●
            (0ms)                                                 (400ms)
```

## 문제 해결

### 1. 추론 시간이 너무 긴 경우

```python
# FP16 사용
config['model']['optimization']['use_fp16'] = True

# 배치 크기 조정
config['inference']['chunk_size'] = 5  # 10 → 5
```

### 2. 액션 검증 실패

```python
# 속도 제한 조정
validator = InferenceValidator(
    max_linear_vel=2.0,  # 1.0 → 2.0
    max_angular_vel=2.0
)
```

### 3. 메모리 부족

```python
# CPU 사용
import torch
torch.cuda.empty_cache()

# 또는 CPU 모드로 실행
device = torch.device("cpu")
```

## 설정 파일 예제

`configs/inference_config.yaml` 참조

## API 문서

### ActionChunkInferenceSystem

메인 추론 시스템 클래스

**메서드:**
- `__init__(checkpoint_path, config)`: 시스템 초기화
- `initialize(image, text, distance)`: 초기 입력으로 시스템 초기화
- `step()`: 한 스텝 실행, 현재 액션 반환
- `run_demo(duration)`: 데모 실행

### ActionScheduler

액션 청크 스케줄러

**메서드:**
- `should_infer(current_time)`: 추론 필요 여부 확인
- `get_current_action()`: 현재 액션 가져오기
- `update_chunk(new_chunk)`: 새 액션 청크로 업데이트
- `reset()`: 스케줄러 리셋

### InputManager

입력 관리자

**메서드:**
- `should_collect_velocity(current_time)`: 속도 수집 필요 여부
- `add_velocity(velocity)`: 속도 입력 추가
- `get_recent_velocities(n)`: 최근 n개 속도 반환
- `set_initial_input(image, text, distance)`: 초기 입력 설정

### InferenceValidator

추론 검증기

**메서드:**
- `validate_action_chunk(action_chunk)`: 액션 청크 검증
- `log_action(action, timestamp)`: 액션 로깅
- `save_action_log(filepath)`: 로그 저장

### PerformanceMonitor

성능 모니터

**메서드:**
- `record_inference_time(time_ms)`: 추론 시간 기록
- `record_action_execution(success)`: 액션 실행 기록
- `get_statistics()`: 통계 반환
- `print_report()`: 성능 보고서 출력

## 참고 자료

- [설계 문서](../docs/inference_design_kr.md)
- [테스트 코드](../tests/test_inference_system.py)
- [설정 파일](../configs/inference_config.yaml)

## 라이선스

MIT License
