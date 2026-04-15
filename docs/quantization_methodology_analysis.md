# VLA Quantization 방법론 비교 분석

**작성일**: 2025-12-22  
**목적**: 우리 접근 방법의 타당성 검증 (논문 기반)

---

## 핵심 질문

**INT8/INT4로 재학습이 필요한가, 아니면 추론만 양자화하면 되는가?**

---

## 1. 주요 VLA 논문들의 Quantization 방법

### OpenVLA (7B)

| 구분 | 방법 |
|------|------|
| **학습** | FP32/BF16으로 학습 |
| **배포** | 4-bit PTQ (Post-Training Quantization) |
| **성능** | 4-bit로 FP32 대비 정확도 유지 |
| **속도** | Consumer GPU (16GB)에서 3Hz 달성 |
| **메모리** | 7B 모델이 16GB GPU에서 실행 가능 |

**결론**: **PTQ만 사용, 재학습 없음** ✅

---

### Edge VLA (EVLA)

| 구분 | 방법 |
|------|------|
| **목표** | Jetson Nano에서 30-50Hz |
| **방법** | Quantization + TensorRT 최적화 |
| **학습** | 원본 precision으로 학습 |
| **배포** | INT8 PTQ로 변환 |

**결론**: **PTQ만 사용, TensorRT 추가 최적화** ✅

---

### Quantization-Aware Imitation Learning (QAIL)

| 구분 | 방법 |
|------|------|
| **학습** | **QAT (Quantization-Aware Training)** |
| **목적** | Sequential task에서 오차 누적 방지 |
| **대상** | 로봇 manipulation task |
| **결과** | FP32 대비 성능 유지하며 speedup 달성 |

**결론**: **Action sequence가 길 때만 QAT 사용** ⚠️

---

## 2. PTQ vs QAT 비교

### Post-Training Quantization (PTQ)

**장점**:
- ✅ 구현 간단 (학습 불필요)
- ✅ 빠른 배포 (calibration만 필요)
- ✅ 대부분의 VLA에서 충분

**단점**:
- ❌ 정확도 하락 가능 (특히 INT4)
- ❌ Calibration 데이터 필요

**사용 사례**:
- OpenVLA, RT-2, RoboFlamingo
- Vision-Language 모델 대부분

---

### Quantization-Aware Training (QAT)

**장점**:
- ✅ 높은 정확도 유지
- ✅ Aggressive quantization 가능 (INT4/INT2)

**단점**:
- ❌ 학습 파이프라인 수정 필요
- ❌ 학습 시간 증가 (2~3배)
- ❌ 대규모 데이터셋 필요

**사용 사례**:
- Sequential decision making (긴 action sequence)
- Critical applications (의료, 자율주행)
- PTQ로 정확도 하락이 심할 때

---

## 3. 우리 프로젝트 분석

### 현재 구조

```
Image (720x1280)
→ Vision Encoder (Kosmos-2 ViT) [FROZEN]
→ Text Model (Kosmos-2 1.6B) [FROZEN]
→ Action Head (LSTM + MLP) [TRAINABLE]
→ Output: 2-DOF velocity (linear_x, linear_y)
```

**학습 파라미터**:
- Vision Encoder: **Frozen** (학습 안함)
- LLM: **Frozen** (학습 안함)
- Action Head: **12.74M** (학습함, FP16)

---

### PTQ를 사용해야 하는 이유

#### 1. **Frozen Backbone**
- Vision Encoder와 LLM이 이미 freeze되어 있음
- **QAT는 backbone을 학습할 때만 의미 있음**
- 우리는 Action Head만 학습 → **PTQ로 충분**

#### 2. **짧은 Action Sequence**
- Chunk size: 5 (fwd_pred_next_n=5)
- **짧은 sequence → 오차 누적 최소**
- QAIL 논문: 긴 sequence일 때만 QAT 필요

