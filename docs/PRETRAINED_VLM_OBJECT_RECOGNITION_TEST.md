# Pretrained VLM의 실제 데이터 객체 인식 테스트 결과

**테스트 일시**: 2026-01-13 22:51  
**모델**: Kosmos-2 (Pretrained, Frozen)  
**데이터**: 실제 Mobile VLA 데이터셋 이미지

---

## 🖼️ 테스트 이미지

### 실제 내용
```
Environment: 실내 바닥
Objects:
  - 1 cardboard box (갈색 박스)
  - 1 beverage bottle (음료수 병)
  - Floor (회색 바닥)
  
Viewpoint: 로봇 카메라 (낮은 시점, ~30cm 높이)
Lighting: 실내 조명
```

### Language Instruction (실제)
```
LEFT: "Navigate around obstacles and reach the front of 
       the beverage bottle on the left"

RIGHT: "Navigate around obstacles and reach the front of
        the beverage bottle on the right"
```

---

## 🤖 Pretrained Kosmos-2 응답 결과

### Test 1: General Description

#### Prompt: "Describe this image in detail."

**Response**:
```
"The image captures a group of people gathered around a 
 dining table, with some of them standing closer to the 
 camera. The table is covered with a variety of items, 
 including a cup, a bowl, a spoon, and a fork. There are 
 also a few bottles scattered around the table..."
```

**분석**: ❌ **완전히 잘못 인식**
- "people" ← 없음!
- "dining table" ← 없음! (바닥에 박스만)
- "cup, bowl, spoon, fork" ← 없음!
- 실제 객체 (box, bottle, floor) 인식 못함

---

### Test 2: Object Detection

#### Prompt: "What objects do you see?"

**Response**:
```
"A woman <object><patch_index_0160><patch_index_0353></object>"
```

**분석**: ❌ **완전히 잘못됨**
- "A woman" ← 사람 없음!
- Grounding coordinates 있지만 잘못된 객체

---

### Test 3: Specific Questions

#### Q: "Is there a bottle in this image?"

**Response**:
```
"Yes, there is a bottle on the ground in the image."
```

**분석**: ✅ **부분 정답!**
- Bottle 존재 인식 ✅
- 위치 "on the ground" ✅ (맞음!)
- 하지만 beverage bottle인지는 모름

---

#### Q: "Is there a box in this image?"

**Response**:
```
"Yes, there is a box. It is located in the middle of the image."
```

**분석**: ✅ **부분 정답!**
- Box 존재 인식 ✅
- 위치 "middle of the image" ✅ (대략 맞음)
- Cardboard box인지는 모름

---

#### Q: "What color is the object?"

**Response**:
```
"The object is gray."
```

**분석**: ⚠️ **애매함**
- Gray ← 바닥을 말하는 건지?
- 박스는 갈색(brown/tan)
- Bottle은 투명/플라스틱

---

#### Q: "Describe the floor."

**Response**:
```
"The floor is a bit dirty."
```

**분석**: ✅ **맞음!**
- Floor 인식 ✅
- "a bit dirty" ← 실내 바닥 특성 포착

---

### Test 4: Captioning

#### Prompt: "An image of"

**Response**:
```
"An image of the interior of a building taken from the 
 interior. The image shows a large group of people 
 standing around a table..."
```

**분석**: ❌ **잘못됨**
- "interior of a building" ← 맞음 (실내)
- "people", "table" ← 완전히 잘못됨

---

#### RIGHT Image Prompt: "An image of"

**Response**:
```
"An image of the outside of the building taken from the video."
```

**분석**: ❌ **잘못됨**
- "outside" ← 틀림 (실내임)
- "from the video" ← ??

---

## 📊 종합 분석

### 인식 성공률

| 질문 유형 | 성공 | 실패 | 비율 |
|----------|------|------|------|
| **General Description** | 0 | 1 | 0% |
| **Object Detection** | 0 | 1 | 0% |
| **Specific Yes/No** | 2 | 0 | 100% |
| **Color** | 0 | 1 | 0% |
| **Floor** | 1 | 0 | 100% |
| **Captioning** | 0 | 2 | 0% |
| **Total** | 3 | 5 | 37.5% |

### 인식 가능한 것

✅ **Specific 질문에는 어느정도 답변**:
- "Is there a bottle?" → YES ✅
- "Is there a box?" → YES ✅
- "Describe the floor" → "dirty" ✅

### 인식 못하는 것

❌ **General description 완전히 잘못됨**:
- Hallucination: "people", "dining table", "chairs"
- 실제 없는 객체들 생성
- 로봇 환경 이해 못함

❌ **객체 특성 인식 못함**:
- Bottle type (beverage)
- Box type (cardboard)
- 정확한 색상

---

## 🔍 왜 이런 결과가 나왔나?

### 1. Training Data Mismatch

