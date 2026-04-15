# Mobile VLA LoRA Fine-tuning 실행 요약

## 📋 생성된 파일

### 1. Config 파일
```
Mobile_VLA/configs/finetune_mobile_vla_lora_20251106.json
```
- RoboVLMs upstream config 기반
- LoRA 설정: r=32, alpha=16, dropout=0.1
- 2D 액션 공간: action_dim=2 (linear_x, linear_y)
- Jetson 최적화: batch_size=2, fp16, memory_limit=14GB

### 2. 데이터셋 구현
```
Mobile_VLA/src/data/mobile_vla_h5_dataset.py
```
- HDF5 파일 로드 (20251106 에피소드)
- Window size=8, Action chunk=10
- 이미지 전처리 (224x224, ImageNet 정규화)
- Train/Val 분할 (80/20)

### 3. LoRA Fine-tuning 스크립트
```
Mobile_VLA/src/training/finetune_lora_20251106.py
```
- Kosmos-2 VLM + LoRA 적용
- AdamW Optimizer + Cosine Annealing LR
- Gradient Clipping (max_norm=1.0)
- 체크포인트 저장 (best + 주기적)

### 4. 실행 스크립트
```
Mobile_VLA/scripts/run_lora_finetune_20251106.sh
```
- CUDA 확인
- 데이터셋 확인
- LoRA Fine-tuning 실행
- 학습 시간 측정

### 5. 테스트 스크립트
```
Mobile_VLA/scripts/test_dataset_20251106.py
```
- 데이터셋 로드 테스트
- 배치 생성 테스트

### 6. 가이드 문서
```
Mobile_VLA/README_LORA_FINETUNING.md
```
- 전체 실행 가이드
- 문제 해결 방법
- 참고 자료

---

## 🚀 실행 순서

### 1단계: 데이터셋 테스트
```bash
cd /home/billy/25-1kp/vla
python3 Mobile_VLA/scripts/test_dataset_20251106.py
```

**예상 결과:**
- ✅ 11개 Training 에피소드
- ✅ 2개 Validation 에피소드
- ✅ 배치 로드 성공

### 2단계: LoRA 시간 측정 (1 에포크)
```bash
# Config 수정: max_epochs를 1로 변경
vim Mobile_VLA/configs/finetune_mobile_vla_lora_20251106.json

# 실행
bash Mobile_VLA/scripts/run_lora_finetune_20251106.sh

# 결과 확인
cat Mobile_VLA/runs/mobile_vla_lora/logs/training_results.json | grep avg_epoch_time
```

### 3단계: 전체 학습 (50 에포크)
```bash
# Config 수정: max_epochs를 50으로 변경
vim Mobile_VLA/configs/finetune_mobile_vla_lora_20251106.json

# 실행
bash Mobile_VLA/scripts/run_lora_finetune_20251106.sh
```

---

## 📊 예상 결과

### 학습 시간 (Jetson AGX Orin 16GB)
- **1 에포크**: ~5-10분 (예상)
- **50 에포크**: ~4-8시간 (예상)

### 모델 크기
- **Full Model**: ~2GB (Kosmos-2)
- **LoRA Adapter**: ~50MB (학습 파라미터만)

### 학습 파라미터
- **Total Parameters**: ~1.3B (Kosmos-2)
- **Trainable Parameters**: ~10M (LoRA, <1%)

---

## 🎯 핵심 차이점: RoboVLMs vs Mobile VLA

| 항목 | RoboVLMs | Mobile VLA |
|------|----------|------------|
| **Fine-tuning** | Full FT | LoRA |
| **Action Space** | 7D (6-DOF + gripper) | 2D (linear_x, linear_y) |
| **Dataset** | CALVIN 24K episodes | 13 episodes (20251106) |
| **Epochs** | 5 | 50 |
| **Learning Rate** | 2e-5 | 1e-4 |
| **Batch Size** | 4 | 2 |
| **Hidden Size** | 1024 | 512 |
| **Trainable %** | 100% | <1% |

---

## 📁 출력 구조

```
Mobile_VLA/runs/mobile_vla_lora/
├── checkpoints/
│   ├── best_model.pth              # 최고 성능 모델
│   ├── checkpoint_epoch_10.pth
│   ├── checkpoint_epoch_20.pth
│   ├── checkpoint_epoch_30.pth
│   ├── checkpoint_epoch_40.pth
│   └── checkpoint_epoch_50.pth
└── logs/
    ├── training_results.json       # 학습 결과 요약
    ├── events.out.tfevents.*       # TensorBoard
    └── metrics.csv
```

---

## 🔍 학습 모니터링

### TensorBoard
```bash
tensorboard --logdir=Mobile_VLA/runs/mobile_vla_lora/logs
# http://localhost:6006
```

### 실시간 로그
```bash
tail -f Mobile_VLA/runs/mobile_vla_lora/logs/training_results.json
```

---

## ✅ 검증 항목

### 데이터셋
- [x] 20251106 에피소드 13개 확인
- [x] HDF5 구조 확인 (images, actions, action_event_types)
- [x] Train/Val 분할 (11/2)

### 모델
- [x] Kosmos-2 로드
- [x] LoRA 적용 (r=32, alpha=16)
- [x] 2D 액션 헤드 (action_dim=2)
- [x] Gripper 제거

### 학습
- [x] AdamW Optimizer
- [x] Cosine Annealing LR
- [x] Gradient Clipping
- [x] 체크포인트 저장

### Config
- [x] RoboVLMs upstream 참조
- [x] Mobile VLA 태스크 적응
- [x] Jetson 최적화

---

## 📚 참고 코드

### RoboVLMs Upstream
```
RoboVLMs_upstream/configs/calvin_finetune/
└── finetune_kosmos_cont-lstm-post_full-ft_text_vision_wd-0_ws-8_act-10.json
```

### Mobile VLA 구현
```
Mobile_VLA/src/
├── model/mobile_vla_model.py           # LoRA 적용된 Kosmos-2
├── data/mobile_vla_h5_dataset.py       # HDF5 데이터셋
└── training/finetune_lora_20251106.py  # LoRA Fine-tuning
```

---

## 🎉 완료 후 다음 단계

1. **추론 테스트**: 학습된 모델로 추론
2. **성능 평가**: MAE, MSE 계산
3. **실시간 테스트**: Jetson에서 로봇 제어
4. **100 Dataset 수집**: 추가 데이터 수집
5. **논문 작성**: RoboVLMs + Robot Manipulator

---

**작성일**: 2025-11-06  
**상태**: 구현 완료, 실행 준비 완료  
**다음**: LoRA 시간 측정 (1 에포크)

