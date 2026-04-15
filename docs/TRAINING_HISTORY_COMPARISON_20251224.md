# 전체 학습 히스토리 비교 분석

**작성일**: 2025-12-24 01:56 KST  
**현재 시각**: 새벽 2시

---

## 📊 날짜별 학습 모델 전체 비교표

### 🗓️ 12월 17일 (화) - Chunk 비교 실험

| 모델명 | 데이터 | Chunk | Best Epoch | Best Val Loss | 크기 | Language Task | 비고 |
|--------|--------|-------|------------|---------------|------|---------------|------|
| **Chunk5** | 500 mixed | 5 | **Epoch 6** | **0.067** ⭐⭐⭐ | 6.4GB | ✅ Yes | 최고 성능! |
| **Chunk10** | 500 mixed | 10 | Epoch 5 | 0.284 | 6.4GB | ✅ Yes | Overfitting 심함 |

**발견사항**:
- **Chunk5가 압도적 우수** (0.067 vs 0.284)
- Chunk10은 overfitting 문제 심각
- Chunk5: Train-Val gap 작음 (generalization 좋음)

---

### 🗓️ 12월 18일 (수) - Left/Right 분리 실험

| 모델명 | 데이터 | Chunk | Best Epoch | Best Val Loss | 크기 | Language Task | 비고 |
|--------|--------|-------|------------|---------------|------|---------------|------|
| **Left C10** | ~250 left | 10 | Epoch 9 | **0.010** ⭐⭐⭐ | 6.4GB | ❌ No (left only) | **최저 loss!** |
| **Left C5** | ~250 left | 5 | Epoch 8/9 | **0.016** ⭐⭐ | 6.4GB | ❌ No (left only) | 우수 |
| **Right C10** | ~250 right | 10 | Epoch 9 | **0.013** ⭐⭐⭐ | 6.4GB | ❌ No (right only) | **최저 loss!** |

**발견사항**:
- **분리 학습이 압도적 우수** (0.010, 0.013)
- **통합 대비 20배 이상 낮은 loss**
- ⚠️ **단점**: Language task 무시됨 (항상 같은 방향만)

---

### 🗓️ 12월 23일 (월) - QAT 통합 모델 (1차 시도)

| 모델명 | 데이터 | Chunk | Best Epoch | Best Val Loss | 크기 | Quantization | Language Task | 비고 |
|--------|--------|-------|------------|---------------|------|--------------|---------------|------|
| **QAT Unified (실패)** | 500 mixed | 10 | Epoch 8 | 0.267 | 6.4GB | ❌ **실패** | ✅ Yes | QAT 미작동 |

**문제점**:
- ❌ Vision Encoder 경로 불일치
- ❌ QAT 미적용 (FP32로 학습됨)
- ❌ 파일 크기 6.4GB (INT8이면 ~2GB여야 함)

---

### 🗓️ 12월 24일 (화) - QAT 통합 모델 (2차 시도) ⏳ 진행 중

| 모델명 | 데이터 | Chunk | 상태 | Quantization | Language Task | 비고 |
|--------|--------|-------|------|--------------|---------------|------|
| **QAT Unified v2** | 500 mixed | 10 | **❌ 에러** | ⚠️ **에러 발생** | ✅ Yes | wrapper 인자 문제 |

**에러 내용**:
```
TypeError: QuantizedVisionWrapper.forward() got an unexpected keyword argument 'pixel_values'
```

**원인**:
- Kosmos2의 vision_model은 `pixel_values`를 키워드 인자로 받음
- 하지만 wrapper는 positional arg만 받도록 구현됨

---

## 📈 성능 종합 비교

### Val Loss 순위 (낮을수록 좋음)

| 순위 | 모델 | Val Loss | 데이터 | Language | 날짜 |
|------|------|----------|--------|----------|------|
| 🥇 1위 | **Left Chunk10** | **0.010** | 250 left | ❌ | 12/18 |
| 🥈 2위 | **Right Chunk10** | **0.013** | 250 right | ❌ | 12/18 |
| 🥉 3위 | **Left Chunk5** | **0.016** | 250 left | ❌ | 12/18 |
| 4위 | **Chunk5** | **0.067** | 500 mixed | ✅ | 12/17 |
| 5위 | **QAT Unified** | **0.267** | 500 mixed | ✅ | 12/23 |
| 6위 | **Chunk10** | **0.284** | 500 mixed | ✅ | 12/17 |

---

## 🔍 핵심 발견사항

### 1. **분리 vs 통합 모델**

**분리 모델 (Left/Right 각각)**:
- ✅ **압도적 성능** (0.010, 0.013)
- ❌ **Language task 무시**
- ❌ **메모리 2배** (12.8GB)
- ❌ **실제 VLA가 아님**

**통합 모델 (Left+Right 혼합)**:
- ❌ **낮은 성능** (0.267)
- ✅ **Language task 포함** (진짜 VLA)
- ✅ **메모리 절반** (6.4GB)
- ✅ **실용성 높음**

### 2. **Chunk Size 영향**

| Chunk Size | Val Loss (통합) | Val Loss (분리) | 경향 |
|------------|-----------------|-----------------|------|
| **Chunk 5** | **0.067** ⭐ | 0.016 | 통합에서 유리 |
| **Chunk 10** | 0.284 | **0.010/0.013** ⭐ | 분리에서 유리 |

**분석**:
- 통합 모델: Chunk 5가 더 안정적 (4배 낮은 loss)
- 분리 모델: Chunk 10이 더 우수 (task가 단순해서)

### 3. **Quantization 시도**

| 시도 | 날짜 | 결과 | 문제점 |
|------|------|------|--------|
| QAT v1 | 12/23 | ❌ 실패 | Vision encoder 경로 불일치 |
| QAT v2 | 12/24 | ❌ 에러 | Wrapper forward 인자 불일치 |

---

## 🎯 현재 상황 요약

### ✅ 사용 가능한 모델 (FP32, 6.4GB)

1. **Left Chunk10** - Val Loss: 0.010 ⭐⭐⭐
2. **Right Chunk10** - Val Loss: 0.013 ⭐⭐⭐
3. **Chunk5 (통합)** - Val Loss: 0.067 ⭐
4. **QAT Unified v1** - Val Loss: 0.267

### ⏳ 진행 중

- **QAT Unified v2** - 에러 수정 필요

### 🚨 해결 필요

1. **QAT wrapper 수정** - `pixel_values` 인자 처리
2. **성능 vs Language task 선택**
   - 성능 우선: 분리 모델 사용
   - Language 우선: 통합 모델 사용

---

## 💡 다음 단계 제안

### Option A: QAT wrapper 수정 후 재학습 (40분)
- wrapper의 forward를 `**kwargs` 지원하도록 수정
- 재학습 실행
- **예상 결과**: Val Loss ~0.27, 크기 ~2-3GB

### Option B: 분리 모델 PTQ 적용 (30분)
- Left/Right 모델을 PTQ로 INT8 변환
- **예상 결과**: Val Loss 유지, 크기 ~3GB × 2

### Option C: Chunk5 (통합) PTQ 적용 (15분) ⭐ 추천
- **즉시 가능**
- Language task 포함
- **예상 결과**: Val Loss ~0.07, 크기 ~2-3GB

---

**현재 시각**: 2025-12-24 01:56 KST  
**다음 작업**: QAT wrapper 수정 필요!
