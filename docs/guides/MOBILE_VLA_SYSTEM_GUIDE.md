# 🚀 Mobile VLA 시스템 완전 가이드

## 📋 시스템 개요

Mobile VLA 시스템은 PyTorch 2.3.0 기반의 Vision Language Agent를 사용하여 실시간 이미지 분석과 로봇 제어를 수행하는 통합 시스템입니다.

### 🏗️ 시스템 구성

```
┌─────────────────────────────────────────────────────────────┐
│                    Mobile VLA System                        │
├─────────────────────────────────────────────────────────────┤
│  🐳 Docker Container (mobile_vla:pytorch-2.3.0-cuda)        │
│                                                             │
│  📹 Camera Service Node                                     │
│  ├── CSI 카메라 스트림                                      │
│  └── 이미지 서비스 제공                                     │
│                                                             │
│  🧠 VLA Inference Node                                      │
│  ├── PyTorch 2.3.0 + CUDA                                   │
│  ├── Kosmos-2 모델 추론                                     │
│  └── 액션 예측                                              │
│                                                             │
│  🤖 Robot Control Node                                      │
│  ├── 수동 제어 (WASD)                                       │
│  ├── VLA 자동 제어                                          │
│  └── 하이브리드 모드                                        │
│                                                             │
│  📊 Data Collector Node                                     │
│  ├── 실시간 데이터 수집                                     │
│  └── HDF5 저장                                             │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 빠른 시작

### 1. 시스템 실행

```bash
# 시스템 실행
./run_mobile_vla_system.sh

# 또는 Docker Compose 사용
docker-compose -f docker-compose.mobile-vla.yml up -d
```

### 2. 컨테이너 접속

```bash
# 컨테이너에 접속
docker exec -it mobile_vla_main bash

# ROS2 환경 설정
source /opt/ros/humble/setup.bash
source /workspace/vla/ROS_action/install/setup.bash
```

### 3. 노드 실행

```bash
# 1. 카메라 노드 실행
ros2 run camera_pub camera_publisher_continuous

# 2. VLA 추론 노드 실행 (새 터미널)
ros2 run vla_inference vla_inference_node

# 3. 로봇 제어 노드 실행 (새 터미널)
ros2 run robot_control robot_control_node

# 4. 데이터 수집 노드 실행 (선택사항)
ros2 run mobile_vla_data_collector mobile_vla_data_collector
```

## 🎮 제어 모드

### 수동 모드 (Manual)
- **키**: `M`
- **설명**: WASD 키보드로 직접 로봇 제어
- **사용법**: 
  - `W`: 전진
  - `A`: 좌이동
  - `S`: 후진
  - `D`: 우이동
  - `Q/E/Z/C`: 대각선 이동
  - `R/T`: 회전
  - `Space`: 정지

### VLA 자동 모드
- **키**: `V`
- **설명**: VLA 모델이 이미지를 분석하여 자동으로 로봇 제어
- **동작**: 카메라 이미지 → VLA 추론 → 액션 예측 → 로봇 제어

### 하이브리드 모드
- **키**: `H`
- **설명**: 수동 입력 우선, 입력이 없으면 VLA 자동 제어
- **장점**: 안전성과 자동화의 균형

### 속도 조절
- **F**: 속도 증가 (+10%)
- **G**: 속도 감소 (-10%)

## 📊 시스템 모니터링

### 상태 확인

```bash
# 컨테이너 상태
docker ps
docker logs mobile_vla_main

# GPU 상태
docker exec mobile_vla_main nvidia-smi

# ROS2 노드 목록
ros2 node list

# ROS2 토픽 목록
ros2 topic list

# 토픽 모니터링
ros2 topic echo /vla_inference_result
ros2 topic echo /vla_action_command
ros2 topic echo /cmd_vel
```

### 성능 모니터링

```bash
# 시스템 리소스
docker stats mobile_vla_main

# ROS2 토픽 주파수
ros2 topic hz /camera/image_raw
ros2 topic hz /vla_inference_result

# 메모리 사용량
docker exec mobile_vla_main free -h
```

## 🔧 문제 해결

### 일반적인 문제들

#### 1. 카메라 연결 실패
```bash
# 카메라 장치 확인
ls -la /dev/video*

# 카메라 권한 설정
sudo chmod 666 /dev/video0

# 컨테이너 재시작
docker restart mobile_vla_main
```

#### 2. GPU 가속 문제
```bash
# CUDA 확인
docker exec mobile_vla_main python3 -c "import torch; print(torch.cuda.is_available())"

# NVIDIA 드라이버 확인
nvidia-smi

