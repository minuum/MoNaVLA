# Google Robot Pretrained VLM 테스트 결과

**테스트 일시**: 2026-01-14 00:10  
**모델**: Google Robot Pretrained VLM (kosmos_ph_google-robot-post-train.pt)  
**데이터**: 실제 Mobile VLA 데이터셋 이미지

---

## ⚠️ 중요 발견: Weights 로딩 실패

### Checkpoint 구조 문제

```python
Checkpoint keys: 20개만 추출됨

Weight loading:
  Missing: 886 keys
  Unexpected: 20 keys
  
→ Google Robot weights가 제대로 로딩 안됨!
→ 기본 Kosmos-2 weights 그대로 유지됨
```

### 원인 분석

```
Google Robot checkpoint:
  - RoboVLMs framework 전용 형식
  - VLM + Action Head 통합 저장
  - Key prefix가 다름 ('backbone.', 'model.' 등)
  
Hugging Face Kosmos-2:
  - 표준 transformers 형식
  - Key 구조가 다름
  
→ Direct loading 불가능!
```

---

## 📊 테스트 결과 (실제로는 기본 Kosmos-2)

### ❌ 결과 무효

**실제로 테스트된 것**:
```
Google Robot VLM (X)
→ 기본 Kosmos-2 (O) ← weights 로딩 실패로

결론: 위 테스트는 기본 Kosmos-2와 동일
```

### 응답 예시 (기본 Kosmos-2와 동일)

```
Q: "Describe this image"
A: "people gathered around a dining table..."
   ← Hallucination (기본 Kosmos-2와 동일!)

Q: "Is there a bottle?"
A: "Yes, there is a bottle... there is a person..."
   ← Hallucination 포함

Q: "An image of"
A: "interior of a building... group of people standing around table..."
   ← 기본 Kosmos-2와 완전 동일
```

---

## 🔍 Google Robot VLM 제대로 테스트하기

### 올바른 방법

#### Method 1: RoboVLMs Framework 사용 (권장)

```python
# RoboVLMs trainer를 통해 로드
from robovlms.train.mobile_vla_trainer import MobileVLATrainer

# Config 준비 (VLM만 로드하도록 설정)
config = {
    "load_vlm_only": True,  # Action Head 제외
    "pretrained_vlm_path": "kosmos_ph_google-robot-post-train.pt",
    ...
}

# Load
trainer = MobileVLATrainer.from_checkpoint(
    ckpt_path=checkpoint_path,
    configs=config
)

# VLM access
vlm = trainer.model.backbone

# Generate
outputs = vlm.generate(...)
```

#### Method 2: Weight Mapping 수정

```python
# Checkpoint 구조 분석
checkpoint = torch.load(ckpt_path)

# Key mapping 필요
# 'backbone.vision_model.embeddings.patch_embedding.weight'
# → 'vision_model.embeddings.patch_embedding.weight'

# Correct mapping 후 load
```

---

## 💡 왜 이런 일이?

### RoboVLMs의 특수한 Checkpoint 구조

```
RoboVLMs checkpoint:
{
  'buffer_names': [...],
  'param_shapes': {...},
  'frozen_param_shapes': {...},
  'shared_params': [...],
  'frozen_param_fragments': {...},  ← VLM weights 여기 있음!
  ...
}

→ 일반 state_dict가 아님!
→ 특별한 loading 로직 필요
```

### Our Attempt

```
우리 시도:
  1. checkpoint.items()로 직접 추출
  2. 20개 key만 추출됨 (metadata만)
  3. VLM weights (frozen_param_fragments) 추출 못함
  
→ Weights 로딩 실패
→ 기본 Kosmos-2로 테스트됨
```

---

## 🎯 실제로 확인하려면?

### Plan A: RoboVLMs 코드 분석

```bash
# base_backbone.py 확인
# - load_pretrained_weights() 메서드
# - frozen_param_fragments 처리 로직

# 이 로직을 직접 구현하거나
# RoboVLMs framework 그대로 사용
```

### Plan B: 학습된 Model_LEFT/RIGHT 사용

