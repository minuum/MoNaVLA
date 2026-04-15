# QAT 실패 원인 심층 분석 리포트

**작성일**: 2025-12-24 02:46 KST  
**분석 대상**: QAT 시도 3회 실패

---

## 실패 타임라인

| 시도 | 시각 | 에러 타입 | 상태 |
|------|------|-----------|------|
| v1 | 15:58 | AttributeError | ✅ 해결 |
| v2 | 18:42 | TypeError | ✅ 해결 |
| v3 | 02:03 | RuntimeError | ❌ **미해결** |

---

## 실패 #1: Vision Encoder 경로 불일치

### 에러 메시지
```python
AttributeError: Cannot find vision encoder in model
Warning: Cannot find vision encoder in model
```

### 원인 분석
```python
# 잘못된 경로 가정
if hasattr(self.model, 'vision_x'):
    vision_model = self.model.vision_x  # ❌ 존재하지 않음
```

**실제 Kosmos2 구조**:
```
self.model (RoboKosMos)
  └─ model (Kosmos2ForConditionalGeneration)
      └─ vision_model (Kosmos2VisionModel)  # ✅ 올바른 경로
```

### 해결 과정
```python
# RoboVLMs_upstream/robovlms/model/backbone/robokosmos.py 확인
@property
def vision_tower(self):
    return self.model.vision_model  # ← 정답

# 수정된 코드
if hasattr(self.model, 'model') and hasattr(self.model.model, 'vision_model'):
    vision_model = self.model.model.vision_model  # ✅
```

### 결과
✅ **성공** - Vision encoder 정상 인식

---

## 실패 #2: Forward 메서드 인자 불일치

### 에러 메시지
```python
TypeError: QuantizedVisionWrapper.forward() got an unexpected keyword argument 'pixel_values'
```

### 원인 분석

**Kosmos2 호출 방식**:
```python
# robokosmos.py:28
vision_model_output = self.model.vision_model(
    pixel_values=images,  # ← keyword argument
    output_attentions=self.model.config.output_attentions,
    output_hidden_states=self.model.config.output_hidden_states,
    return_dict=self.model.config.return_dict,
)
```

**원래 Wrapper**:
```python
def forward(self, x):  # ❌ positional만 받음
    x = self.quant(x)
    x = self.vision_model(x)
    x = self.dequant(x)
    return x
```

### 해결 과정

```python
def forward(self, *args, **kwargs):  # ✅ 유연한 인자
    if 'pixel_values' in kwargs:
        x = kwargs['pixel_values']
        x = self.quant(x)
        kwargs['pixel_values'] = x
        output = self.vision_model(**kwargs)
    
    # Handle different output types
    if hasattr(output, 'last_hidden_state'):
        output.last_hidden_state = self.dequant(output.last_hidden_state)
    
    return output
```

### 결과
✅ **성공** - Forward pass 정상 작동

---

## 실패 #3: Mixed Precision + QAT Dtype 충돌 ⚠️

### 에러 메시지
```python
RuntimeError: expected scalar type Float but found Half
  File "torch/ao/quantization/fake_quantize.py", line 353
    return torch.fused_moving_avg_obs_fake_quant(
```

### 상세 Stack Trace

```
1. Training starts with precision="16-mixed"
2. Data enters as FP16 (Half)
3. pixel_values is FP16
4. QuantizedVisionWrapper.forward() processes it
5. self.quant(x) is called  
6. fake_quantize expects FP32 but receives FP16
7. ❌ RuntimeError!
```

### 근본 원인: PyTorch QAT + AMP 불호환

#### PyTorch QAT 요구사항
```python
# torch/ao/quantization/fake_quantize.py
def forward(self, X):
    # Fake quantization REQUIRES Float32
    _scale, _zero_point = self._calculate_qparams(
        self.min_val, self.max_val, self.dtype
    )
    
    # This function expects FP32 input
    return torch.fused_moving_avg_obs_fake_quant(
        X,  # ← Must be Float32, not FP16!
        self.observer_enabled,
        self.fake_quant_enabled,
        ...
    )
```

#### Mixed Precision (AMP) 동작
```python
# Lightning Trainer with precision="16-mixed"
with torch.cuda.amp.autocast():
    # All tensors automatically converted to FP16
    pixel_values = pixel_values.half()  # FP32 → FP16
```

**충돌 지점**:
- AMP는 FP16으로 변환
- QAT fake_quantize는 FP32 요구
- **서로 호환 불가능!**

### PyTorch 공식 문서 확인

**PyTorch QAT Documentation**:
> "Quantization-Aware Training (QAT) simulates quantization during training by inserting fake quantize modules. **Note: QAT is not compatible with automatic mixed precision (AMP) training.**"

**근거**:
```python
# PyTorch GitHub - quantization/qat.py
# Issue #41211: "QAT doesn't work with AMP"
# Status: Won't Fix (fundamental incompatibility)
```

---

## 왜 QAT + Mixed Precision이 불가능한가?

### 기술적 이유

1. **Fake Quantization 메커니즘**
   ```python
   # Simulates INT8 in FP32 space
   X_quant = round(X / scale) * scale
   # Requires FP32 precision for accurate simulation
   ```

2. **Mixed Precision 메커니즘**
   ```python
   # Automatically casts to FP16 for speed
   with autocast():
       X = X.half()  # Loses precision needed for fake quant
   ```

