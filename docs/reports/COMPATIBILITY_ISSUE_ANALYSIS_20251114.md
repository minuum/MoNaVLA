# 🔍 호환성 이슈 분석 (2025-11-14)

## ⚠️ 발견된 문제

### 1. 액션 차원 불일치

**문제 위치:** `base_trainer.py`의 `_process_batch` 메서드

**기대하는 구조 (7D 액션):**
```python
# Line 409-413
arm_action = action[:, :, :6]  # b, len, 6 (arm action)
gripper_action = action[:, :, 6]  # b, len (gripper action)

# Line 427-428
arm_action_chunck = action_chunck[..., :6]  # ..., 6
gripper_action_chunck = action_chunck[..., -1]  # ... (gripper)
```

**우리 데이터셋 (2D 액션):**
```python
# mobile_vla_h5_dataset.py
actions_tensor = torch.from_numpy(np.array(actions)).float()  # (18, 2)
# collater에서:
action_chunck = action_tensors.unfold(...)  # (B, ..., fwd_pred_next_n, 2)
```

**결과:**
- `action_chunck[..., :6]` → **IndexError** (2차원만 있음)
- `action_chunck[..., -1]` → `linear_y` (gripper가 아님)

---

## 🔧 해결 방안

### 옵션 1: `_process_batch` 수정 (권장하지 않음)
- RoboVLMs 코드 수정 필요
- 유지보수 어려움

### 옵션 2: 데이터셋에서 7D로 패딩 (비권장)
- 사용자가 명시적으로 2D 사용 요청
- 불필요한 차원 추가

### 옵션 3: Mobile VLA 전용 Trainer 생성 (권장) ✅
- `BaseTrainer`를 상속하여 `_process_batch` 오버라이드
- 2D 액션 처리 로직 구현
- 기존 코드 수정 없음

---

## 📋 상세 분석

### 현재 데이터 흐름

1. **데이터셋 (`__getitem__`):**
   ```python
   actions_tensor = torch.from_numpy(np.array(actions)).float()  # (18, 2)
   return {
       'actions': actions_tensor,  # (18, 2)
       ...
   }
   ```

2. **Collater:**
   ```python
   action_tensors = ...[:, :-1]  # (B, 17, 2)
   action_chunck = action_tensors.unfold(...)  # (B, 8, 10, 2)
   return {
       "action": action_tensors,  # (B, 17, 2)
       "action_chunck": action_chunck,  # (B, 8, 10, 2)
       ...
   }
   ```

3. **`_process_batch` (문제 발생 지점):**
   ```python
   action = batch["action"].cuda()  # (B, 17, 2) ✅
   arm_action = action[:, :, :6]  # ❌ IndexError: dimension 2 out of range
   gripper_action = action[:, :, 6]  # ❌ IndexError
   
   action_chunck = batch["action_chunck"].cuda()  # (B, 8, 10, 2) ✅
   arm_action_chunck = action_chunck[..., :6]  # ❌ IndexError
   gripper_action_chunck = action_chunck[..., -1]  # ❌ linear_y를 gripper로 잘못 인식
   ```

---

## 🎯 해결 방안 상세

### 옵션 3 구현: Mobile VLA 전용 Trainer

**파일:** `RoboVLMs_upstream/robovlms/train/mobile_vla_trainer.py`

