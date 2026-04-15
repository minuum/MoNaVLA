# Latent Space 분석 계획

**목적**: Frozen vs UnFrozen VLM의 의미 벡터 비교  
**교수님 의견**: Approach 2 (Frozen) 의미 있을 듯 ⭐

---

## 🎯 연구 질문

**"Frozen VLM과 Fine-tuned VLM의 latent space가 어떻게 다른가?"**

### Sub-questions
1. Left vs Right를 어떻게 구분하는가?
2. Frozen이 더 의미있는 representation인가?
3. 코사인 유사도로 측정 가능한가?

---

## 📊 Approach 비교

### Approach 1: UnFrozen VLM + LoRA
**설정**:
- VLM: LoRA로 fine-tune
- Action head: 학습
- Data: **1000-3000 episodes** 필요

**추출**:
- VLM hidden states (last layer)
- Shape: (batch, tokens, 2048)

**장점**:
- Task-specific representation
- End-to-end 학습

**단점**:
- 데이터 많이 필요
- Overfitting 위험

---

### Approach 2: Frozen VLM + Action Head ⭐
**설정**:
- VLM: **Frozen** (pre-trained 유지)
- Action head: 학습
- Data: 500 episodes (현재)

**추출**:
- VLM hidden states (frozen)
- Shape: (batch, tokens, 2048)

**장점**:
- Pre-trained knowledge 유지
- 적은 데이터로 가능
- **교수님 추천!**

**단점**:
- Task-specific adaptation 제한

---

## 🔬 비교 방법

### 1. Latent Vector 추출

**Left episodes**:
```python
# Forward pass
hidden_states = model.vlm(images, text)  # (N, 64, 2048)
left_vectors = hidden_states.mean(dim=1)  # (N, 2048)
```

**Right episodes**:
```python
right_vectors = ...  # (M, 2048)
```

---

### 2. 유사도 측정

#### Cosine Similarity
```python
from scipy.spatial.distance import cosine

# Intra-class (같은 방향끼리)
left_left = 1 - cosine(left_vectors[i], left_vectors[j])
right_right = 1 - cosine(right_vectors[i], right_vectors[j])

# Inter-class (다른 방향끼리)
left_right = 1 - cosine(left_vectors[i], right_vectors[j])

# Separation
separation = (left_left + right_right)/2 - left_right
```

**기대**:
- Frozen: separation < 0.3 (pre-trained만으로)
- UnFrozen: separation > 0.5 (task-specific)

---

#### CKA (Centered Kernel Alignment)
```python
from CKA import cka

# Layer-wise comparison
cka_score = cka(frozen_hidden, unfrozen_hidden)
```

**참고**: Kornblith et al. (2019)

---

#### t-SNE Visualization
```python
from sklearn.manifold import TSNE

# Combine
all_vectors = np.vstack([left_vectors, right_vectors])
labels = ['left'] * len(left_vectors) + ['right'] * len(right_vectors)

# Project to 2D
tsne = TSNE(n_components=2)
projected = tsne.fit_transform(all_vectors)

# Plot
plt.scatter(projected[labels=='left'], c='blue')
plt.scatter(projected[labels=='right'], c='red')
```

---

## 📚 논문 예시

### RT-2 (Brohan et al., 2023)
**"Frozen VLM preserves general knowledge"**
- VLM frozen
- Only action head trained
- Visual representations analyzed

**Key finding**:
- Frozen VLM generalizes better
- Task-specific fine-tuning hurts generalization

---

### OpenVLA (Kim et al., 2024)
**"Pre-trained representations transfer well"**
- Cross-task representation sharing
- Latent space clustering
- Cosine similarity analysis

**Key method**:
- Extract last layer features
- Compute inter/intra-task similarity
- Measure clustering quality

---

### RoboFlamingo (Li et al., 2023)
**"Frozen vision encoder + trainable adapter"**
- Vision encoder frozen
- Language adapter learned
- Representation analysis with CKA

**Key result**:
- Frozen preserves structure
- Adapter creates task-specific routing

---

## 🔧 구현 계획

### Week 1 (다음 주)
1. Hidden states 추출 코드 작성
2. Approach 2 (Frozen) 먼저 분석
3. 코사인 유사도 계산

### Week 2
1. Approach 1 (UnFrozen) 데이터 수집
2. 동일 방법으로 분석
3. 두 approach 비교

### Week 3
1. CKA, t-SNE 추가 분석
2. 논문 예시와 비교
3. 결과 정리

---

## 📊 예상 결과

### Frozen VLM (Approach 2)
**Hypothesis**:
- Moderate separation (0.2-0.3)
- Pre-trained visual features 활용
- General한 representation

**의미**:
- 적은 데이터로 가능 ✅
- Generalization 좋음 ✅
- **교수님 추천 이유!**

---

### UnFrozen VLM (Approach 1)
**Hypothesis**:
- High separation (0.5-0.7)
- Task-specific adaptation
- Specialized representation

**의미**:
- 데이터 많이 필요 ⚠️
- Overfitting 위험 ⚠️
- Generalization 의문

---

## 💡 교수님께 보고할 Points

### Frozen VLM의 장점
1. **Efficient**: 적은 데이터 (500 episodes)
2. **Generalizable**: Pre-trained knowledge 유지
3. **Analyzable**: Latent space 의미 명확

### 분석 방법
1. **코사인 유사도**: 간단하고 직관적
2. **CKA**: Layer-wise 비교
3. **t-SNE**: 시각화

### 논문 근거
- RT-2: Frozen > Fine-tuned for generalization
- OpenVLA: Cross-task transfer
- RoboFlamingo: Frozen + adapter

---

**다음 단계**: Frozen VLM hidden states 추출 및 분석  
**예상 소요**: 2-3주  
**결과물**: 논문 submission
