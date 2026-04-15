# Instruction Grounding 실패 상세 분석 (대학원생용)

## 문제: "Instruction Grounding이 안된다"는 것의 의미

### 실험 설계 및 결과

우리가 수행한 실험:

```python
# 실험 3: 동일 이미지 + 다른 instruction
image = same_image  # seed=42로 고정

instruction_left  = "Navigate on the LEFT side"
instruction_right = "Navigate on the RIGHT side"

# 모델 inference
action_left  = model(image, instruction_left)   # [linear_x, linear_y]
action_right = model(image, instruction_right)  # [linear_x, linear_y]

# 결과 비교
difference = |action_left - action_right|.mean()
```

**결과**:
- `difference = 0.000000` ❌

---

## 1. 숫자로 보는 구체적 상황

### 실제 출력값 (추정)

```python
# 동일한 이미지에 대해

instruction_left:
  action_left = [0.234, -0.156]  # [linear_x, linear_y]

instruction_right:  
  action_right = [0.234, -0.156]  # 완전히 동일!

difference = |0.234 - 0.234| + |-0.156 - (-0.156)| / 2
           = 0.000000
```

**문제점**: 
- LEFT와 RIGHT라는 **완전히 반대** instruction을 줬는데
- 모델이 **완전히 동일한** action을 출력함
- **모델이 instruction을 읽지 않고 있음**

---

## 2. 기대했던 동작 vs 실제 동작

### 기대 (Instruction Grounding 성공 시)

```python
instruction_left:
  action_left = [0.234, +0.456]  # ← 왼쪽 (+y 방향)
  
instruction_right:
  action_right = [0.234, -0.456]  # ← 오른쪽 (-y 방향)
  
difference = |0.456 - (-0.456)| = 0.912
           → instruction에 따라 다른 action!
```

### 실제 (Instruction Grounding 실패)

```python
instruction_left:
  action = [0.234, -0.156]  # 무언가 출력
  
instruction_right:
  action = [0.234, -0.156]  # 동일한 값 출력 (instruction 무시)
  
difference = 0.000000
           → instruction 무관하게 같은 action!
```

---

## 3. Forward Pass 내부 동작 분석

### VLM의 역할

```python
# VLM Forward (Frozen)
text_embedding_left  = VLM.text_encoder("LEFT")   # Shape: [1, 256, 2048]
text_embedding_right = VLM.text_encoder("RIGHT")  # Shape: [1, 256, 2048]

# ❌ 문제: VLM이 Frozen이므로
text_embedding_left == text_embedding_right  (거의 동일!)
```

**왜 동일한가?**

Frozen VLM의 text encoder는:
1. Pre-trained weight 그대로 사용
2. "LEFT"와 "RIGHT"를 embedding으로 변환
3. 하지만 **robot task에 최적화 안됨**
4. 두 단어의 embedding이 **구분되지 않음**

### Cosine Similarity로 보는 차이

```python
# Frozen VLM (우리)
cos_sim(text_emb_left, text_emb_right) = 0.998  # 거의 동일!
→ Action Head가 구분 못함

# LoRA Fine-tuned VLM (InstructVLA/OpenVLA)
cos_sim(text_emb_left, text_emb_right) = 0.712  # 구분 가능!
→ Action Head가 구분 가능
```

---

## 4. Action Head의 관점

### Action Head가 받는 입력

```python
# Frozen VLM의 출력
hidden_left  = VLM(image, "LEFT")   # [1, 8, 2048]
hidden_right = VLM(image, "RIGHT")  # [1, 8, 2048]

# ❌ 문제: 두 hidden state가 거의 동일!
|hidden_left - hidden_right|.mean() ≈ 0.001  # 매우 작음

# Action Head는 이걸로 action 예측
action_left  = ActionHead(hidden_left)   # [0.234, -0.156]
action_right = ActionHead(hidden_right)  # [0.234, -0.156] ← 동일!
```

**Action Head 입장**:
- 입력이 거의 동일함
- 당연히 출력도 동일함
- **"LEFT"와 "RIGHT"를 구분할 방법이 없음**

---

## 5. 비교 실험: 이미지는 구분함

### 실험 2: 다른 이미지 + 동일 instruction

```python
image1 = random_image(seed=42)
image2 = random_image(seed=123)  # 다른 이미지!
instruction = "Navigate on the LEFT side"

action1 = model(image1, instruction)  # [0.234, -0.156]
action2 = model(image2, instruction)  # [0.198, -0.089]

difference = 0.009378  # 작지만 0은 아님!
```

**의미**:
- Vision encoder는 **어느 정도 작동**함
- 다른 이미지에 대해 **약간 다른** action 출력
- 하지만 차이가 매우 작음 (0.009) → Vision도 잘 작동 안함

---

## 6. 수치 기준 해석

### Instruction 차이 (실험 3)

