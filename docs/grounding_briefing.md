# Grounding 조사 기술 브리핑

> 작성일: 2026-04-09  
> 대상: MoNaVLA V5 데이터셋 BBox-Centric 검증 파이프라인 설계

---

## 1. 세 가지 모델 옵션 비교

### 1.1 옵션 개요

| 모델 | 로딩 방식 | Backbone 구조 | Text Generation | Grounding 사용 가능 여부 |
|------|-----------|---------------|-----------------|--------------------------|
| **Pure HF Kosmos-2** | `AutoModelForVision2Seq.from_pretrained("microsoft/kosmos-2-patch14-224")` | 원본 HuggingFace 가중치 | 정상 — 자연어 생성 | **가능** |
| **Google-robot pretrained** | `MobileVLAInference` via `kosmos_ph_google-robot-post-train.pt` | `PeftModelForCausalLM` (LoRA wrapping) | 비정상 — garbage 출력 | **불가** |
| **V4 LoRA** | `MobileVLAInference` via V4 checkpoint | `PeftModelForCausalLM` (LoRA wrapping) | 비정상 — garbage 출력 | **불가** |

### 1.2 각 모델의 실제 출력 예시

**Pure HF Kosmos-2** (정상):
```
"The gray basket is located in the middle of the room."
Entity: "the gray box" | BBox: (0.33, 0.45) → (0.55, 0.83)
```

**Google-robot / V4 LoRA** (비정상):
```
"Ring Ring Ring Lighted Ring Light Ring Ring Ring Ring..."
```

---

## 2. 왜 순수 모델만 작동하는가: `image_to_text_projection` 오염 문제

### 2.1 구조 설명

Kosmos-2의 멀티모달 아키텍처는 세 구성 요소로 나뉜다:

```
Image Encoder (Vision)
       ↓
image_to_text_projection   ← 핵심 브릿지 레이어
       ↓
Text Decoder (Language Model)
       ↓
Grounding / Text Output
```

`image_to_text_projection`은 비전 feature를 언어 모델 토큰 공간으로 매핑하는 **브릿지 레이어**다. 이 레이어가 정상적으로 작동해야 이미지 정보가 텍스트 생성 경로에 올바르게 전달된다.

### 2.2 오염 메커니즘

Google-robot pretrained과 V4 LoRA 체크포인트는 **action prediction**을 위해 fine-tune된 모델이다.

- Action prediction 학습 목표: 이미지 + 지시문 → `[linear_x, linear_y, angular_z, ...]` 형태의 연속 action vector 예측
- 이 과정에서 `image_to_text_projection`이 **action 예측 목적에 맞게 재학습됨**
- 결과적으로 텍스트 생성 경로(`generate()`)에 비정상적인 feature가 입력됨

```
학습 전: image features → text tokens (grounding/caption 생성)
학습 후: image features → action features (텍스트 생성 불가)
```

### 2.3 LoRA 우회 시도의 실패

`backbone.base_model.model.generate()`를 통해 LoRA 레이어를 건너뛰어도 동일한 garbage 출력이 발생하는 이유:

1. LoRA adapter 자체도 action prediction 방향으로 수렴됨
2. `image_to_text_projection`은 LoRA 레이어가 아닌 **full fine-tune**으로 덮어씌워짐
3. 기반 모델 가중치 자체가 이미 오염되어 있음

따라서 fine-tuned 체크포인트에서 원본 grounding 능력을 복구하는 것은 **현실적으로 불가능**하며, 별도의 pure HF 모델을 로딩하는 것이 유일한 해결책이다.

---

## 3. 프롬프트 형식 비교

### 3.1 전체 비교표

V5 로봇 이미지(복도에 회색 바구니)를 동일 이미지에서 테스트한 결과:

