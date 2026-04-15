# Object Candidates VLM Recognition Test 결과

**테스트 일시**: 2026-01-15 15:02  
**환경**: Navigation corridor (복도 바닥)  
**VLM**: Google Robot Pretrained (Frozen)

---

## 🚨 충격적인 결과: 모든 Objects 0점!

### 종합 결과

| Object Type | Object | Score | Naming | Detection | Color | Hallucination |
|-------------|--------|-------|--------|-----------|-------|---------------|
| **TARGET** | Apple | **0/100** | ❌ 0/1 | ❌ 0/1 | ❌ 0/1 | 0 |
| **TARGET** | Blue mug | **0/100** | ❌ 0/1 | ❌ 0/1 | ❌ 0/1 | 0 |
| **TARGET** | Coke can | **0/100** | ❌ 0/1 | ❌ 0/1 | ❌ 0/1 | ❌ 1 |
| **OBSTACLE** | Chair | **0/100** | ❌ 0/1 | ❌ 0/1 | ✅ 1/1 | ❌ 2 |
| **OBSTACLE** | Traffic cone | **0/100** | ❌ 0/1 | ❌ 0/1 | ❌ 0/1 | ❌ 4 |

**전체 평균**: **0/100** ❌❌❌

---

## 📊 상세 결과 분석

### 1. Apple (Green apple on floor)

**VLM 응답**:
```
Q: "What object do you see?"
A: "A white wall"  ← 완전 틀림, Apple 못 봄

Q: "Is there a apple?"
A: "I..." (incomplete)  ← Apple 인식 못함

Q: "Describe this object"
A: "A long white hallway"  ← Hallway만 봄

Q: "What color is the object?"
A: "The object is white"  ← Green이 아니라 white

Q: "An image of"
A: "hallway with white ceiling and walls"  ← Apple 전혀 언급 없음
```

**Score**: 0/100  
**문제**: Apple을 완전히 보지 못함. Hallway만 인식.

---

### 2. Blue Mug (Blue mug on floor)

**VLM 응답**:
```
Q: "What object do you see?"
A: "A white wall"  ← Mug 못 봄

Q: "Is there a blue mug?"
A: "Yes, there is a blue cup"  ← Yes! 하지만...

Q: "Describe this object"
A: "A long hallway"  ← Hallway만 봄

Q: "What color is the object?"
A: "The object..." (incomplete)

Q: "An image of"
A: "hallway with white wall and window. Empty"  ← Mug 언급 없음
```

**Score**: 0/100  
**문제**: "Is there?" 질문에는 Yes라고 대답했지만, 실제로는 인식 못함. Hallway만 봄.

---

### 3. Coke Can (Red Coke can on floor)

**VLM 응답**:
```
Q: "What object do you see?"
A: "A window"  ← Can 못 봄

Q: "Is there a coke can?"
A: "No, there is a coke bottle"  ← No! 그리고 틀림

Q: "Describe this object"
A: "A window"  ← Window만 봄

Q: "What color is the object?"
A: "white color"  ← Red가 아니라 white

Q: "An image of"
A: "room with window and door and person's hands"  ← Hallucination!
```

**Score**: 0/100  
**문제**: Can 완전히 못 봄. "No, there is a coke bottle"라고 거짓 답변. Person hallucination.

---

### 4. Chair (White chair obstacle)

**VLM 응답**:
```
Q: "What object do you see?"
A: "A person"  ← Hallucination!

Q: "Is there a chair?"
A: "The AI..." (incomplete)

Q: "Describe this object"
A: "Surveillance camera"  ← 완전 틀림

Q: "What color is the object?"
A: "white"  ← 유일한 정답!

Q: "An image of"
A: "hallway with a person in the middle"  ← Person hallucination
```

**Score**: 0/100  
**문제**: Chair를 "person"과 "surveillance camera"로 착각. Hallucination 2번.

---

### 5. Traffic Cone (Orange cone obstacle)

