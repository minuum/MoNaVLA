# 🚀 Mobile VLA Jetson Docker 환경 가이드

## 📋 개요

**Jetson Orin NX**에 최적화된 **Mobile VLA Docker 환경**입니다.

- **베이스 이미지**: `dustynv/pytorch:2.6-r36.4.0` (JetPack 6.0 기반)
- **지원 기능**: CSI 카메라, ROS2 Humble, PyTorch 2.6, CUDA 12.2
- **아키텍처**: ARM64 (aarch64) 최적화

---

## 🔧 시스템 요구사항

### 하드웨어
- **NVIDIA Jetson Orin NX** (16GB 권장)
- **CSI 카메라** (IMX219 등)
- **최소 32GB 저장공간**

### 소프트웨어
- **JetPack 6.0** (L4T R36.4)
- **Ubuntu 22.04** (호스트)
- **Docker** + **NVIDIA Container Runtime**

---

## 🚀 빠른 시작

### 1️⃣ 환경 설정
```bash
# 설정 스크립트 실행
chmod +x docker-setup-jetson.sh
./docker-setup-jetson.sh
```

### 2️⃣ Docker 이미지 빌드
```bash
./docker-build.sh
```

### 3️⃣ GPU 테스트 (선택사항)
```bash
./test-docker-gpu.sh
```

### 4️⃣ 컨테이너 시작
```bash
./docker-run.sh
```

### 5️⃣ 컨테이너 접속
```bash
docker exec -it mobile_vla_jetson bash
```

---

## 🎥 CSI 카메라 테스트

### 컨테이너 내부에서:
```bash
# 방법 1: alias 사용
vla-camera

# 방법 2: 직접 실행
ros2 run camera_pub camera_publisher_continuous
```

### 호스트에서 직접:
```bash
docker exec -it mobile_vla_jetson vla-camera
```

---

## 📊 Mobile VLA 데이터 수집

### 컨테이너 내부에서:
```bash
# 방법 1: alias 사용
vla-collect

# 방법 2: 직접 실행
python mobile_vla_data_collector.py
```

### 호스트에서 직접:
```bash
docker exec -it mobile_vla_jetson vla-collect
```

---

## 🔍 유용한 명령어

### 컨테이너 관리
```bash
# 컨테이너 상태 확인
docker ps

# 로그 확인
docker-compose -f docker-compose.jetson.yml logs mobile-vla

# 컨테이너 중지
./docker-stop.sh

# 컨테이너 재시작
docker-compose -f docker-compose.jetson.yml restart mobile-vla
```

### 시스템 모니터링
```bash
# 모니터링 서비스 시작
./docker-monitor.sh

# 모니터링 로그 확인
docker logs -f mobile_vla_monitoring

# GPU 사용량 확인 (컨테이너 내부)
nvidia-smi
```

### ROS2 관리
```bash
# 컨테이너 내부에서
source /opt/ros/humble/setup.bash

# ROS2 노드 확인
ros2 node list

# 토픽 확인
ros2 topic list

# 카메라 토픽 확인
ros2 topic echo /camera/image_raw --once
```

### 개발 도구
```bash
# 컨테이너 내부 유용한 alias들
cuda-test      # CUDA/PyTorch 상태 확인
vla-build      # ROS2 워크스페이스 빌드
vla-source     # ROS2 환경 소싱
```

---

## 📁 디렉토리 구조

```
vla/
├── Dockerfile.jetson              # Jetson 최적화 Dockerfile
├── docker-compose.jetson.yml      # Docker Compose 설정
├── docker-setup-jetson.sh         # 환경 설정 스크립트
├── docker-build.sh               # 빌드 스크립트
├── docker-run.sh                 # 실행 스크립트
├── docker-stop.sh                # 중지 스크립트
├── docker-monitor.sh             # 모니터링 스크립트
├── test-docker-gpu.sh            # GPU 테스트 스크립트
├── .env                          # 환경 변수
├── docker_volumes/               # Docker 볼륨
│   ├── cache/                   # 모델 캐시
│   ├── dataset/                 # 데이터셋
│   └── logs/                    # 로그
├── mobile_vla_dataset/          # 수집된 데이터
├── ROS_action/                  # ROS2 워크스페이스
└── ...                          # 기타 파일들
```

---

## 🐛 문제 해결

### 1. CSI 카메라 문제
```bash
# 호스트에서 카메라 디바이스 확인
ls -la /dev/video*

# nvargus-daemon 상태 확인
systemctl status nvargus-daemon

# 카메라 권한 확인
groups | grep video
```

### 2. Docker 권한 문제
```bash
# Docker 그룹 추가
sudo usermod -aG docker $USER

# 로그아웃 후 재로그인 또는
newgrp docker
```

### 3. NVIDIA Runtime 문제
```bash
# NVIDIA Container Runtime 확인
docker info | grep nvidia

# NVIDIA Runtime 재설치 (필요시)
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

### 4. 메모리 부족
```bash
# Swap 확인
free -h

# Swap 추가 (필요시)
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### 5. 컨테이너 빌드 실패
```bash
# Docker 캐시 정리
docker system prune -a

# 다시 빌드 (캐시 없이)
docker-compose -f docker-compose.jetson.yml build --no-cache
```

---

## 📊 성능 최적화

### GPU 메모리 최적화
```bash
# 컨테이너 내부에서
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
```

### ROS2 DDS 최적화
```bash
# 컨테이너 내부에서
export ROS_DOMAIN_ID=42
export RMW_IMPLEMENTATION=rmw_cyclonedx_cpp
```

### CSI 카메라 최적화
- **해상도**: 1280x720 (기본)
- **FPS**: 30fps (조정 가능)
- **포맷**: NV12 → BGRx → BGR

---

## 🔗 참고 자료

- [NVIDIA Jetson Containers](https://github.com/dusty-nv/jetson-containers)
- [JetPack 6.0 Release Notes](https://developer.nvidia.com/embedded/jetpack)
- [ROS2 Humble Documentation](https://docs.ros.org/en/humble/)
- [Mobile VLA Project](./README.md)

---

## 📞 지원

문제가 발생하면:
1. 이 가이드의 **문제 해결** 섹션 참조
2. Docker 로그 확인: `docker logs mobile_vla_jetson`
3. 시스템 상태 확인: `./test-docker-gpu.sh`

---

**Happy Mobile VLA Development! 🚀**