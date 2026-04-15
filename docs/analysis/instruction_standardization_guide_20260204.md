# 지시어 표준화 가이드 (Instruction Standardization Guide)

**작성일**: 2026-02-04  
**대상 모델**: `basket_grounding_v1` (Phase 5 - Mixed Grounding)  
**배경**: 모델이 지시어와 시각 정보를 동시에 고려하기 시작함에 따라, 모델이 가장 명확하게 반응하고 오작동이 적은 표준 지시어(Prompt) 정의가 필요함.

---

## 1. 권장 표준 지시어 (Recommended Prompts)

테스트 결과, 모델은 '행동(Action)'을 직접적으로 강조하는 지시어에 더 민감하게 반응합니다.

### ✅ 가장 성능이 좋은 지시어 (Primary)
*   **Left**: `Steer left to the brown pot`
*   **Right**: `Steer right to the brown pot`
*   **Straight**: `Go straight to the brown pot` (현재 학습 반영 중)

### ✅ 보조 지시어 (Secondary)
*   **Left**: `Perform left navigation to the object`
*   **Right**: `Perform right navigation to the object`

---

## 2. 주의 및 피해야 할 지시어 (Avoid/Caution)

### ❌ 모호한 설명 (Vague Descriptions)
*   `Navigate to the brown pot on the left`
    *   **이유**: 'on the left'를 장소 설명으로만 인식하고 행동 명령으로 강하게 받아들이지 않아, 시각적 편향(Visual Bias)에 의해 반대 방향으로 갈 위험이 있음.

### ❌ 학습되지 않은 지시어
*   `Turn left`, `Slide right`
    *   **이유**: 학습 데이터셋(Phase 5)에서 사용된 동사가 아니므로 반응성이 떨어질 수 있음.

---

## 3. 지능적 판단 특징 (Grounding Behavior)

본 모델은 **"시각 정보 우선 원칙"**을 따릅니다.

*   **Conflict Resolution**: 화분이 오른쪽에 있는데 "Steer left"라고 명령할 경우, 모델은 명령을 무시하고 오른쪽(`Right`)으로 가거나 정지(`Stop`)하는 안전한 선택을 하려는 경향이 있음.
*   **Robustness**: 이는 엉뚱한 명령에 로봇이 사고를 내지 않도록 보호하는 긍정적인 '지능적 필터' 역할을 함.

---

## 4. API 적용 가이드

로봇 클라이언트(Jetson/ROS)에서 요청을 보낼 때, 지시어를 단순히 `left`로 보내지 말고 위 표준 프롬프트를 사용하여 래핑(Wrapping)하는 것이 최적의 성능을 보장함.

```python
# API 요청 예시
def get_action(direction):
    prompt_map = {
        "left": "Steer left to the brown pot",
        "right": "Steer right to the brown pot",
        "straight": "Go straight to the brown pot"
    }
    return call_vla_api(instruction=prompt_map[direction])
```

---

## 5. 결론 및 향후 계획

현재 모델은 **"동사 + 방향 + 목적지"** 구조에서 가장 안정적인 성능을 보입니다. 향후 "목적지(Object)"가 다양해질 경우를 대비해, 지시어 템플릿의 유연성을 확장하는 Phase 6 학습을 고려 중입니다.
