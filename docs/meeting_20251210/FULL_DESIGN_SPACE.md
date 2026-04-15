# 전체 실험 Design Space

**작성**: 2025-12-10 16:01

---

## 변수 정의

### 1. VLM Training
- **Frozen + LoRA**: VLM backbone frozen, LoRA만 학습 (우리 접근)
- **Fine-tuned**: VLM 전체 fine-tune (향후 비교용)

### 2. Data
- **L+R**: Left 250 + Right 250 = 500 episodes
- **R only**: Right 250 episodes
- **L only**: Left 250 episodes (미수행)

### 3. Chunk (fwd_pred_next_n)
- **Chunk=1**: No chunk (reactive)
- **Chunk=10**: RoboVLMs 기본값

### 4. Strategy
- **Baseline**: 기본
- **Abs**: Absolute action (방향 제거)
- **Aug**: Data augmentation (mirroring)
- **Aug+Abs**: 둘 다

---

## 전체 케이스 조합 (완료 + 미완료)

| ID | VLM | Data | Chunk | Strategy | 상태 | Val Loss | 비고 |
|:---:|:---|:---:|:---:|:---|:---:|---:|:---|
| **1** | Frozen+LoRA | L+R (500) | 10 | Baseline | ✅ 완료 | 0.027 | Baseline |
| **2** | Frozen+LoRA | L+R (500) | 10 | Fixed | ✅ 완료 | 0.048 | Xavier init |
| **3** | Frozen+LoRA | L+R (500) | 10 | Aug+Abs | ✅ 완료 | 0.050 | - |
| **4** | Frozen+LoRA | R (250) | 10 | Baseline | ✅ 완료 | 0.016 | Data 비교 |
| **5** 🏆 | Frozen+LoRA | L+R (500) | **1** | Baseline | ✅ 완료 | **0.000532** | **Best!** |
| **6** | Frozen+LoRA | L+R (500) | 10 | Abs | ❌ 미수행 | - | - |
| **7** | Frozen+LoRA | L+R (500) | 1 | Fixed | ❌ 미수행 | - | 낮은 우선순위 |
| **8** | Frozen+LoRA | L+R (500) | 1 | Abs | ✅ 완료 | 0.00243 | 2등 |
| **9** | Frozen+LoRA | L+R (500) | 1 | Aug+Abs | ✅ 완료 | 0.004 | 3등 |
| **10** | Frozen+LoRA | R (250) | 10 | Fixed | ❌ 미수행 | - | - |
| **11** | Frozen+LoRA | R (250) | 10 | Abs | ❌ 미수행 | - | - |
| **12** | Frozen+LoRA | R (250) | 10 | Aug+Abs | ❌ 미수행 | - | - |
| **13** | Frozen+LoRA | R (250) | 1 | Baseline | ❌ 미수행 | - | 참고용 |
| **14** | Frozen+LoRA | R (250) | 1 | Fixed | ❌ 미수행 | - | - |
| **15** | Frozen+LoRA | R (250) | 1 | Abs | ❌ 미수행 | - | - |
| **16** | Frozen+LoRA | R (250) | 1 | Aug+Abs | ❌ 미수행 | - | - |

**완료**: 7/16 (43.75%)

---

## 향후 비교용 (Fine-tuned VLM)

| ID | VLM | Data | Chunk | Strategy | 상태 | 예상 |
|:---:|:---|:---:|:---:|:---|:---:|:---|
| **FT-1** | Fine-tuned | L+R (1000-3000) | 1 | Baseline | 계획 | Latent space 비교 |
| **FT-2** | Fine-tuned | L+R (1000-3000) | 10 | Baseline | 계획 | - |

---

## 핵심 발견 (완료된 케이스 기반)

### 1. Chunk 효과 (최우선 변수!)
- **Chunk=1**: 0.000532 (Best)
- **Chunk=10**: 0.027 이상
- **개선**: 98% ⭐⭐⭐

### 2. Data 효과
- **L+R (500)**: 0.000532
- **R only (250)**: 0.016
- **차이**: 30배

### 3. Strategy 효과
- **Baseline**: 0.000532 (Best)
- **Abs**: 0.00243 (4.6배 worse)
- **Aug+Abs**: 0.004 (7.5배 worse)

---

## 미수행 케이스 예상

### High Priority (추천)

**Case 13: R only + Chunk=1**
- 예상: Case 5보다 worse (데이터 부족)
- 목적: Data diversity 효과 정량화

**FT-1: Fine-tuned VLM + Large Data**
- 예상: Separation 0.5-0.7 (vs Frozen 0.3-0.4)
- 목적: Latent space 비교 (교수님 추천)

### Low Priority

**Case 6, 11, 12**: Chunk=10 조합
- Chunk=10이 이미 worse로 확인됨
- 우선순위 낮음
