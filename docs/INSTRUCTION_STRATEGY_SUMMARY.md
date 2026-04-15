# Instruction Strategy - 정리 및 재확인

**Date**: 2026-01-29  
**Context**: Brown Pot 학습 준비 - Instruction 전략 재확인

---

## 📋 이전에 논의한 Instruction 전략 요약

### 1. 데이터 수집 시 사용하는 Instruction (전체 문장)

사람이 읽을 수 있고, Task를 명확히 설명하는 자연어 instruction을 H5 파일에 저장합니다.

#### LEFT Instruction 예시:
```
"Navigate around obstacles and reach the front of the brown pot on the left"
"Navigate to the left of the brown pot"
"Go to the brown pot on the left"
```

#### RIGHT Instruction 예시:
```
"Navigate around obstacles and reach the front of the brown pot on the right"
"Navigate to the right of the brown pot"
"Go to the brown pot on the right"
```

**목적**:
- Episode metadata로 저장
- LEFT/RIGHT 분류 기준
- 사람이 task 이해 가능
- 향후 instruction grounding 연구에 활용

---

### 2. VLM에 실제로 입력하는 Prompt (간소화)

학습 및 추론 시 VLM의 입력으로 사용하는 **단순한 Object Detection Query**:

```python
VLM_PROMPT = "<grounding> Is there a brown pot?"
```

**Why?**
- VLM은 **Object Detection + Localization**만 잘하면 됨
- Navigation 지시("LEFT/RIGHT")는 VLM을 혼란시킴
- Action Head가 instruction grounding을 학습

---

### 3. 이전 데이터셋(Beverage Bottle)의 Instruction

#### 실제 사용했던 것:
```
LEFT:  "Navigate around obstacles and reach the front of the beverage bottle on the left"
RIGHT: "Navigate around obstacles and reach the front of the beverage bottle on the right"
```

#### 파일명에 포함:
```
episode_20251119_080007_1box_hori_right_core_medium.h5
                                 ^^^^^ 
                                 right 정보가 파일명에
```

#### H5 내부 저장 여부:
❌ **현재 데이터셋에는 H5 내부에 instruction 없음!**
- Keys: `['action_event_types', 'actions', 'images']`
- Instruction은 파일명으로만 구분

---

## 🔧 Brown Pot 데이터 수집 시 개선사항

### A. H5 파일에 Instruction 명시적 저장

**이전 방식 (문제)**:
```python
# episode_xxx_left.h5
{
    'images': [...],
    'actions': [...],
    # instruction 없음! 파일명에만 의존
}
```

**개선 방식 (권장)**:
```python
# episode_xxx_left.h5
{
    'images': [...],
    'actions': [...],
    'instruction': "Navigate to the left of the brown pot",  # ✅ 명시적 저장
    'metadata': {
        'target': 'brown_pot',
        'side': 'left',
        'obstacle': 'gray_basket'
    }
}
```

---

### B. 데이터 수집 스크립트 수정 필요

**File**: ROS data collection script

```python
def save_episode(episode_data, filename):
    with h5py.File(filename, 'w') as f:
        # 기존 저장
        f.create_dataset('images', data=episode_data['images'])
        f.create_dataset('actions', data=episode_data['actions'])
        
        # ✅ Instruction 추가!
        instruction = episode_data.get('instruction', '')
        f.create_dataset('instruction', data=instruction.encode('utf-8'))
        
        # ✅ Metadata 추가!
        metadata = f.create_group('metadata')
        metadata.create_dataset('target', data=b'brown_pot')
        metadata.create_dataset('side', data=episode_data['side'].encode('utf-8'))
        metadata.create_dataset('obstacle', data=episode_data.get('obstacle', b'none'))
```

---

## 📊 Instruction의 두 가지 역할

### Role 1: Episode Metadata (파일에 저장)

```python
# H5 파일에 저장되는 전체 instruction
FULL_INSTRUCTION_LEFT = "Navigate around obstacles and reach the front of the brown pot on the left"

# 목적:
# 1. Human-readable task description
# 2. LEFT/RIGHT 분류 기준
# 3. Dataset documentation
# 4. 향후 end-to-end instruction following 연구
```

---

### Role 2: VLM Input (학습/추론 시 override)

```python
# 실제 VLM에 들어가는 prompt (학습 시 override)
VLM_PROMPT = "<grounding> Is there a brown pot?"

# 목적:
# 1. VLM이 가장 잘하는 일(Object Detection)에 집중
# 2. LEFT/RIGHT 혼란 제거
# 3. 깔끔한 visual feature 추출
```

---

## 🎯 학습 Pipeline의 Instruction 흐름

### Step 1: Data Loading
```python
# Dataset loader가 H5에서 읽어옴
episode = load_h5("episode_001_left.h5")
print(episode['instruction'])
# Output: "Navigate around obstacles and reach the front of the brown pot on the left"
```

### Step 2: Training (VLM Input Override)
```python
# Config에서 vlm_prompt.template 읽기
vlm_prompt = config['vlm_prompt']['template']  
# "<grounding> Is there a brown pot?"

# Trainer가 instruction을 override
if config.get('vlm_prompt', {}).get('override_instruction'):
    batch['instruction'] = vlm_prompt  # ✅ Override!

# VLM forward
vlm_features = vlm(image, prompt=vlm_prompt)  # Simple prompt!
```