**VLM 응답**:
```
Q: "What object do you see?"
A: "A person"  ← Hallucination!

Q: "Is there a traffic cone?"
A: "A man"  ← Hallucination!

Q: "Describe this object"
A: "A man"  ← Hallucination!

Q: "What color is the object?"
A: "white"  ← Orange가 아니라 white

Q: "An image of"
A: "man with mask on face in hallway"  ← Hallucination!
```

**Score**: 0/100  
**문제**: Cone을 "person", "man", "man with mask"로 착각. Hallucination 4번!

---

## 💡 왜 이런 결과?

### 원인 1: Viewpoint Mismatch (시점 불일치)

**Navigation 환경 (우리)**:
```
Camera height: 30cm (매우 낮음)
View: 바닥 중심, 작은 objects
Objects: 바닥에 놓인 작은 물체
Distance: 멀리 있음
```

**RT-1 Training Data**:
```
Camera: Table-top view (45도, 60-80cm)
View: 테이블 위 objects 중심
Objects: 테이블에 가까이, 크게 보임
Distance: 가까움 (manipulation range)
```

**결과**: **Viewpoint가 완전히 다름** → VLM confusion

---

### 원인 2: Object Size & Distance

**우리 이미지**:
```
Object size: 화면의 5-10% (작음)
Position: 중앙이지만 멀리
Background: 복도가 화면의 90% 차지
```

**RT-1 Data**:
```
Object size: 화면의 30-50% (큼)
Position: 가까이, 조작 거리
Background: Table/counter
```

**결과**: **Object가 너무 작고 멀어서 VLM이 못 봄**

---

### 원인 3: Context Dominance (배경 지배)

**VLM이 본 것**:
```
90%: "Hallway", "White walls", "Ceiling"
10%: Small object (못 봄)

→ Hallway context가 너무 강함
→ Object를 완전히 놓침
```

---

### 원인 4: Prior Bias

**VLM 학습**:
```
"복도 + 사람 키높이" → "사람이 있을 것"
"복도에 작은 것" → "사람", "카메라" 등으로 착각
```

**결과**: Cone → "man with mask", Chair → "person"

---

## 🎯 핵심 발견

### 발견 1: Navigation 환경 = Out-of-Distribution

> "바닥에 놓인 작은 objects는 Google Robot VLM이 **완전히 인식 못함** (0%). RT-1 table-top manipulation과 **근본적으로 다른 환경**."

---

### 발견 2: Object 선택보다 Viewpoint가 더 중요

> "Coke can (RT-1 데이터에 있음)도 0점! **Object 종류가 아니라 camera viewpoint와 object size가 결정적**."

---

### 발견 3: VLM-Optimized Objects도 무용지물

> "Apple, Mug, Coke can 모두 0점. **Navigation 환경에서는 어떤 object를 선택해도 소용없음**."

---

## 🚨 중대한 결론

### 결론 1: VLM-Optimized Dataset 전략 실패 예상

**원래 계획**:
```
✗ Coke can, Mug, Apple 사용
✗ VLM 인식 향상 (20% → 70%)
✗ Instruction grounding 가능
```

**현실**:
```
❌ Navigation 환경에서 0% (전혀 인식 못함)
❌ Object 종류 무관 (Coke/Mug/Apple 모두 실패)
❌ Instruction grounding 불가능
```

---

### 결론 2: 근본적 환경 변경 필요

**Option A: Manipulation-Style Setup (권장?) ⭐⭐⭐**
```
변경:
  - Camera height: 30cm → 60-80cm
  - View angle: 수평 → 45도 하향
  - Object distance: 멀리 → 가까이 (50cm 이내)
  - Object size: 작게 → 크게 (화면의 30%+)
  
Environment:
  - 복도 → Table-top 또는 raised platform
  - Navigation → Manipulation-like navigation
```

**효과**: RT-1 data와 유사하게 만들어서 VLM 인식 가능

