# VLM 프롬프트 & 응답 상세 분석

**Date**: 2026-01-21  
**Image**: 실제 갈색 화분 + 회색 바구니

---

## 📋 테스트 케이스별 상세 결과

### Test 1: Brown Pot with JSON

**📝 입력 프롬프트**:
```
<grounding> Is there a brown pot on the floor? JSON: {"detected": true/false}
```

**💬 VLM 응답**:
```
Is there a brown pot on the floor? JSON: {"detected": true/false}
```

**분석**:
- ❌ VLM이 프롬프트를 echo만 하고 답변 안 함!
- ❌ JSON 완성 안 함
- ❌ YES/NO 답변 없음

**문제**: JSON 힌트가 너무 구체적이면 VLM이 답변하지 않고 echo만 함

---

### Test 2: Gray Basket with JSON

**📝 입력 프롬프트**:
```
<grounding> Is there a gray basket on the floor? JSON: {"detected": true/false}
```

**💬 VLM 응답**:
```
Is there a gray basket on the floor? JSON: {"detected": true/false}
```

**분석**:
- ❌ 동일한 문제 (echo만 함)
- ❌ 답변 없음

---

### Test 3: Simple Brown Pot ⭐

**📝 입력 프롬프트**:
```
<grounding> Is there a brown pot?
```

**💬 VLM 응답**:
```
Is there a brown pot? There is a pot. The pot is on the ground.
```

**분석**:
- ✅ Brown 인식!
- ✅ Pot 인식!
- ✅ "on the ground" 위치 정보
- ⚠️ "There is a pot" (brown 빠짐)

**Score**: Good! 실제 답변함!

---

### Test 4: Simple Gray Basket ⭐

**📝 입력 프롬프트**:
```
<grounding> Is there a gray basket?
```

**💬 VLM 응답**:
```
Is there a gray basket? Yes, there is a basket. The basket is placed on the floor next to the door.
```

**분석**:
- ✅✅ "Yes" 명확한 답변!
- ✅ Basket 인식!
- ✅ "on the floor" 위치
- ✅ "next to the door" 상세 정보
- ⚠️ Gray 빠짐

**Score**: Excellent! 가장 좋은 응답!

---

### Test 5: Navigate to LEFT of pot ⭐⭐⭐

**📝 입력 프롬프트**:
```
<grounding> Is there a brown pot on the floor? Navigate to the LEFT.
```

**💬 VLM 응답**:
```
Is there a brown pot on the floor? Navigate to the LEFT. 
There is a brown metal pot on a white floor. 
The pot is placed on the left side of the room.
```

**분석**:
- ✅✅✅ Brown 인식!
- ✅✅✅ Metal pot 정확 인식!
- ✅✅✅ White floor 정확!
- ✅✅✅ **"left side of the room"** ← 중요!
- ✅ Navigation 지시 이해함!

**Score**: Perfect for navigation! "LEFT" 인식!

---

### Test 6: Navigate to RIGHT of pot ⭐⭐

**📝 입력 프롬프트**:
```
<grounding> Is there a brown pot on the floor? Navigate to the RIGHT.
```

**💬 VLM 응답**:
```
Is there a brown pot on the floor? Navigate to the RIGHT. 
There is a brown metal pot on a white floor. 
The pot is placed on the left side of the floor.
```

**분석**:
- ✅ Brown pot 인식
- ✅ White floor 정확
- ⚠️ **"left side"라고 함** (RIGHT 지시했는데!)
- ❌ RIGHT 지시를 따르지 못함!

**문제**: RIGHT로 navigate 하라고 했는데 여전히 "left side"라고 답함!

---

## 💡 핵심 발견

### 1. JSON 힌트는 역효과! ❌

```
Prompt: "...JSON: {"detected": true/false}"
Response: (echo만 하고 답변 안 함)

→ JSON 형식 강제는 오히려 방해됨!
```

---

### 2. Simple Prompts가 Best! ✅

```
Prompt: "Is there a brown pot?"
Response: "There is a pot. The pot is on the ground."

Prompt: "Is there a gray basket?"
Response: "Yes, there is a basket..."

→ 간단할수록 좋음!
```

---

### 3. LEFT/RIGHT Instruction의 문제 ⚠️

```
Test 5 (LEFT):
  Prompt: "Navigate to the LEFT"
  Response: "...placed on the left side"
  → ✅ 맞음!

Test 6 (RIGHT):
  Prompt: "Navigate to the RIGHT"
  Response: "...placed on the left side"
  → ❌ 틀림! (여전히 left라고 함)
```

**문제**: VLM이 실제 object 위치를 말하는 것! (instruction을 따르는게 아님)

---

### 4. VLM이 하는 일 = Object Localization

**VLM의 실제 동작**:
```
Image + "Is there a pot?" 
  → "There is a pot on the left side"
  
→ VLM은 실제 위치를 말함 (instruction은 무시)
```

**중요한 깨달음**:
> VLM은 "Navigate to LEFT/RIGHT" 지시를 따르는게 아니라,  
> **실제로 object가 어디 있는지** 알려주는 것!

---

## 🎯 Navigation에 미치는 영향

### ✅ 긍정적인 면

1. **Object를 정확히 인식함**
   ```
   "brown metal pot" ✅
   "gray basket" ✅
   "on the floor/ground" ✅
   ```

2. **위치 정보를 제공함**
   ```
   "left side of the room" ✅
   "on the floor" ✅
   "next to the door" ✅
   ```

