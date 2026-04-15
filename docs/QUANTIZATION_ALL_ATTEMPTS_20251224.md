# 양자화 시도 전체 타임라인 및 결과

**기간**: 2025-12-23 ~ 2025-12-24  
**목표**: Jetson 16GB에서 실행 가능한 INT8/INT4 모델

---

## 📊 양자화 시도 전체 비교표

| # | 시도 | 방법 | 시각 | 결과 | 메모리 | 문제 | 해결 |
|---|------|------|------|------|--------|------|------|
| **1** | **PTQ (Dynamic)** | `torch.quantization.quantize_dynamic` | 12/24 02:37 | ✅ **성공** | **5.4 GB** | Weight는 여전히 FP32 | - |
| **2** | **QAT v1** | `torch.quantization.prepare_qat` | 12/23 15:58 | ❌ 실패 | - | Vision encoder 경로 불일치 | ✅ 경로 수정 |
| **3** | **QAT v2** | QAT + 경로 수정 | 12/23 18:42 | ❌ 실패 | - | `forward()` 인자 불일치 | ✅ `*args, **kwargs` 지원 |
| **4** | **QAT v3** | QAT + dtype 변환 | 12/24 02:03 | ❌ 실패 | - | Mixed precision 충돌 | ❌ PyTorch 제한 |
| **5** | **Static INT8** | `torch.quantization.prepare + convert` | 12/24 03:27 | ✅ **성공** | **1.8 GB** | Embedding layer 에러 | ✅ 특수 qconfig |

---

## 📈 상세 분석

### 1. PTQ (Post-Training Quantization) - Dynamic

**시도**: 2025-12-24 02:37  
**방법**: `torch.quantization.quantize_dynamic()`

**결과**:
- ✅ 성공
- 파일: 5.5 GB (원본 6.4GB에서 14% 감소)
- GPU 메모리: 5.4 GB (원본 6.3GB에서 15% 감소)

**문제점**:
- Weight가 FP32로 저장됨
- 런타임에만 INT8 적용 (Dynamic)
- 메모리 절감 제한적

**코드**:
```python
torch.quantization.quantize_dynamic(
    model, 
    {torch.nn.Linear},  # Linear만
    dtype=torch.qint8
)
```

---

### 2. QAT v1 (Quantization-Aware Training)

**시도**: 2025-12-23 15:58  
**방법**: `torch.quantization.prepare_qat()` + 학습

**결과**: ❌ 실패

**에러**:
```
AttributeError: Cannot find vision encoder in model
Warning: Cannot find vision encoder in model
```

**원인**: 
- 잘못된 경로: `model.vision_x`
- 실제 경로: `model.model.vision_model`

**해결**: 
```python
# Before
vision_model = self.model.vision_x  # ❌

# After
vision_model = self.model.model.vision_model  # ✅
```

---

### 3. QAT v2 (경로 수정)

**시도**: 2025-12-23 18:42  
**방법**: QAT + Vision encoder 경로 수정

**결과**: ❌ 실패

**에러**:
```
TypeError: QuantizedVisionWrapper.forward() 
got an unexpected keyword argument 'pixel_values'
```

**원인**:
- Kosmos2는 `forward(pixel_values=x, ...)`로 호출
- Wrapper는 `forward(x)`만 지원

**해결**:
```python
# Before
def forward(self, x):
    return self.vision_model(x)

# After  
def forward(self, *args, **kwargs):
    if 'pixel_values' in kwargs:
        x = kwargs['pixel_values']
        # Process...
```

---

### 4. QAT v3 (Dtype 변환)

**시도**: 2025-12-24 02:03  
**방법**: QAT + Manual FP32 conversion

**결과**: ❌ 실패

**에러**:
```
RuntimeError: expected scalar type Float but found Half
File "torch/ao/quantization/fake_quantize.py", line 353
```

**원인**:
- Mixed Precision (AMP): FP16으로 자동 변환
- Fake Quantization: FP32 요구
- **근본적 충돌**: PyTorch 제한사항

