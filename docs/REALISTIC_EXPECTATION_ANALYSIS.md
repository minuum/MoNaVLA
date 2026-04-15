# 왜 안되는가: 근본적 원인 재분석

**작성일**: 2026-01-11  
**목적**: 예상 결과의 근거 검증 및 실패 원인 완전 분석

---

## 1. 제가 말한 "예상 결과 > 0.05"의 근거

### 1.1 OpenVLA 사례

```
OpenVLA + LoRA:
  - Success rate: 76.5% → 97.1%
  - Task: Manipulation (pick, place, slide)
  - Instruction: "Slide the block LEFT/RIGHT"
  
→ "LEFT/RIGHT instruction grounding 성공했다"
```

**하지만**:
- OpenVLA는 **manipulation task**
- 우리는 **navigation task**
- **Task domain이 다름**

---

### 1.2 InstructVLA 사례

```
InstructVLA + LoRA:
  - MoE adaptation (220M params)
  - Task: CALVIN manipulation
  - Instruction: Complex task instructions
  
→ "Instruction grounding 향상"
```

**하지만**:
- CALVIN도 **manipulation**
- **7-DoF action space**
- 우리는 **2-DoF navigation**

---

### 1.3 근거의 문제점

| 항목 | OpenVLA/InstructVLA | 우리 Task |
|------|---------------------|----------|
| Task | Manipulation | **Navigation** |
| Action | 7-DoF [x,y,z,r,p,y,g] | **2-DoF [linear_x, linear_y]** |
| Instruction | "Pick red cup" | **"Navigate LEFT"** |
| Data | OXE (manipulation) | **Mobile navigation** |

**핵심**: 
> **성공 사례는 모두 manipulation task**  
> **Navigation task 성공 사례는 없음**

---

## 2. 왜 안되는가: 층층이 쌓인 문제들

### Layer 1: Frozen VLM (확인됨)

#### 문제
```python
VLM frozen
→ Text encoder frozen
→ emb("Navigate LEFT") ≈ emb("Navigate RIGHT")
→ cosine_similarity = 0.998
```

**증거**: 
- Test 결과: difference = 0.000000
- 완벽하게 동일한 action 출력

#### 왜 이런가?
```
Kosmos-2 (또는 Google Robot VLM)가 frozen이면:
  - "LEFT"와 "RIGHT"의 embedding이 고정됨
  - 이 embedding은 ImageNet/WebText에서 학습됨
  - Robot navigation domain에 최적화 안됨
  - "LEFT" = "오른쪽이 아닌 방향" (추상적)
  - "RIGHT" = "왼쪽이 아닌 방향" (추상적)
  
→ Robot의 linear_y action [+0.5 vs -0.5]와 연결 안됨
```

---

### Layer 2: Task Domain Mismatch (심각)

#### 우리 데이터
```
Mobile navigation:
  - 2-DoF action space
  - Spatial navigation
  - LEFT/RIGHT = direction of movement
  - 데이터: 737 episodes
```

#### Pretrained VLM이 본 데이터
```
Google Robot:
  - Manipulation (pick, place)
  - 7-DoF arm control
  - LEFT/RIGHT = object location
  - "Pick the cup on the LEFT" ← object-centric

OXE:
  - 80% Manipulation
  - "Slide the block to the LEFT" ← object manipulation
  - 20% 기타 (navigation 소수)
```

**문제**:
```
Pretrained VLM의 "LEFT/RIGHT" 개념:
  - Object location: "물체가 왼쪽에 있다"
  - Action direction: "물체를 왼쪽으로 민다"

우리 Task의 "LEFT/RIGHT":
  - Movement direction: "로봇이 왼쪽으로 간다"
  - NO object manipulation
  
→ 의미론적으로 다름!
```

---

### Layer 3: Data Scale (매우 심각)

#### 학습 데이터 비교

| 모델 | 데이터 규모 | Navigation Data |
|------|------------|-----------------|
| **OpenVLA** | 970K trajectories | ~0% |
| **Google Robot** | ~100K+ (추정) | ~0% |
| **OXE** | 1M+ trajectories | **~10-20%** (200K?) |
| **우리** | **737 episodes** | **100%** (737) |

