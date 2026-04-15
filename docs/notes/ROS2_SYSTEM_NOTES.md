# ROS2 시스템 노트 - Mobile VLA RoboVLMs

## 📁 관련 파일들
- [ROS_action/](./ROS_action/) - ROS2 워크스페이스
- [ROS_action/src/mobile_vla_package/](./ROS_action/src/mobile_vla_package/) - 메인 패키지
- [ROS_action/launch/](./ROS_action/launch/) - 런치 파일들
- [launch_mobile_vla.launch.py](./launch_mobile_vla.launch.py) - 시스템 런치
- [launch_mobile_vla_system.py](./launch_mobile_vla_system.py) - 시스템 실행

## 🎯 주요 아이디어들

### 1. ROS2 패키지 구조
```
mobile_vla_package/
├── __init__.py
├── robovlms_inference.py      # 추론 노드
├── camera_publisher.py        # 카메라 노드
├── robot_control_node.py      # 로봇 제어 노드
├── data_collection_node.py    # 데이터 수집 노드
└── ros_env_setup.py          # 환경 설정 노드
```

### 2. 노드 간 통신 구조
- **카메라 → 추론**: `CompressedImage` 토픽
- **추론 → 제어**: `String` (액션 명령), `Float32MultiArray` (신뢰도)
- **제어 → 로봇**: `Twist` (속도 명령)
- **데이터 수집**: 모든 토픽 모니터링

### 3. 추론 노드 다중 모드 지원
```python
# 지원하는 추론 모드
- 'pytorch': PyTorch 모델 직접 로드
- 'onnx': ONNX Runtime 사용
- 'tensorrt': TensorRT 최적화
- 'auto': 자동 폴백 (PyTorch → ONNX → TensorRT)
- 'test': 테스트 모드
```

### 4. 런치 파일 구조
```python
# launch_mobile_vla.launch.py
- camera_node: CSI 카메라 스트림
- inference_node: RoboVLMs 추론 (지연 시작)
- control_node: 로봇 제어
- data_collection_node: 데이터 수집
- rviz_node: 시각화
```

### 5. 환경 설정 자동화
```python
# ros_env_setup.py
- RMW_IMPLEMENTATION 설정
- ROS_DOMAIN_ID 설정
- LD_LIBRARY_PATH 설정
- PYTHONPATH 설정
```

## 🔧 핵심 기능들

### 1. 실시간 추론
- 0.360ms 추론 시간 (2,780 FPS)
- GPU 가속 지원
- 멀티스레드 처리

### 2. 안전한 로봇 제어
- 속도 제한
- 긴급 정지 기능
- 충돌 감지

### 3. 데이터 수집
- 실시간 토픽 모니터링
- 이미지 + 액션 + 상태 저장
- HDF5 형식 지원

## 📋 테스트 시나리오
1. **기본 테스트**: 카메라 스트림 확인
2. **추론 테스트**: 모델 로드 및 추론
3. **제어 테스트**: 로봇 명령 전송
4. **통합 테스트**: 전체 시스템 실행

## 🚀 실행 명령어
```bash
# 전체 시스템 실행
ros2 launch mobile_vla_package launch_mobile_vla.launch.py

# 개별 노드 실행
ros2 run mobile_vla_package robovlms_inference
ros2 run mobile_vla_package camera_publisher
ros2 run mobile_vla_package robot_control_node
```

## 📝 다음 개선사항
1. 노드 간 통신 최적화
2. 에러 처리 강화
3. 로깅 시스템 개선
4. 성능 모니터링 추가
