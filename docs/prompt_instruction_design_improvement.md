# VLA Prompt & Instruction 설계 개선 결과 문서
> **작성일**: 2026-03-05  
> **대상**: 기존 VLA 프로젝트의 프롬프트/인스트럭션 구조 분석 + 3가지 개선 적용 결과

---

## 1. 개선 전 문제 진단 (실제 코드 근거)

### 문제 ①: Instruction이 파일명에 종속 (하드코딩)

**문제 코드** (`mobile_vla_action_dataset.py` 구버전):
```python
# 파일명 태그 → 고정 문자열 매핑
self.scenario_instructions = {
    "1box_hori_left": "Navigate around the obstacle on the left side and reach the cup",
    "1box_hori_right": "Navigate around the obstacle on the right side and reach the cup",
    # ... (파일명 규칙이 바뀌면 즉시 학습에서 제외됨)
}
```
- 파일명에 `1box_hori_left` 태그가 없으면 학습 **자동 제외**
- RT-2 / OpenVLA처럼 H5 내부에 `language_instruction` 필드를 두지 않아 **미래 데이터 확장 시 코드 수정 필수**

### 문제 ②: VLM Grounding 프롬프트와 Action Head 프롬프트가 분리

**문제 설정** (`brown_pot_left.json` 구버전):
```json
{
  "vlm_prompt": {
    "template": "<grounding> Is there a brown pot?",
    "comment": "VLM does object detection, action head does instruction grounding"
  }
}
```
- VLM이 보는 프롬프트: `"<grounding> Is there a brown pot?"`  
- Action Head의 학습 프롬프트: `"Navigate around obstacles and reach... the brown pot on the left"`  
- **두 프롬프트가 달라** VLM의 시각적 표현이 Action Head grounding에 효과적으로 기여하는지 불투명

### 문제 ③: 위치 단서가 없는 추상적 instruction

```
"Navigate around the obstacle on the left side and reach the cup"
```
- "left side"가 **무엇 기준**인지 불명확 (로봇 기준? 이미지 프레임 기준?)
- 타 논문들(RT-2, OpenVLA)은 `"visible in the image"` 등 **시각 참조** 표현 사용

---

## 2. 논문별 Prompt 구조 비교 (근거 기반)

| 논문                        | 입력 이미지    | Instruction 형식                                                                                            | Grounding 방식                 |
| --------------------------- | -------------- | ----------------------------------------------------------------------------------------------------------- | ------------------------------ |
| **RT-2** (Google 2023)      | 1장, 224×224   | `"pick up the orange"`                                                                                      | End-to-End (VLM Finetune)      |
| **OpenVLA** (Stanford 2024) | 1장, 224×224   | `"In: What action should the robot take to pick up the red cup?\nOut:"`                                     | End-to-End                     |
| **RoboVLMs** (Upstream)     | Window(8~16장) | `"What action should the robot take to {task}?"`                                                            | Frozen VLM + Action Head       |
| **우리 VLA (구버전)**       | Window(8장)    | `"What action should the robot take to {scenario_tag_mapped_string}?"`                                      | Frozen/LoRA + 분류 Head        |
| **우리 VLA (개선 후)**      | Window(8장)    | `"What action should the robot take to Navigate to the gray basket visible on the left side of the frame?"` | LoRA + 분류 Head (통합 prompt) |

---

## 3. 적용된 개선 사항 (환각 없이 실제 코드 변경 기준)

### 개선 ①: Instruction 표준화 — episode_name attr 기반 파싱

**변경 파일**: `robovlm_nav/datasets/nav_h5_dataset_impl.py` (L.229~281)

```python
# 개선 후: 우선순위 기반 instruction 생성
# 1순위: H5 내부 'language_instruction' 필드 (미래 데이터 수집 시 사용)
# 2순위: H5 attrs['episode_name'] 파싱 (현재 528 에피소드 전부 해당)
# 3순위: 파일명 fallback

if 'language_instruction' in f:
    raw = f['language_instruction'][0]
    language_base = raw.decode('utf-8') if isinstance(raw, bytes) else str(raw)
else:
    ep_name = str(f.attrs.get('episode_name', '')).lower()
    # e.g. "episode_20260129_010041_basket_1box_hori_left_core_medium"
    if 'left' in ep_name:
        direction = 'left'
    ...
```