**문제**:
```
우리 데이터: 737 episodes
  vs
OXE navigation: ~200,000 episodes (추정)

→ 1/270의 데이터!
→ 심각한 data scarcity
```

#### Data/Parameter Ratio
```
OpenVLA:
  - Data: 970K episodes
  - Params: 7B
  - Ratio: 0.14 episodes/M params

우리 (LoRA):
  - Data: 737 episodes
  - Trainable params: ~230M (LoRA + Action Head)
  - Ratio: 0.003 episodes/M params
  
→ 50배 부족!
```

---

### Layer 4: Embodiment Mismatch (심각)

#### Action Space 비교
```
Pretrained (Google Robot / OXE):
  Input: Image + "Pick the red cup"
  Output: [x, y, z, roll, pitch, yaw, gripper]  # 7-DoF
  
  각 dimension이 독립적
  x: forward/backward (absolute position)
  y: left/right (absolute position)
  z: up/down (absolute position)

우리:
  Input: Image + "Navigate LEFT"
  Output: [linear_x, linear_y]  # 2-DoF
  
  linear_x: forward speed (velocity)
  linear_y: lateral movement (velocity)
  
  의미: x와 y가 결합되어 movement direction 결정
```

**문제**:
```
Pretrained VLM 학습:
  y dimension = object의 left/right position
  
우리 Task:
  linear_y = robot의 left/right movement
  
→ 의미론적으로 다름!
→ Transfer 어려움
```

---

### Layer 5: Instruction 구조 차이

#### Pretrained 데이터의 Instruction
```
Manipulation:
  "Pick up the RED cup"
   ↑        ↑
   verb   color attribute
  
  "Move the block to the LEFT"
   ↑         ↑         ↑
   verb    object   location
```

#### 우리 Instruction
```
Navigation:
  "Navigate around the obstacle on the LEFT side"
   ↑                              ↑
   verb (implicit)             direction
   
  핵심: Direction만 중요
       Object는 "obstacle" (generic)
```

**문제**:
```
Pretrained VLM이 학습한 것:
  - Object identification (red, blue, cup, block)
  - Object-centric LEFT/RIGHT
  - "어떤 물체를 어디로"

우리가 필요한 것:
  - Spatial direction only
  - Ego-centric LEFT/RIGHT  
  - "로봇이 어느 방향으로"
  
→ Grounding 방식이 다름
```

---

## 3. LoRA가 해결할 수 있는 것 vs 없는 것

### ✅ LoRA가 해결할 수 있는 것

#### 1. Text Embedding Adaptation
```python
# Frozen
emb_left = f_θ("LEFT")  # θ frozen
emb_right = f_θ("RIGHT")
→ emb_left ≈ emb_right (general language)

# LoRA
emb_left = f_{θ+Δθ}("LEFT")  # Δθ learnable
emb_right = f_{θ+Δθ}("RIGHT")
→ emb_left ≠ emb_right (task-specific)
```

**가능**: Text embedding을 우리 task에 맞게 fine-tune

---

#### 2. Vision-Language Alignment
```
LoRA adapters:
  - Vision encoder에 task-specific features 학습
  - Text encoder에 navigation semantics 학습
  - Cross-modal alignment 개선
```

**가능**: Image-Instruction 연결 개선

---

### ❌ LoRA가 해결 못하는 것

#### 1. Fundamental Data Scarcity
```
737 episodes로 230M parameters 학습?

Required (경험적):
  - Minimum: 10 episodes per 1K params
  - 230M params → 2.3M episodes 필요
  
우리:
  - 737 episodes
  - 부족: 737 / 2,300,000 = 0.03%
```

**불가능**: 데이터가 절대적으로 부족

---

#### 2. Task Domain Transfer
```
VLM이 manipulation으로 학습됨
  → "LEFT" = object location
  
Navigation으로 transfer
  → "LEFT" = movement direction
  
LoRA adapters (230M):
  - 1.66B VLM의 semantic knowledge 완전히 바꾸기 어려움
  - Adapters는 "adaptation" not "re-learning"
```

