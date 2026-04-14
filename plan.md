# Plan: Exp07 — Path-Type-Aware Instruction (에피소드 타입별 고정 instruction)

## 핵심 아이디어

**문제:** 현재 모든 V5 에피소드가 동일한 instruction ("Navigate until the gray basket is centered...") 을 가짐. 모델이 instruction을 무시해도 학습 손실이 최소화됨.

**해결:** 에피소드 파일명의 path_type(`straight_path`, `left_path`, `right_path`)을 읽어서 direction-specific instruction을 할당. 학습 데이터에 실제 텍스트-액션 correlation을 부여.

**목표:** 추론 시 "go left" vs "go right" 입력에 모델이 다른 액션을 출력.

---

## 구현 계획

### Step 1: `nav_h5_dataset_impl.py` — `_get_path_type_instruction()` 추가

`__getitem__` 내부에서 파일명으로 path_type을 감지하고 instruction을 반환하는 메서드 추가.

```python
# nav_h5_dataset_impl.py에 추가 (클래스 변수)
PATH_TYPE_INSTRUCTIONS = {
    "left": [
        "Navigate to the left toward the gray basket",
        "Move left to approach the target",
        "Steer left to reach the basket",
        "Head left toward the object",
        "왼쪽으로 이동해서 바구니에 접근해",
        "좌측으로 방향을 잡아 목표로 이동해",
    ],
    "right": [
        "Navigate to the right toward the gray basket",
        "Move right to approach the target",
        "Steer right to reach the basket",
        "Head right toward the object",
        "오른쪽으로 이동해서 바구니에 접근해",
        "우측으로 방향을 잡아 목표로 이동해",
    ],
    "straight": [
        "Navigate straight forward to the gray basket",
        "Go directly ahead to the target",
        "Proceed straight to the basket",
        "Move forward toward the object",
        "바구니를 향해 직진해",
        "앞으로 곧장 이동해",
    ],
    "default": [
        "Navigate until the gray basket is centered and fills the lower half of the frame.",
    ],
}

def _get_path_type_instruction(self, ep_file_path):
    """에피소드 파일명에서 path_type을 감지해 direction-specific instruction 반환."""
    stem = Path(ep_file_path).stem
    if "left_path" in stem:
        key = "left"
    elif "right_path" in stem:
        key = "right"
    elif "straight_path" in stem:
        key = "straight"
    else:
        key = "default"
    variations = self.PATH_TYPE_INSTRUCTIONS[key]
    return f"<grounding>An image of a robot {random.choice(variations)}"
```

### Step 2: `__getitem__`의 instruction 분기에 `path_type_aware` preset 추가

현재 코드 (nav_h5_dataset_impl.py:379):
```python
use_action_aware_train = (self.instruction_preset == "action_aware_train")
if use_action_aware_train:
    language_base = self._get_action_aware_instruction(actions)
elif 'language_instruction' in f:
    ...
```

변경 후:
```python
use_action_aware_train = (self.instruction_preset == "action_aware_train")
use_path_type_aware = (self.instruction_preset == "path_type_aware")
if use_action_aware_train:
    language_base = self._get_action_aware_instruction(actions)
elif use_path_type_aware:
    language_base = self._get_path_type_instruction(self.episode_files[ep_idx])
elif 'language_instruction' in f:
    ...
```

**주의:** `ep_idx`는 `__getitem__` 안에서 `ep_idx, start_frame = self.frame_indices[idx]` 로 이미 분리됨. `self.episode_files[ep_idx]` 로 파일 경로 접근 가능.

### Step 3: `configs/mobile_vla_v5_exp07_path_type.json` 생성

Exp06을 parent로, `instruction_preset`만 변경:

```json
{
    "_comment": "V5 Exp07: Pure HF Kosmos-2 + path_type_aware instruction. 에피소드 타입별 고정 direction instruction으로 텍스트-액션 correlation 강제.",
    "parent": "configs/mobile_vla_v5_exp06_pure_hf.json",
    "exp_name": "v5-exp07-path-type",
    "task_name": "mobile_vla_v5_exp07",
    "train_dataset": {
        "instruction_preset": "path_type_aware"
    },
    "val_dataset": {
        "instruction_preset": "path_type_aware"
    }
}
```

**val도 path_type_aware로** — val_loss가 같은 instruction 공간에서 측정되어야 의미 있음.

### Step 4: 학습 실행

```bash
tmux new-session -d -s v5exp07 -c /home/billy/25-1kp/MoNaVLA \
  "PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
   /home/billy/anaconda3/envs/openvla/bin/python robovlm_nav/train.py \
   configs/mobile_vla_v5_exp07_path_type.json \
   2>&1 | tee /tmp/v5_exp07_train_log.txt"
```

### Step 5: 텍스트 감도 테스트

학습 완료 후 `test_v5_text_understanding.py`의 CHECKPOINTS에 Exp07 추가, neutral frame(straight_path)으로 테스트.

---

## 수정 파일 목록

| 파일 | 변경 내용 |
|------|----------|
| `robovlm_nav/datasets/nav_h5_dataset_impl.py` | `PATH_TYPE_INSTRUCTIONS` 클래스 변수 + `_get_path_type_instruction()` 추가, `__getitem__` 분기 추가 |
| `configs/mobile_vla_v5_exp07_path_type.json` | 신규 생성 |
| `scripts/test_v5_text_understanding.py` | CHECKPOINTS에 Exp07 추가 (학습 완료 후) |

---

## 합격 기준

```
성공: left instruction → LEFT 또는 FWD+L 예측
      right instruction → RIGHT 또는 FWD+R 예측
      (두 instruction에서 예측 클래스가 달라야 함)

실패: 모든 instruction → 동일 클래스
```

---

## 리스크

- `path_type_aware`는 val에서도 direction-specific instruction이 주어짐 → val 중 "go left" + left_path 에피소드가 paired → val_loss는 Exp06보다 낮아질 것 (더 쉬운 task)
- val_loss 낮다고 텍스트 이해가 확인된 건 아님 — 반드시 text sensitivity test로 최종 확인