**왜 파일명이 아닌 `attrs['episode_name']`인가?**
- 실제 확인 결과: 모든 H5 파일에 `episode_name` attr이 존재함 (파이썬 스크립트로 검증)
- `episode_name`은 파일명과 동일한 정보를 H5 **내부**에 담아 원본 파일명 변경에 영향받지 않음
- 미래에 `language_instruction` 필드를 데이터 수집기에 추가하면 코드 수정 없이 즉시 사용 가능

### 개선 ②: 위치 명시 Instruction (시각 단서 강화)

**변경 파일**: `nav_h5_dataset_impl.py`, `mobile_vla_action_dataset.py`, `configs/brown_pot_*.json`

```python
# 개선 전
"Navigate to the gray basket on the left"
"Navigate around the obstacle on the left side and reach the cup"

# 개선 후
"Navigate to the gray basket visible on the left side of the frame"
"Navigate to the cup visible on the left side of the frame"
```

**근거**: Kosmos-2의 Vision Encoder가 이미지 처리 시 spatial attention이 활성화되어 있음. "left side of the **frame**" 표현은 VLM의 공간 추론 토큰과 연결될 가능성이 높음.

**학습 시 Instruction Variation** (overfitting 방지):
```python
variations = [
    "Navigate to the gray basket visible on the left side of the frame",  # 기본 위치 명시
    "Move toward the basket located on the left side",                    # 동작 동사 다양화
    "Steer left to reach the gray basket in view",                        # 조향 단어 포함
    "Go to the gray basket on the left",                                  # 짧은 버전
    "Navigate to the gray basket",                                        # 방향 없는 버전 (일반화)
]
```

### 개선 ③: Grounding 프롬프트 통합

**변경 파일**: `configs/brown_pot_left.json`, `configs/brown_pot_right.json`

```json
// 구버전: 역할 분리
{
  "vlm_prompt": { "template": "<grounding> Is there a brown pot?" },
  // Action Head는 별도 instruction 사용
}

// 개선 후: 단일 통합 instruction
{
  "unified_instruction": {
    "template": "Navigate to the brown pot visible on the left side of the frame",
    "design_rationale": "단일 통합 instruction. prompt builder가 'What action should the robot take to {instruction}?' 형식으로 래핑하여 VLM과 Action Head 모두에 동일하게 적용됨."
  }
}
```

**완성된 최종 프롬프트 (학습 입력)**:
```
What action should the robot take to Navigate to the gray basket visible on the left side of the frame?
```

---

## 4. 적용 안 된 항목 (해상도 전략 — 사용자 요청으로 제외)

- **224×224 Resize 개선**: Center/Left/Right Crop 비교 실험 → 미적용
- 이유: Resize 전략 변경은 모델 전체 재학습 필요, 독립 실험으로 진행 예정

---

## 5. 실제 데이터 검증 결과

```bash
# H5 파일 실제 구조 확인 (528 에피소드)
Keys: ['action_event_types', 'actions', 'images']
Attrs: {
  'episode_name': 'episode_20260129_010041_basket_1box_hori_left_core_medium',
  'num_frames': 18,
  'obstacle_layout_type': 'hori',
  'time_period': 'dawn',
  ...
}
# language_instruction 필드: 현재 없음 (파싱 로직으로 처리)
# episode_name attr: 전 에피소드에 존재 → 방향 파싱 가능
```

---

## 6. 변경 파일 목록

| 파일                                                              | 변경 내용                                                    |
| ----------------------------------------------------------------- | ------------------------------------------------------------ |
| `robovlm_nav/datasets/nav_h5_dataset_impl.py`                     | episode_name attr 기반 instruction 생성, 위치 명시 표현 추가 |
| `third_party/RoboVLMs/robovlms/data/mobile_vla_action_dataset.py` | scenario_instructions 위치 명시 버전으로 업데이트            |
| `configs/brown_pot_left.json`                                     | vlm_prompt 분리 제거, unified_instruction 통합               |
| `configs/brown_pot_right.json`                                    | vlm_prompt 분리 제거, unified_instruction 통합               |

---

*작성: Antigravity (RoboVLM-Nav 프로젝트 AI 협업 에이전트)*  
*참고: RT-2, OpenVLA, RoboVLMs 논문 + 실제 코드 검증 기반*