**불가능**: Task semantics가 너무 다름

---

#### 3. Embodiment Transfer
```
7-DoF manipulation → 2-DoF navigation

LoRA로 action space mapping 학습?
  - 가능하지만 매우 어려움
  - 737 episodes로는 불가능
```

**불가능**: 데이터 부족 + embodiment mismatch

---

## 4. 실제로 일어날 일 (현실적 시나리오)

### Scenario 1: LoRA + 현재 데이터 (737 episodes)

#### 예상 결과
```python
Epoch 0-2:
  - Train loss 감소
  - Val loss 감소
  - 학습되는 것처럼 보임

Epoch 3-5:
  - Train loss 계속 감소 (overfitting)
  - Val loss 증가
  - 데이터 부족 드러남

LEFT vs RIGHT Test:
  - Difference: 0.000 → 0.005 ← 약간 개선
  - 하지만 여전히 << 0.05
  - 통계적으로 유의미하지 않음
```

**이유**:
```
1. Data scarcity
   737 episodes로 230M params 학습 불가

2. Task mismatch
   Pretrained knowledge가 navigation에 맞지 않음

3. Embedding space
   LoRA adapters만으로 VLM의 deep semantic 바꾸기 어려움
```

---

### Scenario 2: LoRA + 10K episodes (가상)

#### 예상 결과
```python
10,000 navigation episodes 있다면:
  - Train loss: 잘 감소
  - Val loss: 안정적
  - Overfitting: 덜함

LEFT vs RIGHT Test:
  - Difference: 0.000 → 0.02-0.03
  - 약간의 grounding
  - 하지만 여전히 완벽하지 않음
```

**이유**:
```
1. Data가 10배 늘어났지만
2. Task/Embodiment mismatch 여전
3. Pretrained VLM의 manipulation bias 강함
```

---

### Scenario 3: From Scratch + LoRA + 737 episodes

#### 예상 결과
```python
Kosmos-2 from scratch (no pretrained):
  - Pretrained knowledge 없음
  - Task-specific 학습 가능
  - 하지만 data 부족

LEFT vs RIGHT Test:
  - Difference: 0.000 → 0.001-0.002
  - 거의 없음
  - Robot domain knowledge 없어서 더 나쁠 수도
```

**이유**:
```
1. Pretrained VLM의 general knowledge 사라짐
2. 737 episodes로 1.8B VLM 학습 불가능
3. Random initialization → 수렴 어려움
```

---

## 5. 근본적 문제: Impossible Triangle

```
        Large VLM (1.6B)
              /\
             /  \
            /    \
           /      \
          /        \
    Small Data  ←→  Different Task
    (737 ep)        (Navigation)
```

**Problem**:
- Large VLM: 많은 data 필요
- Small Data: 737 episodes만
- Different Task: Manipulation → Navigation transfer 어려움

**삼각형의 모순**:
```
Large VLM + Small Data → Overfitting
Large VLM + Different Task → Mismatch
Small Data + Different Task → Cannot learn
```

---

## 6. 현실적 기대치

### Best Case (LoRA + 모든 최적화)

```python
# 매우 운이 좋다면
LEFT vs RIGHT difference: 0.000 → 0.01-0.02

왜 이 정도가 최선인가?
1. 737 episodes로 230M params 학습
   → Severe overfitting
   
2. Manipulation → Navigation transfer
   → Semantic mismatch
   
3. LoRA adapters 한계
   → Cannot fully re-learn VLM semantics
```

### Realistic Case

```python
# 현실적으로
LEFT vs RIGHT difference: 0.000 → 0.002-0.005

왜?
1. Data scarcity dominates
2. Task mismatch 극복 못함
3. Val loss는 낮아도 grounding은 안됨
```

### Worst Case

```python
# 가능성 있음
LEFT vs RIGHT difference: 0.000 → 0.000-0.001

왜?
1. LoRA adapters가 수렴 못함
2. Learning rate 등 hyperparameter 문제
3. 여전히 average action 학습
```

