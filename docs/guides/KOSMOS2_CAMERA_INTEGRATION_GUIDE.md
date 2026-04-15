# 📷 Kosmos-2 + 카메라 통합 가이드

## 🎯 개요

이 가이드는 Microsoft Kosmos-2 Vision Language Model을 Jetson Orin NX 환경에서 카메라와 통합하여 실시간 이미지 분석을 수행하는 방법을 설명합니다.

## 🏗️ 시스템 요구사항

### 하드웨어
- **Jetson Orin NX** (8GB RAM 권장)
- **CSI 카메라** 또는 **USB 카메라**
- **GPU 메모리**: 4GB 이상

### 소프트웨어
- **Ubuntu 22.04 LTS**
- **Python 3.10+**
- **PyTorch 2.0+**
- **Transformers 4.52.3**
- **OpenCV 4.8+**

## 🚀 설치 및 설정

### 1.1 기본 환경 설정

```bash
# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# Python 패키지 설치
pip3 install torch torchvision torchaudio
pip3 install transformers pillow opencv-python
pip3 install huggingface_hub
```

### 1.2 Hugging Face 설정

```bash
# Hugging Face CLI 설치
pip3 install huggingface_hub

# 환경 변수 설정
export HF_HOME="/home/$USER/.cache/huggingface"
export TRANSFORMERS_CACHE="/home/$USER/.cache/huggingface/transformers"
```

### 3.2 Hugging Face 로그인

```bash
# Hugging Face CLI 로그인
huggingface-cli login

# 토큰 입력 (프롬프트가 나타나면)
# Token: [YOUR_HUGGING_FACE_TOKEN_HERE]
```

## 🧠 4. Kosmos-2 모델 테스트

### 4.1 기본 모델 테스트

```bash
# Kosmos-2 모델 로드 테스트
python3 -c "
from transformers import AutoProcessor, AutoModelForVision2Seq
print('Loading Kosmos-2 model...')
model = AutoModelForVision2Seq.from_pretrained('microsoft/kosmos-2-patch14-224')
print('Model loaded successfully!')
"
```

### 4.2 카메라 + Kosmos-2 통합 테스트

```bash
# 테스트 스크립트 실행
python3 simple_camera_kosmos_test.py
```

## 📷 5. 카메라 설정

### 5.1 실제 카메라 사용 (선택사항)

- **CSI 카메라**: Jetson 기본 카메라
- **USB 카메라**: /dev/video0 또는 /dev/video1

### 5.2 가상 카메라 모드

- 실제 카메라가 없어도 가상 이미지로 테스트 가능
- 컵과 책이 포함된 테스트 이미지 자동 생성

## 📊 6. 테스트 결과 확인

### 6.1 생성된 파일들

```bash
# 테스트 이미지 확인
ls -la test_image_*.jpg

# 이미지 내용 확인
file test_image_1.jpg
```

### 6.2 분석 결과

- **이미지 크기**: 640x480 픽셀
- **처리 상태**: "Vision features extracted successfully"
- **분석 횟수**: 3회 연속 테스트

## 🔄 7. 고급 사용법

### 7.1 ROS2와 연동 (선택사항)

```bash
# ROS2 환경 설정
cd ROS_action
source install/setup.bash

# 카메라 노드 실행
ros2 run camera_pub camera_publisher_continuous

# Kosmos-2 분석 노드 실행 (별도 터미널)
python3 kosmos_camera_test.py
```

### 7.2 커스텀 이미지 분석

```python
# Python 스크립트에서 직접 사용
from transformers import AutoProcessor, AutoModelForVision2Seq
from PIL import Image

# 모델 로드
model = AutoModelForVision2Seq.from_pretrained("microsoft/kosmos-2-patch14-224")
processor = AutoProcessor.from_pretrained("microsoft/kosmos-2-patch14-224")

# 이미지 분석
image = Image.open("your_image.jpg")
inputs = processor(text="<grounding>Describe this image:", images=image, return_tensors="pt")
# 분석 로직...
```

## 🐛 8. 문제 해결

### 8.1 Docker 관련 문제

```bash
# Docker 권한 문제
sudo usermod -aG docker $USER
newgrp docker

# GPU 접근 문제
docker run --gpus all --rm nvidia/cuda:11.0-base nvidia-smi
```

### 8.2 메모리 부족 문제

```bash
# 스왑 메모리 확인
free -h

# 스왑 파일 생성 (필요시)
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### 8.3 모델 다운로드 문제

```bash
# 캐시 정리
rm -rf ~/.cache/huggingface

# 프록시 설정 (필요시)
export HTTP_PROXY="http://proxy.example.com:8080"
export HTTPS_PROXY="http://proxy.example.com:8080"
```

## 📈 9. 성능 최적화

### 9.1 GPU 메모리 최적화

```python
# 모델을 GPU로 이동
model = model.to('cuda')

# 메모리 정리
import torch
torch.cuda.empty_cache()
```

### 9.2 배치 처리

```python
# 여러 이미지 동시 처리
images = [Image.open(f"image_{i}.jpg") for i in range(5)]
inputs = processor(text="<grounding>Describe this image:", images=images, return_tensors="pt")
```

## 🔒 10. 보안 고려사항

### 10.1 토큰 관리

- **환경 변수 사용**: `export HF_TOKEN="your_token"`
- **설정 파일**: `~/.huggingface/token`
- **Docker 시크릿**: Docker Compose secrets 사용

### 10.2 네트워크 보안

```bash
# 방화벽 설정
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 8888  # Jupyter Notebook
```

## 📚 11. 참고 자료

- [Kosmos-2 공식 문서](https://huggingface.co/microsoft/kosmos-2-patch14-224)
- [Transformers 라이브러리](https://huggingface.co/docs/transformers)
- [Jetson 개발자 가이드](https://developer.nvidia.com/embedded/learn/get-started-jetson-orin)

## 🤝 12. 지원 및 문의

문제가 발생하거나 추가 지원이 필요한 경우:

1. **GitHub Issues**: 프로젝트 저장소에 이슈 등록
2. **문서 확인**: 이 가이드의 문제 해결 섹션 참조
3. **커뮤니티**: Jetson 개발자 포럼 활용

---

**⚠️ 주의사항**: 이 가이드는 개발 및 테스트 목적으로 작성되었습니다. 프로덕션 환경에서는 추가적인 보안 및 성능 최적화가 필요할 수 있습니다.
