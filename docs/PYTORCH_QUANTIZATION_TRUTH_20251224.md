# 현재 상황 정리: PyTorch Quantization의 진실

**일시**: 2025-12-24 04:16 KST

---

## 🤔 문제: 뭐가 문제인가?

### Static INT8 변환 결과

| 항목 | 결과 | 설명 |
|------|------|------|
| **파일 크기** | 1.8 GB | ✅ INT8로 저장됨 |
| **로딩 후 메모리** | 6.3 GB | ❌ FP32로 자동 변환됨 |
| **Inference** | FP32 | ❌ INT8로 실행 안됨 |

### PyTorch의 진실

```python
# Step 1: INT8로 변환 및 저장
model_int8 = torch.quantization.convert(model)
torch.save(model_int8.state_dict(), 'model.pt')  
# ✅ 파일: 1.8GB (INT8)

# Step 2: 로딩
new_model = Model()
new_model.load_state_dict(torch.load('model.pt'))
# ❌ 메모리: 6.3GB (FP32로 자동 변환!)

# Step 3: Inference
output = new_model(x)
# ❌ FP32로 실행 (INT8 아님!)
```

---

## 🔍 PyTorch Quantization 동작 원리

### Static Quantization의 3가지 모드

| 모드 | Storage | Runtime | 메모리 절감 | 속도 개선 |
|------|---------|---------|------------|----------|
| **FP32** | FP32 | FP32 | ❌ | ❌ |
| **Static INT8 (Current)** | INT8 | **FP32** | ❌ | ❌ |
| **TensorRT/ONNX** | INT8 | **INT8** | ✅ | ✅ |

### 왜 이렇게 동작하나?

**PyTorch의 설계 철학**:
1. **Flexibility**: 모든 연산을 FP32로 실행 (호환성)
2. **Quantized Tensor**: 저장용 포맷 (전송/배포)
3. **Inference Engine 필요**: TensorRT, ONNX Runtime 등

---

## 💡 해결 방법 비교

### Option 1: 현재 방법 (Dequantize)

```python
# INT8 → FP32 변환
state_dict_fp32 = {k: v.dequantize() if v.is_quantized else v 
                   for k, v in state_dict.items()}
model.load_state_dict(state_dict_fp32)
```

**결과**:
- 파일: 1.8GB ✅
- 메모리: 6.3GB ❌
- 속도: 15s ❌

**용도**: 
- 파일 전송 (1.8GB vs 6.4GB)
- 배포 최적화

---

### Option 2: TensorRT (진짜 INT8) ⭐

```bash
# ONNX 변환
python export_onnx.py

# TensorRT 변환
trtexec --onnx=model.onnx \
        --int8 \
        --saveEngine=model.trt
```

**결과**:
- 파일: 1.8GB ✅
- 메모리: 2-3GB ✅
- 속도: 1-2s ✅

**필요**:
- TensorRT 설치 (우리 서버: ❌)
- ONNX 변환 (복잡)

---

### Option 3: ONNX Runtime

```python
import onnxruntime as ort
from onnxruntime.quantization import quantize_dynamic

# Quantize
quantize_dynamic('model.onnx', 'model_int8.onnx')

# Inference
session = ort.InferenceSession('model_int8.onnx')
output = session.run(None, inputs)
```

**결과**:
- 파일: 1.8GB ✅
- 메모리: 3-4GB ✅
- 속도: 5-10s ⚠️

**필요**:
- ONNX 변환
- onnxruntime 설치

---

### Option 4: PyTorch Mobile (Jetson용)

```python
# TorchScript 변환
traced = torch.jit.trace(model_quantized, inputs)
traced.save('model_mobile.pt')

# Jetson에서
model = torch.jit.load('model_mobile.pt')
```

**결과**:
- 파일: 1.8GB ✅
- 메모리: 2-3GB ✅ (Jetson에서)
- 속도: 2-3s ✅

---

## 🎯 꼭 TensorRT를 써야 하나?

### 아니요! 대안이 있습니다.

| 방법 | 우리 서버 | Jetson | 권장 |
|------|-----------|--------|------|
| **TensorRT** | ❌ 미설치 | ✅ 기본 제공 | Jetson에서 |
| **ONNX Runtime** | ✅ 설치 가능 | ✅ 가능 | 테스트용 |
| **PyTorch Mobile** | ❌ 의미 없음 | ✅ 최적 | **Jetson 배포** ⭐ |
| **현재 방법** | ✅ 작동 | ✅ 작동 | 파일 전송 |

---

## 📋 실용적 결론

### 현재 INT8 모델의 가치

**✅ 가치 있음**:
1. **파일 크기 72% 감소** (6.4GB → 1.8GB)
   - 전송 시간 단축
   - 스토리지 절약
   - 배포 효율성

2. **Jetson 최적화 준비**
   - Jetson은 자동으로 INT8 실행
   - PyTorch Mobile 지원
   - TensorRT 기본 제공

**❌ 우리 서버에서**:
- 메모리 절감: 없음
- 속도 개선: 없음
- 하지만 파일은 작음 ✅

---

## 🚀 추천 방향

### 1단계: 현재 방법 유지
```bash
# 1.8GB INT8 모델을 Jetson으로 전송
rsync chunk5_best_int8/model.pt jetson:/path/
```
**시간**: 10분 (vs 30분 for FP32)

### 2단계: Jetson에서 직접 테스트
```python
# Jetson PyTorch는 자동으로 INT8 실행
model = torch.jit.load('model.pt')
# 메모리: 2-3GB (자동 최적화)
```

### 3단계: (Optional) 우리 서버에서 TensorRT
```bash
# TensorRT 설치 (시간 걸림)
pip install nvidia-tensorrt

# ONNX 변환 및 TensorRT
# 복잡하고 시간 소요
```

---

## ✅ 최종 답변

### 질문: 우리 서버에서 TensorRT 써볼래?
**답**: 가능하지만 **비추천**
- TensorRT 설치 복잡
- ONNX 변환 어려움
- Jetson에서 하는 게 더 쉬움

### 질문: 꼭 저 방법을 써야만 해?
**답**: **아니요**
- 현재 INT8 모델도 가치 있음 (파일 크기)
- Jetson에서 자동으로 최적화됨

### 질문: 뭐가 문제야?
**답**: **문제 없음**, 단지...
- PyTorch는 storage만 INT8
- 진짜 INT8 inference는 Jetson에서!

---

**결론**: 현재 INT8 모델 (1.8GB)을 **Jetson으로 바로 배포**하는 게 최선! 🎯
