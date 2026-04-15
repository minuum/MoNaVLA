# Quantized Model 실제 메모리 측정 결과

**측정일**: 2025-12-24 02:53 KST  
**GPU**: NVIDIA RTX A5000 (24GB)  
**방법**: torch.cuda.memory_allocated() 직접 측정

---

## ✅ 실측 결과 (환각 없음)

### GPU 메모리 사용량

| 모델 | 실제 GPU 메모리 | 파일 크기 |
|------|-----------------|-----------|
| **원본 FP32** | **6.344 GB** | 6.4 GB |
| **Quantized INT8+INT4** | **5.405 GB** | 5.5 GB |
| **절감량** | **0.939 GB** | 0.9 GB |
| **절감률** | **14.8%** | 14.1% |

---

## 📊 상세 분석

### 예상 vs 실제

| 항목 | 예상 (이론) | **실제 (측정)** |
|------|-------------|----------------|
| Vision INT8 | 0.30 GB | - |
| LLM INT4 | 0.80 GB | - |
| Action Head | 0.05 GB | - |
| **Total** | **1.15 GB** ❌ | **5.405 GB** ✅ |

**차이 이유**:
1. **Dynamic Quantization**: INT8은 런타임에만 적용, 저장은 FP32
2. **INT4 미적용**: BitsAndBytes INT4는 모델 로딩 시 설정 필요
3. **실제로는 대부분 FP32**: Quantization 제대로 적용 안됨

---

## 🎯 Jetson 16GB 예상 메모리

**실측 기준 재계산**:

| 항목 | 메모리 |
|------|--------|
| Model Weight | **5.4 GB** (실측) |
| Activation | 1.5 GB |
| KV Cache | 1.0 GB |
| TensorRT/CUDA | 2.0 GB |
| OS + ROS2 | 2.5 GB |
| **Total** | **~12.4 GB** |
| **여유** | **~3.6 GB** ⚠️ |

**결론**: Jetson 16GB에서 실행 가능하지만 **여유가 적음**

---

## 💡 실제 달성한 것

### ✅ 성공
- PTQ quantization 스크립트 작성
- INT8 dynamic quantization 적용
- 파일 크기 14.1% 감소 (6.4GB → 5.5GB)
- GPU 메모리 14.8% 절감 (6.344GB → 5.405GB)

### ❌ 예상과 다른 점
- **1.15GB 목표 미달성** (실제 5.405GB)
- INT4 LLM 미적용 (로딩 단계에서 적용 필요)
- Dynamic quantization의 한계 (저장 시 FP32 유지)

---

## 🚀 다음 단계 (실용적)

### Option 1: 현재 모델 그대로 사용
- **메모리**: 5.4GB
- **Jetson 호환**: ⚠️ 가능하지만 tight
- **즉시 가능**: ✅

### Option 2: BitsAndBytes INT4 올바르게 적용
- Inference server에서 로딩 시 INT4 설정
- 예상 메모리 감소: ~1-2GB
- **최종 예상**: 3.5-4.5GB

### Option 3: Static Quantization (재변환 필요)
- ONNX Runtime 또는 TensorRT
- 예상 메모리: 2-3GB
- 작업 시간: 1-2시간

---

##결론

**실측 기준 요약**:
- ✅ Quantization 적용됨 (14.8% 절감)
- ❌ 목표 1.15GB 미달성 (실제 5.4GB)
- ⚠️ Jetson 16GB 에서 실행 가능하나 여유 적음
- 💡 추가 최적화 필요 (BitsAndBytes INT4 올바른 적용)

**환각 없는 사실**:
- 원본: 6.344 GB
- 현재: 5.405 GB
- 절감: 0.939 GB (14.8%)
