# 🚀 Mobile VLA Docker 환경 - 검증된 VLA 기반

## 📋 개요

**검증된 vla_app_final 환경**을 기반으로 한 **Mobile VLA Docker 시스템**입니다.

- **베이스 이미지**: `nvcr.io/nvidia/l4t-pytorch:r35.2.1-pth2.0-py3` (검증된 43.7GB)
- **기반 환경**: 기존 vla_app_final_restored (실제 작동 검증됨)
- **추가 기능**: CSI 카메라, Mobile VLA 데이터 수집, ROS2 확장

---

## 🎯 왜 검증된 환경을 사용하나요?

✅ **안정성**: 이미 작동이 확인된 VLA 환경  
✅ **호환성**: OpenVLA, Transformers, PyTorch 버전 검증됨  
✅ **신뢰성**: Accelerate 패치, HDF5 설정 등 모든 설정 검증됨  
✅ **효율성**: 처음부터 구축하는 것보다 빠르고 안전  

---

## 🚀 빠른 시작

### 1️⃣ 환경 준비
```bash
cd ~/vla

# 필요한 볼륨 디렉토리 생성 (자동으로 생성되지만 미리 확인)
mkdir -p docker_volumes/{cache,dataset,logs}
```

### 2️⃣ Docker 이미지 빌드
```bash
./docker-build-verified.sh
```
⏰ **예상 시간**: 30-60분 (베이스 이미지 43.7GB + 추가 패키지)

### 3️⃣ 컨테이너 실행
```bash
./docker-run-verified.sh
```

### 4️⃣ 컨테이너 접속 및 테스트
```bash
# 컨테이너 접속
docker exec -it mobile_vla_verified bash

# 환경 테스트 (컨테이너 내부에서)
torch_cuda_test      # 기존 VLA CUDA 테스트 (검증된)
cuda-test           # 간단한 CUDA 테스트
/usr/local/bin/healthcheck.sh  # 전체 시스템 헬스체크
```

---

## 🎥 CSI 카메라 테스트

### 컨테이너 내부에서:
```bash
# ROS2 환경 소싱 (자동으로 됨)
source /opt/ros/humble/setup.bash

# ROS_action 워크스페이스 빌드 (필요시)
vla-build

# CSI 카메라 노드 실행
vla-camera
```

### 호스트에서 직접:
```bash
docker exec -it mobile_vla_verified vla-camera
```

---

## 📊 Mobile VLA 데이터 수집

### 컨테이너 내부에서:
```bash
# 데이터 수집 시작
vla-collect

# 또는 직접 실행
python mobile_vla_data_collector.py
```

### 호스트에서 직접:
```bash
docker exec -it mobile_vla_verified vla-collect
```

### 수집된 데이터 확인:
```bash
# HDF5 파일 확인
python check_h5_file.py mobile_vla_dataset/episode_*.h5

# 데이터 인스펙터 실행
python mobile_vla_package/mobile_vla_package/data_inspector.py
```

---

## 🔧 주요 명령어 모음

### 컨테이너 관리
```bash
# 빌드
./docker-build-verified.sh

# 실행
./docker-run-verified.sh

# 중지
./docker-stop-verified.sh

# 모니터링 서비스 시작
./docker-monitor-verified.sh

# 컨테이너 접속
docker exec -it mobile_vla_verified bash

# 로그 확인
docker logs -f mobile_vla_verified
```

### 시스템 테스트
```bash
# 컨테이너 내부에서 사용 가능한 alias들
torch_cuda_test      # 기존 VLA CUDA 테스트
cuda-test           # 간단한 CUDA 테스트
vla-build           # ROS2 워크스페이스 빌드
vla-source          # ROS2 환경 소싱
vla-camera          # CSI 카메라 노드 실행
vla-collect         # Mobile VLA 데이터 수집
```

### ROS2 관리
```bash
# 컨테이너 내부에서
ros2 node list                    # 실행 중인 노드 확인
ros2 topic list                   # 토픽 목록
ros2 topic echo /camera/image_raw --once  # 카메라 이미지 확인
ros2 topic hz /camera/image_raw   # 카메라 FPS 확인
```

---

## 📁 디렉토리 구조

