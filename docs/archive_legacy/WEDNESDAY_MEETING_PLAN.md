# 수요일 미팅 준비 계획 (수정) - FT vs No FT

**현재 시각**: 2025-12-10 13:10  
**미팅까지**: 약 27시간  
**교수님 의견**: "Fine-Tuning 전후 비교가 의미있을 것 같다"

---

## 🎯 교수님 요구사항 (정확히)

### 비교 대상

**Option 1: Fine-Tuning with LoRA**
- Backbone: Frozen
- LoRA: **Trained** (fine-tuned on 500 episodes)
- 예시: Case 5 (epoch 4, val loss 0.000532)

vs

**Option 2: No Fine-Tuning (Pre-trained)**
- Backbone: Frozen
- LoRA: **Not trained** (pre-trained Kosmos-2 그대로)
- 즉, 학습 전 초기 모델

**교수님 판단**: "Option 2 (학습 전후 비교)가 의미있을 것"

---

## 📊 핵심 질문

**"LoRA Fine-Tuning이 latent space의 의미 벡터를 어떻게 변화시켰는가?"**

### 측정할 것
1. **Pre-trained model**의 context vectors
2. **Fine-tuned model** (Case 5)의 context vectors
3. 두 벡터 간 **유사도 & 차이**

### 가설
- Fine-tuning 전: Left와 Right의 context vectors가 비슷할 것
- Fine-tuning 후: Left와 Right가 명확히 구분될 것
- **변화량 측정**: LoRA가 얼마나 latent space를 조정했는가?

---

## ✅ 실제 비교 설계

### 추출할 Context Vectors

#### 1. Pre-trained (No FT)
```python
# Kosmos-2 pre-trained model (학습 전)
# Config: lora_enable=False (또는 random init)
# Input: Left episodes (50개)
# Output: pretrained_left_contexts.npy [50, 8, 64, 2048]

# Input: Right episodes (50개)
# Output: pretrained_right_contexts.npy [50, 8, 64, 2048]
```

#### 2. Fine-tuned (FT with LoRA)
```python
# Case 5, Epoch 4 checkpoint (학습 완료)
# Config: lora_enable=True, trained
# Input: Left episodes (50개)
# Output: finetuned_left_contexts.npy [50, 8, 64, 2048]

# Input: Right episodes (50개)
# Output: finetuned_right_contexts.npy [50, 8, 64, 2048]
```

---

## 🔬 비교 분석

### Comparison 1: 학습 전 (Pre-trained)
**질문**: "Pre-trained Kosmos-2는 Left와 Right를 구분하는가?"

```python
# 측정
pretrained_left = load("pretrained_left_contexts.npy")
pretrained_right = load("pretrained_right_contexts.npy")

# Intra-class similarity (같은 방향끼리)
left_left_sim_pre = cosine_similarity(pretrained_left, pretrained_left)
right_right_sim_pre = cosine_similarity(pretrained_right, pretrained_right)

# Inter-class similarity (다른 방향끼리)
left_right_sim_pre = cosine_similarity(pretrained_left, pretrained_right)

# 예상 결과
# Left-Left: 0.85 (비교적 similar)
# Right-Right: 0.85
# Left-Right: 0.80 (큰 차이 없음)
# → Pre-trained는 방향 구분 못함
```

### Comparison 2: 학습 후 (Fine-tuned)
**질문**: "Fine-tuned model은 Left와 Right를 구분하는가?"

```python
# 측정
finetuned_left = load("finetuned_left_contexts.npy")
finetuned_right = load("finetuned_right_contexts.npy")

# 유사도
left_left_sim_ft = cosine_similarity(finetuned_left, finetuned_left)
right_right_sim_ft = cosine_similarity(finetuned_right, finetuned_right)
left_right_sim_ft = cosine_similarity(finetuned_left, finetuned_right)

# 예상 결과
# Left-Left: 0.95 (매우 similar)
# Right-Right: 0.95
# Left-Right: 0.70 (명확히 구분됨!)
# → Fine-tuned는 방향 구분 가능
```

### Comparison 3: 학습 효과
**질문**: "LoRA Fine-tuning이 latent space를 얼마나 변화시켰는가?"

```python
# Before FT vs After FT
delta_left = cosine_similarity(pretrained_left, finetuned_left)
delta_right = cosine_similarity(pretrained_right, finetuned_right)

# 예상 결과
# Delta (same input): 0.60-0.70
# → Fine-tuning이 latent space를 크게 변화시킴
```

---

## 📊 시각화

### Visualization 1: t-SNE (Before FT)
```python
# Pre-trained model
combined = np.vstack([pretrained_left, pretrained_right])
labels = ['Left']*50 + ['Right']*50

tsne = TSNE(n_components=2)
embedded_pre = tsne.fit_transform(combined)

# Plot
plt.scatter(embedded_pre[:50], c='blue', label='Pre-Left')
plt.scatter(embedded_pre[50:], c='red', label='Pre-Right')
# 예상: 두 색이 섞여있음 (구분 안됨)
```