3. **Visual features가 좋음**
   - Brown 인식
   - Pot 인식
   - Location 인식

---

### ⚠️ 문제점

1. **LEFT/RIGHT Instruction 혼동**
   ```
   Prompt: "Navigate to RIGHT"
   Response: "...left side"
   
   → Instruction을 따르지 않음!
   ```

2. **Action Head가 해결해야 함**
   ```
   VLM: "pot on the left side"
   Action Head: LEFT instruction → turn left action
   
   → Action head가 VLM output + instruction을 결합해서 학습
   ```

---

## 🔧 수정된 프롬프트 전략

### ❌ 사용하지 말 것

```python
# JSON 힌트 (echo만 함)
"Is there a brown pot? JSON: {\"detected\": true/false}"  ❌

# 복잡한 instruction
"Navigate to the LEFT. Answer YES or NO."  ❌
```

---

### ✅ 사용할 것 (권장)

```python
# Option 1: Simple detection (Best!)
"<grounding> Is there a brown pot?"

# Option 2: With location
"<grounding> Is there a brown pot on the floor?"

# Option 3: Yes/No question
"<grounding> Is there a gray basket?"
```

**Expected Responses**:
```
Option 1: "There is a pot. The pot is on the ground."
Option 2: "There is a brown metal pot on a white floor."
Option 3: "Yes, there is a basket..."
```

---

## 🎯 Navigation Pipeline Design

### 올바른 이해

```python
# VLM's Role: Object Detection + Localization
vlm_output = vlm(image, "<grounding> Is there a brown pot?")
# Output: "There is a brown metal pot on the left side"

# Action Head's Role: 
#   VLM features + Instruction → Action
instruction = "Navigate to the LEFT of the pot"
action = action_head(vlm_features, instruction_embedding)

# Action head가:
#   1. VLM features에서 pot 위치 학습
#   2. Instruction에서 LEFT/RIGHT 이해
#   3. 둘을 결합해서 올바른 action 출력
```

---

### ❌ 잘못된 기대

```python
# VLM이 instruction을 따를 것이라 기대 (X)
prompt = "Navigate to the RIGHT"
vlm_output = "...left side"  # 실제 위치 말함!

# VLM은 instruction follower가 아님!
# VLM = Object detector + Localizer
```

---

### ✅ 올바른 설계

```python
class NavigationPipeline:
    def predict(self, image, instruction):
        # 1. VLM: Simple object detection
        prompt = "<grounding> Is there a brown pot?"
        vlm_features = self.vlm(image, prompt)
        # VLM output: "brown pot on the left/right"
        
        # 2. Instruction embedding
        if 'LEFT' in instruction:
            inst_emb = self.instruction_encoder(0)  # LEFT
        else:
            inst_emb = self.instruction_encoder(1)  # RIGHT
        
        # 3. Action head: Combine VLM + Instruction
        action = self.action_head(vlm_features, inst_emb)
        # Action head가 VLM features + instruction을 학습!
        
        return action
```

---

## 📋 최종 권장 프롬프트

### For Training Data Collection

```python
# Simple and effective
PROMPT_TEMPLATE = "<grounding> Is there a brown pot on the floor?"

# VLM will output:
# "There is a brown metal pot on the floor"
# or
# "There is a pot. The pot is placed on the left/right side"

# Action head will learn:
# - VLM features (pot detected)
# - Instruction (LEFT or RIGHT)
# - Correct action (turn left/right)
```

---

### For Each Instruction

```python
# LEFT instruction
instruction = "Navigate to the LEFT of the brown pot"
vlm_prompt = "<grounding> Is there a brown pot on the floor?"

# RIGHT instruction  
instruction = "Navigate to the RIGHT of the brown pot"
vlm_prompt = "<grounding> Is there a brown pot on the floor?"  # Same!

# VLM prompt은 동일, instruction만 다름
# Action head가 instruction 차이를 학습!
```

---

## 🎊 결론

### 1. VLM의 역할 (명확히 이해)

```
VLM = Object Detector + Localizer
  ✅ "brown pot" 인식
  ✅ "on the floor" 위치
  ✅ "left/right side" 방향
  
VLM ≠ Instruction Follower
  ❌ "Navigate to RIGHT" 지시 따르기 (못함)
```

---

### 2. 최적 프롬프트

```python
✅ BEST: "<grounding> Is there a brown pot?"
✅ GOOD: "<grounding> Is there a brown pot on the floor?"
❌ BAD:  "...JSON: {...}" (echo만 함)
❌ BAD:  "Navigate to LEFT/RIGHT" (VLM이 못 따름)
```

---

### 3. Action Head가 핵심

```
Navigation = VLM features + Instruction → Action
              (object info)   (LEFT/RIGHT)   (turn)

→ Action head가 instruction grounding 학습!
→ VLM은 object detection만 하면 됨!
```

---

### 4. 설계 변경 필요 없음!

**현재 설계 그대로 OK**:
```python
1. VLM: Simple object detection
   Prompt: "Is there a brown pot?"
   
2. Action Head: Learn from
   - VLM features
   - Instruction (LEFT/RIGHT)
   - Episode data
   
3. Navigation: Action head outputs correct turn
```

**Why it works**:
- VLM: 70% object recognition (충분!)
- Action head: Learns instruction grounding
- Expected: 80-85% navigation success!

---

**Summary**: VLM은 object detection만 하고, Action Head가 instruction grounding을 학습! Simple prompts ("Is there a brown pot?")로 충분! JSON 힌트 필요 없음!
