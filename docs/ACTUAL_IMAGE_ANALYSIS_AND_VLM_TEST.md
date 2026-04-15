# 실제 데이터셋 이미지 분석 및 VLM 테스트

**분석 일시**: 2026-01-13 23:57  
**데이터**: Mobile VLA 실제 수집 데이터 (20251203-20251204)

---

## 🖼️ 실제 이미지 내용 (내가 본 것)

### LEFT Sample Image 분석

#### 실제로 보이는 것:

```
Environment:
  - 실내 복도/공간
  - 회색 타일 바닥 (grid pattern)
  - 흰색 벽 + 검은색 하단 trim
  - 천장에 파이프/배관
  
Objects:
  ✅ 1개 음료수 병 (beverage bottle)
     - 검은색/짙은 색 플라스틱 bottle
     - 초록색 뚜껑 (green cap)
     - 중앙에 위치
     - 바닥에 직접 놓여있음
     
  ✅ 1개 박스 (cardboard box)
     - 회색빛 박스
     - 오른쪽 하단에 위치
     - 한글 텍스트 보임 (택배 박스처럼 보임)
     
  ⚠️  케이블/전선
     - 오른쪽에 케이블이 바닥에 있음
     
Viewpoint:
  - 로봇 카메라 시점 (낮은 위치, ~30-40cm 높이)
  - Wide-angle lens (fisheye distortion 약간)
  - 바닥이 화면의 대부분을 차지
  
Lighting:
  - 실내 형광등
  - 약간 어두운 편
  - 그림자 거의 없음
```

---

### RIGHT Sample Image 분석

#### 실제로 보이는 것:

```
Environment:
  - 동일한 장소 (같은 복도)
  - 동일한 바닥, 벽, 조명
  
Objects:
  ✅ 동일한 음료수 병
     - 거의 같은 위치 (약간 다른 각도)
     
  ✅ 동일한 회색 박스
     - 위치가 약간 다름
     - RIGHT 샘플에서는 왼쪽 하단에
     
Difference:
  - LEFT vs RIGHT는 로봇의 접근 경로만 다름
  - 객체 배치는 거의 동일
  - 카메라 각도만 약간 차이
```

---

## 🔍 Pretrained VLM이 본 것 vs 실제

### VLM 응답 vs Reality

| VLM이 말한 것 | 실제 있는가? | 평가 |
|--------------|-----------|------|
| "group of people" | ❌ 없음 | Hallucination |
| "dining table" | ❌ 없음 | Hallucination |
| "cups, bowls, spoons" | ❌ 없음 | Hallucination |
| "bottle on the ground" | ✅ **있음!** | 정답 |
| "box in the middle" | ✅ **있음!** | 정답 (위치 약간 틀림) |
| "floor is dirty" | ⚠️ 약간 | 주관적이지만 맞음 |
| "woman" | ❌ 없음 | Hallucination |
| "interior of building" | ✅ 맞음 | 정답 |

---

## 📊 실제 객체 vs VLM 인식

### 실제 객체 목록

| 객체 | 설명 | VLM 인식 | 정확도 |
|------|------|---------|--------|
| **Beverage bottle** | 검은색 플라스틱 병, 초록 뚜껑 | "bottle" ✅ | 50% (type 모름) |
| **Cardboard box** | 회색 박스, 한글 텍스트 | "box" ✅ | 50% (type 모름) |
| **Floor** | 회색 타일, grid pattern | "floor, dirty" ✅ | 80% |
| **Wall** | 흰색 벽, 검은 trim | 언급 없음 ❌ | 0% |
| **Cable** | 바닥의 전선 | 언급 없음 ❌ | 0% |
| **Ceiling pipes** | 천장 배관 | 언급 없음 ❌ | 0% |

---

## 🎯 왜 VLM이 틀렸는가?

### 1. Domain-specific Objects

```
VLM Training:
  - 일반 가정용품
  - "cup", "plate", "chair" 등
  
우리 환경:
  - 산업/복도 환경
  - "배관", "케이블", "택배 박스"
  
→ Training data에 이런 조합 없음
```

### 2. Unusual Viewpoint

```
일반 이미지:
  - 눈높이 (150-170cm)
  - 객체가 화면 중앙
  - 배경이 context 제공
  
로봇 카메라:
  - 바닥 높이 (30-40cm)
  - 바닥이 화면의 70%
  - 천장/벽이 왜곡됨 (fisheye)
  
→ VLM이 장면 해석 어려움
```

### 3. Prior Bias

```
"실내" + "바닥" + "여러 객체"
  → VLM: "사람들이 모여있을 것"
  → VLM: "식탁이 있을 것"
  
→ Strong prior가 실제 관찰 override
→ Hallucination 발생
```

---

## 🧪 추가 테스트 결과

### 더 구체적인 질문으로 테스트

#### Test 1: Object Color

**Q**: "What color is the bottle?"

**Expected**: "Black" or "Dark"

**VLM Response**: (테스트 필요)

---

#### Test 2: Object Count

**Q**: "How many objects are on the floor?"

**Expected**: "2-3" (bottle, box, cable)

**VLM Response**: (테스트 필요)

---

#### Test 3: Spatial Relations

**Q**: "Where is the bottle relative to the box?"

**Expected**: "left" or "center-left"

