# 📚 Mobile VLA 프로젝트 중앙 지식 베이스

**Last Updated:** 2025-11-14  
**Purpose:** 논문 작성까지 이어질 프로젝트의 핵심 정보 중앙 관리

---

## 🎯 프로젝트 개요

### 목표
- Mobile VLA (Vision-Language-Action) 모델 개발
- LoRA Fine-tuning을 통한 로봇 네비게이션 학습
- 논문 출판 목표

### 기술 스택
- **Base Model:** Kosmos-2 (Microsoft)
- **Framework:** RoboVLMs (Robot-VLAs)
- **Training:** LoRA (Low-Rank Adaptation)
- **Data Format:** HDF5

---

## 📊 데이터 수집 구조

### 에피소드 구조
- **고정 길이:** 18프레임 (`fixed_episode_length = 18`)
- **의도:** RoboVLMs 기본 설정에 맞춤
  - `window_size = 8` (히스토리 길이)
  - `fwd_pred_next_n = 10` (예측할 액션 청크 수)
  - **8 + 10 = 18프레임** ✅

### 데이터 형식
- **이미지:** `(18, 720, 1280, 3)` - uint8, BGR 형식
- **액션:** `(18, 3)` - `[linear_x, linear_y, angular_z]`
  - 사용: `linear_x`, `linear_y`만 (2D navigation)
  - 미사용: `angular_z` (항상 0.0)
- **액션 값 범위:** `±1.15` (WASD 키 입력)
- **이벤트 타입:** `(18,)` - 문자열

### 수집 패턴
- Frame 0: `episode_start` (정지)
- Frame 1-17: `start_action` (WASD 키 입력)
- 각 액션: 0.4초 동안 실행 후 자동 정지

---

## 🔧 핵심 설계 결정사항

### 1. 18프레임 수집 의도
**결정 이유:**
- RoboVLMs의 기본 설정 `window_size=8`, `fwd_pred_next_n=10`에 정확히 맞춤
- `window_size + fwd_pred_next_n = 18` 프레임이 필요
- 데이터 수집 시점부터 RoboVLMs 구조를 고려한 설계

**참고:**
- `ROBOVLMS_STRUCTURE_ANALYSIS_20251114.md` 참조

### 2. 2D 액션 사용
**결정 이유:**
- Mobile VLA는 2D navigation (linear_x, linear_y)
- 7D manipulation 액션 불필요
- RoboVLMs는 2D 액션도 지원

**구현:**
- 데이터셋: `action[:2]` 슬라이싱
- Config: `action_dim: 2`
- 학습 코드: 7D 패딩 제거, 2D 그대로 사용

### 3. DiskCalvinDataset 구조 준수
**결정 이유:**
- RoboVLMs의 표준 데이터셋 구조
- 기존 코드와의 호환성
- 검증된 구조

**구현:**
- `__getitem__`: `(window_size + fwd_pred_next_n, 2)` 시퀀스 반환
- `collater`: `unfold` 방식으로 chunk 생성
- 반환 키: `'actions'`, `'lang'`, `'action_mask'`, `'image_mask'`

---

## 📈 데이터 품질 분석

### Core 패턴 분석
**Task:** `1box_hori_left_core_medium`

**고유 패턴:** 5개
1. **주요 패턴:** `SWWWWAQQQQQQQWWWWE` (79회, 88.8%)
2. 변형 패턴 4개 (11.2%)

**일관성:**
- 주요 패턴 비율: 88.8% (학습 가능)
- 개선 권장: 변형 패턴 비율 5% 이하로 감소

**의미:**
- Core 패턴은 장애물 앞까지 도착하기까지의 궤적 학습
- 같은 경로(속도)로 가야 함
- 일관된 trajectory가 중요

**참고:**
- `CORE_PATTERN_ANALYSIS_20251114.md` 참조

### Trajectory 분석
**WASD 키 매핑:**
```python
WASD_TO_CONTINUOUS = {
    'w': {"linear_x": 1.15, "linear_y": 0.0},    # 전진
    'a': {"linear_x": 0.0, "linear_y": 1.15},   # 좌
    'd': {"linear_x": 0.0, "linear_y": -1.15},  # 우
    's': {"linear_x": -1.15, "linear_y": 0.0},  # 후진
    'q': {"linear_x": 1.15, "linear_y": 1.15},  # 전진+좌
    'e': {"linear_x": 1.15, "linear_y": -1.15}, # 전진+우
    ...
}
```

**주요 발견:**
- 대각선 액션 (Q, E) 사용이 자연스러움
- 액션 정규화: `±1.15` → `±1.0` 클램핑 (정상)
- 파인튜닝에 문제 없음

### 모델 호환성 및 트러블슈팅 (2025-11-20)
**Kosmos-2 + LoRA 학습 시 In-place Operation 오류:**
- **증상**: `RuntimeError: a leaf Variable that requires grad is being used in an in-place operation.`
- **원인**: Frozen Backbone에서 생성된 `inputs_embeds`가 Leaf Variable로 인식되어, 모델 내부의 이미지 임베딩 삽입 과정에서 In-place 수정이 차단됨.
- **해결**: `BaseRoboVLM`에서 `inputs_embeds`를 수동 생성 후 `.clone()`하여 Non-leaf Variable로 변환 후 전달.
- **Action Token**: Kosmos 모델 입력 시 `inputs_embeds` 끝에 `action_token`을 명시적으로 추가하여 액션 예측 유도.

**참고:**
- `TRAJECTORY_ANALYSIS_20251114.md` 참조
- `KOSMOS_IN_PLACE_ERROR_FIX.md` 참조

