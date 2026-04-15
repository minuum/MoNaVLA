# 📁 Mobile VLA Config 디렉토리

이 디렉토리는 Mobile VLA 프로젝트의 모든 설정 파일과 모델 관련 파일들을 체계적으로 관리합니다.

## 📂 디렉토리 구조

```
config/
├── checkpoints/          # 모델 체크포인트 파일들
├── scripts/              # 실행 스크립트들
├── weights/              # PyTorch 휠 파일들
├── models/               # 모델 정의 파일들
├── datasets/             # 데이터셋 파일들
└── README.md             # 이 파일
```

## 🚀 사용 방법

### 모델 추론 실행
```bash
cd /home/soda/vla
python3 config/scripts/final_mobile_vla_inference.py
```

### CUDA 테스트
```bash
python3 config/scripts/pytorch_cuda_test.py
```

### 체크포인트 분석
```bash
python3 config/scripts/checkpoint_analysis.py
```

## 📋 파일 설명

### checkpoints/
- `best_simple_lstm_model.pth`: Simple LSTM 모델 체크포인트
- `best_simple_clip_lstm_model.pth`: CLIP + LSTM 하이브리드 모델 체크포인트

### scripts/
- `final_mobile_vla_inference.py`: 최종 Mobile VLA 추론 스크립트
- `pytorch_cuda_test.py`: PyTorch CUDA 환경 테스트
- `checkpoint_analysis.py`: 모델 체크포인트 분석 도구
- `kosmos_camera_test.py`: Kosmos2 + 카메라 테스트
- `launch_mobile_vla_system.py`: Mobile VLA 시스템 런처
- `local_inference_test.py`: 로컬 추론 테스트
- `actual_model_inference_test.py`: 실제 모델 추론 테스트
- `real_model_inference_test.py`: 실제 모델 추론 검증

### weights/
- PyTorch Jetson용 휠 파일들 (CUDA 지원)

## ⚠️ 주의사항

- 큰 파일들(*.whl, *.pth)은 Git LFS로 관리됩니다
- 로컬 환경에서 실행하는 것을 권장합니다 (BSP 호환성)
- 도커 환경은 현재 CUDA 호환성 문제가 있습니다
