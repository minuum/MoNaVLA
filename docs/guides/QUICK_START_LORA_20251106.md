# 🚀 Mobile VLA LoRA Fine-tuning Quick Start (20251106)

## 📋 요약

- **목표**: 20251106 에피소드를 Kosmos VLM에 LoRA로 파인튜닝
- **데이터**: 13개 HDF5 에피소드
- **방법**: LoRA (r=32, alpha=16)
- **예상 시간**: 1 에포크 ~5-10분

---

## ✅ 1단계: 데이터셋 테스트

```bash
cd /home/billy/25-1kp/vla
python3 Mobile_VLA/scripts/test_dataset_20251106.py
```

**예상 출력:**
```
🧪 20251106 에피소드 데이터셋 테스트 시작
📊 Training 데이터셋: 11개 에피소드
📊 Validation 데이터셋: 2개 에피소드
✅ 총 XXX개 샘플 생성
✅ 배치 로드 성공
```

---

## ⏱️ 2단계: LoRA 시간 측정 (1 에포크)

### Config 수정
```bash
vim Mobile_VLA/configs/finetune_mobile_vla_lora_20251106.json
```

**변경:**
```json
{
  "trainer": {
    "max_epochs": 1  // 50 → 1
  }
}
```

### 실행
```bash
bash Mobile_VLA/scripts/run_lora_finetune_20251106.sh
```

### 결과 확인
```bash
cat Mobile_VLA/runs/mobile_vla_lora/logs/training_results.json | grep avg_epoch_time
```

**예상 출력:**
```json
"avg_epoch_time": 300.5  // 약 5분
```

---

## 🎯 3단계: 전체 학습 (50 에포크)

### Config 복원
```bash
vim Mobile_VLA/configs/finetune_mobile_vla_lora_20251106.json
```

**변경:**
```json
{
  "trainer": {
    "max_epochs": 50  // 1 → 50
  }
}
```

### 실행
```bash
bash Mobile_VLA/scripts/run_lora_finetune_20251106.sh
```

**예상 소요 시간:**
- 1 에포크 5분 × 50 = **약 4시간**

---

## 📊 학습 모니터링

### TensorBoard
```bash
tensorboard --logdir=Mobile_VLA/runs/mobile_vla_lora/logs
# 브라우저에서 http://localhost:6006 접속
```

### 실시간 로그
```bash
tail -f Mobile_VLA/runs/mobile_vla_lora/logs/training_results.json
```

---

## 📁 결과 확인

### 체크포인트
```bash
ls -lh Mobile_VLA/runs/mobile_vla_lora/checkpoints/
```

**예상 출력:**
```
best_model.pth              # 최고 성능 모델 (~50MB)
checkpoint_epoch_10.pth
checkpoint_epoch_20.pth
...
```

### 학습 결과
```bash
cat Mobile_VLA/runs/mobile_vla_lora/logs/training_results.json
```

**주요 지표:**
- `avg_epoch_time`: 에포크당 평균 시간
- `best_val_loss`: 최고 검증 손실
- `total_epochs`: 총 에포크 수

---

## 🐛 문제 해결

### CUDA Out of Memory
```json
// Config 수정
{
  "batch_size": 1,              // 2 → 1
  "accumulate_grad_batches": 8  // 4 → 8
}
```

### 데이터셋 없음
```bash
ls -lh /home/billy/25-1kp/vla/ROS_action/mobile_vla_dataset/episode_20251106_*.h5
```

---

## 📚 상세 가이드

- **전체 가이드**: `Mobile_VLA/README_LORA_FINETUNING.md`
- **구현 요약**: `Mobile_VLA/LORA_FINETUNING_SUMMARY.md`

---

## 🎯 다음 단계

1. ✅ 데이터셋 테스트
2. ✅ LoRA 시간 측정 (1 에포크)
3. ⏳ 전체 학습 (50 에포크)
4. ⏳ 추론 테스트
5. ⏳ 100 Dataset 수집

---

**작성일**: 2025-11-06  
**실행 환경**: Jetson AGX Orin 16GB  
**참조**: [RoboVLMs GitHub](https://github.com/Robot-VLAs/RoboVLMs)

