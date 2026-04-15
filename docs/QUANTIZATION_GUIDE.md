# INT8/INT4 양자화 가이드

Jetson 16GB 메모리 최적화를 위한 Mobile VLA 모델 양자화 가이드

---

## 1. 양자화 개요

### 목표
- **Vision Encoder**: FP16 → INT8 (메모리 0.6GB → 0.3GB)
- **LLM**: FP16 → INT4 (메모리 3.2GB → 0.8GB)
- **총 메모리 감소**: ~7.4GB → ~4GB

### 방법론
1. **Vision Encoder INT8**: PyTorch Post-Training Quantization (PTQ)
2. **LLM INT4**: BitsAndBytes NF4 quantization with double quantization

---

## 2. 사전 준비

### 필요 패키지 설치

```bash
# BitsAndBytes (INT4 양자화)
pip install bitsandbytes transformers

# PyTorch Quantization (기본 포함)
# tqdm, h5py (이미 설치됨)
```

### 체크포인트 확인

```bash
cd /home/billy/25-1kp/vla

# 사용 가능한 체크포인트 확인
ls -lh runs/mobile_vla_no_chunk_20251209/kosmos/mobile_vla_finetune/2025-12-17/mobile_vla_chunk5_20251217/

# 최적 모델: Chunk5 Epoch 6 (Val Loss 0.067)
# epoch_epoch=05-val_loss=val_loss=0.067.ckpt
```

---

## 3. 양자화 실행

### 방법 1: 자동 스크립트 (권장)

```bash
cd /home/billy/25-1kp/vla

# 전체 양자화 프로세스 실행 (Vision INT8 + LLM INT4 + Validation)
bash scripts/run_quantization.sh
```

**실행 단계**:
1. Vision Encoder INT8 양자화
2. LLM INT4 양자화
3. 정확도 및 메모리 검증

**예상 소요 시간**: 약 10~15분

---

### 방법 2: 수동 실행

#### Step 1: Vision Encoder만 INT8

```bash
python scripts/quantize_for_jetson.py \
    --checkpoint runs/.../chunk5_epoch6.ckpt \
    --config Mobile_VLA/configs/mobile_vla_chunk5_20251217.json \
    --data-dir /home/billy/25-1kp/vla/ROS_action/mobile_vla_dataset \
    --vision-int8 \
    --calib-size 100 \
    --output quantized_models/vision_int8_only
```

#### Step 2: Full Quantization (Vision INT8 + LLM INT4)

```bash
python scripts/quantize_for_jetson.py \
    --checkpoint runs/.../chunk5_epoch6.ckpt \
    --config Mobile_VLA/configs/mobile_vla_chunk5_20251217.json \
    --data-dir /home/billy/25-1kp/vla/ROS_action/mobile_vla_dataset \
    --vision-int8 \
    --llm-int4 \
    --calib-size 100 \
    --output quantized_models/full_quant
```

#### Step 3: 검증

```bash
python scripts/validate_quantized_model.py \
    --original runs/.../chunk5_epoch6.ckpt \
    --quantized quantized_models/full_quant/model_quantized.ckpt \
    --config Mobile_VLA/configs/mobile_vla_chunk5_20251217.json \
    --val-data /home/billy/25-1kp/vla/ROS_action/mobile_vla_dataset \
    --num-samples 100 \
    --output validation_results.json
```

---

## 4. 검증 기준

양자화 모델이 다음 기준을 만족해야 합니다:

| 메트릭 | 기준 | 설명 |
|--------|------|------|
| **Direction Accuracy** | ≥ 95% | 원본 모델 100% 대비 5% 이내 하락 |
| **Latency** | ≤ 500ms | 원본 ~385ms 대비 허용 범위 |
| **Memory** | < 6GB | Jetson 16GB에서 여유 확보 |

### 검증 결과 확인

```bash
# Validation 결과
cat quantized_models/full_quant/validation_results.json

# 예상 출력:
{
  "validation_results": {
    "direction_accuracy": {
      "original": 1.0,
      "quantized": 0.98,
      "drop": 0.02
    },
    "latency_ms": {
      "original": 385.2,
      "quantized": 350.5,
      "speedup": 1.10
    }
  },
  "memory_results": {
    "original_gb": 7.4,
    "quantized_gb": 4.2,
    "reduction_gb": 3.2,
    "reduction_percent": 43.2
  },
  "pass_criteria": {
    "direction_accuracy": true,
    "latency": true,
    "memory": true
  }
}
```

✅ **모든 pass_criteria가 true이면 성공**

---

## 5. Billy 서버에서 테스트

### FP16 모델 (기본)

