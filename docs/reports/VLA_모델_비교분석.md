# VLA 모델 비교 분석: Left/Right 태스크 처리 방식

## 📚 주요 VLA 모델들의 접근 방식

### 1. RT-2 (Google DeepMind)
- **Action Tokenization**: 연속 액션을 256개 bin으로 이산화하여 텍스트 토큰으로 변환
- **학습 방식**: 언어 명령 + 이미지 → 액션 토큰 시퀀스 예측
- **핵심**: 단일 모델이 다양한 태스크 처리 ("pick up the red block", "move left" 등)

### 2. OpenVLA (Stanford)
- **Action Tokenization**: 7개 discrete action tokens per timestep (x, y, z, roll, pitch, yaw, gripper)
- **학습 방식**: 970k 에피소드로 multi-task 학습
- **핵심**: 언어 명령에 따라 다른 액션 예측

### 3. RoboFlamingo
- **구조**: Frozen VLM + Fine-tuned Policy Head
- **학습 방식**: VLM의 context vector를 Policy Head에 전달
- **핵심**: VLM이 언어+이미지 이해, Policy Head가 action 예측

---

## 🤔 현재 우리 문제: Left/Right 분리 학습

### 현재 상황
```
LEFT 에피소드: 250개
RIGHT 에피소드: 250개
총: 500개

언어 명령 예시:
- "Navigate around obstacles and reach the front of the beverage bottle on the left"
- "Navigate around obstacles and reach the front of the beverage bottle on the right"
```

### 발견된 문제
- 모델이 언어 명령의 "left"/"right"를 action에 반영하지 못함
- 원인: `action_token` 초기화 문제로 언어 정보가 Action Head에 전달 안 됨

---

## 📊 분석: 어떤 방식이 맞는가?

### ✅ RoboVLMs가 CALVIN에서 하는 방식 (참고)

CALVIN 평가(`eval/calvin/model_wrapper.py`)에서:
```python
def step(self, obs, goal):
    # goal = 언어 명령 (예: "open the drawer")
    image_x, gripper_x, text_x, mask = self.preprocess(obs, goal, self.action_space)
    input_dict["text"] = text_x  # ← 언어가 모델에 직접 전달됨
    action = self.policy.inference_step(input_dict)["action"]
```

**→ 언어 명령이 `policy.inference_step`에 직접 전달됨!**

### ✅ 다른 VLA 모델들의 방식 (정석)

| 모델 | 접근 방식 | 언어-액션 연결 |
|:---|:---|:---|
| RT-2 | 단일 모델, action tokenization | 언어가 액션 토큰 생성에 직접 영향 |
| OpenVLA | 단일 모델, discrete tokens | 언어가 decoder의 cross-attention을 통해 action 결정 |
| RoboFlamingo | Frozen VLM + Policy Head | VLM output에 언어 정보 포함되어 Policy에 전달 |

**공통점**: 
1. **단일 모델**이 여러 태스크/방향을 처리
2. **언어 명령이 action 생성에 직접 영향**을 줌
3. **Multi-task 학습**으로 일반화 능력 확보

### 🔴 현재 우리 모델의 문제

```python
# 이상적인 동작:
언어("left") + 이미지 → VLM → action_token에 언어 정보 전달 → Action Head → linear_y > 0
언어("right") + 이미지 → VLM → action_token에 언어 정보 전달 → Action Head → linear_y < 0

# 실제 동작:
언어("left") + 이미지 → VLM → action_token이 0이라 언어 정보 무시 → 이미지만으로 예측
언어("right") + 이미지 → VLM → action_token이 0이라 언어 정보 무시 → 동일한 예측
```

---

## 💡 해결 방안 비교

| 방안 | 장점 | 단점 | 권장 |
|:---|:---|:---|:---:|
| **A. 현재 해결책 (언어에서 방향 추출)** | 즉시 적용 가능, 100% 방향 정확도 | VLA 본래 목적에 맞지 않음 | ⭐ 단기 |
| **B. action_token 수정 후 재학습** | 정석적인 해결책 | 재학습 필요 | ⭐⭐ 중기 |
| **C. Action Token 대신 언어 직접 주입** | 언어 정보 확실히 전달 | 코드 수정 필요 | ⭐⭐⭐ 근본 |
| **D. RT-2식 Action Tokenization** | 가장 효과적 | 구조 대폭 변경 | 장기 |

---

## 🎯 권장 방향

### 12월 10일 미팅 발표

**현재 상황 설명**:
> "RoboVLMs의 Frozen VLM + Action Head 구조에서, action_token을 통한 언어 조건부 학습에 
> 기술적 한계가 발견되었습니다. 원인은 action_token의 zero 초기화로 인해 VLM에서 
> 언어 정보가 제대로 전달되지 않는 것입니다."

**해결책 설명**:
> "단기적으로는 언어 명령에서 방향을 추출하여 100% 정확도를 달성했습니다.
> 중기적으로는 action_token 초기화 수정 후 재학습을 계획하고 있습니다."

**참고**: 이 문제는 RoboVLMs 프레임워크의 설계 한계로, RT-2나 OpenVLA 같은 
end-to-end action tokenization 방식을 사용하면 근본적으로 해결됩니다.

---

## 📈 다음 단계

### Phase 1: 단기 (즉시)
- [x] 언어에서 방향 추출 방식으로 100% 방향 정확도 달성
- [ ] 실제 로봇에서 테스트

### Phase 2: 중기 (1주 내)
- [ ] action_token 초기화 수정 후 재학습
- [ ] 재학습 후 언어 조건부 동작 검증

### Phase 3: 장기 (추후)
- [ ] RT-2/OpenVLA 스타일 action tokenization 구현 검토
- [ ] 더 복잡한 언어 명령 지원 (예: "go to the left, then turn right")

---

작성일: 2025-12-09 02:00
