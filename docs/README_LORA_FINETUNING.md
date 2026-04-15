# Mobile VLA LoRA Fine-tuning Guide (20251106 Episodes)

## 📋 개요

20251106 날짜에 수집한 에피소드를 Kosmos VLM에 LoRA로 파인튜닝하는 가이드입니다.

참조: [RoboVLMs GitHub](https://github.com/Robot-VLAs/RoboVLMs)

---

## 🎯 목표

- **데이터**: 20251106 에피소드 (13개 HDF5 파일)
- **모델**: Kosmos-2 (microsoft/kosmos-2-patch14-224)
- **방법**: LoRA Fine-tuning (r=32, alpha=16)
- **태스크**: 2D Mobile Robot Navigation (linear_x, linear_y)

---

## 📊 데이터셋 구조

### HDF5 파일 구조
```python
episode_20251106_*.h5
├── images: (T, 720, 1280, 3) uint8      # RGB 이미지
├── actions: (T, 3) float32              # [linear_x, linear_y, angular_z]
└── action_event_types: (T,)             # 액션 이벤트 타입
```

### 수집된 에피소드
```bash
ROS_action/mobile_vla_dataset/
├── episode_20251106_145248_1box_hori_left_core_medium.h5
├── episode_20251106_145456_1box_hori_left_core_medium.h5
├── episode_20251106_145609_1box_hori_left_core_medium.h5
├── episode_20251106_145705_1box_hori_left_core_medium.h5
├── episode_20251106_145841_1box_hori_left_core_medium.h5
├── episode_20251106_145934_1box_hori_left_core_medium.h5
├── episode_20251106_150243_1box_hori_left_core_medium.h5
├── episode_20251106_150407_1box_hori_left_core_medium.h5
├── episode_20251106_151110_1box_hori_left_core_medium.h5
├── episode_20251106_151305_1box_hori_left_core_medium.h5
├── episode_20251106_151417_1box_hori_left_core_medium.h5
├── episode_20251106_151744_1box_hori_left_core_medium.h5
└── episode_20251106_151851_1box_hori_left_core_medium.h5
```

**총 13개 에피소드**

---

## ⚙️ LoRA 설정

### RoboVLMs vs Mobile VLA

| 항목 | RoboVLMs (Full FT) | Mobile VLA (LoRA) |
|------|-------------------|-------------------|
| **Fine-tuning 방법** | Full Fine-tuning | LoRA |
| **freeze_backbone** | false | true |
| **lora_enable** | false | true |
| **lora_r** | 64 | 32 |
| **lora_alpha** | 16 | 16 |
| **lora_dropout** | 0.05 | 0.1 |
| **train_vision** | true | false |
| **train_text_embedding** | true | false |
| **learning_rate** | 2e-5 | 1e-4 |
| **weight_decay** | 0 | 0.01 |
| **batch_size** | 4 | 2 |
| **max_epochs** | 5 | 50 |
| **action_dim** | 7 (6-DOF + gripper) | 2 (linear_x, linear_y) |
| **hidden_size** | 1024 | 512 |
| **window_size** | 8 | 8 |
| **action_chunk_size** | 10 | 10 |

### LoRA 적용 이유

1. **메모리 효율**: Jetson 16GB 메모리 제약
2. **학습 시간 단축**: 파라미터 1% 미만만 학습
3. **적은 데이터**: 13개 에피소드로 Full FT는 과적합 위험
4. **배포 효율**: LoRA 어댑터만 저장 (수 MB)

---

## 🚀 실행 방법

### 1. 데이터셋 테스트

```bash
cd /home/billy/25-1kp/vla
python3 Mobile_VLA/scripts/test_dataset_20251106.py
```

**예상 출력:**
```
🧪 20251106 에피소드 데이터셋 테스트 시작
📊 Validation 데이터셋: 2개 에피소드
📊 Training 데이터셋: 11개 에피소드
✅ 총 XXX개 샘플 생성
✅ 배치 로드 성공:
  - images shape: torch.Size([2, 8, 3, 224, 224])
  - actions shape: torch.Size([2, 10, 2])
  - language: go to the red box
✅ 데이터셋 테스트 성공!
```

### 2. LoRA Fine-tuning 실행

```bash
cd /home/billy/25-1kp/vla
bash Mobile_VLA/scripts/run_lora_finetune_20251106.sh
```

**실행 과정:**
1. CUDA 확인
2. 데이터셋 확인
3. 모델 로드 (Kosmos-2)
4. LoRA 적용
5. 학습 시작 (50 에포크)
6. 체크포인트 저장

### 3. 학습 모니터링

```bash
# TensorBoard 실행
tensorboard --logdir=Mobile_VLA/runs/mobile_vla_lora/logs

# 학습 결과 확인
cat Mobile_VLA/runs/mobile_vla_lora/logs/training_results.json
```

---

## 📈 예상 학습 시간

### Jetson AGX Orin (16GB)

- **에포크당 시간**: ~5-10분 (예상)
- **총 학습 시간**: 50 에포크 × 5분 = ~4시간 (예상)
- **체크포인트 크기**: ~50MB (LoRA 어댑터만)

### 학습 시간 측정 방법

```bash
# 1 에포크만 실행하여 시간 측정
python3 Mobile_VLA/src/training/finetune_lora_20251106.py \
    --config Mobile_VLA/configs/finetune_mobile_vla_lora_20251106.json \
    --device cuda

# training_results.json에서 avg_epoch_time 확인
```

---

## 📁 출력 파일

### 체크포인트
```
Mobile_VLA/runs/mobile_vla_lora/checkpoints/
├── best_model.pth              # 최고 성능 모델
├── checkpoint_epoch_10.pth     # 10 에포크 체크포인트
├── checkpoint_epoch_20.pth     # 20 에포크 체크포인트
├── checkpoint_epoch_30.pth     # 30 에포크 체크포인트
├── checkpoint_epoch_40.pth     # 40 에포크 체크포인트
└── checkpoint_epoch_50.pth     # 50 에포크 체크포인트
```

### 로그
```
Mobile_VLA/runs/mobile_vla_lora/logs/
├── training_results.json       # 학습 결과 요약
├── events.out.tfevents.*       # TensorBoard 로그
└── metrics.csv                 # CSV 로그
```

---

## 🔍 학습 결과 분석

### training_results.json 구조
```json
{
  "config": {...},
  "train_losses": [0.5, 0.4, 0.3, ...],
  "val_losses": [0.6, 0.5, 0.4, ...],
  "learning_rates": [1e-4, 9e-5, ...],
  "epoch_times": [300, 310, 295, ...],
  "avg_epoch_time": 302.5,
  "total_epochs": 50,
  "best_val_loss": 0.25,
  "timestamp": "2025-11-06T15:30:00"
}
```

### 성능 지표

- **Train Loss**: 학습 손실 (낮을수록 좋음)
- **Val Loss**: 검증 손실 (낮을수록 좋음)
- **Learning Rate**: 학습률 변화 (Cosine Annealing)
- **Epoch Time**: 에포크당 소요 시간

---

## 🐛 문제 해결

### 1. CUDA Out of Memory

**증상:**
```
RuntimeError: CUDA out of memory
```

**해결:**
```json
// finetune_mobile_vla_lora_20251106.json 수정
{
  "batch_size": 1,              // 2 → 1
  "accumulate_grad_batches": 8  // 4 → 8
}
```

### 2. 데이터셋 로드 실패

**증상:**
```
ValueError: No episodes found matching pattern
```

**해결:**
```bash
# 에피소드 파일 확인
ls -lh /home/billy/25-1kp/vla/ROS_action/mobile_vla_dataset/episode_20251106_*.h5

# 경로 확인
pwd
```

### 3. 모델 로드 실패

**증상:**
```
OSError: Can't load tokenizer for 'microsoft/kosmos-2-patch14-224'
```

**해결:**
```bash
# Hugging Face 토큰 설정
export HUGGING_FACE_HUB_TOKEN="your_token_here"

# 또는 로그인
huggingface-cli login
```

---

## 📚 참고 자료

### RoboVLMs 원본 Config
- `RoboVLMs_upstream/configs/calvin_finetune/finetune_kosmos_cont-lstm-post_full-ft_text_vision_wd-0_ws-8_act-10.json`

### Mobile VLA 구현
- `Mobile_VLA/src/model/mobile_vla_model.py` - 모델 구조
- `Mobile_VLA/src/data/mobile_vla_h5_dataset.py` - 데이터셋
- `Mobile_VLA/src/training/finetune_lora_20251106.py` - 학습 스크립트

### GitHub
- [RoboVLMs](https://github.com/Robot-VLAs/RoboVLMs)
- [PEFT (LoRA)](https://github.com/huggingface/peft)

---

## ✅ 체크리스트

- [ ] 데이터셋 테스트 완료
- [ ] CUDA 사용 가능 확인
- [ ] LoRA Fine-tuning 실행
- [ ] 학습 시간 측정 (1 에포크)
- [ ] 전체 학습 완료 (50 에포크)
- [ ] 최고 모델 체크포인트 확인
- [ ] 학습 결과 분석
- [ ] 추론 테스트

---

## 🎯 다음 단계

1. **LoRA 시간 측정**: 1 에포크 실행하여 시간 측정
2. **전체 학습**: 50 에포크 학습 완료
3. **추론 테스트**: 학습된 모델로 추론 테스트
4. **성능 평가**: MAE, MSE 등 메트릭 계산
5. **배포**: Jetson에서 실시간 추론 테스트

---

**작성일**: 2025-11-06  
**작성자**: Mobile VLA Team  
**참조**: RoboVLMs GitHub