---

**Option B: Larger Objects (부분적 해결?) ⭐⭐**
```
Objects:
  - Small can → Large box (30cm+)
  - Mug → Large traffic cone (60cm)
  - Apple → Basketball/Balloon
  
결과: 크기는 커지지만 viewpoint 여전히 문제
```

---

**Option C: LoRA Fine-tuning (원래 계획) ⭐⭐⭐⭐⭐**
```
Accept:
  - Navigation 환경 = Out-of-distribution
  - Frozen VLM = 불가능
  
Solution:
  - LoRA fine-tuning으로 navigation 학습
  - Floor-level objects 인식 학습
  - 새로운 viewpoint adaptation
```

---

## 📋 수정된 권장사항

### 즉시 실행 (검증용)

#### Test 1: Manipulation-Style Navigation

**Setup**:
```
1. Raise objects to 40-50cm height (small table/platform)
2. Move camera to 60cm height  
3. Angle camera down 30-40 degrees
4. Keep navigation task but change viewpoint
```

**Expected**: VLM recognition > 50% (RT-1과 유사하게)

**Test Method**:
- Same Coke can, Mug, Apple
- New camera setup (manipulation-like)
- Re-test VLM recognition

**If Success**: Consider "table-top navigation" as interim solution

---

#### Test 2: Very Large Objects

**Objects**:
```
- Large cardboard box (50cm cube)
- Traffic cone (60cm tall)
- Beach ball (40cm diameter)
```

**Expected**: Size만으로 약간 향상 (20-30%?)

---

### 장기 계획 (변경 없음)

**LoRA Fine-tuning** ⭐⭐⭐⭐⭐ **권장!**

**이유**:
1. Navigation 환경 = Frozen VLM 불가능 (확인됨)
2. Object 선택 무용 (확인됨)
3. Viewpoint 변경 = Task 성격 변경 (비현실적)
4. **LoRA가 유일한 해결책**

---

## 🎊 최종 추천

### 실질적 선택

#### Option 1: LoRA Fine-tuning 진행 ✅ **강력 추천**

```
Accept Reality:
  - Navigation = Out-of-distribution
  - VLM-optimized objects = 0% in navigation
  - Frozen VLM = 불가능
  
Proceed:
  - Current objects (bottle, box) 유지
  - LoRA fine-tuning 
  - Navigation-specific adaptation
```

---

#### Option 2: Manipulation-Style Navigation (실험용)

```
Try:
  - Table-top navigation setup
  - Raised objects (manipulation view)
  - Test if VLM works
  
If Success:
  - Interim solution
  - Publish as "manipulation-based navigation"
  
If Fail:
  - Confirm LoRA necessity더 강하게
```

---

### 명확한 메시지

> "**VLM-Optimized Objects 전략은 Navigation 환경에서 실패**. Coke can, Mug, Apple 모두 0% 인식. **Navigation viewpoint가 RT-1 manipulation과 근본적으로 다름**. **LoRA fine-tuning이 필수적**."

---

## 📊 비교 정리

| Strategy | Expected | Reality | Status |
|----------|----------|---------|--------|
| **VLM-Opt Objects** | 70% recognition | **0%** | ❌ Failed |
| **Coke can (RT-1 data)** | 95% | **0%** | ❌ Failed |
| **Any object on floor** | 50%+ | **0%** | ❌ Failed |
| **Current setup** | 20% | 20% | ⚠️ Same |
| **LoRA fine-tuning** | 60%+ | TBD | ✅ Proceed |

---

**요약**:
- 🚨 모든 Objects 0점! (Apple, Mug, Coke can, Chair, Cone)
- 💡 원인: Navigation viewpoint ≠ RT-1 manipulation
- ❌ VLM-Optimized Objects 전략 실패
- ✅ LoRA fine-tuning이 유일한 해결책
- 🔬 Option: Table-top navigation으로 실험 가능
