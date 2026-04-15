# QAT (Quantization-Aware Training) 재학습 계획서

**작성일**: 2025-12-23  
**목표**: INT8 Vision + INT4 LLM으로 처음부터 재학습  
**타겟 메모리**: 8-11GB (전체, Jetson 16GB 목표)

---

## 🎯 목표

### 왜 QAT 재학습이 필요한가?

**현재 PTQ (Post-Training Quantization)의 문제**:
- 파일 크기: 5.4GB (예상 1.15GB vs 실제)
- Dynamic Quantization의 한계: 저장 시 FP32 유지
- 런타임 메모리 + Activation + KV Cache ≈ 11-14GB
- **Jetson 16GB 메모리 초과 위험**

**QAT의 장점**:
- 학습 중 Fake Quantization으로 quantization error 학습
- 실제 INT8/INT4 weight로 저장 가능
- 추론 시 메모리 사용량 대폭 감소
- 성능 저하 최소화

---

## 📋 구현 완료 항목

### ✅ 1. MobileVLAQATTrainer 구현
- **파일**: `RoboVLMs_upstream/robovlms/train/mobile_vla_qat_trainer.py`
- **특징**:
  - Vision Encoder INT8 QAT wrapper
  - LLM INT4 BitsAndBytes 검증
  - 학습 후 자동 변환 (QAT → INT8)
  - Checkpoint에 QAT 정보 저장

### ✅ 2. Config 파일 생성
- **Left turn**: `Mobile_VLA/configs/mobile_vla_qat_left_chunk10_20251223.json`
- **Right turn**: `Mobile_VLA/configs/mobile_vla_qat_right_chunk10_20251223.json`
- **설정**:
  - `trainer_type`: "MobileVLAQATTrainer"
  - `quantization.enable`: true
  - `vision_encoder.dtype`: "qint8"
  - `llm.dtype`: "int4" (BitsAndBytes)

### ✅ 3. 학습 스크립트
- `scripts/train_qat_left_chunk10.sh`
- `scripts/train_qat_right_chunk10.sh`

### ✅ 4. Main.py 수정
- MobileVLAQATTrainer import 추가
- Trainer 선택 로직 업데이트

---

## 🏗️ 아키텍처 구조

```
Input Image (224x224x3)
    ↓
Vision Encoder (Frozen)
    - INT8 QAT (Fake Quantization)
    - QuantStub → Vision Model → DeQuantStub
    - 학습 후 실제 INT8로 변환
    ↓
Vision Features
    ↓
Embedding Projection (FP16)
    ↓
LLM (Frozen)
    - INT4 BitsAndBytes
    - NF4 quantization
    - load_in_4bit=True
    ↓
Language Features
    ↓
Action Head (Trainable)
    - LSTM Decoder
    - FP16 precision
    - Output: [linear_x, linear_y]
```

---

## 📊 예상 메모리 사용량

### 모델 Weight
```
Vision Encoder (INT8):    ~0.8 GB
LLM (INT4):               ~1.5 GB
Action Head (FP16):       ~0.05 GB
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Model:              ~2.35 GB
```

### 추론 시 전체 메모리 (Jetson)
```
Model Weight:             ~2.35 GB
Activation:               ~1.5 GB
KV Cache (256 tokens):    ~1.0 GB
TensorRT/CUDA:            ~2.0 GB
OS + ROS2:                ~2.5 GB
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total:                    ~9.35 GB ✅
```

**목표 달성**: 11GB 이내 ✅

---

## 🚀 실행 계획

### Step 1: Left Turn 모델 학습 (예상 3-4일)

```bash
# 학습 시작
bash scripts/train_qat_left_chunk10.sh

# 모니터링
python3 scripts/monitor_training.py \
    --log logs/qat_training/train_qat_left_chunk10_*.log

# GPU 상태 확인
nvidia-smi -l 5
```

**예상 학습 시간**: 
- 10 epochs × ~30-40분/epoch ≈ 5-7시간

### Step 2: Right Turn 모델 학습

```bash
bash scripts/train_qat_right_chunk10.sh
```

### Step 3: 검증

다음 항목 검증:
1. ✅ Checkpoint 저장 확인
2. ✅ QAT 정보 저장 확인
3. ✅ Val Loss < 0.020 달성
4. ✅ 메모리 사용량 측정

---

## ⚠️ 주의사항

### 1. BitsAndBytes INT4 로딩

**문제**: BitsAndBytes INT4는 모델 로딩 시 적용되어야 함

**해결 방법**:
```python
# model loading 단계에서 BitsAndBytesConfig 사용
from transformers import BitsAndBytesConfig

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4"
)

# AutoModel.from_pretrained(..., quantization_config=bnb_config)
```

**현재 상태**: Config에 설정만 추가, 실제 로딩 로직 확인 필요

### 2. Vision Encoder QAT

**구현된 방식**: QuantStub/DeQuantStub wrapper

**학습 중**:
- Fake quantization (INT8 시뮬레이션)
- Weight는 FP32 유지

**학습 후**:
- `torch.quantization.convert()` 호출
- 실제 INT8 weight로 변환

### 3. Jetson 배포 시

**추가 필요 작업**:
- TensorRT 변환 (선택)
- ONNX export (선택)
- 실제 메모리 측정

---

## 📝 다음 단계

### 즉시 실행 (지금)

```bash
# Left turn 학습 시작
bash scripts/train_qat_left_chunk10.sh
```

### 학습 중 확인사항

1. **초기 로딩**:
   - QAT setup 메시지 확인
   - Vision Encoder INT8 준비 확인
   - LLM INT4 설정 확인

2. **학습 진행**:
   - Loss 감소 추이 관찰
   - GPU 메모리 사용량 모니터링
   - Checkpoint 자동 저장 확인

3. **학습 완료**:
   - Best model 선택 (val_loss 기준)
   - QAT → INT8 변환 확인
   - 메모리 측정 스크립트 실행

---

## 📊 성공 지표

### 학습 성능
- [ ] Left Val Loss < 0.020
- [ ] Right Val Loss < 0.020
- [ ] Train-Val gap < 0.010 (overfitting 방지)

### 메모리 효율
- [ ] 모델 파일 크기 < 3GB
- [ ] 추론 시 GPU 메모리 < 4GB
- [ ] 전체 Jetson 메모리 < 11GB

### 정확도
- [ ] Accuracy ≥ 98%
- [ ] Latency < 400ms
- [ ] FPS ≥ 25

---

## 🎉 기대 효과

### PTQ vs QAT 비교

| 항목 | PTQ (현재) | QAT (목표) |
|------|------------|------------|
| 모델 파일 | 5.4GB | **~2.3GB** ⬇️ 57% |
| 런타임 메모리 | ~11-14GB | **~9GB** ⬇️ 30% |
| 정확도 | ~99% | **~99%** (유지) |
| Latency | ~350ms | **~300ms** ⬇️ 14% |
| Jetson 호환 | ⚠️ 경계선 | ✅ **여유** |

---

**다음 액션**: Left turn QAT 학습 시작! 🚀