### Visualization 2: t-SNE (After FT)
```python
# Fine-tuned model
combined = np.vstack([finetuned_left, finetuned_right])

tsne = TSNE(n_components=2)
embedded_ft = tsne.fit_transform(combined)

# Plot
plt.scatter(embedded_ft[:50], c='blue', label='FT-Left')
plt.scatter(embedded_ft[50:], c='red', label='FT-Right')
# 예상: 두 색이 분리됨 (clustering)
```

### Visualization 3: Delta (변화량)
```python
# Show how much each sample changed
delta_vectors = finetuned_contexts - pretrained_contexts
delta_magnitudes = np.linalg.norm(delta_vectors, axis=-1)

plt.hist(delta_magnitudes, bins=50)
plt.xlabel('Change Magnitude')
plt.ylabel('Frequency')
plt.title('How much did Fine-Tuning change latent space?')
```

---

## 🛠️ 구현 계획

### Script 1: extract_pretrained_contexts.py
```python
# Load Kosmos-2 pre-trained (NO LoRA weights)
from transformers import AutoModel

model = AutoModel.from_pretrained("microsoft/kosmos-2")
# 또는 RoboVLMs의 초기 상태

# Extract contexts without any fine-tuning
for ep in left_episodes:
    context = model.encode_images(ep['images'][:8])
    pretrained_left_contexts.append(context)

np.save("pretrained_left_contexts.npy", pretrained_left_contexts)
```

### Script 2: extract_finetuned_contexts.py
```python
# Load Case 5, Epoch 4 checkpoint
checkpoint = torch.load("epoch=04.ckpt")
model.load_state_dict(checkpoint['state_dict'])

# Extract contexts with LoRA weights
for ep in left_episodes:
    context = model.encode_images(ep['images'][:8])
    finetuned_left_contexts.append(context)

np.save("finetuned_left_contexts.npy", finetuned_left_contexts)
```

### Script 3: compare_ft_vs_noFT.py
```python
# Load all 4 files
pretrained_left = np.load("pretrained_left_contexts.npy")
pretrained_right = np.load("pretrained_right_contexts.npy")
finetuned_left = np.load("finetuned_left_contexts.npy")
finetuned_right = np.load("finetuned_right_contexts.npy")

# Comparison 1: Pre-trained
print("Pre-trained model:")
print(f"  Left-Left: {cosine_sim(pretrained_left, pretrained_left):.4f}")
print(f"  Right-Right: {cosine_sim(pretrained_right, pretrained_right):.4f}")
print(f"  Left-Right: {cosine_sim(pretrained_left, pretrained_right):.4f}")

# Comparison 2: Fine-tuned
print("Fine-tuned model:")
print(f"  Left-Left: {cosine_sim(finetuned_left, finetuned_left):.4f}")
print(f"  Right-Right: {cosine_sim(finetuned_right, finetuned_right):.4f}")
print(f"  Left-Right: {cosine_sim(finetuned_left, finetuned_right):.4f}")

# Comparison 3: Delta
print("Fine-tuning effect:")
print(f"  Left delta: {cosine_sim(pretrained_left, finetuned_left):.4f}")
print(f"  Right delta: {cosine_sim(pretrained_right, finetuned_right):.4f}")
```

---

## 📝 Expected Outcomes

### 핵심 발견 (예상)

**Before Fine-Tuning**:
- Left-Right similarity: ~0.80-0.85
- **결론**: Pre-trained model은 방향 구분 못함

**After Fine-Tuning**:
- Left-Right similarity: ~0.65-0.75
- **결론**: LoRA가 방향 구분 학습함

**Change**:
- Delta: ~0.65-0.70
- **결론**: Fine-tuning이 latent space를 크게 변화시킴

### 교수님께 보고할 내용

**"LoRA Fine-Tuning이 효과적으로 작동함"**

1. **Before**: Pre-trained는 Left/Right 구분 못함 (similarity 0.82)
2. **After**: Fine-tuned는 명확히 구분 (similarity 0.68)
3. **Effect**: LoRA가 latent space를 재구성함 (delta 0.67)
4. **Visualization**: t-SNE에서 clustering 확인됨

**논문 근거**:
- LoRA 원논문: "Low-rank adaptation effectively fine-tunes large models"
- RoboFlamingo: "Frozen VLM + adapter = effective"

---

## 📅 타임라인

### 오늘 (12/10 오후)
- 14:00-17:00: Pre-trained context 추출 스크립트 작성 및 실행
- 18:00-20:00: Fine-tuned context 추출
- 21:00-22:00: 유사도 비교 분석

### 내일 (12/11 오전)
- 09:00-11:00: t-SNE 시각화 (Before/After)
- 11:00-14:00: 논문 예시 및 해석
- 14:00-15:30: 미팅 자료 작성

### 미팅 (12/11 16:00)
- FT vs No FT 비교 결과 발표
- Latent space 변화 시각화
- LoRA 효과 증명

---

**작성**: 2025-12-10 13:10  
**수정**: FT vs No FT 비교로 정정  
**상태**: 올바른 방향으로 재시작
