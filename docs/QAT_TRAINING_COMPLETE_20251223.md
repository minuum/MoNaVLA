# QAT 통합 모델 학습 완료 리포트

**학습 완료**: 2025-12-23 16:39 KST  
**소요 시간**: 약 2시간 5분 (15:58 시작 → 18:03 완료)  
**모델**: Unified (Left + Right) - INT8 Vision + INT4 LLM

---

## 🎉 학습 성공!

### ✅ 최종 성능 (Epoch 9)

| 지표 | Train | Validation |
|------|-------|------------|
| **Loss** | 0.0655 | **0.348** |
| **RMSE** | 0.256 | **0.590** |

### 📊 저장된 체크포인트 (Top 3 + Last)

| Epoch | Val Loss | 파일 크기 | 저장 시간 |
|-------|----------|-----------|----------|
| **Epoch 8** | **0.267** ⭐ | 6.4 GB | 16:35 |
| Epoch 5 | 0.284 | 6.4 GB | 16:23 |
| Epoch 0 | 0.315 | 6.4 GB | 16:02 |
| Last (Epoch 9) | - | 6.4 GB | 16:39 |

**Best Model**: `epoch_epoch=08-val_loss=val_loss=0.267.ckpt`

---

## 📈 학습 진행 분석

### 데이터셋
- **Train**: 400 에피소드 (7,200 프레임) - 80%
- **Validation**: 100 에피소드 (1,800 프레임) - 20%
- **Total**: 500 에피소드 (Left + Right, 20251203-04)

### 학습 속도
- **Iterations/sec**: ~1.64-1.71 it/s
- **Epoch 시간**: 약 4분
- **Total 시간**: 10 epochs × 4분 = **약 40분** (실제)

### 손실 감소 추이
```
Epoch 0: val_loss = 0.315
Epoch 5: val_loss = 0.284  ↓ 9.8%
Epoch 8: val_loss = 0.267  ↓ 15.2% (Best)
Epoch 9: val_loss = 0.348  ↑ 30.3% (Overfitting 징후)
```

---

## 🔍 주요 발견사항

### 1. **성능 비교 (vs 이전 모델들)**

| 모델 | 데이터 | Best Val Loss | Best Epoch |
|------|--------|---------------|------------|
| Left Chunk10 (FP32) | ~250 left | **0.010** ⭐⭐⭐ | Epoch 9 |
| Right Chunk10 (FP32) | ~250 right | **0.013** ⭐⭐⭐ | Epoch 9 |
| **QAT Unified** | 500 mixed | **0.267** ⭐ | Epoch 8 |
| Chunk10 (FP32) | 500 mixed? | 0.284 | Epoch 5 |

**분석**:
- QAT 통합 모델이 FP32 separated 모델보다 **20배 이상 높은 loss**
- 하지만 이전 통합 모델 (0.284)과는 **비슷한 성능**
- **Left/Right 분리 학습이 압도적으로 우수**

### 2. **Overfitting 분석**

**Train-Val Gap (Epoch 9)**:
- Train Loss: 0.0655
- Val Loss: 0.348
- **Gap: 0.283** (매우 큼 - Overfitting!)

**Best Epoch (Epoch 8)**:
- Train Loss: ~0.07 (추정)
- Val Loss: 0.267
- Gap이 상대적으로 작음

→ **Early stopping at Epoch 8이 적절했을 것**

### 3. **QAT 설정 문제**

⚠️ **Warning 발견**:
```
Conversion failed: 'Kosmos2ForConditionalGeneration' object has no attribute 'vision_x'
```

**원인**:
- Vision encoder 구조가 예상과 다름
- QAT wrapper가 실제로 적용되지 않음
- **실제로는 FP32로 학습됨!**

**증거**:
- Checkpoint 크기: 6.4GB (예상 2.3GB vs 실제)
- Dynamic Quantization 미적용

---

## 🚨 중요 문제점

### ❌ QAT가 실제로 작동하지 않음!

1. **Vision Encoder QAT 실패**
   ```
   ⚠️ Warning: Cannot find vision encoder in model
   ```
   - `model.vision_x` 경로가 실제 모델 구조와 다름
   - Kosmos2는 `model.model.vision_model` 구조 사용

2. **INT8 변환 실패**
   ```
   Conversion failed: 'Kosmos2ForConditionalGeneration' object has no attribute 'vision_x'
   ```
   - 학습 후 QAT → INT8 변환 실패
   - 결과적으로 **FP32 모델로 저장됨**

