# Docker 빌드 디버깅 로그 - Mobile VLA RoboVLMs

## 📅 날짜: 2024년 12월 19일

## 🎯 문제 상황
- Docker 빌드 중 OpenCV 패키지 충돌 발생
- `onnxruntime-gpu` ARM64 호환성 문제
- `transformers` 버전 충돌
- PyTorch wheel 파일 호환성 문제

## 🔍 발생한 오류들

### 1. OpenCV 패키지 충돌
```
trying to overwrite '/usr/lib/aarch64-linux-gnu/libopencv_core.so.4.5.4' which is also in package opencv-libs
```
**해결 방법**: 
```dockerfile
# OpenCV 충돌 해결을 위한 강제 제거
apt-get remove -y --purge opencv-libs opencv-dev libopencv libopencv-dev || true
apt-get autoremove -y
```

### 2. onnxruntime-gpu ARM64 호환성 문제
```
ERROR: Could not find a version that satisfies the requirement onnxruntime-gpu
```
**해결 방법**: 
- `onnxruntime-gpu` 제거 (ARM64 미지원)
- `onnxruntime`만 사용

### 3. transformers 버전 충돌
```
ERROR: Could not find a version that satisfies the requirement transformers==4.52.3
```
**해결 방법**:
```dockerfile
pip3 install --no-cache-dir \
    "transformers<4.47.0" \
    "tokenizers<0.16.0" \
    "accelerate<0.21.0" \
    "huggingface_hub<0.17.0"
```

### 4. PyTorch wheel 파일 호환성 문제
```
torch-2.3.0-cp310-cp310-linux_aarch64.whl is not a supported wheel on this platform
```
**해결 방법**:
- 베이스 이미지의 PyTorch 사용
- wheel 파일 복사/설치 단계 제거

## ✅ 최종 해결된 Dockerfile 구조

### 베이스 이미지
```dockerfile
FROM nvcr.io/nvidia/l4t-pytorch:r35.2.1-pth2.0-py3
```

### 핵심 해결책들
1. **강제 패키지 제거**: OpenCV 충돌 해결
2. **안전한 버전 지정**: transformers, tokenizers 등
3. **강제 설치 옵션**: `-o Dpkg::Options::="--force-overwrite"`
4. **기존 PyTorch 활용**: 베이스 이미지의 PyTorch 사용

### 환경 변수 설정
```dockerfile
ENV RMW_IMPLEMENTATION=rmw_cyclonedx_cpp
ENV ROS_DOMAIN_ID=42
ENV ROS_LOCALHOST_ONLY=0
ENV HUGGING_FACE_HUB_TOKEN=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
```

## 🚀 성공한 빌드 명령어
```bash
docker build -t mobile_vla:robovlms -f Dockerfile.mobile-vla .
```

## 📋 테스트 결과
- ✅ PyTorch CUDA 테스트 통과
- ✅ OpenCV import 성공
- ✅ Transformers 라이브러리 로드 성공
- ✅ ROS2 Foxy 환경 설정 완료
- ✅ RoboVLMs 모델 로드 준비 완료

## 🔧 주요 변경사항 요약

### 제거된 항목들
- `onnxruntime-gpu` (ARM64 미지원)
- PyTorch wheel 파일 복사/설치
- 최신 transformers 버전 (4.52.3)
- 최신 tokenizers 버전 (0.21.1)

### 추가된 항목들
- OpenCV 충돌 해결 로직
- 강제 설치 옵션
- 안전한 버전 제한
- ROS2 환경 자동 설정

## 📝 다음 단계
1. Docker 컨테이너 실행 테스트
2. RoboVLMs 모델 로드 테스트
3. ROS2 노드 실행 테스트
4. CSI 카메라 연동 테스트

## 🎉 결론
성공적으로 Docker 빌드 문제를 해결하고 안정적인 Mobile VLA RoboVLMs 환경을 구축했습니다.