```bash
export VLA_API_KEY="your-api-key"
export VLA_CHECKPOINT_PATH="runs/.../chunk5_epoch6.ckpt"
export VLA_CONFIG_PATH="Mobile_VLA/configs/mobile_vla_chunk5_20251217.json"

python Mobile_VLA/inference_server.py
```

### INT8/INT4 모델 (양자화)

```bash
export VLA_API_KEY="your-api-key"
export VLA_USE_QUANTIZATION=true
export VLA_QUANTIZED_CHECKPOINT="quantized_models/full_quant/model_quantized.ckpt"
export VLA_QUANTIZED_CONFIG="quantized_models/full_quant/config.json"

python Mobile_VLA/inference_server.py
```

### Health Check

```bash
curl http://localhost:8000/health

# 예상 출력:
{
  "status": "healthy",
  "model_loaded": true,
  "device": "cuda",
  "gpu_memory": {
    "allocated_gb": 4.2,
    "peak_allocated_gb": 4.5,
    "total_memory_gb": 24.0
  },
  "quantization": {
    "enabled": true,
    "precision": "INT8/INT4"
  }
}
```

---

## 6. Jetson 배포

### 모델 전송

```bash
# Billy 서버에서 실행
rsync -avz --progress \
    quantized_models/full_quant/ \
    jetson@<JETSON_IP>:/home/jetson/vla/quantized_models/full_quant/
```

### Jetson에서 실행

```bash
# Jetson Orin에서 실행
ssh jetson@<JETSON_IP>

cd /home/jetson/vla

# 환경 변수 설정
export VLA_API_KEY="your-api-key"
export VLA_USE_QUANTIZATION=true
export VLA_QUANTIZED_CHECKPOINT="/home/jetson/vla/quantized_models/full_quant/model_quantized.ckpt"
export VLA_QUANTIZED_CONFIG="/home/jetson/vla/quantized_models/full_quant/config.json"

# 추론 서버 시작
python Mobile_VLA/inference_server.py
```

### 메모리 모니터링

```bash
# Jetson에서 실행
watch -n 1 "free -h && echo '' && nvidia-smi"

# GPU 메모리 < 8GB 확인 (총 16GB 중)
```

---

## 7. 트러블슈팅

### 문제 1: BitsAndBytes 설치 실패

```bash
# CUDA 버전 확인
nvcc --version

# PyTorch CUDA 버전과 일치하는 BitsAndBytes 설치
pip install bitsandbytes --extra-index-url https://wheels.bitsandbytes.co.uk/
```

### 문제 2: Calibration 데이터 부족

```bash
# 데이터셋 확인
ls -lh ROS_action/mobile_vla_dataset/*.h5 | wc -l

# 최소 10개 에피소드 필요 (각 10 샘플 = 100개 샘플)
```

### 문제 3: Quantized 모델 로드 실패

```bash
# Checkpoint 파일 확인
file quantized_models/full_quant/model_quantized.ckpt

# Config 확인
cat quantized_models/full_quant/config.json | grep quantization
```

---

## 8. 성능 비교

| 구성 | 메모리 (GB) | Latency (ms) | Accuracy (%) |
|------|------------|--------------|--------------|
| **FP32** | ~12 | ~450 | 100 |
| **FP16 (현재)** | ~7.4 | ~385 | 100 |
| **INT8/INT4 (목표)** | ~4.0 | ~350 | ≥95 |

**목표 달성**:
- ✅ 메모리 ~50% 감소 (7.4GB → 4GB)
- ✅ Latency 유지 또는 향상
- ✅ Accuracy 95% 이상 유지

---

## 9. 추가 최적화 (선택)

### TensorRT 변환 (추가 최적화)

```bash
# TensorRT로 추가 최적화 (Jetson에서 실행)
# Note: 복잡도가 높으므로 양자화만으로 충분하면 생략 가능

python scripts/convert_to_tensorrt.py \
    --quantized quantized_models/full_quant/model_quantized.ckpt \
    --output tensorrt_models/chunk5_trt
```

**예상 개선**:
- Latency: 350ms → 250ms
- 메모리: 큰 변화 없음

---

## 10. 체크리스트

양자화 완료 전 확인 사항:

- [ ] BitsAndBytes 설치 확인
- [ ] Calibration 데이터 준비 (100+ 샘플)
- [ ] 양자화 실행 (run_quantization.sh)
- [ ] Validation 결과 확인 (Accuracy ≥95%)
- [ ] Billy 서버에서 테스트
- [ ] Jetson으로 모델 전송
- [ ] Jetson에서 메모리 측정 (< 8GB)
- [ ] 실제 로봇 주행 테스트

---

## 문의

문제 발생 시:
1. `quantized_models/full_quant/model_info.json` 확인
2. `validation_results.json` 확인
3. Inference server 로그 확인