# 컨테이너 GPU 접근 확인
docker exec mobile_vla_main nvidia-smi
```

#### 3. ROS2 노드 연결 실패
```bash
# ROS2 환경 재설정
source /opt/ros/humble/setup.bash
source /workspace/vla/ROS_action/install/setup.bash

# ROS2 데몬 재시작
ros2 daemon stop
ros2 daemon start

# 네트워크 확인
ros2 node list
```

#### 4. 메모리 부족
```bash
# 메모리 사용량 확인
docker stats mobile_vla_main

# 불필요한 컨테이너 정리
docker system prune

# 스왑 메모리 확인
free -h
```

### 로그 분석

```bash
# 전체 로그 확인
docker logs mobile_vla_main

# 실시간 로그 모니터링
docker logs -f mobile_vla_main

# 특정 노드 로그
ros2 run camera_pub camera_publisher_continuous --ros-args --log-level debug
```

## 🛠️ 고급 설정

### Docker Compose 설정

```yaml
# docker-compose.mobile-vla.yml 수정
services:
  mobile_vla_main:
    environment:
      # GPU 메모리 제한
      - NVIDIA_MEM_LIMIT=4g
      # ROS2 도메인 ID
      - ROS_DOMAIN_ID=42
      # VLA 추론 간격
      - VLA_INFERENCE_INTERVAL=0.5
```

### ROS2 QoS 설정

```python
# 노드별 QoS 설정
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy

# 카메라용 QoS (BEST_EFFORT)
camera_qos = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    durability=DurabilityPolicy.VOLATILE,
    depth=1
)

# 제어용 QoS (RELIABLE)
control_qos = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.VOLATILE,
    depth=10
)
```

### 성능 최적화

```bash
# PyTorch 최적화
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
export TORCH_DTYPE=float16

# ROS2 최적화
export RMW_IMPLEMENTATION=rmw_cyclonedx_cpp
export ROS_DOMAIN_ID=42

# 시스템 최적화
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

## 📈 실험 및 데이터 수집

### 데이터 수집 모드

```bash
# 데이터 수집 시작
ros2 run mobile_vla_data_collector mobile_vla_data_collector

# 수집된 데이터 확인
ls -la /workspace/vla/mobile_vla_dataset/

# 데이터 분석
python3 /workspace/vla/analyze_mobile_vla_data.py
```

### 실험 시나리오

1. **기본 주행 테스트**
   - 수동 모드로 기본 주행
   - VLA 모드로 자동 주행
   - 하이브리드 모드 테스트

2. **장애물 회피 테스트**
   - 장애물 설치
   - VLA 모델의 회피 성능 측정

3. **장거리 주행 테스트**
   - 연속 주행 성능
   - 시스템 안정성 확인

## 🔒 보안 고려사항

### 네트워크 보안
```bash
# 방화벽 설정
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 8888  # Jupyter Notebook

# ROS2 네트워크 격리
export ROS_LOCALHOST_ONLY=1
```

### 데이터 보안
```bash
# 민감한 데이터 암호화
gpg --encrypt --recipient user@example.com sensitive_data.h5

# 백업 설정
rsync -av /workspace/vla/mobile_vla_dataset/ /backup/vla_data/
```

## 📚 참고 자료

### 공식 문서
- [ROS2 Humble Documentation](https://docs.ros.org/en/humble/)
- [PyTorch Documentation](https://pytorch.org/docs/)
- [Docker Documentation](https://docs.docker.com/)

### 프로젝트 관련
- [Mobile VLA GitHub Repository](https://github.com/minuum/vla)
- [Kosmos-2 Model](https://huggingface.co/microsoft/kosmos-2-patch14-224)
- [Jetson Development Guide](https://developer.nvidia.com/embedded/learn/get-started-jetson-orin)

### 커뮤니티
- [ROS2 Community](https://discourse.ros.org/)
- [PyTorch Forums](https://discuss.pytorch.org/)
- [NVIDIA Jetson Forums](https://forums.developer.nvidia.com/c/agx-autonomous-machines/jetson-embedded-systems/70)

## 🆘 지원 및 문의

### 문제 보고
1. GitHub Issues에 상세한 문제 설명
2. 시스템 로그 첨부
3. 재현 단계 명시

### 기능 요청
1. GitHub Discussions에서 논의
2. 상세한 사용 사례 설명
3. 우선순위 설정

### 기여하기
1. Fork & Pull Request
2. 코드 리뷰 참여
3. 문서 개선 제안

---

**⚠️ 주의사항**: 이 시스템은 연구 및 개발 목적으로 설계되었습니다. 실제 로봇에 적용하기 전에 충분한 테스트와 안전 검증이 필요합니다.

**📄 라이선스**: MIT License

**👥 기여자**: Mobile VLA Team
