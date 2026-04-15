# INT8 Inference 테스트 결과

**일시**: 2025-12-24 04:14 KST  
**모델**: Chunk5 Best (Val Loss 0.067)

---

## ✅ 테스트 성공

### 결과 요약

| 항목 | 값 |
|------|------|
| **Status** | ✅ Working |
| **Latency** | 15.5초 (CPU inference) |
| **GPU Memory** | 6.265 GB |
| **Output** | ✅ Valid action tensor |

---

## 📊 상세 결과

### 1. 모델 로딩
```
✅ Config loaded
✅ State dict loaded (1863 parameters)
✅ Quantized parameters: 477/1863 (25.6%)
```

### 2. Dequantization
```python
# INT8 → FP32 변환
dequantized_state = {}
for key, value in state_dict.items():
    if value.is_quantized:
        dequantized_state[key] = value.dequantize()
```

**Why?**  
- PyTorch quantized tensor는 일반 모델에 직접 로드 불가
- Inference 시 dequantize 필요
- 파일은 INT8로 저장 (1.8GB), 메모리는 FP32로 로드

### 3. Inference
```
Input: (1, 8, 3, 224, 224) vision + (1, 256) language
Output: (1, 8, 5, 2) action
```

**Latency**: 15.5초 (CPU mode)
**Action Values**: `[4.78e-04, -4.90e-03, -9.13e-03, ...]`

---

## 🔍 메모리 분석

### 파일 vs 메모리

| 단계 | INT8 파일 | 메모리 (로딩 후) |
|------|-----------|------------------|
| **저장** | 1.8 GB | - |
| **로딩 (Dequantize)** | - | 6.3 GB (FP32) |

### 왜 메모리가 6.3GB?

**Dequantization 때문**:
```
INT8 weights (1.8GB 파일) 
    ↓ dequantize()
FP32 weights (6.3GB 메모리)
```

### Jetson에서는?

**Option 1: Dequantize (현재)**
- 파일: 1.8 GB
- 메모리: 6.3 GB
- Latency: 15.5초 (CPU)

**Option 2: Native INT8 Inference** (TensorRT)
- 파일: 1.8 GB
- 메모리: ~2-3 GB
- Latency: ~1-2초
- **권장** ✅

---

## 💡 핵심 인사이트

### Static INT8의 의미

1. **Storage**: INT8로 저장 (1.8GB)
2. **Runtime**: FP32로 변환하여 실행 (6.3GB)
3. **진짜 INT8 inference**: TensorRT 필요

### 실용적 해법

| 방법 | 파일 | 메모리 | Latency | 구현 |
|------|------|--------|---------|------|
| **FP32 원본** | 6.4GB | 6.3GB | ~15s | ✅ 현재 |
| **Static INT8 + Dequant** | 1.8GB | 6.3GB | ~15s | ✅ 현재 |
| **TensorRT INT8** | 1.8GB | ~2GB | ~2s | 🎯 **Next** |

---

## 🎯 결론

### ✅ 성공
1. **INT8 모델 inference 작동**
2. **Output 정상**
3. **파일 크기 72% 감소** (6.4GB → 1.8GB)

### ⚠️ 주의
1. **메모리 절감 없음** (dequantize 때문에)
2. **속도 개선 없음** (FP32로 실행)

### 🚀 Next Step: TensorRT
```bash
# Jetson에서
trtexec --onnx=model.onnx \
        --int8 \
        --saveEngine=model_int8.trt

# 실제 INT8 inference
# Memory: ~2GB
# Latency: ~2s
```

---

## 📋 최종 요약

**양자화 표**:

| # | 방법 | 파일 | 메모리 | Latency | 상태 |
|---|------|------|--------|---------|------|
| 1 | **FP32** | 6.4GB | 6.3GB | 15s | ✅ |
| 2 | **PTQ Dynamic** | 5.5GB | 5.4GB | ~15s | ✅ |
| 3 | **Static INT8** | **1.8GB** | 6.3GB | 15s | ✅ |
| 4 | **TensorRT INT8** | 1.8GB | ~2GB | ~2s | 🎯 **Target** |

**다음**: Jetson에서 TensorRT 변환 및 테스트
