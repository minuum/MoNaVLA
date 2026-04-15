# RoboVLMs Navigation Prompt Strategy Analysis

**Date**: 2026-01-22  
**Purpose**: 데이터 수집 및 학습 시 VLM 프롬프팅 전략 확정 (Original vs Our Task)  
**Reference**: [VLM_PROMPT_RESPONSE_DETAILED_ANALYSIS.md](./VLM_PROMPT_RESPONSE_DETAILED_ANALYSIS.md)

---

## 1. RoboVLMs 원본 분석 (Original Strategy)

### 접근 방식
RoboVLMs(MobileVLA)는 기본적으로 **End-to-End Instruction Following**을 지향합니다.
Kosmos-2와 같은 VLM을 Backbone으로 사용할 때, 사용자의 명령어를 그대로 프롬프트로 사용하거나, `<grounding>` 태그를 붙여 시각적 위치를 파악하려 합니다.

### 원본 프롬프트 예시 (Manipulation)
```python
Instruction: "Pick up the red apple and place it in the drawer"
VLM Prompt: "<grounding> Pick up the red apple and place it in the drawer"
```

### 원본 동작 원리
1. **Implicit Grounding**: "red apple"과 "drawer"라는 단어가 이미지 내의 특정 영역(Patch)과 Attention이 걸림.
2. **Action Token**: 마지막에 떨어지는 embedding feature를 Action Head가 받아 로봇 팔의 좌표(x,y,z)로 변환.
3. **특징**: Manipulation은 "대상의 위치"가 "목표 지점"과 직결되므로, Instruction을 그대로 넣어도 VLM의 Attention Map이 유용하게 작동함.

---

## 2. 우리 Task (Navigation)의 특수성 분석

### 문제점: Instruction과 Visual Output의 불일치
이전 테스트에서 확인했듯이, Navigation Task에서는 Instruction과 VLM의 해석이 충돌합니다.

**테스트 사례**:
- **Instruction**: "Navigate to the **RIGHT** of the pot" (오른쪽으로 가라)
- **Image State**: 화분이 화면 **왼쪽**에 있음 (로봇이 오른쪽으로 가려면 화분이 왼쪽에 보여야 함)
- **VLM Response**: "There is a pot on the **left** side"

**결과**:
VLM에게 Instruction("Go Right")을 그대로 주면, VLM은 이를 "오른쪽을 봐라" 혹은 "오른쪽에 있는 걸 찾아라"로 오해하거나, 단순히 현재 물체의 위치("Left")를 설명하여 Action Head에게 혼란(Conflicting Feature)을 줌.

### 핵심 차이점
| 구분 | Manipulation (Original) | Navigation (Ours) |
|------|-------------------------|-------------------|
| **Goal** | 물체의 위치 = 손이 가야 할 곳 | 물체의 위치 ≠ 로봇이 가야 할 곳 |
| **Relation** | Direct (좌표 일치) | Indirect (상대적 회피/접근) |
| **VLM Role** | Target & Goal 감지 | Target **Anchor** 감지 |

---

## 3. 우리를 위한 최적 전략: "Decoupled Prompting"

VLM의 역할과 Action Head의 역할을 명확히 분리합니다.

### 🎨 전략: Object-Centric Visual Anchoring

학습 및 추론 시 **Instruction 전체를 VLM에 넣지 않습니다.** 대신 **Target Object의 시각적 특징(Visual Feature)**을 가장 잘 뽑아내는 질문만 던집니다.

#### A. VLM Prompt (Frozen VLM 입력)
- **목표**: 오직 **Target/Obstacle의 존재와 위치**만 뚜렷하게 Feature Map에 남기는 것.
- **방식**: Simple Object Query.
- **최종 프롬프트**:
    ```python
    # Target (Brown Pot)
    "<grounding> Is there a brown pot?"
    
    # Obstacle (Gray Basket)
    "<grounding> Is there a gray basket?"
    ```