```
Kosmos-2 학습 데이터:
  - WebImage, COCO, Flickr 등
  - 사람 중심, 일상 생활 이미지
  - 정상 시점 (눈높이)
  - 밝은 조명, 다양한 배경

우리 데이터:
  - 로봇 환경
  - 바닥 중심, 객체 중심
  - 낮은 시점 (~30cm)
  - 실내 조명, 단순한 배경

→ Domain Gap 매우 큼!
```

### 2. Viewpoint Bias

```
일반 이미지: 눈높이 (150-170cm)
로봇 카메라: 바닥 높이 (20-40cm)

→ 같은 객체도 다르게 보임
→ Perspective 완전히 다름
```

### 3. Context Hallucination

```
Pretrained VLM:
  - "실내" + "바닥" → "사람이 있을 것"
  - "객체들" → "식탁일 것"
  - Prior knowledge가 강함
  
→ 실제 없는 것을 생성 (hallucination)
```

---

## 💡 Google Robot Pretrained는?

### 왜 Google Robot으로 학습했나?

```
Google Robot Pretrained:
  - Robot data로 학습됨 ✅
  - 로봇 시점 익숙함 ✅
  - 객체 manipulation 학습 ✅
  
→ 우리 환경과 더 가까움
→ Frozen VLM으로도 feature 추출 가능
```

### 하지만 여전히 한계

```
Google Robot:
  - Manipulation tasks (pick, place)
  - 테이블탑 환경
  - Object-centric
  
우리:
  - Navigation tasks
  - 바닥 환경
  - Space-centric
  
→ Task domain mismatch
→ Instruction grounding 어려움
```

---

## 🎯 결론

### Pretrained Kosmos-2의 객체 인식

**종합 평가**: ⭐⭐ (5점 만점에 2점)

```
✅ 장점:
  - Specific 질문에는 답변 가능
  - Bottle, box 존재 인식 가능
  - Floor 특성 포착

❌ 단점:
  - General description 완전 실패
  - Hallucination 심함 (people, table 등)
  - 객체 특성 인식 못함 (beverage, cardboard)
  - 로봇 환경 이해 부족
```

### 실용적 의미

#### For Instruction Following

```
Instruction: "Navigate to the beverage bottle on the LEFT"

VLM 이해:
  "bottle" ← ✅ 인식 가능
  "LEFT" ← ❓ 공간 관계는?
  "beverage" ← ❌ 특성 인식 못함

→ Instruction parsing은 가능
→ 하지만 정확한 이해는 어려움
```

#### For Vision Features

```
VLM Frozen → Feature Extraction

Features:
  - 객체 존재: 일부 포착
  - 공간 관계: 불확실
  - 세부 특성: 인식 못함
  
→ Feature quality 제한적
→ Action Head가 많이 배워야 함
```

---

## 📋 권장 사항

### 1. Frozen VLM 한계 인정

```
현재:
  - Kosmos-2 (또는 Google Robot) frozen
  - 객체 인식 제한적
  - Instruction grounding 어려움
  
→ 이 한계를 인지하고 설계
```

### 2. LoRA Fine-tuning 고려

```
LoRA:
  - Vision encoder: robot 환경 적응
  - Text encoder: robot instruction 적응
  - Cross-modal: bottle ↔ LEFT 연결
  
→ 객체 인식 향상 기대
```

### 3. 또는 Simpler Model

```
LoRA 없이:
  - Instruction-specific models (현재)
  - Vision-only architecture
  - Task-specific design
  
→ VLM complexity 우회
```

---

## 🔬 추가 테스트 제안

### Google Robot Pretrained로 테스트

```python
# Load Google Robot pretrained
checkpoint = "kosmos_ph_google-robot-post-train.pt"
model = load_pretrained_vlm(checkpoint)

# Same test
response = model.caption(image)

# 예상
- Manipulation-focused vocabulary
- Better robot viewpoint understanding
- But still not perfect for navigation
```

### Fine-tuned Model로 테스트

```python
# After LoRA fine-tuning
model = load_finetuned("left_lora.ckpt")

response = model.caption(image)

# 기대
- "box", "bottle" 정확히 인식
- "floor", "obstacle" 이해
- Spatial relations 개선
```

---

## 🎊 최종 평가

**Pretrained VLM (Kosmos-2)**:
- 일반 이미지: ⭐⭐⭐⭐⭐
- 로봇 환경: ⭐⭐ ← **우리 경우**
- Specific 질문: ⭐⭐⭐
- General scene: ⭐

**결론**:
> Pretrained VLM은 로봇 환경의 객체를 **부분적으로만** 인식  
> Frozen 상태로는 **Instruction grounding 어려움**  
> **LoRA fine-tuning 또는 Task-specific 설계 필요**

---

**테스트 이미지 위치**:
- `test_images/left_sample.jpg`
- `test_images/right_sample.jpg`

**재현 방법**: 위 스크립트 재실행