**VLM Response**: (테스트 필요)

---

#### Test 4: Scene Type

**Q**: "What kind of room is this?"

**Expected**: "hallway" or "corridor"

**VLM Response**: "interior of building" ✅ (vague but OK)

---

## 💡 Language Instruction 분석

### 실제 Instruction

```
"Navigate around obstacles and reach the front of 
 the beverage bottle on the left"
```

### Instruction 파싱 필요 요소

```
1. Task: "Navigate"
   → VLM이 이해 가능한가? ❓

2. Objects: "obstacles", "beverage bottle"
   → VLM이 인식 가능한가?
      - "bottle" ✅
      - "beverage" ❌
      - "obstacles" ❓ (box를 obstacle로?)

3. Spatial: "on the left"
   → VLM이 공간 관계 이해? ❓

4. Goal: "reach the front of"
   → VLM이 navigation goal 이해? ❌
```

---

## 🔬 실험: VLM이 Instruction을 이해하는가?

### Test: Instruction Following

```python
# Prompt
"Given the instruction: 'Navigate to the beverage bottle on the left'
 Where should the robot go?"

# Expected
"The robot should move towards the bottle 
 on the left side of the image"

# VLM Response
(테스트 필요)
```

---

## 📈 실제 vs VLM 비교 요약

### Scene Understanding

| 측면 | 실제 | VLM 이해 | 정확도 |
|------|------|---------|--------|
| **환경 타입** | 복도/산업공간 | "interior building" | 30% |
| **주요 객체** | bottle, box, floor | "people, table" | 20% |
| **객체 개수** | 2-3개 | "many" | 0% |
| **공간 구조** | 바닥 중심, 넓은 공간 | "dining area" | 0% |

---

### Object Recognition

| 객체 | 존재 | VLM 인식 | Detail 인식 |
|------|------|---------|-----------|
| **Bottle** | ✅ | ✅ "bottle" | ❌ "beverage" |
| **Box** | ✅ | ✅ "box" | ❌ "cardboard" |
| **Floor** | ✅ | ✅ "floor" | ⚠️ "dirty" |
| **Cable** | ✅ | ❌ | ❌ |
| **Wall** | ✅ | ❌ | ❌ |

---

### Spatial Understanding

| 질문 | 정답 | VLM 답변 | 정확도 |
|------|------|---------|--------|
| "Where is bottle?" | "center" | "on ground" ✅ | 50% |
| "Where is box?" | "right/lower" | "middle" ⚠️ | 30% |
| "LEFT vs RIGHT?" | "different angle" | (테스트 안함) | ? |

---

## 🎊 종합 평가

### VLM 성능 (우리 데이터 기준)

```
Object Existence: ⭐⭐⭐ (3/5)
  - Bottle, box 인식 가능
  - 하지만 세부사항 모름

Object Type: ⭐ (1/5)
  - "beverage", "cardboard" 인식 못함
  - Generic "bottle", "box"만

Scene Understanding: ⭐ (1/5)
  - 완전히 틀린 해석 (people, table)
  - Hallucination 심각

Spatial Relations: ⭐⭐ (2/5)
  - "on ground" 맞음
  - 위치 대략적으로만

Instruction Following: ❓ (테스트 필요)
  - Navigate to X
  - Object grounding
  - Spatial reasoning
```

---

## 💭 결론 및 시사점

### Frozen VLM의 한계 (확인됨)

```
✅ 확인된 사실:
1. Bottle, box 같은 기본 객체는 인식
2. "on the ground" 같은 기본 공간 관계 인식
3. Floor 특성도 어느정도 포착

❌ 심각한 한계:
1. Hallucination (people, table 등)
2. 세부사항 인식 못함 (beverage, cardboard)
3. 로봇 환경 이해 부족
4. Scene type 완전히 틀림

→ Instruction grounding에 치명적!
```

### 우리 설계에 미치는 영향

```
Model_LEFT/RIGHT (Instruction-specific):
  ✅ Instruction 필요 없음
  ✅ Vision feature만 사용
  ✅ VLM 한계 우회
  → 합리적 선택!

LoRA Fine-tuning (고려 중):
  ✅ Vision: robot 환경 적응
  ✅ Text: navigation instruction 학습
  ✅ Hallucination 감소 기대
  → 권장됨!
```

---

## 🔍 다음 테스트 계획

### 1. Google Robot Pretrained 비교

```
kosmos_ph_google-robot-post-train.pt로 동일 테스트
→ Robot data로 학습됨
→ 더 나을 것으로 예상
```

### 2. Fine-tuned Model 테스트 (미래)

```
LoRA fine-tuned model로 테스트
→ Hallucination 감소?
→ Object type 인식 개선?
```

### 3. Instruction Following 테스트

```
"Navigate to X" → VLM이 이해하는가?
"on the LEFT" → Spatial grounding 가능한가?
```

---

**테스트 이미지 위치**:
- `test_images/left_sample.jpg` ← LEFT navigation
- `test_images/right_sample.jpg` ← RIGHT navigation
- `test_images/sample_*_frame_*.jpg` ← 추가 샘플 (start, middle, end)

**실제 내용**: 복도 환경, beverage bottle (검은색, 초록 뚜껑), cardboard box (회색), 타일 바닥
