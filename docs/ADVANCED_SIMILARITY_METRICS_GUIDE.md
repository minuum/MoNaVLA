# 고급 Similarity 메트릭 가이드

## 📊 추가된 메트릭 개요

기존 기본 메트릭(Cosine, Euclidean, Pearson, MSE)에 더해, 논문에서 검증된 **8가지 고급 메트릭**을 추가했습니다.

---

## 🔬 고급 메트릭 목록

### 1. CKA (Centered Kernel Alignment)
**논문**: Kornblith et al., "Similarity of Neural Network Representations Revisited" (ICML 2019)

**개념**: 
- 두 representation의 kernel matrix 유사도 측정
- HSIC (Hilbert-Schmidt Independence Criterion) 기반

**장점**:
- ✅ Orthogonal transformation에 invariant (뉴런 순서 무관)
- ✅ Isotropic scaling에 invariant
- ✅ 다른 initialization에도 robust

**해석**:
- **Linear CKA**: 선형 관계 측정
- **RBF CKA**: 비선형 관계 측정
- **범위**: 0~1 (1이 perfect match)
- **기준**: > 0.8 매우 유사, 0.5~0.8 중간, < 0.5 낮음

---

### 2. SVCCA (Singular Vector CCA)
**논문**: Raghu et al., "SVCCA: Singular Vector Canonical Correlation Analysis" (NeurIPS 2017)

**개념**:
- SVD로 차원 축소 + CCA로 correlation 계산
- 중요한 subspace만 비교

**장점**:
- ✅ Affine transformation에 invariant
- ✅ 노이즈에 robust
- ✅ 중요한 feature subspace 발견

**해석**:
- **SVCCA Similarity**: 1 - distance
- **범위**: 0~1 (1이 perfect alignment)
- **기준**: > 0.7 높은 정렬, 0.4~0.7 중간, < 0.4 낮음

---

### 3. Procrustes Distance
**논문**: Ding et al., "Grounding Representation Similarity" (NeurIPS 2021)

**개념**:
- Optimal orthogonal alignment (회전, 반사) 후 거리 측정
- Shape metric (기하학적 유사도)

**장점**:
- ✅ 기하학적으로 직관적
- ✅ Benchmark에서 일관된 성능
- ✅ 계산 효율적

**해석**:
- **Procrustes Similarity**: 1 - distance
- **범위**: 0~1 (1이 perfect shape match)
- **기준**: > 0.8 매우 유사, 0.5~0.8 중간, < 0.5 다른 shape

---

### 4. RSA (Representational Similarity Analysis)
**논문**: Kriegeskorte et al., "Representational similarity analysis" (2008)

**개념**:
- RDM (Representational Dissimilarity Matrix) 간 correlation
- 신경과학에서 검증됨

**장점**:
- ✅ Model-agnostic
- ✅ Interpretable
- ✅ 구조적 유사도 측정

**해석**:
- **RSA Correlation**: RDM 간 Spearman correlation
- **범위**: -1~1 (1이 perfect structural match)
- **기준**: > 0.7 높은 구조 유사도, 0.4~0.7 중간, < 0.4 낮음

**2가지 버전**:
- **Correlation-based**: 패턴 유사도
- **Euclidean-based**: 거리 유사도

---

### 5. MNN (Mutual Nearest Neighbors)
**개념**:
- 두 space에서 서로 가까운 샘플 개수
- Local structure 비교

**장점**:
- ✅ Local similarity 측정
- ✅ Outlier에 robust
- ✅ 직관적 해석

**해석**:
- **MNN Score (k=5)**: 5-NN 중 mutual neighbors 비율
- **범위**: 0~1 (1이 perfect local match)
- **기준**: > 0.7 높은 local 유사도, 0.4~0.7 중간, < 0.4 낮음

---

### 6. Linear Regression R²
**개념**:
- Y를 X로 선형 예측 가능 정도
- Predictability metric

**장점**:
- ✅ 예측 가능성 측정
- ✅ Asymmetric (방향성 있음)
- ✅ 해석 용이

**해석**:
- **R² Score**: 설명 가능한 분산 비율
- **범위**: 0~1 (1이 perfect prediction)
- **기준**: > 0.8 높은 예측력, 0.5~0.8 중간, < 0.5 낮음

---

## 📈 메트릭 비교표

| 메트릭 | 측정 대상 | Invariance | 범위 | 해석 | 계산 복잡도 |
|:---|:---|:---|:---|:---|:---|
| **CKA (Linear)** | 선형 관계 | Orthogonal, Scaling | 0~1 | 높을수록 유사 | O(n²) |
| **CKA (RBF)** | 비선형 관계 | Orthogonal, Scaling | 0~1 | 높을수록 유사 | O(n²) |
| **SVCCA** | Subspace 정렬 | Affine | 0~1 | 높을수록 정렬 | O(n³) |
| **Procrustes** | Shape 유사도 | Orthogonal | 0~1 | 높을수록 유사 | O(n²) |
| **RSA (Corr)** | 구조 유사도 | - | -1~1 | 높을수록 유사 | O(n²) |
| **RSA (Eucl)** | 거리 구조 | - | -1~1 | 높을수록 유사 | O(n²) |
| **MNN** | Local 구조 | - | 0~1 | 높을수록 유사 | O(n² log n) |
| **Linear R²** | 예측 가능성 | - | 0~1 | 높을수록 예측 가능 | O(n²) |