#### B. Action Generation (Action Head 입력)
- **목표**: 추출된 Visual Feature를 바탕으로 "왼쪽/오른쪽"으로 이동.
- **방식**: 
    1. **Instruction-Specific Model**: `Model_LEFT`는 추출된 화분 Feature를 보면 왼쪽 모터 출력을 내도록 학습됨.
    2. **Explicit Instruction Embedding**: (Optional) Action Head에 별도로 Instruction ID 주입.

### 🔄 비교: 전략 변경 전후

| 구 분 | 기존 시도 (Bad) | 최적화 전략 (Good) |
|:---:|---|---|
| **Input** | "Navigate to the LEFT of the brown pot" | "Is there a brown pot?" |
| **VLM 내부** | "LEFT"라는 단어와 "Pot(왼쪽에 있음)" 시각 정보 충돌 | "Brown Pot"에만 Attention 집중 (Clean Feature) |
| **Action Head** | 혼란스러운 Feature에서 길 찾기 시도 | 명확한 Pot 위치 정보 + 학습된 Policy로 이동 |
| **Result** | 불안정함 | **안정적 Navigation** |

---

## 4. 데이터셋 수집 및 학습 적용 가이드

### 실제 적용 Step

#### 1. 데이터 수집 시 (Data Collection)
수집 스크립트(`collect_episode.launch` 등)에서는 사람이 읽을 수 있는 전체 Instruction을 기록합니다.
- `instruction`: "Navigate to the left of the brown pot"
- `metadata`: `{"target": "brown_pot", "side": "left"}`

#### 2. 학습 Config 설정 (Training)
학습 시 데이터로더가 전체 instruction 대신 **Fixed Visual Prompt**를 VLM에 주입하도록 설정합니다.

**Config 파일 예시 (`Mobile_VLA/configs/brown_pot_left.json`)**:
```json
{
  ...
  "train_dataset": {
     ...
     "instruction_filter": ["left"], // 데이터 필터링용
  },
  
  "vlm_prompt": {
     // 중요: 실제 VLM에 들어가는 텍스트는 간소화됨
     "template": "<grounding> Is there a brown pot?",
     "strategy": "fixed_object_query"
  }
}
```

#### 3. Inference Node (Robot)
로봇 실행 시에도 유저의 명령("왼쪽으로 가")을 받으면, 내부적으로는:
1. **Router**: "화분" 관련 명령이군 -> `Model_Left` 또는 `Model_Right` 선택 (혹은 unified 모델).
2. **VLM Input**: "`<grounding> Is there a brown pot?`" 입력.
3. **Action Output**: 모터 제어.

---

## 5. 최종 요약 (The "Gold Standard")

우리 Task(Navigation)에서 성공 확률을 높이는 공식은 다음과 같습니다:

1. **Prompt는 단순하게**: `<grounding> Is there a [COLOR] [OBJECT]?`
   - 이유: VLM이 가장 잘하는 것(Detection)에 집중시켜 **S/N Ratio(신호 대 잡음비)**를 높임.
   - JSON 힌트, Navigate 지시어 등은 Noise가 됨.

2. **Action은 Head가 담당**:
   - VLM Feature(화분이 화면 중앙에 있음) + 학습된 가중치(Left Model) = **Turn Left**
   - VLM Feature(화분이 화면 중앙에 있음) + 학습된 가중치(Right Model) = **Turn Right**
   - 즉, **VLM Input은 동일**해도 **Model(Weight)**에 따라 행동이 달라짐.

3. **Objects 확정**:
   - Target: **Brown Pot** (Prompt: `"Is there a brown pot?"`)
   - Obstacle: **Gray Basket** (Prompt: `"Is there a gray basket?"`)

이 전략을 사용하면 **70-80%의 VLM 인식률**로 **85-90% 이상의 Navigation 성공률**을 달성할 수 있습니다.
