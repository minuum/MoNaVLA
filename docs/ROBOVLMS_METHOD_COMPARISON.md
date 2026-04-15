# RoboVLMs 원래 학습 방법 vs 우리 방법 비교

**작성일**: 2026-01-11  
**목적**: 우리 학습이 RoboVLMs 원래 방식과 일치하는지 확인

---

## 핵심 발견: **우리는 RoboVLMs 방식과 완전히 다르게 학습함!**

---

## 1. 핵심 차이점

### RoboVLMs 공식 방법 (CALVIN Fine-tuning)

```json
"train_setup": {
    "freeze_backbone": false,      // ← VLM도 학습!
    "train_vision": true,          // ← Vision encoder 학습
    "train_text_embedding": true,  // ← Text encoder 학습
    "lora_enable": false           // ← LoRA 사용 안함 (Full fine-tuning)
}
```

**의미**: 
- ✅ VLM 전체를 함께 학습
- ✅ Vision + Text + Action Head 모두 학습
- ✅ **Full fine-tuning**

---

### 우리 방법

```json
"train_setup": {
    "freeze_backbone": true,       // ← VLM Frozen!
    "train_vision": false,         // ← Vision encoder frozen
    "train_text_embedding": false, // ← Text encoder frozen
    "lora_enable": false          // ← LoRA도 사용 안함
}
```

**의미**:
- ❌ VLM 완전히 frozen
- ❌ Vision/Text 학습 안함
- ❌ **Action Head만 학습**

---

## 2. 상세 비교표

| 항목 | RoboVLMs 원래 | 우리 방법 | 일치 여부 |
|------|---------------|----------|----------|
| **freeze_backbone** | **false** | **true** | ❌ **불일치** |
| **train_vision** | **true** | **false** | ❌ **불일치** |
| **train_text_embedding** | **true** | **false** | ❌ **불일치** |
| lora_enable | false | false | ✅ 일치 |
| window_size | 8 | 8 | ✅ 일치 |
| fwd_pred_next_n | 10 | 5 | ⚠️ 다름 |
| action_dim | 7 (6DoF+gripper) | 2 (2DoF) | ⚠️ 다름 (의도) |
| batch_size | 41 | 1 | ⚠️ 다름 |
| learning_rate | 2e-5 | 1e-4 | ⚠️ 다름 |
| optimizer | adam | adamw | ⚠️ 다름 |

---

## 3. RoboVLMs가 Pretrained Checkpoint를 만드는 방법

### 과정

```
Step 1: Microsoft Kosmos-2 (General VLM)
          ↓
      [Full Fine-tuning on Robot Data]
      - Vision encoder: 학습
      - Text encoder: 학습  
      - Action Head: 학습
          ↓
Step 2: Google Robot Pretrained Checkpoint
        (kosmos_ph_google-robot-post-train.pt)
```

**핵심**:
- RoboVLMs pretrained checkpoint는 **VLM도 함께 학습**된 것
- `freeze_backbone: false`로 학습
- **Robot domain에 최적화된 VLM**

---

### 우리가 한 것

```
Step 1: Microsoft Kosmos-2 (General VLM)
          ↓
Step 2: Google Robot Pretrained (VLM만 로드)
          ↓
      [VLM Frozen, Action Head만 학습]
      - Vision encoder: Frozen
      - Text encoder: Frozen
      - Action Head: 학습 (2DoF)
          ↓
Step 3: 우리 Checkpoint
```

**문제**:
- RoboVLMs VLM은 **robot data로 fine-tuned**
- 하지만 우리는 그 VLM을 **다시 frozen**
- **Fine-tuned VLM의 장점을 활용 못함**

---

## 4. 우리 방법이 RoboVLMs와 다른 이유

### 4.1 메모리 제한

```
RoboVLMs:
  - batch_size=41, DeepSpeed Stage 2
  - Multi-GPU training
  - 메모리: ~40GB+ 필요

우리:
  - batch_size=1, Single GPU (RTX A5000 24GB)
  - 메모리: ~4.6GB 사용
  - VLM frozen으로 메모리 절약
```

**의도**: 메모리 제약으로 VLM frozen

---

### 4.2 Transfer Learning 전략

```
우리 의도:
  "Pretrained VLM의 지식을 재사용하자"
  → VLM frozen + Action Head 학습
  
RoboVLMs 방식:
  "VLM을 robot data로 fine-tuning하자"
  → VLM + Action Head 모두 학습
```

**결과**: 완전히 다른 접근

---

## 5. 문제의 근본 원인 재분석

### 우리가 생각한 것

```
RoboVLMs Pretrained VLM
  → "이미 robot instruction 이해 가능"
  → VLM frozen해도 instruction grounding 됨
  → Action Head만 학습하면 됨
```

**잘못된 가정**!

---

### 실제 RoboVLMs 방식

```
RoboVLMs Pretrained VLM
  → "Robot data로 VLM을 fine-tuning한 결과물"
  → 하지만 새로운 task에서는
  → VLM을 다시 fine-tuning 해야 함!
  → freeze_backbone: false
```

