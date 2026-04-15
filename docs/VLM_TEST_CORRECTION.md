# VLM 테스트 정정: 기본 Kosmos-2 vs Google Robot Pretrained

**중요 발견 일시**: 2026-01-14 00:01  
**문제**: 잘못된 VLM으로 테스트함

---

## ❌ 테스트 오류 발견

### 위에서 사용한 VLM

```python
model_path = ".vlms/kosmos-2-patch14-224"

→ 이것은 **기본 Kosmos-2** (Microsoft pretrained)
→ 일반 이미지 (ImageNet, WebText, COCO 등)로 학습
→ Google Robot이나 OXE pretrained가 **아님**!
```

---

## ✅ 우리가 실제 학습에 사용한 VLM

### Google Robot Pretrained

```python
Checkpoint: pretrained_ckpts/checkpoints/kosmos_ph_google-robot-post-train.pt

학습 데이터:
  - Google Robot dataset
  - Manipulation tasks (pick, place)
  - 7-DoF robot arm
  - Object-centric tasks
  
특징:
  ✅ Robot 환경 이미지로 학습됨
  ✅ Robot instructions 학습됨
  ✅ 우리 학습에 사용함 (Model_LEFT/RIGHT)
```

---

## 🔍 차이점 분석

### 기본 Kosmos-2 (위 테스트에서 사용)

```
Training Data:
  - 일반 웹 이미지
  - 사람, 동물, 자연, 도시 등
  - 눈높이 시점
  - 일상 생활 vocabulary
  
우리 데이터 이해:
  ❌ Robot 환경 생소함
  ❌ 바닥 시점 처음 봄
  ❌ Hallucination 심각
  
→ "people", "dining table" 등 잘못 인식
```

### Google Robot Pretrained (우리가 학습에 사용)

```
Training Data:
  - Robot manipulation 이미지
  - Pick, place, move tasks
  - 로봇 시점 (테이블탑)
  - Robot vocabulary ("gripper", "object" 등)
  
우리 데이터 이해 (예상):
  ✅ Robot 환경 익숙함
  ✅ 낮은 시점 경험 있음
  ⚠️ 하지만 navigation은 아님
  
→ Hallucination 덜함 (예상)
→ Object 인식 더 나음 (예상)
```

---

## 📊 예상 차이

### 기본 Kosmos-2 (위 테스트 결과)

| 질문 | 응답 | 평가 |
|------|------|------|
| "Describe image" | "people around table" | ❌ Hallucination |
| "Is there a bottle?" | "Yes, on ground" | ✅ 정답 |
| "What objects?" | "A woman" | ❌ 틀림 |

---

### Google Robot Pretrained (예상)

| 질문 | 예상 응답 | 평가 |
|------|-----------|------|
| "Describe image" | "robot workspace" / "objects on floor" | ✅ 더 정확할 것 |
| "Is there a bottle?" | "Yes" | ✅ 정답 (동일) |
| "What objects?" | "bottle, box" | ✅ Hallucination 덜할 것 |

---

## 💡 왜 이런 차이?

### Domain Adaptation

```
기본 Kosmos-2:
  ImageNet → COCO → WebImages
  → General vision understanding
  → Robot 환경은 out-of-distribution

Google Robot Pretrained:
  ImageNet → COCO → Google Robot Data
  → Robot-specific adaptation
  → Robot 환경에 더 적합
```

### Vocabulary Shift

```
기본 Kosmos-2:
  "people", "table", "chairs", "cup" 등
  → 일상 vocabulary

Google Robot:
  "gripper", "object", "workspace", "target" 등
  → Robot vocabulary
  → Hallucination 덜함
```

---

## 🎯 우리 학습에 미치는 영향

### Model_LEFT/RIGHT 학습

```python
# 우리가 사용한 것
Pretrained VLM: Google Robot ✅
학습 방식: Frozen VLM
학습 대상: Action Head only

VLM Features:
  - Google Robot에서 학습된 features
  - Robot 환경에 적응됨
  - Object detection capacity 있음
  
→ 기본 Kosmos-2보다 나은 features
→ 하지만 여전히 Frozen
→ Instruction grounding은 여전히 어려움
```

---

## 🔬 재테스트 필요성

### Google Robot Pretrained로 재테스트

```
Test 1: Object Recognition
  - "Is there a bottle?"
  - "Is there a box?"
  → 기본 Kosmos-2와 비교

Test 2: Scene Understanding
  - "Describe this image"
  → Hallucination 감소 확인

Test 3: Instruction Understanding
  - "Navigate to the bottle"
  → Robot instruction 이해도

Test 4: Spatial Reasoning
  - "Where is the bottle?"
  → 공간 관계 이해
```

---

## 📋 정정 사항

### 이전 테스트 결과 해석 수정

```
❌ 이전: "Pretrained VLM이 로봇 환경 못 알아봄"
✅ 수정: "**기본 Kosmos-2**가 로봇 환경 못 알아봄"
        "**Google Robot VLM**은 테스트 안함"

결론:
  - 이전 테스트는 worst-case scenario
  - Google Robot VLM은 더 나을 것으로 예상
  - 하지만 여전히 navigation task는 다름
```

---

## 🎊 결론

### 테스트 오류 인정

```
✅ 확인:
  - 위 테스트는 기본 Kosmos-2로 함
  - 우리가 학습에 사용한 것은 Google Robot
  - 두 개는 다름!

⚠️  영향:
  - 이전 테스트 결과는 worst-case
  - Google Robot VLM은 더 나을 것
  - 하지만 근본적 한계는 동일
    (Frozen VLM → Instruction grounding 어려움)
```

### 우리 설계 정당성 (여전히 유효)

```
✅ Instruction-specific models:
  - Google Robot VLM features 사용
  - Frozen이지만 robot-adapted
  - Instruction grounding 우회
  → 합리적!

✅ LoRA fine-tuning (권장):
  - Google Robot 기반
  - Navigation task 적응
  - 더 나은 결과 기대
```

---

## 📝 다음 단계

### 1. Google Robot VLM 재테스트 (시간 있을 때)

```python
# RoboVLMs framework 사용
trainer = MobileVLATrainer.from_pretrained(
    "pretrained_ckpts/checkpoints/kosmos_ph_google-robot-post-train.pt"
)

# VLM 접근
vlm = trainer.model.backbone

# Test
response = vlm.generate_caption(image)
```

### 2. 결과 비교

```
기본 Kosmos-2 vs Google Robot VLM
  → Hallucination 차이
  → Object recognition 차이
  → Scene understanding 차이
```

### 3. 문서 업데이트

```
이전 테스트 결과에 disclaimer 추가
Google Robot 테스트 결과 추가
```

---

## 🎯 핵심 교훈

```
⚠️  VLM 테스트 시 주의사항:
1. 어떤 pretrained model 사용했는지 명확히
2. Training data domain 확인
3. 우리 학습에 사용한 것과 일치하는지 확인

✅ 올바른 비교:
- 기본 Kosmos-2: General images
- Google Robot: Robot manipulation
- OXE: Multi-embodiment robot
→ 각각 다른 domain!
```

---

**요약**:
- ❌ 위 테스트: 기본 Kosmos-2 (일반 이미지)
- ✅ 우리 학습: Google Robot (robot manipulation)
- 🔄 재테스트: Google Robot VLM 필요
- 💡 결론: 이전 테스트는 worst-case였음