```
vla/
├── Dockerfile.mobile-vla              # 검증된 환경 기반 Dockerfile
├── docker-compose.mobile-vla.yml      # Docker Compose 설정
├── docker-build-verified.sh           # 빌드 스크립트
├── docker-run-verified.sh             # 실행 스크립트
├── docker-stop-verified.sh            # 중지 스크립트
├── docker-monitor-verified.sh         # 모니터링 스크립트
├── pytorch_cuda_test.py               # CUDA 테스트 스크립트
├── docker_volumes/                    # Docker 볼륨
│   ├── cache/                        # 모델 캐시
│   ├── dataset/                      # 수집된 데이터
│   └── logs/                         # 로그 파일
├── mobile_vla_dataset/               # Mobile VLA 데이터
├── ROS_action/                       # ROS2 워크스페이스
└── ...                               # 기타 파일들
```

---

## 🔍 모니터링 & 디버깅

### 시스템 모니터링
```bash
# 모니터링 서비스 시작
./docker-monitor-verified.sh

# 실시간 모니터링 로그
docker logs -f mobile_vla_monitoring

# GPU 사용량 확인
docker exec -it mobile_vla_verified nvidia-smi

# 리소스 사용량 확인
docker stats mobile_vla_verified
```

### 헬스체크 및 진단
```bash
# 전체 시스템 헬스체크
docker exec -it mobile_vla_verified /usr/local/bin/healthcheck.sh

# 개별 컴포넌트 테스트
docker exec -it mobile_vla_verified torch_cuda_test
docker exec -it mobile_vla_verified python -c "import cv2; print(cv2.__version__)"
docker exec -it mobile_vla_verified python -c "import h5py; print(h5py.__version__)"
```

---

## 🐛 문제 해결

### 1. 컨테이너 빌드 실패
```bash
# Docker 캐시 정리
docker system prune -a

# 다시 빌드
./docker-build-verified.sh
```

### 2. CSI 카메라 문제
```bash
# 호스트에서 카메라 상태 확인
ls -la /dev/video*
systemctl status nvargus-daemon

# 컨테이너에서 카메라 테스트
docker exec -it mobile_vla_verified ls -la /dev/video*
```

### 3. ROS2 문제
```bash
# 컨테이너 내부에서 ROS2 환경 재설정
source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID=42

# ROS2 데몬 재시작
ros2 daemon stop
ros2 daemon start
```

### 4. GPU/CUDA 문제
```bash
# 호스트에서 NVIDIA 런타임 확인
docker info | grep nvidia

# 컨테이너에서 GPU 테스트
docker exec -it mobile_vla_verified nvidia-smi
docker exec -it mobile_vla_verified torch_cuda_test
```

---

## 🔄 업데이트 & 백업

### 데이터 백업
```bash
# 수집된 데이터 백업
tar -czf mobile_vla_backup_$(date +%Y%m%d).tar.gz \
    docker_volumes/ mobile_vla_dataset/

# 컨테이너 이미지 백업
docker save mobile_vla:verified-base | gzip > mobile_vla_verified_backup.tar.gz
```

### 환경 업데이트
```bash
# 새 버전 빌드
./docker-build-verified.sh

# 기존 컨테이너 중지 후 새 버전 실행
./docker-stop-verified.sh
./docker-run-verified.sh
```

---

## 📈 성능 최적화

### GPU 메모리 최적화
- 환경 변수: `PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512`
- 자동으로 설정됨

### ROS2 DDS 최적화
```bash
# 컨테이너 내부에서 (자동 설정됨)
export ROS_DOMAIN_ID=42
export RMW_IMPLEMENTATION=rmw_cyclonedx_cpp
```

### CSI 카메라 최적화
- **해상도**: 1280x720 (조정 가능)
- **FPS**: 3fps (Mobile VLA 데이터 수집 최적화)
- **포맷**: NV12 → BGRx → BGR

---

## 🎯 다음 단계

1. **데이터 수집**: Mobile VLA 데이터 수집 시작
2. **모델 학습**: 수집된 데이터로 VLA 모델 학습
3. **성능 평가**: 컵 추적 시나리오 테스트
4. **스케일링**: 더 복잡한 시나리오로 확장

---

## 📞 지원

문제가 발생하면:
1. **헬스체크 실행**: `docker exec -it mobile_vla_verified /usr/local/bin/healthcheck.sh`
2. **로그 확인**: `docker logs mobile_vla_verified`
3. **모니터링 확인**: `./docker-monitor-verified.sh`

---

**Happy Mobile VLA Development with Verified Environment! 🚀**