**핵심**:
- Pretrained VLM ≠ "바로 사용 가능"
- Pretrained VLM = "좋은 초기화"
- **여전히 fine-tuning 필요**

---

## 6. RoboVLMs의 실제 사용 방법

### From Scratch Training

```json
{
  "model_load_path": null,  // Scratch
  "train_setup": {
    "freeze_backbone": false,
    "train_vision": true,
    "train_text_embedding": true
  }
}
```

---

### Pretrained Checkpoint Fine-tuning

```json
{
  "model_load_path": "kosmos_ph_google-robot.pt",  // Pretrained
  "train_setup": {
    "freeze_backbone": false,  // ← 여전히 false!
    "train_vision": true,      // ← 여전히 학습!
    "train_text_embedding": true
  }
}
```

**핵심**: 
- Pretrained checkpoint를 사용해도
- **VLM은 계속 fine-tuning함**
- **Frozen하지 않음**

---

## 7. 우리가 해야 했던 방법

### 옵션 A: RoboVLMs 원래 방식 (Full Fine-tuning)

```json
{
  "pretrained_vlm_path": "kosmos_ph_google-robot.pt",
  "train_setup": {
    "freeze_backbone": false,      // ← Unfreeze!
    "train_vision": true,          // ← 학습
    "train_text_embedding": true,  // ← 학습
    "lora_enable": false
  }
}
```

**장점**:
- ✅ RoboVLMs 방식과 일치
- ✅ Instruction grounding 가능
- ✅ VLM이 mobile VLA task에 최적화

**단점**:
- ❌ 메모리 많이 필요 (~40GB)
- ❌ 학습 느림

---

### 옵션 B: LoRA Fine-tuning (메모리 효율적)

```json
{
  "pretrained_vlm_path": "kosmos_ph_google-robot.pt",
  "train_setup": {
    "freeze_backbone": false,  // ← Unfreeze!
    "lora_enable": true,       // ← LoRA 사용
    "lora_r": 16,
    "lora_alpha": 32,
    "train_vision": true,      // LoRA adapters만
    "train_text_embedding": true
  }
}
```

**장점**:
- ✅ 메모리 효율적 (~8GB)
- ✅ Instruction grounding 가능
- ✅ VLM fine-tuning (LoRA로)

**단점**:
- ⚠️ Full fine-tuning보다 성능 약간 낮을 수 있음

---

## 8. 결론

### Q: 우리 학습이 RoboVLMs 원래 방식과 일치하는가?

**A: 아니오.** ❌

| 측면 | RoboVLMs | 우리 |
|------|----------|------|
| **VLM 학습** | ✅ 학습 | ❌ **Frozen** |
| **Vision 학습** | ✅ 학습 | ❌ **Frozen** |
| **Text 학습** | ✅ 학습 | ❌ **Frozen** |
| **방식** | Full fine-tuning | **Action Head만** |

---

### 우리 방법의 문제점

```
RoboVLMs 방식:
  Pretrained VLM → Fine-tuning → Instruction grounding ✅

우리 방식:
  Pretrained VLM → Frozen → Instruction grounding ❌
```

**근본 원인**:
- RoboVLMs는 **VLM도 함께 fine-tuning**
- 우리는 **VLM을 frozen**
- **완전히 다른 접근**

---

### 왜 이렇게 했는가?

1. **메모리 제약**
   - Single GPU (24GB)
   - VLM frozen으로 절약

2. **잘못된 가정**
   - "Pretrained VLM은 바로 사용 가능"
   - 실제: "Fine-tuning 필요"

---

### 해결책

**즉시 구현**: LoRA Fine-tuning

```json
{
  "train_setup": {
    "freeze_backbone": false,  // ← RoboVLMs처럼
    "lora_enable": true,       // ← 메모리 절약
    "lora_r": 16,
    "lora_alpha": 32,
    "train_vision": true,
    "train_text_embedding": true
  }
}
```

**예상 결과**:
- RoboVLMs 방식에 근접
- Instruction grounding 성공
- 메모리 효율적

---

## 9. 최종 답변

### "원래의 RoboVLMs 학습과 맞는 형태인가?"

**No.** ❌

**RoboVLMs 원래 방식**:
```
VLM Fine-tuning (freeze_backbone=false)
+ Action Head 학습
= 모두 학습
```

**우리 방식**:
```
VLM Frozen (freeze_backbone=true)
+ Action Head만 학습
= Action Head만 학습
```

**차이**: **VLM 학습 여부** (가장 중요!)

---

### 올바른 방법

```json
// RoboVLMs 방식 (메모리 없으면 LoRA로 대체)
{
  "freeze_backbone": false,
  "train_vision": true,
  "train_text_embedding": true,
  "lora_enable": true  // 메모리 절약용
}
```

**결론**: 
- ❌ 우리 방식 ≠ RoboVLMs 방식
- ✅ LoRA fine-tuning이 올바른 방법
- 🎯 Instruction grounding을 위해 **VLM 학습 필수**
