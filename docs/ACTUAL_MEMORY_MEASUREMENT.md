# 실제 메모리 측정 결과 - 환각 없는 사실

**작성일**: 2025-12-23  
**측정 방법**: GPU Memory Profiling  
**대상**: left_chunk10 (Best 모델)

---

## 📊 실제 측정 결과

### Raw Data (JSON):
```json
{
  "fp32": {
    "before": { "allocated_gb": 0.0 },
    "after": { "allocated_gb": 13.54 },
    "memory_used_gb": 13.54
  },
  "quantized": {
    "before": { "allocated_gb": 13.54 },  // FP32가 아직 메모리에
    "after": { "allocated_gb": 5.80 },    // FP32 unload + Quantized load
    "memory_used_gb": -7.74  // 잘못된 계산
  }
}
```

---

## ✅ 올바른 해석

### 실제 메모리 사용량:

| Model | GPU Memory | 비고 |
|-------|-----------|------|
| **FP32** | **13.54 GB** | Clean state에서 로딩 |
| **Quantized** | **5.80 GB** | FP32 unload 후 측정값 |

### 실제 절감:

```
절감량 = 13.54 GB - 5.80 GB = 7.74 GB
절감률 = (7.74 / 13.54) × 100 = 57.2%
```

---

## 🔍 예상치(1.15GB)와 차이 분석

### 예상 (model_info.json):
```json
{
  "estimated_memory_gb": {
    "vision": 0.30,
    "llm": 0.80,
    "action_head": 0.05,
    "total": 1.15
  }
}
```

### 실제 (측정값):
- **5.80 GB**

### 차이 이유:

1. **INT8 Dynamic Quantization의 한계**
   - INT8은 Linear layer만 적용
   - Embedding, Activation 등은 FP32 유지
   - 전체 모델의 일부만 quantize됨

2. **PyTorch 메모리 오버헤드**
   - Model weights: ~5.4 GB (파일 크기)
   - Optimizer states: 없음 (inference only)
   - Activation memory: ~0.4 GB (추정)

3. **예상치는 Linear layer만 계산**
   - Vision encoder Linear: 0.30 GB
   - LLM Linear: 0.80 GB
   - 하지만 전체 모델은 더 큼

---

## 📊 정확한 수치 정리

### FP32 Model:
- **파일 크기**: 6.4 GB (.ckpt)
- **GPU 메모리**: **13.54 GB** ✅ (실측)
- **Parameters**: 1,677,224,724 (1.68B)
- **FP32 이론값**: 6.71 GB (params × 4 bytes)
- **오버헤드**: 6.83 GB (2x)

### Quantized Model:
- **파일 크기**: 5.4 GB (.pt)
- **GPU 메모리**: **5.80 GB** ✅ (실측)
- **Quantization**: INT8 (Linear only)
- **절감**: 57.2%

---

## 💡 왜 파일(5.4GB)과 메모리(5.8GB)가 비슷한가?

**이유**: Dynamic quantization은 저장 시 FP32 유지

1. **파일에 저장**: FP32 weights (5.4GB)
2. **로딩 시**: FP32로 메모리에 올림 (~5.4GB)
3. **추론 시**: Linear layer를 INT8로 변환 (일시적)
4. **실제로는**: FP32와 INT8 혼재

➡️ **결론**: 메모리 절감이 거의 없음!

---

## 🚨 중요한 발견

### Dynamic Quantization의 실체:

**기대**:
- Vision: 0.30 GB
- LLM: 0.80 GB
- Total: 1.15 GB

**실제**:
- **Total: 5.80 GB**

**차이**: 5.04배 더 큼!

### 이유:

1. **INT8은 계산 시에만 적용**
   - Weights는 FP32로 유지
   - Forward pass 때만 INT8로 변환
   - 속도는 빨라지지만 메모리 절감 미미

2. **BitsAndBytes INT4도 미적용**
   - 코드에서 "requires model reload"
   - 실제로는 적용 안된 상태

3. **Static Quantization 필요**
   - QAT (Quantization-Aware Training)
   - 또는 Static PTQ with calibration

---

## ✅ 결론

### 사실:
1. **Quantized 모델 메모리: 5.80 GB** (실측)
2. **FP32 모델 메모리: 13.54 GB** (실측)
3. **실제 절감: 7.74 GB (57%)**

### 오해:
1. ~~"1.15 GB로 줄어든다"~~ → 실제로는 5.80 GB
2. ~~"INT4 적용됨"~~ → 실제로는 미적용
3. ~~"Dynamic quantization으로 충분"~~ → 메모리 절감 미미

### 권장:
1. **Jetson 배포 시**: Static quantization (TensorRT) 사용
2. **현재 quantized 모델**: 속도 향상에는 도움, 메모리는 미미
3. **실제 절감 필요 시**: QAT 또는 TensorRT 재고려

---

## 📋 다음 단계

### Option A: TensorRT 변환 ⭐
- Static INT8 quantization
- 실제 메모리 < 2GB 예상
- Jetson 최적화

### Option B: 현재 모델 사용
- 5.8GB 메모리 (Jetson 16GB에서 여유)
- 속도 향상 있음
- 메모리 절감은 적음

### Option C: QAT 재학습
- From scratch
- 시간 소요 大

**권장**: Option B (현재 모델로 충분, Jetson 16GB OK)

---

**최종 결론**: 
- Quantized 모델은 5.8GB 메모리 사용
- 1.15GB 예상은 Linear layer만 계산한 이론값
- Jetson 16GB에서 충분히 실행 가능