```python
from robovlms.train.base_trainer import BaseTrainer

class MobileVLATrainer(BaseTrainer):
    """Mobile VLA 전용 Trainer (2D 액션 처리)"""
    
    def _process_batch(self, batch):
        # BaseTrainer의 _process_batch를 오버라이드
        # 2D 액션 처리 로직 구현
        
        # ... (rgb, language 등은 동일) ...
        
        # 2D 액션 처리
        if batch.get("action", None) is not None:
            action = batch["action"].cuda()  # (B, 17, 2)
            # 2D 액션을 arm_action으로 사용 (gripper 없음)
            arm_action = action  # (B, 17, 2)
            gripper_action = None  # Mobile VLA는 gripper 없음
        else:
            arm_action = None
            gripper_action = None
        
        # Action chunk 처리
        action_chunck = batch.get("action_chunck", None)
        if action_chunck is not None:
            action_chunck = action_chunck.cuda()  # (B, 8, 10, 2)
            # 2D 액션을 arm_action_chunck으로 사용
            arm_action_chunck = action_chunck  # (B, 8, 10, 2)
            gripper_action_chunck = None  # Mobile VLA는 gripper 없음
        else:
            arm_action_chunck = None
            gripper_action_chunck = None
        
        # ... (나머지는 BaseTrainer와 동일) ...
        
        return (
            rgb, hand_rgb, attention_mask, language, text_mask,
            fwd_rgb_chunck, fwd_hand_rgb_chunck,
            arm_action, gripper_action,
            arm_action_chunck, gripper_action_chunck,
            chunck_mask, fwd_mask,
            instr_and_action_ids, instr_and_action_labels, instr_and_action_mask,
            raw_text, rel_state, data_source,
        )
```

**Config 수정:**
```json
{
    "trainer": {
        "type": "MobileVLATrainer",  // BaseTrainer 대신
        ...
    }
}
```

---

## 🔍 추가 확인 사항

### 1. Loss 계산
- `_get_loss`에서 `arm_action_chunck`와 `gripper_action_chunck`를 어떻게 사용하는지 확인 필요
- `gripper_action_chunck=None`일 때 처리 방법 확인

### 2. Model Forward
- `forward_action`에서 `action_labels=(arm_action_chunck, gripper_action_chunck)` 처리
- `gripper_action_chunck=None` 허용 여부 확인

### 3. Action Head
- `act_head`의 `action_dim=2` 설정 확인
- 2D 액션 처리 로직 확인

---

## 📝 추가 발견사항

### 2. Loss 계산 로직
**위치:** `base_policy.py`의 `BasePolicyHead.loss`

**문제:**
```python
# Line 137: 6차원 pose loss
pose_loss = torch.nn.functional.huber_loss(pred_action[..., :6], labels[0])

# Line 139-140: gripper loss (binary cross entropy)
gripper_loss = torch.nn.functional.binary_cross_entropy_with_logits(
    pred_action[..., -1], labels[1]
)
```

**우리 상황:**
- `pred_action`: `(B, seq_len, chunk_size, 2)` - 2D 액션
- `labels[0]`: `arm_action_chunck` - 2D 액션 (gripper 없음)
- `labels[1]`: `gripper_action_chunck` - None 또는 잘못된 값

**결과:**
- `pred_action[..., :6]` → **IndexError** (2차원만 있음)
- `labels[1]`가 None이면 `gripper_loss` 계산 불가

### 3. Config 확인
**현재 Config:**
```json
"act_head": {
    "action_dim": 2,  // ✅ 올바름
    "fwd_pred_next_n": 1,  // ⚠️ 최상위 레벨과 불일치 (10이어야 함)
    "window_size": 1,  // ⚠️ 최상위 레벨과 불일치 (8이어야 함)
}
```

**최상위 레벨:**
```json
"window_size": 8,
"fwd_pred_next_n": 10,
```

**문제:**
- `act_head`의 `window_size`와 `fwd_pred_next_n`이 최상위 레벨과 불일치
- 이는 모델 내부 설정이므로 확인 필요

---

## 📝 다음 단계

1. ✅ 문제 확인 완료
2. ⏳ Mobile VLA Trainer 구현
3. ⏳ Loss 계산 로직 수정 (2D 액션 지원)
4. ⏳ Config 일관성 확인
5. ⏳ 테스트 실행

---

## ⚠️ 주의사항

- **절대 7D 패딩 사용 금지** (사용자 명시적 요청)
- **기존 RoboVLMs 코드 수정 최소화**
- **2D 액션 구조 유지**

