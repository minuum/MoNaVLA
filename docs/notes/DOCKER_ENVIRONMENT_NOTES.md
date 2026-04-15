# Docker 환경 노트 - Mobile VLA RoboVLMs

## 📁 관련 파일들
- [Dockerfile.mobile-vla](./Dockerfile.mobile-vla) - 메인 Docker 환경 설정
- [DOCKER_DEBUG_LOG.md](./DOCKER_DEBUG_LOG.md) - Docker 빌드 디버깅 과정
- [docker-compose.mobile-vla.yml](./docker-compose.mobile-vla.yml) - Docker Compose 설정
- [run_robovlms_docker.sh](./run_robovlms_docker.sh) - Docker 실행 스크립트

## 🎯 주요 아이디어들

### 1. 베이스 이미지 선택
- **선택**: `nvcr.io/nvidia/l4t-pytorch:r35.2.1-pth2.0-py3`
- **이유**: Jetson 최적화, PyTorch 2.0 포함, CUDA 지원
- **장점**: ARM64 호환, GPU 가속, 안정성

### 2. OpenCV 충돌 해결
```dockerfile
# OpenCV 충돌 해결을 위한 강제 제거
apt-get remove -y --purge opencv-libs opencv-dev libopencv libopencv-dev || true
apt-get autoremove -y
```
- **문제**: 시스템 OpenCV와 pip OpenCV 충돌
- **해결**: 기존 OpenCV 제거 후 pip로 설치

### 3. ARM64 호환성 고려사항
- `onnxruntime-gpu` 제거 (ARM64 미지원)
- `onnxruntime`만 사용
- PyTorch wheel 파일 호환성 문제 해결

### 4. 안전한 패키지 버전
```dockerfile
pip3 install --no-cache-dir \
    "transformers<4.47.0" \
    "tokenizers<0.16.0" \
    "accelerate<0.21.0" \
    "huggingface_hub<0.17.0"
```

### 5. ROS2 Foxy 환경
- Ubuntu 20.04 기반 ROS2 Foxy
- `rmw_cyclonedx_cpp` 사용
- ROS2 패키지 자동 설치

## 🔧 환경 변수 설정
```dockerfile
ENV RMW_IMPLEMENTATION=rmw_cyclonedx_cpp
ENV ROS_DOMAIN_ID=42
ENV ROS_LOCALHOST_ONLY=0
ENV HUGGING_FACE_HUB_TOKEN=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
```

## 📋 테스트 결과
- ✅ PyTorch CUDA 테스트 통과
- ✅ OpenCV import 성공
- ✅ Transformers 라이브러리 로드 성공
- ✅ ROS2 Foxy 환경 설정 완료

## 🚀 빌드 명령어
```bash
docker build -t mobile_vla:robovlms -f Dockerfile.mobile-vla .
```

## 📝 다음 개선사항
1. 멀티스테이지 빌드로 이미지 크기 최적화
2. 캐시 레이어 최적화
3. 보안 강화 (non-root 사용자)
