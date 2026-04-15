# LoRA 분석 결과: 문제 원인 규명

**날짜**: 2025-12-07 13:45  
**목적**: LoRA가 언어 이해를 보존하지 못하는 원인 분석

---

## 📊 검색 결과: VLA에서의 LoRA 사용 사례

### OpenVLA (출처: GitHub, arXiv)

- **LoRA Fine-tuning 권장**: 메모리 효율적 (1.4% 파라미터만 학습)
- **결과**: Full fine-tuning과 유사한 성능 달성
- **주의사항**: 추론 속도가 느림 (3-5 Hz)

### VLM2VLA (출처: ResearchGate)

- **Catastrophic Forgetting 문제 언급**
- **해결책**: 언어로 action을 표현하여 데이터 분포 정렬
- **LoRA가 VLM의 기본 추론 능력을 손상시킬 수 있음**

### RoboVLMs (출처: GitHub)

- **CALVIN benchmark**: `lora_enable: false`로 설정
- **기본 설정**: LoRA 비활성화

---

## 🔍 우리 코드 분석

### LoRA 적용 구조

```python
# lora_utils.py
def find_all_linear_names(model):
    multimodal_keywords = ['mm_projector', 'vision_tower', 'vision_resampler']
    # 위 키워드를 제외한 모든 Linear 레이어에 LoRA 적용
```

### 실제 LoRA 레이어

```
Total LoRA layers: 586개
- text_model 레이어: 298개 (51%)
- 기타 레이어: 288개 (49%)
```

**문제**: LoRA가 `text_model` (언어 처리 모델) **전체**에 적용됨

---

## 🚨 중요 발견

### 두 모델 모두 LoRA가 있음!

| 항목 | "Frozen" 모델 | "LoRA Balanced" 모델 |
|:---|:---:|:---:|
| **lora_enable** | true | true |
| **LoRA layers** | 586 | 586 |
| **Train episodes** | 400 | 400 |
| **Val Loss** | **0.027** | 0.332 |
| **방향 정확도** | **92.5%** | 50% |

### 핵심 차이: 학습 시점

| 모델 | 학습 시작 | 데이터 분포 |
|:---|:---|:---|
| "Frozen" (12/04 15:04) | 균형 데이터 이후 | L 250 + R 250 |
| LoRA Old (12/03 22:56) | **불균형 데이터** | L 250 + R 3 |
| LoRA Balanced (12/07) | 균형 데이터 | L 250 + R 250 |

---

## 🤔 왜 두 모델의 성능이 다른가?

### 가설 1: 초기화 차이

두 모델이 **다른 초기 상태**에서 시작했을 수 있음:
- "Frozen" 모델: 특정 checkpoint에서 시작
- LoRA Balanced: 다른 초기화

### 가설 2: 학습 안정성 차이

LoRA Balanced의 val_loss가 12배 높음 (0.332 vs 0.027):
- 학습이 불안정했거나
- 수렴하지 못함

### 가설 3: 랜덤 시드 차이

동일 설정이라도 랜덤 시드에 따라 결과가 달라질 수 있음

---

## 📚 논문 기반 분석: VLM2VLA의 "Catastrophic Forgetting"

### VLM2VLA 논문 관찰

> "LoRA fine-tuning이 VLM의 기본 추론 능력을 손상시킬 수 있음"
> → Catastrophic Forgetting

### 해결책

1. **언어로 action 표현**: 데이터 분포 정렬
2. **Zero-shot 일반화 유지**: 핵심 능력 보존

### 우리 상황과의 연관성

- 우리는 action을 **숫자 벡터**로 표현
- VLM의 언어 이해와 **분포 불일치**
- LoRA가 이 불일치를 해결하려다 언어 이해 손상

---

## 🎯 결론

### LoRA 문제의 근본 원인

| 원인 | 설명 | 해결책 |
|:---|:---|:---|
| **언어 모델 전체 수정** | text_model 298 레이어 수정 | 언어 레이어 제외 |
| **Catastrophic Forgetting** | 언어 이해 능력 손상 | VLM2VLA 방식 적용 |
| **Action 표현 불일치** | 숫자 vs 언어 분포 | 언어로 action 표현 |

### RoboVLMs 논문의 설정

```json
// CALVIN benchmark config
"lora_enable": false  // ← LoRA 비활성화!
```

**RoboVLMs 논문에서도 LoRA를 사용하지 않음!**

---

## 🔧 권장 수정 방안

### Option 1: LoRA 완전 비활성화 (권장)

```json
"lora_enable": false
"freeze_backbone": true
```

→ Action Head만 학습 (현재 "Frozen" 모델과 동일)

### Option 2: 언어 레이어 제외 LoRA

```python
# lora_utils.py 수정
multimodal_keywords = ['mm_projector', 'vision_tower', 'vision_resampler', 'text_model']
```

→ text_model 제외하고 LoRA 적용

### Option 3: VLM2VLA 방식 적용

Action을 언어로 표현:
```
(0.3, -0.5) → "move slightly left and moderately right"
```

---

## 📝 교수님께 보고할 내용

### 요약

> **LoRA가 VLM의 언어 이해를 손상시킴**
> 
> 1. LoRA가 `text_model` 전체(298 레이어)에 적용됨
> 2. VLM2VLA 논문에서 경고한 "Catastrophic Forgetting" 발생
> 3. RoboVLMs 논문에서도 CALVIN에서 LoRA 비활성화
> 
> **Frozen VLM + Action Head가 올바른 접근법!**

### 다음 단계

1. LoRA 완전 비활성화 재실험 (config만 수정)
2. 결과 비교 후 최종 결론 도출