---

## 🎯 어떤 메트릭을 사용할까?

### 상황별 권장 메트릭

#### 1. 전체적인 유사도 (Overall Similarity)
```
권장: CKA (Linear) + Procrustes
이유: 
  - CKA: 통계적 의존성
  - Procrustes: 기하학적 유사도
  - 두 관점 모두 중요
```

#### 2. 구조적 유사도 (Structural Similarity)
```
권장: RSA (Correlation)
이유:
  - RDM 비교로 구조 파악
  - 신경과학에서 검증됨
  - Interpretable
```

#### 3. 중요한 Subspace 비교
```
권장: SVCCA
이유:
  - 노이즈 제거
  - 중요한 차원만 비교
  - 고차원에 효과적
```

#### 4. Local Structure 비교
```
권장: MNN
이유:
  - 샘플 level 유사도
  - Outlier 탐지 가능
  - 직관적 해석
```

---

## 💡 Frozen vs LoRA 비교 시 기대 결과

### 가설

#### Frozen VLM (Case 3)
```
Context Vector 특성:
  - Pretrain knowledge 보존
  - 안정적 representation
  - Mobile task에 일부만 adapt
```

#### LoRA VLM (Case 4)
```
Context Vector 특성:
  - Mobile task에 fine-tuned
  - Task-specific adaptation
  - 일부 feature shifted
```

### 예상 메트릭 결과

```
┌─────────────────────────────────────────────────┐
│ 메트릭                 예상 범위    의미         │
├─────────────────────────────────────────────────┤
│ CKA (Linear)          0.7 ~ 0.9    높은 선형 유사도    │
│ CKA (RBF)             0.8 ~ 0.95   높은 비선형 유사도  │
│ SVCCA Similarity      0.6 ~ 0.8    중간~높은 subspace │
│ Procrustes Similarity 0.7 ~ 0.85   유사한 shape        │
│ RSA (Correlation)     0.5 ~ 0.7    중간 구조 유사도    │
│ MNN Score             0.4 ~ 0.6    중간 local 유사도   │
│ Linear R²             0.8 ~ 0.95   높은 예측력         │
└─────────────────────────────────────────────────┘
```

**해석**:
- **CKA 높음** → 전반적으로 유사한 representation
- **SVCCA 중간** → 일부 subspace는 달라짐 (task adaptation)
- **RSA 중간** → 구조는 유지하되 세부적으로 변화
- **MNN 중간** → Local structure 일부 변화

**결론**:
- Frozen과 LoRA가 **전반적으로 유사**하지만
- **세부적인 차이 존재** (LoRA adaptation 효과)
- **교수님 의견** ("Frozen이 의미 있을 것") 지지

---

## 🔍 실제 사용 예시

### 기본 사용
```python
from advanced_similarity_metrics import compute_all_metrics, interpret_metrics

# Context vectors (numpy or torch)
context_frozen = ...  # Shape: (N, T, tokens, features)
context_lora = ...

# Compute all metrics
metrics = compute_all_metrics(context_frozen, context_lora, "Frozen", "LoRA")

# Interpret results
interpretation = interpret_metrics(metrics)
print(interpretation)
```

### 출력 예시
```
고급 Similarity 메트릭 계산: Frozen vs LoRA
======================================================================
Shape: X=(50, 26214400), Y=(50, 26214400)

[1/8] Computing CKA (Linear)...
[2/8] Computing CKA (RBF)...
...

✅ 모든 메트릭 계산 완료!

📊 고급 메트릭 결과:
   CKA (Linear):         0.852341
   CKA (RBF):            0.913457
   SVCCA Similarity:     0.678912
   Procrustes Similarity: 0.789234
   RSA (Correlation):    0.612345
   RSA (Euclidean):      0.598765
   MNN Score (k=5):      0.523456
   Linear Reg R²:        0.891234

💡 메트릭 해석:
   ✅ CKA (Linear): 매우 유사 (>0.8) - 선형 관계 강함
   ⚠️ SVCCA: 중간 subspace 정렬 (0.4~0.7)
   ⚠️ Procrustes: 중간 shape 유사도 (0.5~0.8)
   ⚠️ RSA: 중간 구조적 유사도 (0.4~0.7)
```

---

## 📚 참고 문헌

1. **CKA**: Kornblith et al., "Similarity of Neural Network Representations Revisited" (ICML 2019)
2. **SVCCA**: Raghu et al., "SVCCA: Singular Vector Canonical Correlation Analysis" (NeurIPS 2017)
3. **Procrustes**: Ding et al., "Grounding Representation Similarity" (NeurIPS 2021)
4. **RSA**: Kriegeskorte et al., "Representational similarity analysis" (Frontiers in Systems Neuroscience, 2008)

---

## ✅ 사용 가능 확인

```bash
# Test 실행
cd /home/billy/25-1kp/vla
python3 scripts/advanced_similarity_metrics.py

# 출력에서 확인:
# ✅ 모든 메트릭 계산 완료!
```

**통합 스크립트**: `scripts/compare_frozen_vs_lora.py`에 자동으로 통합됨!