### Step 3: Action Head Learning
```python
# Action Head는 VLM features + 원본 instruction 정보(LEFT/RIGHT)를 학습
# 두 가지 방식:

# Option A: Instruction-Specific Models (우리 방식)
model_left.action_head(vlm_features)   # LEFT episodes로 학습
model_right.action_head(vlm_features)  # RIGHT episodes로 학습

# Option B: Unified Model with Instruction Embedding (대안)
instruction_emb = embed("left")  # or "right"
model.action_head(vlm_features, instruction_emb)
```

---

## 💡 핵심 깨달음 (재확인)

### 1. VLM은 Instruction Follower가 아님!

**Test 결과**:
```
Instruction: "Navigate to the RIGHT"
Image: 화분이 왼쪽에 있음
VLM Response: "The pot is on the left side"

→ VLM은 현재 시각적 상태를 설명함
→ "오른쪽으로 가라"는 지시를 따르지 못함!
```

---

### 2. 간단한 Prompt가 Best!

**Bad Prompts (피해야 할 것)**:
```python
❌ "<grounding> Is there a brown pot? JSON: {\"detected\": true/false}"
   → VLM이 echo만 하고 답변 안 함!

❌ "<grounding> Navigate to the LEFT of the brown pot"
   → LEFT 지시와 실제 위치(right)가 충돌!

❌ "Is there a brown pot on the floor? Answer YES or NO"
   → 복잡한 지시는 혼란만 가중
```

**Good Prompts (사용할 것)**:
```python
✅ "<grounding> Is there a brown pot?"
   → Simple, clean, effective!

✅ "<grounding> Is there a gray basket?"
   → Object detection에만 집중
```

---

### 3. Action Head가 핵심!

```
Navigation Success = VLM Features (clean) + Action Head (trained)

VLM: "화분이 중앙에 있습니다" (객관적 사실)
Action Head (LEFT model): "화분 보임 → 왼쪽으로 회전" (학습된 정책)
Action Head (RIGHT model): "화분 보임 → 오른쪽으로 회전" (학습된 정책)
```

---

## 📋 Brown Pot 데이터 수집 시 사용할 Instructions

### LEFT Episodes (200개)

**Variations**:
```python
LEFT_INSTRUCTIONS = [
    # Standard
    "Navigate around obstacles and reach the front of the brown pot on the left",
    
    # Simplified
    "Navigate to the left of the brown pot",
    "Go to the brown pot on the left",
    
    # With obstacle mention
    "Avoid the gray basket and reach the brown pot on the left",
    
    # Short form
    "Left side of brown pot",
]
```

**Distribution**:
- 주력: 첫 번째 (50%)
- 나머지 균등 분배 (50%)

---

### RIGHT Episodes (200개)

**Variations**:
```python
RIGHT_INSTRUCTIONS = [
    # Standard
    "Navigate around obstacles and reach the front of the brown pot on the right",
    
    # Simplified
    "Navigate to the right of the brown pot",
    "Go to the brown pot on the right",
    
    # With obstacle mention
    "Avoid the gray basket and reach the brown pot on the right",
    
    # Short form
    "Right side of brown pot",
]
```

---

## ⚙️ Config 설정

### brown_pot_left.json
```json
{
  "vlm_prompt": {
    "template": "<grounding> Is there a brown pot?",
    "override_instruction": true,
    "comment": "VLM은 object detection만, Action Head가 LEFT 학습"
  },
  
  "train_dataset": {
    "instruction_filter": ["left", "LEFT"],
    "comment": "LEFT instruction이 포함된 episodes만 사용"
  }
}
```

### brown_pot_right.json
```json
{
  "vlm_prompt": {
    "template": "<grounding> Is there a brown pot?",  // ✅ LEFT와 동일!
    "override_instruction": true
  },
  
  "train_dataset": {
    "instruction_filter": ["right", "RIGHT"],
    "comment": "RIGHT instruction이 포함된 episodes만 사용"
  }
}
```

---

## ✅ Checklist: 데이터 수집 전 확인사항

### 1. H5 파일 구조
```python
with h5py.File(episode_file, 'r') as f:
    assert 'images' in f
    assert 'actions' in f
    assert 'instruction' in f  # ✅ 필수!
    
    instruction = f['instruction'][()].decode('utf-8')
    assert 'left' in instruction.lower() or 'right' in instruction.lower()
```

### 2. Instruction Variations
```python
instructions = collect_all_instructions(dataset)
assert len(instructions) >= 2  # LEFT + RIGHT 최소
print(f"Found {len(instructions)} unique instructions")
```

### 3. Episode Distribution
```python
left_count = count_episodes_with("left")
right_count = count_episodes_with("right")
assert abs(left_count - right_count) < 20  # 균형 확인 (200 vs 200)
print(f"LEFT: {left_count}, RIGHT: {right_count}")
```

---

## 🎯 최종 정리

### 데이터 수집 시:
```
✅ Full instruction 저장: "Navigate to the left of the brown pot"
✅ Metadata 저장: {"side": "left", "target": "brown_pot"}
✅ 200 LEFT + 200 RIGHT 균형있게 수집
```

### 학습 시:
```
✅ VLM Input: "<grounding> Is there a brown pot?" (override!)
✅ Model 분리: LEFT model, RIGHT model
✅ Episode Filtering: instruction_filter=['left'] or ['right']
```

### 추론 시:
```
✅ User instruction: "Go left" → Model_LEFT 선택
✅ VLM Input: "<grounding> Is there a brown pot?"
✅ Output: (linear_x, angular_z) for LEFT navigation
```

---

**핵심**: 
- 데이터엔 **전체 instruction** 저장
- VLM엔 **간단한 prompt** 입력
- Action Head가 **instruction grounding** 학습!
