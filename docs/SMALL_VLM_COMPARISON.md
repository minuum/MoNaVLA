# VLA-Suitable Small VLMs 비교 분석

## 📊 현재 상황

### 현재 사용 중: Kosmos-2
- **Parameters**: 1.6B
- **메모리** (Frozen): ~22-23 GB ✅
- **메모리** (LoRA): ~25-26 GB ❌ (A5000로 불가능)
- **Vision**: ViT-L/14 (CLIP)
- **Language**: Decoder-only Transformer

---

## 🔍 VLA 논문에서 사용된 VLM들

### 1. **OpenVLA** (2024)
- **Base VLM**: Prismatic VLM (PaliGemma-based)
- **Size**: 7B parameters
- **메모리**: ~30 GB (Frozen), ~35 GB (LoRA)
- **결론**: ❌ 더 큼 (불가능)

### 2. **RT-2** (Google, 2023)
- **Base VLM**: PaLI-X, PaLM-E
- **Size**: 5B - 55B parameters
- **결론**: ❌ 훨씬 큼 (불가능)

### 3. **RoboFlamingo** (2023)
- **Base VLM**: CLIP + Flamingo
- **Size**: 3B parameters
- **메모리**: ~15 GB (Frozen), ~20 GB (LoRA 예상)
- **결론**: ⚠️ 여전히 큼

### 4. **Octo** (2024)
- **Base VLM**: ViT + Transformer
- **Size**: ~93M parameters (Vision-only!)
- **메모리**: ~5 GB
- **결론**: ⚠️ Language 기능 없음

---

## ✅ 작은 VLM 후보들

### 🥇 **1. CLIP + GPT-2 Small** (권장)

**구조**:
```
Vision: CLIP ViT-B/16 (86M params)
Language: GPT-2 Small (117M params)
Total: ~200M parameters
```

**메모리 예상**:
- Frozen: ~5 GB
- LoRA (rank=16): ~8 GB ✅ **가능!**

**장점**:
- ✅ A5000에서 LoRA 가능
- ✅ 검증된 구조 (CLIP은 VLA에서 많이 사용)
- ✅ Pre-trained weights 사용 가능

**단점**:
- ⚠️ 작은 모델 → 성능 저하 가능
- ⚠️ 직접 결합 필요

**VLA 사례**: CLIP은 거의 모든 VLA에서 vision encoder로 사용됨

---

### 🥈 **2. MiniGPT-4 (7B base) → MiniGPT-v2**

**MiniGPT-v2 구조**:
```
Vision: EVA-CLIP ViT-g (1B params)
Language: LLaMA-2 7B (7B params)
Total: 8B parameters
```

❌ **결론**: 여전히 큼 (불가능)

---

### 🥉 **3. LLaVA-Phi (Smaller variant)**

**구조**:
```
Vision: CLIP ViT-L/14 (304M params)
Language: Phi-2 (2.7B params)
Total: ~3B parameters
```

**메모리 예상**:
- Frozen: ~12 GB
- LoRA (rank=16): ~18 GB ✅ **가능!**

**장점**:
- ✅ A5000에서 LoRA 가능
- ✅ 검증된 instruction-following
- ✅ Pre-trained 사용 가능

**단점**:
- ⚠️ VLA에서 직접 사용 사례 없음
- ⚠️ Kosmos-2보다 크지만 성능은 비슷할 수 있음

---

### 🏆 **4. PaliGemma-3B** (Google, 2024)

**구조**:
```
Vision: SigLIP-So400m (400M params)
Language: Gemma-2B (2B params)  
Total: ~2.4B parameters
```

**메모리 예상**:
- Frozen: ~10 GB
- LoRA (rank=16): ~15 GB ✅ **가능!**

**장점**:
- ✅ A5000에서 LoRA 가능
- ✅ Google의 최신 VLM
- ✅ Instruction-following 성능 좋음
- ✅ OpenVLA의 base model (7B variant)

**단점**:
- ⚠️ VLA에서 3B variant 사례 없음 (7B는 있음)

---

### 🎯 **5. BLIP-2 (Flan-T5 XL variant)**

**구조**:
```
Vision: EVA-CLIP ViT-g (1B params)
Language: Flan-T5-XL (3B params)
Total: ~4B parameters
```

**메모리 예상**:
- Frozen: ~16 GB
- LoRA (rank=16): ~22 GB ✅ **가능!**