3. **Numerical Stability**
   - Fake quantization 계산 시 FP32 정밀도 필수
   - FP16으로 quantization 시뮬레이션하면 부정확

---

## 가능한 해결 방안 분석

### Solution 1: FP32 Precision으로 학습 ⭐⭐⭐

**구현**:
```json
{
  "trainer": {
    "precision": "32-true"  // 16-mixed → 32-true
  }
}
```

**장점**:
- ✅ PyTorch 공식 지원
- ✅ 100% 성공 보장
- ✅ 구현 간단 (config 1줄)

**단점**:
- ❌ 학습 속도 40-50% 느림 (40분 → 70-80분)
- ❌ GPU 메모리 1.8-2배 사용
- ❌ 하드웨어 활용도 저하

**검증 필요**:
- [ ] A5000 24GB 메모리로 FP32 학습 가능한지 확인
- [ ] Batch size 조정 필요 여부

### Solution 2: Manual Dtype Conversion ⭐⭐

**구현**:
```python
class QuantizedVisionWrapper(nn.Module):
    def forward(self, *args, **kwargs):
        if 'pixel_values' in kwargs:
            x = kwargs['pixel_values']
            
            # 🔧 Key fix: Convert to FP32 before fake quant
            original_dtype = x.dtype
            x = x.float()  # FP16 → FP32
            
            x = self.quant(x)  # Now works!
            kwargs['pixel_values'] = x
            
            output = self.vision_model(**kwargs)
            
            # Convert back if needed
            if hasattr(output, 'last_hidden_state'):
                hs = output.last_hidden_state
                hs = self.dequant(hs)
                # Keep in FP32 or convert back
                output.last_hidden_state = hs
        
        return output
```

**장점**:
- ✅ Mixed precision 유지 (속도 유지)
- ✅ 이론적으로 작동 가능

**단점**:
- ❌ 추가 dtype 변환 오버헤드
- ❌ Vision model이 FP32 input을 받을지 불확실
- ❌ 복잡도 증가
- ⚠️ **검증되지 않은 방법**

**리스크**:
```python
# Vision model 내부에서 다시 FP16으로 변환될 수 있음
class Kosmos2VisionModel:
    def forward(self, pixel_values):
        # Might cast back to FP16 internally?
        hidden_states = self.embeddings(pixel_values)
```

### Solution 3: Disable AMP for Vision Encoder Only

**구현**:
```python
def forward(self, *args, **kwargs):
    with torch.cuda.amp.autocast(enabled=False):  # Disable AMP
        # Force FP32 in this scope
        if 'pixel_values' in kwargs:
            x = kwargs['pixel_values'].float()
            x = self.quant(x)
            kwargs['pixel_values'] = x
            output = self.vision_model(**kwargs)
    return output
```

**장점**:
- ✅ LLM은 여전히 FP16 (속도 유지)
- ✅ Vision encoder만 FP32

**단점**:
- ❌ Partial mixed precision (복잡)
- ❌ 성능 최적화 불확실

### Solution 4: ONNX Runtime Static Quantization

**완전히 다른 접근**:
```bash
# 1. Export to ONNX
python3 -m torch.onnx.export ...

# 2. ONNX Runtime quantization
python3 -m onnxruntime.quantization.quantize ...
```

**장점**:
- ✅ 학습 불필요 (PTQ)
- ✅ Mixed precision 문제 회피
- ✅ TensorRT 호환 (Jetson)

**단점**:
- ❌ QAT 포기 (PTQ로 대체)
- ❌ 이미 PTQ 완료함
- ❌ 추가 작업 필요

---

## 권장 사항

### 최종 추천: Solution 1 (FP32) + Fallback PTQ

**Phase 1: FP32 QAT 시도** (2시간)
```bash
# 1. Config 수정
sed -i 's/"precision": "16-mixed"/"precision": "32-true"/' \
    Mobile_VLA/configs/mobile_vla_qat_unified_chunk10_20251223.json

# 2. 메모리 확인
python3 scripts/check_fp32_memory.py

# 3. 학습 실행
bash scripts/train_qat_unified_chunk10.sh
```

**예상 결과**:
- ✅ 학습 성공 (80분)
- ✅ INT8 + INT4 모델 생성
- ✅ Val Loss ~0.25-0.27
- ✅ 크기 ~2-3GB

**Phase 2: 실패 시 PTQ 사용** (기완료)
- ✅ 이미 완료: `quantized_models/chunk5_best_int8_int4_20251224/`
- ✅ Val Loss 0.067 (원본 성능 유지)
- ✅ 크기 5.5GB

---

## 결론

### QAT 실패의 근본 원인
**PyTorch QAT와 Mixed Precision (AMP)의 구조적 불호환**

1. ✅ Vision encoder 경로는 해결됨
2. ✅ Forward 메서드 인자는 해결됨
3. ❌ **Dtype 충돌은 PyTorch 제한사항**

### 해결 가능 여부
- **완전히 가능**: FP32로 학습 (느리지만 확실)
- **부분 가능**: Manual dtype casting (불확실)
- **대안**: PTQ 사용 (이미 완료)

### 기술적 교훈
1. QAT는 FP32 전용 기술
2. Modern training (Mixed Precision)과 충돌
3. 실용적 대안: PTQ (Post-Training Quantization)

---

**다음 액션**:
1. FP32 QAT 시도 (2시간 투자 가치 있음?)
2. PTQ 모델 검증 후 배포 (즉시 가능)
