# 코드 리뷰 요약 (2025-11-14)

## 🎯 목적
LoRA 파인튜닝 실행 전 코드 검토 및 호환성 확인

---

## ✅ 완료된 작업

### 1. 데이터셋 구조 확인
- ✅ `MobileVLAH5Dataset` 구조 검증
- ✅ `collater` 메서드 구현 확인
- ✅ DiskCalvinDataset 구조 준수 확인

### 2. Config 확인
- ✅ `window_size=8`, `fwd_pred_next_n=10` 설정 확인
- ✅ `action_dim=2` 설정 확인
- ⚠️ `act_head` 내부 설정 불일치 발견

### 3. 데이터 흐름 확인
- ✅ `__getitem__` → `collater` → `_process_batch` 흐름 확인
- ⚠️ `_process_batch`에서 7D 액션 가정 발견

---

## ⚠️ 발견된 문제

### 문제 1: 액션 차원 불일치 (심각)
**위치:** `base_trainer.py`의 `_process_batch`

**문제:**
- 코드는 7D 액션 (6D arm + 1D gripper)을 가정
- 우리 데이터는 2D 액션 (linear_x, linear_y)

**영향:**
- `arm_action = action[:, :, :6]` → **IndexError**
- `gripper_action = action[:, :, 6]` → **IndexError**
- `arm_action_chunck = action_chunck[..., :6]` → **IndexError**
- `gripper_action_chunck = action_chunck[..., -1]` → 잘못된 값 (linear_y를 gripper로 인식)

**해결 방안:**
- Mobile VLA 전용 Trainer 생성 (`_process_batch` 오버라이드)
- 2D 액션 처리 로직 구현

---

### 문제 2: Loss 계산 로직 (심각)
**위치:** `base_policy.py`의 `BasePolicyHead.loss`

**문제:**
- `pred_action[..., :6]` → 6차원 가정
- `pred_action[..., -1]` → gripper 가정
- 우리는 2D 액션만 사용

**영향:**
- Loss 계산 시 IndexError 발생 가능
- Gripper loss 계산 불가

**해결 방안:**
- 2D 액션 전용 Loss 계산 로직 구현
- Gripper loss 제거 또는 무시

---

### 문제 3: Config 불일치 (경미)
**위치:** `mobile_vla_20251114_lora.json`

**문제:**
```json
// 최상위 레벨
"window_size": 8,
"fwd_pred_next_n": 10,

// act_head 내부
"fwd_pred_next_n": 1,
"window_size": 1,
```

**영향:**
- 모델 내부 설정 불일치 가능
- 확인 필요

**해결 방안:**
- `act_head` 내부 설정 확인 및 필요시 수정

---

## 🔧 해결 방안

### 1. Mobile VLA Trainer 생성
**파일:** `RoboVLMs_upstream/robovlms/train/mobile_vla_trainer.py`

**구현 내용:**
- `BaseTrainer` 상속
- `_process_batch` 오버라이드
- 2D 액션 처리 로직 구현
- Gripper 관련 로직 제거

### 2. Loss 계산 수정
**옵션 A:** Mobile VLA 전용 Policy Head 생성
- `BasePolicyHead` 상속
- 2D 액션 Loss 계산 로직 구현

**옵션 B:** Config에서 gripper loss 비활성화
- `arm_gripper_loss_ratio: 0.0` (이미 설정됨)
- Loss 계산 시 gripper 부분 무시

### 3. Config 일관성 확인
- `act_head` 내부 설정 확인
- 필요시 최상위 레벨과 일치하도록 수정

---

## 📊 영향 범위

### 수정 필요한 파일
1. `RoboVLMs_upstream/robovlms/train/mobile_vla_trainer.py` (신규 생성)
2. `RoboVLMs_upstream/robovlms/model/policy_head/mobile_vla_policy.py` (옵션, 신규 생성)
3. `Mobile_VLA/configs/mobile_vla_20251114_lora.json` (확인 필요)

### 영향받는 기능
- ✅ 데이터 로딩: 문제 없음
- ⚠️ Batch 처리: 수정 필요
- ⚠️ Loss 계산: 수정 필요
- ✅ Model Forward: 확인 필요

---

## 🎯 우선순위

1. **높음:** Mobile VLA Trainer 생성 (문제 1 해결)
2. **높음:** Loss 계산 로직 확인 및 수정 (문제 2 해결)
3. **중간:** Config 일관성 확인 (문제 3 해결)

---

## 📝 다음 단계

1. ✅ 코드 리뷰 완료
2. ⏳ Mobile VLA Trainer 구현
3. ⏳ Loss 계산 로직 확인 및 수정
4. ⏳ Config 일관성 확인
5. ⏳ 테스트 실행

---

## ⚠️ 주의사항

- **절대 7D 패딩 사용 금지** (사용자 명시적 요청)
- **기존 RoboVLMs 코드 수정 최소화**
- **2D 액션 구조 유지**