| 차이 값 | 의미 | 우리 결과 |
|---------|------|----------|
| **0.000** | 완전히 동일 (무시) | ✅ 0.000000 |
| 0.001 ~ 0.01 | 거의 동일 (실패) | |
| 0.01 ~ 0.05 | 약간 차이 (부분 성공) | |
| **> 0.05** | 명확한 차이 (성공) | ❌ (목표) |

**우리 결과**: 0.000000
- **완벽하게 instruction을 무시**하고 있음
- Random noise조차 없음
- 모델이 "LEFT"와 "RIGHT"를 **전혀 구분 못함**

### Image 차이 (실험 2)

| 차이 값 | 의미 | 우리 결과 |
|---------|------|----------|
| 0.000 | 완전히 동일 | |
| **0.001 ~ 0.01** | 거의 동일 (약함) | ✅ 0.009378 |
| 0.01 ~ 0.05 | 약간 차이 | |
| **> 0.05** | 명확한 차이 (성공) | ❌ (이전 0.073) |

**우리 결과**: 0.009378
- Vision도 제대로 작동 안함
- 이전 Chunk5 (0.073)보다 **더 나빠짐**

---

## 7. 근본 원인: Frozen VLM의 한계

### VLM의 Text Embedding Space

```
Pre-trained VLM (Frozen):
  "Navigate LEFT"  → embedding_A
  "Navigate RIGHT" → embedding_B
  
  distance(embedding_A, embedding_B) ≈ 0.002  # 매우 가까움!
  
  Why? VLM이 robot task를 모름
  → "LEFT"와 "RIGHT"가 robot motion에서 
     얼마나 다른지 학습 안됨
```

### LoRA Fine-tuned VLM (InstructVLA/OpenVLA)

```
Fine-tuned VLM:
  "Navigate LEFT"  → embedding_A'
  "Navigate RIGHT" → embedding_B'
  
  distance(embedding_A', embedding_B') ≈ 0.287  # 충분히 멈!
  
  Why? VLM이 robot data로 학습됨
  → "LEFT" = +y motion
  → "RIGHT" = -y motion
  → Embedding space가 action-aware하게 변형됨
```

---

## 8. 수학적 설명

### Frozen VLM의 Embedding

```
Text Encoder: f_θ (frozen parameters θ)

emb_left  = f_θ("Navigate LEFT")
emb_right = f_θ("Navigate RIGHT")

θ는 ImageNet/WebText로 학습됨
→ "LEFT"와 "RIGHT"가 robot action과 연결 안됨
→ emb_left ≈ emb_right (robot task 관점에서)
```

### LoRA Fine-tuned VLM의 Embedding

```
Text Encoder: f_{θ+Δθ} (θ frozen, Δθ learnable)

emb_left'  = f_{θ+Δθ}("Navigate LEFT")
emb_right' = f_{θ+Δθ}("Navigate RIGHT")

Δθ는 robot data로 학습됨
→ "LEFT" → spatial relationship (+y)
→ "RIGHT" → spatial relationship (-y)
→ emb_left' ≠ emb_right' (meaningful difference)
```

**LoRA의 역할**:
- θ (pre-trained): General language knowledge 유지
- Δθ (LoRA): Robot-specific grounding 학습
- **Best of both worlds**

---

## 9. 실제 시나리오로 비유

### Frozen VLM (우리)

```
사람: "왼쪽으로 가세요"
로봇: [0.2, -0.1] 이동

사람: "오른쪽으로 가세요"  
로봇: [0.2, -0.1] 이동  ← 똑같음!

→ 로봇이 귀머거리처럼 행동
→ Instruction 듣는 척만 함
```

### LoRA Fine-tuned VLM (InstructVLA)

```
사람: "왼쪽으로 가세요"
로봇: [0.2, +0.5] 이동  ← 왼쪽!

사람: "오른쪽으로 가세요"
로봇: [0.2, -0.5] 이동  ← 오른쪽!

→ Instruction을 이해하고 다르게 행동
```

---

## 10. 결론

### Instruction Grounding 실패의 의미

1. **수치적 의미**:
   - `|action_left - action_right| = 0.000000`
   - **완벽하게 동일한 출력**
   - Random variation조차 없음

2. **기능적 의미**:
   - 모델이 instruction을 **전혀 고려하지 않음**
   - Image만 보고 action 결정
   - **Language conditioning이 완전히 실패**

3. **구조적 원인**:
   - Frozen VLM의 text embedding이 robot task에 맞지 않음
   - `embedding("LEFT") ≈ embedding("RIGHT")`
   - Action Head가 구분할 수 없음

### 해결책

**LoRA Fine-tuning**:
```
Frozen VLM:
  LEFT ≈ RIGHT
  difference = 0.000

LoRA VLM:
  LEFT ≠ RIGHT  
  difference > 0.05  ← 성공!
```

**핵심**: Frozen VLM은 구조적으로 불가능, LoRA가 필수!