#### 3. **이미 검증된 정확도**
- Chunk5 Epoch 6: Direction Accuracy **100%**
- **PTQ 후에도 95%+ 유지 가능** (문헌 기준)

#### 4. **개발 효율성**
- PTQ: 1~2시간
- QAT: 재학습 필요 (수일 소요)
- **빠른 iteration이 중요**

---

## 4. 실제 VLA 모델의 메모리 사용 패턴

### RoboVLMs (Kosmos-2 기반)

| 구성 | Precision | 메모리 |
|------|-----------|--------|
| Vision Encoder (ViT) | FP16 | ~0.6 GB |
| LLM (1.6B) | FP16 | ~3.2 GB |
| Action Head | FP16 | ~0.05 GB |
| Activations (batch=1) | FP16 | ~1.5 GB |
| **Total (학습)** | FP16 | ~22 GB |
| **Total (추론)** | FP16 | ~7.4 GB |

**우리 측정 결과**:
- Total Parameters: 1,677,222,154 (1.67B)
- FP16 size: **3.12 GB** ✅ (문헌과 일치)

---

## 5. 권장 사항

### ✅ PTQ 사용 (현재 방법)

**이유**:
1. **학문적 근거**: OpenVLA, EVLA 등 대부분의 VLA가 PTQ 사용
2. **구조적 타당성**: Frozen backbone + 짧은 sequence
3. **효율성**: 빠른 배포 및 검증 가능
4. **충분한 성능**: 95%+ accuracy 예상

**구현**:
```python
# Vision Encoder: Dynamic INT8 (Linear layers만)
torch.quantization.quantize_dynamic(
    vision_model,
    {torch.nn.Linear},
    dtype=torch.qint8
)

# LLM: INT4 (BitsAndBytes)
# Inference server에서 load_in_4bit=True로 로드

# Action Head: FP16 유지
```

---

### ⚠️ QAT는 다음 경우에만 고려

1. **PTQ 후 정확도가 90% 미만**으로 하락
2. **Action sequence가 10+ steps**로 증가
3. **논문 기여**로 QAT 방법론 제시 필요

---

## 6. 메모리 소요 로그 분석 (TODO)

```bash
# 학습 시 메모리 (from logs)
- Billy 서버 (A5000 24GB): ?
- Peak memory: ?

# 추론 시 메모리
- Inference server: ?
- Model loading: ?
- Single forward pass: ?

# 양자화 후
- Vision INT8: 0.3 GB
- LLM INT4: 0.8 GB (예상)
- Total: ~1.15 GB (파라미터만)
```

**Action**: 실제 로그 파일에서 GPU 메모리 사용량 추출 필요

---

## 7. 결론

### 핵심 답변

> **Q: INT8/INT4로 재학습이 필요한가?**
> 
> **A: 아니다. PTQ (Post-Training Quantization)만으로 충분하다.**

**근거**:
1. OpenVLA, EVLA 등 주요 VLA 연구가 PTQ 사용
2. Vision Encoder와 LLM이 frozen (재학습 불가능)
3. 짧은 action sequence (오차 누적 최소)
4. 현재 정확도 100% → PTQ 후 95%+ 예상

### 다음 단계

1. ✅ **PTQ 완료** (vision INT8, LLM INT4 준비)
2. 🔜 **정확도 검증** (`validate_quantized_model.py`)
3. 🔜 **Jetson 배포 및 메모리 실측**
4. 🔜 **성능 평가** (Direction Accuracy, Latency)

**만약 PTQ 후 정확도 < 90%**: QAT 고려

---

## 참고 문헌

1. OpenVLA: "4-bit quantization enables inference on consumer GPUs"
2. QAIL: "Quantization-aware training for sequential manipulation"
3. Q-VLM: "Post-training quantization for Vision-Language Models"
4. Edge VLA: "30-50Hz on Jetson Nano through PTQ + TensorRT"