| 프롬프트 | 검출된 entity 이름 | BBox | 유효 비율 | 평가 |
|----------|-------------------|------|-----------|------|
| `<grounding>An image of a robot. Where is the gray basket? Answer:` | "The room" | (0,0)→(1,1) 전체화면 | 1.8% | 실패 — 전체화면 hallucination |
| `<grounding><phrase>gray basket</phrase>` | `<patch_index_493>...` | (0.42,0.48)→(0.58,0.70) | 가변 | bbox는 정확하나 entity 이름 깨짐 |
| `<grounding>An image of <phrase>gray basket</phrase>` | `<patch_index_493>...` | (0.42,0.48)→(0.58,0.70) | 가변 | 위와 동일 |
| `<grounding>A gray basket is located at` | "a white wall" | 배경 위치 | 낮음 | 실패 — 배경 오검출 |
| `<grounding>The gray basket is at` | **"the gray box"** / **"The basket"** | (0.33,0.45)→(0.55,0.83) | **100%** | **최선** |

### 3.2 최종 채택 프롬프트: `<grounding>The gray basket is at`

```python
prompt = "<grounding>The gray basket is at"
```

**채택 이유:**

1. **Entity 이름 정확성**: "the gray box" 또는 "The basket" — 바구니를 올바르게 지칭함
2. **BBox 정확성**: 전체화면이 아닌 실제 객체 위치를 가리키는 좌표 반환
3. **유효 검출률 100%**: 테스트된 모든 프레임에서 non-fullscreen bbox 반환
4. **Completion-style prompting**: 문장을 완성하도록 유도하는 방식 → 모델이 specific location을 생성하려는 경향 활용

**`<phrase>` 태그 방식이 실패한 이유:**
- `<phrase>gray basket</phrase>` 방식은 entity 이름을 `<patch_index_N>` 형태의 포지셔널 토큰으로 치환함
- 이는 grounding token 생성 방식의 차이로, entity 이름 자체가 손실됨
- 분류/필터링 단계에서 entity 이름을 사용할 수 없게 됨

---

## 4. 최종 채택 접근법 요약

```
모델:   microsoft/kosmos-2-patch14-224 (HuggingFace, frozen)
프롬프트: "<grounding>The gray basket is at"
후처리:
  - fullscreen bbox (area > 0.90) 필터링
  - entity 이름으로 색상 분류
    - 초록: "basket", "box", "container" 포함
    - 노랑: "gray", "grey" 포함
    - 주황: 기타 (배경 오검출)
  - 유효 bbox만 v5_grounding.json에 저장
```

820 프레임(50 에피소드) 전수 실행 완료. 결과는 `ROS_action/v5_data_bak/v5_grounding.json` 에 저장됨.

---

## 5. 향후 개선 가능성

### 5.1 Grounding Head 별도 Fine-tune

현재 문제의 근본 원인은 action prediction fine-tuning이 `image_to_text_projection`을 덮어쓴다는 점이다. 이를 해결하려면:

```
옵션 A: image_to_text_projection을 frozen으로 유지하고 action head만 학습
         → V5 이후 학습 설계 시 고려 가능
         → 단점: action prediction 성능 저하 가능성

옵션 B: Dual-head 구조 설계
         - Grounding head: 원본 image_to_text_projection 유지
         - Action head: 별도 projection layer 추가
         → 구조 변경 필요, 메모리 증가

옵션 C: 현재 방식 유지 (pure HF + 별도 inference)
         → 가장 간단, action prediction 모델과 완전 분리
         → 단점: 추론 시 모델 두 개 로딩 필요
```

### 5.2 더 강력한 Grounding 모델 대안

| 모델 | 특징 | 비고 |
|------|------|------|
| Grounding DINO | Open-vocabulary object detection | 텍스트 쿼리 기반 bbox 검출에 특화 |
| OWL-ViT | Zero-shot detection | HuggingFace 지원 |
| Florence-2 | Grounding + Caption 통합 | Microsoft, Kosmos-2 후속 |

현재 Pure HF Kosmos-2 방식이 V5 검증 목적에는 충분하지만, 정밀도 향상이 필요할 경우 Grounding DINO나 Florence-2 도입을 검토할 수 있다.

### 5.3 단기 개선 사항

- **프롬프트 다양화**: 여러 프롬프트로 앙상블하여 검출률 향상
- **신뢰도 기반 필터링**: entity 이름 매칭 스코어를 정량화
- **에피소드별 BBox trajectory 시각화**: convergence 패턴을 자동 감지하는 알고리즘 추가