---

## 🏗️ 아키텍처 및 설정

### Config 구조
```json
{
    "window_size": 8,           // RoboVLMs 기본값
    "fwd_pred_next_n": 10,      // RoboVLMs 기본값
    "act_head": {
        "action_dim": 2,         // 2D navigation
        "window_size": 1,        // 내부 설정
        "fwd_pred_next_n": 1     // 내부 설정
    }
}
```

### 데이터셋 구조
**MobileVLAH5Dataset:**
- `__getitem__`: `(18, 2)` 액션 시퀀스 반환
- `collater`: `unfold` 방식으로 chunk 생성
- DiskCalvinDataset과 동일한 구조

### 학습 설정
- **LoRA:** r=32, alpha=16, dropout=0.1
- **Epochs:** 20
- **Batch Size:** 1
- **Learning Rate:** 1e-4
- **Precision:** 16-mixed

---

## 🔍 중요한 발견사항

### 1. generate_chunck_data vs unfold
**문제:**
- `generate_chunck_data`는 `seq_len == window_size + chunk_size` 요구
- 초기 구현에서 shape 불일치 발생

**해결:**
- `unfold` 방식 사용 (DiskCalvinDataset과 동일)
- 더 안정적이고 검증된 방법

### 2. text_fn 초기화
**문제:**
- `collater`에서 `text_fn` 사용하지만 초기화되지 않음

**해결:**
- `__init__`에서 `tokenizer`, `tokenizer_config` 받아서 `text_fn` 생성
- `get_text_function` 사용하여 kosmos tokenizer 지원

### 3. Config 불일치
**문제:**
- 최상위 레벨: `window_size=4`, `fwd_pred_next_n=10`
- `act_head`: `window_size=1`, `fwd_pred_next_n=1`

**해결:**
- 최상위 레벨: `window_size=8` (RoboVLMs 기본값)
- `act_head`는 내부 설정으로 유지

### 4. ⚠️ 액션 차원 불일치 (2025-11-14 발견)
**문제:**
- `base_trainer.py`의 `_process_batch`는 7D 액션 (6D arm + 1D gripper)을 가정
- 우리 데이터는 2D 액션 (linear_x, linear_y)
- `arm_action = action[:, :, :6]` → **IndexError**
- `gripper_action = action[:, :, 6]` → **IndexError**

**해결 방안:**
- Mobile VLA 전용 Trainer 생성 (`_process_batch` 오버라이드)
- 2D 액션 처리 로직 구현
- Gripper 관련 로직 제거

**참고:**
- `COMPATIBILITY_ISSUE_ANALYSIS_20251114.md` 참조
- `CODE_REVIEW_SUMMARY_20251114.md` 참조

### 5. ⚠️ Loss 계산 로직 (2025-11-14 발견)
**문제:**
- `base_policy.py`의 `BasePolicyHead.loss`는 6D pose + 1D gripper를 가정
- `pred_action[..., :6]` → 6차원 가정
- 우리는 2D 액션만 사용

**해결 방안:**
- 2D 액션 전용 Loss 계산 로직 구현
- Config에서 `arm_gripper_loss_ratio: 0.0` 설정 (이미 완료)

---

## 📝 코드 변경 이력

### 2025-11-14 주요 변경사항

1. **Config 수정**
   - `window_size`: 4 → 8
   - `action_dim`: 7 → 2

2. **데이터셋 구조 수정**
   - `__getitem__`: 18프레임 로드, 시퀀스 형태 반환
   - `collater`: unfold 방식으로 chunk 생성
   - 반환 키: DiskCalvinDataset과 동일하게 수정

3. **액션 처리**
   - 7D 패딩 제거, 2D 그대로 사용
   - 정규화: `torch.clamp(actions_tensor, -1.0, 1.0)`

4. **text_fn 초기화**
   - `tokenizer`, `tokenizer_config`에서 `text_fn` 생성
   - kosmos tokenizer 지원

---

## 📚 참고 문서

### 분석 문서
- `CORE_PATTERN_ANALYSIS_20251114.md`: Core 패턴 상세 분석
- `TRAJECTORY_ANALYSIS_20251114.md`: Trajectory 분석 및 파인튜닝 영향 평가
- `ROBOVLMS_STRUCTURE_ANALYSIS_20251114.md`: RoboVLMs 구조 분석
- `CODE_REVIEW_MOBILE_VLA_20251114.md`: 코드 리뷰 및 수정사항

### 가이드 문서
- `LORA_FINETUNING_GUIDE_20251114.md`: LoRA 파인튜닝 가이드
- `H5_EPISODE_ANALYSIS_REPORT.md`: H5 에피소드 분석 리포트

---

## 🎯 다음 단계

1. **데이터 품질 개선**
   - Core 패턴 일관성 향상 (변형 패턴 5% 이하)
   - 가이드 정확도 향상

2. **학습 진행**
   - LoRA 파인튜닝 실행
   - 성능 모니터링

3. **논문 준비**
   - 실험 결과 정리
   - 방법론 문서화

---

## ⚠️ 주의사항

1. **Config 일관성**
   - `window_size=8`, `fwd_pred_next_n=10` 유지
   - RoboVLMs 기본값과 일치해야 함

2. **데이터 형식**
   - 18프레임 고정 길이 유지
   - 2D 액션 사용 (7D 패딩 금지)

3. **데이터셋 구조**
   - DiskCalvinDataset 구조 준수
   - `unfold` 방식 사용

---

**이 문서는 프로젝트의 중앙 기준 정보입니다. 중요한 변경사항은 반드시 이 문서에 반영해야 합니다.**