```python
# 우리가 이미 학습한 모델
checkpoint = "runs/mobile_vla_left_only/epoch=08.ckpt"

# 이 모델은:
  - Google Robot VLM로 initialized
  - Frozen VLM features
  - 실제 사용됨
  
# VLM 접근
trainer = MobileVLATrainer.load_from_checkpoint(checkpoint)
vlm = trainer.model.backbone

# 이것이 실제 Google Robot VLM!
```

---

## 📋 결론

### 테스트 실패 인정

```
시도: Google Robot VLM 테스트
실제: Weights 로딩 실패
결과: 기본 Kosmos-2로 테스트됨

→ 결과 무효
→ Google Robot VLM 제대로 테스트 못함
```

### 올바른 Google Robot VLM 테스트

```
Option 1: Model_LEFT/RIGHT checkpoint 사용
  - 이미 Google Robot VLM weights 포함
  - Frozen상태로 학습됨
  - 진짜 Google Robot VLM

Option 2: RoboVLMs loading 로직 사용
  - frozen_param_fragments 올바르게 로딩
  - 복잡하지만 정확함
```

---

## 💭 실용적 의미

### 우리가 실제로 사용한 것

```
Model_LEFT/RIGHT 학습:
  ✅ Google Robot VLM (pretrained)
  ✅ Frozen weights  
  ✅ Feature extraction
  
→ 이것이 진짜 Google Robot VLM
→ 이미 우리 모델에 포함됨
```

### Google Robot vs 기본 Kosmos-2 차이

```
알고 있는 것:
  - Google Robot: Robot data로 학습됨
  - 기본 Kosmos-2: 일반 이미지로 학습됨
  
예상:
  - Google Robot이 더 나을 것
  - Hallucination 덜할 것
  - Robot vocabulary 사용할 것
  
하지만 아직 직접 확인 못함!
```

---

## 🔬 다음 단계

### Option A: Model_LEFT로 VLM 테스트 (실용적)

```python
# Load trained model
model_left = load_checkpoint("runs/mobile_vla_left_only/epoch=08.ckpt")

# Extract VLM
google_robot_vlm = model_left.backbone  # 이게 진짜!

# Test
response = google_robot_vlm.generate(...)
```

### Option B: RoboVLMs 로직 분석 (정확)

```python
# Study: RoboVLMs_upstream/robovlms/model/backbone/base_backbone.py
# - How frozen_param_fragments works
# - Implement correct loading

# Then test properly
```

---

## 🎊 최종 정리

### 오늘 테스트한 것들

| 테스트 | 실제 사용한 VLM | 결과 |
|--------|----------------|------|
| **Test 1** | 기본 Kosmos-2 | ✅ 완료 (hallucination 심함) |
| **Test 2** | Google Robot (시도) | ❌ 실패 (weights 로딩 안됨) |
| **Test 2 실제** | 기본 Kosmos-2 | ✅ 동일 결과 |

### 확인된 사실

```
✅ 기본 Kosmos-2:
  - 로봇 환경 못 알아봄
  - Hallucination 심각 ("people", "table")
  - Specific 질문은 일부 가능

❓ Google Robot VLM:
  - 제대로 테스트 못함
  - Weights 로딩 실패
  - 올바른 방법 필요
```

### 우리 설계에 미치는 영향

```
Model_LEFT/RIGHT:
  ✅ Google Robot VLM 사용 (frozen)
  ✅ 이미 우리 checkpoint에 포함됨
  ✅ Feature extraction으로 작동
  
→ 설계는 올바름
→ Google Robot VLM이 기본 Kosmos-2보다 나을 것으로 기대
→ 하지만 직접 비교는 못함 (아직)
```

---

**요약**:
- Google Robot VLM 직접 테스트: ❌ 실패
- Weights 로딩 문제로 기본 Kosmos-2와 동일
- 올바른 테스트는 Model_LEFT checkpoint 사용 또는 RoboVLMs 로직 구현 필요
- 우리 학습은 Google Robot VLM을 정상적으로 사용 중 (RoboVLMs framework 통해)