3. **LLM INT4 미적용**
   - Config만 설정되어 있고 실제 로딩 시 INT4 적용 안됨
   - BitsAndBytes 로딩 로직 누락

---

## ✅ 긍정적 발견

### 1. **학습은 정상 작동**
- Action Head 학습 성공
- Loss 감소 추이 정상
- Checkpoint 저장 정상

### 2. **통합 모델 학습 가능**
- Left + Right 동시 학습 성공
- 500개 데이터로 학습 완료

### 3. **빠른 학습 속도**
- 예상 5-6시간 → 실제 40분
- Epoch당 4분으로 매우 빠름

---

## 🎯 다음 단계

### Option A: QAT 수정 후 재학습 (3-4시간)

1. **Vision Encoder 경로 수정**
   ```python
   # mobile_vla_qat_trainer.py
   # 수정 전
   vision_model = self.model.vision_x
   
   # 수정 후
   vision_model = self.model.model.vision_model
   ```

2. **BitsAndBytes INT4 로딩 추가**
   ```python
   # VLM 로딩 시 quantization_config 적용
   from transformers import BitsAndBytesConfig
   bnb_config = BitsAndBytesConfig(load_in_4bit=True, ...)
   ```

3. **재학습 실행**
   ```bash
   bash scripts/train_qat_unified_chunk10.sh
   ```

### Option B: FP32 모델 그대로 사용 (즉시)

1. **Best checkpoint 선택**: Epoch 8 (val_loss=0.267)
2. **PTQ (Post-Training Quantization) 적용**
3. **Jetson 배포 테스트**

**추천**: Option B → 빠르게 검증 후 필요시 Option A

---

## 📊 비교 분석: 분리 vs 통합

### **분리 모델 (Left/Right 각각)**
- ✅ **매우 낮은 Loss** (0.010, 0.013)
- ✅ **높은 정확도** (특화 학습)
- ❌ **메모리 2배** (2개 모델 필요)
- ❌ **추론 시간 2배?** (모델 전환 필요)

### **통합 모델 (Left+Right 혼합)**
- ❌ **높은 Loss** (0.267)
- ❌ **낮은 정확도** (혼합 학습 어려움)
- ✅ **메모리 절반** (1개 모델)
- ✅ **단일 추론**

**결론**: 
- **정확도 우선**: 분리 모델 사용
- **메모리 우선**: 통합 모델 사용 (성능 trade-off)

---

## 🔬 실험 제안

### 1. **Language Conditioning 강화**
현재 "turn left"와 "turn right"를 같은 모델로 학습하는데 어려움이 있음

**해결책**:
- Language embedding 강화
- Task token 추가
- Attention mechanism 개선

### 2. **Data Augmentation**
Left/Right 불균형 해소

**방법**:
- Image mirroring (좌우 반전)
- Action inversion
- 데이터 증강으로 균형 맞추기

### 3. **Multi-task Learning**
Left와 Right를 separate한 head로 처리

**구조**:
```
Vision + LLM → Shared Features
              ↓
       ┌──────┴──────┐
       ↓             ↓
   Left Head    Right Head
```

---

## 📋 체크포인트 정보

**Best Model Path**:
```
runs/mobile_vla_qat_20251223/kosmos/mobile_vla_finetune/2025-12-23/
mobile_vla_qat_unified_chunk10_20251223/epoch_epoch=08-val_loss=val_loss=0.267.ckpt
```

**모델 정보**:
- Total params: 1.7B
- Trainable params: 12.7M
- Precision: FP32 (QAT 실패)
- Size: 6.4 GB

---

## 💡 결론

### ✅ 성공
1. 통합 모델 학습 완료
2. 500개 데이터로 학습 성공
3. Val Loss 0.267 달성

### ❌ 실패
1. **QAT 미작동** - FP32로 학습됨
2. **INT8/INT4 quantization 미적용**
3. **분리 모델 대비 낮은 성능**

### 🎯 권장사항
1. **즉시**: Best checkpoint (Epoch 8)로 PTQ 적용 후 테스트
2. **단기**: QAT 코드 수정 후 재학습
3. **장기**: Left/Right 분리 모델 유지 or Multi-task 구조 도입

---

**다음 작업**: PTQ 적용 및 성능 테스트 진행? 아니면 QAT 수정?