**장점**:
- ✅ A5000에서 LoRA 가능
- ✅ 검증된 VLM
- ✅ Encoder-decoder 구조 (instruction following 강점)

**단점**:
- ⚠️ VLA 사례 적음

---

## 📊 **비교표**

| Model | Total Params | Memory (Frozen) | Memory (LoRA) | A5000 가능 | VLA 사용 | 추천도 |
|-------|-------------|-----------------|---------------|-----------|----------|--------|
| **현재: Kosmos-2** | 1.6B | 23 GB | 25 GB | ❌ (LoRA 불가) | ✅ RoboKosMos | - |
| **CLIP + GPT-2 Small** | 200M | 5 GB | 8 GB | ✅✅ | ⚠️ (CLIP만) | ⭐⭐⭐⭐⭐ |
| **PaliGemma-3B** | 2.4B | 10 GB | 15 GB | ✅ | ⚠️ (7B만) | ⭐⭐⭐⭐ |
| **LLaVA-Phi** | 3B | 12 GB | 18 GB | ✅ | ❌ | ⭐⭐⭐ |
| **BLIP-2 (T5-XL)** | 4B | 16 GB | 22 GB | ⚠️ (경계) | ❌ | ⭐⭐ |
| OpenVLA | 7B | 30 GB | 35 GB | ❌ | ✅ | ❌ (큼) |
| RT-2 | 5B+ | 25 GB+ | 30 GB+ | ❌ | ✅ | ❌ (큼) |

---

## 🎯 **권장 옵션**

### ✅ **옵션 1: CLIP + GPT-2 Small** (가장 안전)

**이유**:
- 가장 작음 (200M) → LoRA 여유롭게 가능
- CLIP은 VLA에서 검증됨
- 빠른 학습 속도
- 실험하기 좋음

**구현**:
```python
Vision: clip-vit-base-patch16 (86M)
Language: gpt2 (117M)
```

**예상 성능**: Kosmos-2보다 낮을 수 있지만, LoRA로 instruction grounding 가능

---

### ✅ **옵션 2: PaliGemma-3B** (성능과 메모리 균형)

**이유**:
- OpenVLA의 작은 버전
- Google의 검증된 VLM
- A5000에서 LoRA 가능
- Instruction-following 강점

**구현**:
```python
from transformers import PaliGemmaForConditionalGeneration
model = PaliGemmaForConditionalGeneration.from_pretrained("google/paligemma-3b-pt-224")
```

**예상 성능**: Kosmos-2와 비슷하거나 나을 수 있음

---

### ⚠️ **옵션 3: LLaVA-Phi** (대안)

**이유**:
- Instruction-following 좋음
- A5000에서 가능
- 다양한 variant 있음

**단점**: VLA 검증 부족

---

## 💡 **추천 전략**

### 🚀 **빠른 검증 (1주)**
1. **CLIP + GPT-2 Small** 사용
2. LoRA fine-tuning 테스트
3. Instruction grounding 확인
4. 성공 시 → 논문 작성
5. 실패 시 → PaliGemma-3B 시도

### 🎯 **고품질 (2-3주)**
1. **PaliGemma-3B** 직접 시작
2. OpenVLA와 비교 가능
3. 더 나은 성능 기대

---

## 📋 **구현 난이도**

| Model | 구현 난이도 | HuggingFace 지원 | RoboVLMs 호환 |
|-------|------------|------------------|---------------|
| CLIP + GPT-2 | ⭐⭐ (쉬움) | ✅ | ⚠️ (수정 필요) |
| PaliGemma-3B | ⭐⭐⭐ (보통) | ✅ | ⚠️ (수정 필요) |
| LLaVA-Phi | ⭐⭐⭐ (보통) | ✅ | ⚠️ (수정 필요) |

---

## 🎯 **최종 권장**

### 상황에 따른 선택:

#### 1️⃣ **빠르게 검증하고 싶다** → CLIP + GPT-2 Small
- 가장 안전
- 구현 쉬움
- LoRA 확실히 가능

#### 2️⃣ **좋은 성능 원한다** → PaliGemma-3B  
- OpenVLA family
- 검증된 성능
- A5000에서 가능

#### 3️⃣ **안전하게 가고 싶다** → 일단 Frozen VLM으로 Epoch 더 학습
- 현재 Kosmos-2 유지
- Epoch 7-10까지 학습
- 혹시나 개선될 수 있음

---

**Updated**: 2026-01-07 10:19