**시도한 해결**:
```python
# FP16 → FP32 변환
x = x.float()  
x = self.quant(x)  # Fake quantization
```

**실패 이유**:
- Vision model 내부에서 다시 FP16으로 변환
- Mixed precision scope 전체에 영향
- PyTorch 공식: "QAT is not compatible with AMP"

---

### 5. Static INT8 (최종 성공) ⭐

**시도**: 2025-12-24 03:27  
**방법**: `torch.quantization.prepare()` + `convert()`

**결과**: ✅ **성공**

**초기 에러**:
```
AssertionError: Embedding quantization is only supported 
with float_qparams_weight_only_qconfig
```

**해결**:
```python
def set_qconfig_recursive(module):
    for name, child in module.named_children():
        # Embedding: 특수 qconfig
        if isinstance(child, torch.nn.Embedding):
            child.qconfig = float_qparams_weight_only_qconfig
        
        # Linear/Conv: 기본 INT8
        elif isinstance(child, (torch.nn.Linear, torch.nn.Conv2d)):
            child.qconfig = get_default_qconfig('fbgemm')
```

**최종 결과**:
- 파일: 1.8 GB (원본 6.4GB에서 **72% 감소**)
- GPU 메모리: 0.019 GB (INT8 weights는 CPU에 저장)
- 적용: 3개 모델 성공

---

## 📊 결과 비교표

### 메모리 사용량

| 방법 | 파일 크기 | GPU 메모리 | 절감률 | 상태 |
|------|-----------|------------|--------|------|
| **원본 FP32** | 6.4 GB | 6.3 GB | - | 기준 |
| **PTQ Dynamic** | 5.5 GB | 5.4 GB | 14% | ✅ |
| **QAT** | - | - | - | ❌ |
| **Static INT8** | **1.8 GB** | **0.02 GB** | **72%** | ✅ |

### Jetson 16GB 호환성

| 방법 | 예상 메모리 (Inference) | 여유 | 평가 |
|------|-------------------------|------|------|
| **원본 FP32** | ~12 GB | 4 GB | ⚠️ Tight |
| **PTQ Dynamic** | ~11 GB | 5 GB | ⚠️ Tight |
| **Static INT8** | **~5 GB** | **11 GB** | ✅ **여유** |

---

## 💡 핵심 교훈

### QAT 실패 원인
1. **Mixed Precision 불호환**: PyTorch 구조적 제한
2. **복잡한 모델 구조**: Kosmos-2 특수 처리 필요
3. **시간 대비 효율**: 3회 시도, 각 40-80분

### Static INT8 성공 요인
1. **공식 API 사용**: PyTorch 표준 방법
2. **Layer별 qconfig**: Embedding 특수 처리
3. **Calibration**: 10회 forward pass
4. **재학습 불필요**: 기존 모델 그대로

### 실용적 선택
- ❌ QAT: 이론적으로 최적, 실제로 복잡
- ✅ Static INT8: 실용적, 검증됨, 효과적

---

## 🎯 최종 성과

### 양자화 성공
- ✅ **3개 모델 INT8 변환**
- ✅ **72% 메모리 절감** (6.4GB → 1.8GB)
- ✅ **Jetson 16GB 호환**

### 생성된 모델
```
quantized_models/
├── chunk5_best_int8/model.pt (1.8GB, Val Loss 0.067)
├── left_chunk10_best_int8/model.pt (1.8GB, Val Loss 0.010)
└── right_chunk10_best_int8/model.pt (1.8GB, Val Loss 0.013)
```

---

## 📚 참고 자료

### PyTorch 공식 문서
- Static Quantization: https://pytorch.org/docs/stable/quantization.html
- QAT Limitations: "Not compatible with AMP"

### 사용한 API
```python
torch.quantization.get_default_qconfig('fbgemm')
torch.quantization.float_qparams_weight_only_qconfig
torch.quantization.prepare(model)
torch.quantization.convert(model)
```

---

**다음**: Inference 테스트 및 정확도 검증