---

## 7. 왜 제가 > 0.05라고 했는가?

### 잘못된 가정들

1. **"OpenVLA가 됐으니 우리도 될 것"**
   ```
   OpenVLA: 970K episodes, manipulation
   우리: 737 episodes, navigation
   → 완전히 다른 상황
   ```

2. **"LoRA는 만능"**
   ```
   LoRA: Adaptation tool
   NOT: Magic solution for data scarcity
   ```

3. **"Pretrained VLM이 도움될 것"**
   ```
   Pretrained VLM: Manipulation-trained
   우리 task: Navigation
   → Mismatch가 오히려 해가 될 수도
   ```

---

## 8. 그럼 어떻게 해야 하나?

### Option A: Data Collection (근본 해결)

```
현재: 737 episodes
목표: 10,000+ episodes

예상 효과:
  - Difference: 0.000 → 0.05-0.10
  - Real grounding 가능
  
시간: 2-3주 (data collection)
```

**가장 확실한 방법**

---

### Option B: Simpler Model (현실적)

```
VLM 포기, Simpler architecture:
  - ResNet + LSTM + Attention
  - 10M params 정도
  - 737 episodes로 학습 가능
  
예상 효과:
  - Difference: 0.000 → 0.03-0.05
  - Simpler task에 특화
```

**데이터 constraints에 맞춤**

---

### Option C: Instruction as Label (대안)

```
LEFT/RIGHT를 별도 모델로:
  - Model_LEFT: LEFT instruction만
  - Model_RIGHT: RIGHT instruction만
  
또는:
  - Instruction classifier + Single policy
  
예상 효과:
  - Perfect grounding (by design)
  - 하지만 scalability 없음
```

**Short-term 해결책**

---

### Option D: LoRA 시도 (실험적)

```
그래도 LoRA 시도해볼 수는 있음:
  - 예상: 0.000 → 0.01 정도
  - Data collection 전까지 baseline
  - 학습 과정 이해
  
목표:
  - 실패해도 배움
  - 어느 정도 개선되면 lucky
```

**Low expectation, high learning**

---

## 9. 결론

### 왜 안될 것인가?

#### Fundamental Constraints
```
1. Data Scarcity (737 vs 2.3M needed)
   → Cannot train 230M params

2. Task Mismatch (Manipulation vs Navigation)
   → Pretrained knowledge misaligned

3. Embodiment Gap (7-DoF vs 2-DoF)
   → Transfer difficult

4. Semantic Difference (Object-centric vs Ego-centric)
   → "LEFT/RIGHT" 의미가 다름
```

---

### 예상 결과 (정직하게)

```
LoRA Fine-tuning:
  - Best case: difference = 0.01-0.02
  - Realistic: difference = 0.002-0.005
  - Worst case: difference = 0.000-0.001
  
NOT > 0.05 (제가 잘못 말씀드림)
```

---

### 근본 해결책

```
1순위: Data Collection (10K+ episodes)
2순위: Simpler Model (적은 params)
3순위: Instruction as separate models
4순위: LoRA 시도 (실험, learning)
```

---

## 10. 최종 답변

### "예상 결과 > 0.05의 근거는?"

**솔직한 답변**: 
> **근거가 부족했습니다.**

OpenVLA/InstructVLA 성공 사례를 보고 낙관했지만:
- 그들: 970K episodes, manipulation
- 우리: 737 episodes, navigation
- **완전히 다른 상황**

---

### "왜 안되는가?"

**근본 원인**:
1. **Data scarcity** (가장 critical)
   - 737 episodes로 230M params 학습 불가능
   
2. **Task mismatch**
   - Manipulation ≠ Navigation
   
3. **Semantic gap**
   - Object-centric LEFT ≠ Ego-centric LEFT

---

### 현실적 기대

```
LoRA 시도:
  - 0.000 → 0.01 정도 개선 (maybe)
  - 완벽한 grounding: 불가능
  - Data collection 필요
```

**죄송합니다. 너무 낙관적으로 말씀드렸습니다.** 🙏
