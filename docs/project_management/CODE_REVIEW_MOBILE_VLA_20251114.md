# 🔍 Mobile VLA LoRA 코드 리뷰 및 수정사항

**Date:** 2025-11-14  
**목적:** 1차 LoRA 스크립트 실행 전 코드 검토 및 데이터셋 수집 방식 호환성 확인

## 📋 발견된 문제점

### 1. ❌ MobileVLAH5Dataset에 collater 메서드 없음
**문제:** `GRDataModule`이 `dataset.collater`를 사용하는데 `MobileVLAH5Dataset`에 없음

**해결:** `collater` 메서드 추가 완료
- `ConcatDataset`의 `collater`를 참고하여 구현
- 2D 액션 처리 확인
- `text_fn`을 통한 언어 토크나이징 지원

### 2. ⚠️ Config 불일치
**문제:** 
- 최상위 레벨: `window_size: 4`, `fwd_pred_next_n: 10`
- `act_head`: `window_size: 1`, `fwd_pred_next_n: 1`

**영향:** 
- 데이터셋은 `window_size=4`, `action_chunk_size=10` 사용
- 모델 헤드는 `window_size=1`, `fwd_pred_next_n=1` 사용
- **불일치로 인한 학습 오류 가능성**

**해결 필요:** `act_head`의 `window_size`와 `fwd_pred_next_n`을 최상위 레벨과 일치시켜야 함

### 3. ⚠️ text_fn 전달 확인 필요
**문제:** `MobileVLAH5Dataset`의 `collater`에서 `text_fn` 사용하지만, 초기화 시 전달되는지 확인 필요

**확인 사항:**
- `GRDataModule`이 `kwargs`로 `text_fn`을 전달하는지
- `get_text_function`이 올바르게 호출되는지

## 📊 데이터셋 수집 방식 호환성

### 데이터 수집 코드 (`mobile_vla_data_collector.py`)
- **프레임 수:** 18프레임 고정 (`fixed_episode_length = 18`)
- **액션 형식:** `(18, 3)` - `[linear_x, linear_y, angular_z]`
- **이미지 형식:** `(18, 720, 1280, 3)` - uint8

### 학습 코드 요구사항
- **필요 프레임:** `window_size + action_chunk_size = 4 + 10 = 14`
- **액션 차원:** 2D (`linear_x, linear_y`만 사용)
- **이미지 크기:** 224x224로 리사이즈

### ✅ 호환성 확인
1. **프레임 수:** 18프레임 ≥ 14프레임 필요량 ✅
2. **액션 차원:** 3D → 2D 변환 (`[:2]` 슬라이싱) ✅
3. **이미지 크기:** 720x1280 → 224x224 리사이즈 ✅

## 🔧 수정 완료 사항

### 1. collater 메서드 추가
```python
def collater(self, data):
    # 배치 데이터 처리
    # - 액션 텐서 스택 (2D)
    # - 이미지 텐서 스택
    # - Chunk 데이터 생성
    # - 언어 토크나이징 (text_fn 사용)
```

### 2. attention_mask 추가
- `__getitem__`에서 `attention_mask` 반환 추가
- 모든 프레임이 유효하므로 `torch.ones(window_size)`

### 3. text_fn 초기화
- `__init__`에서 `self.text_fn = None` 설정
- `collater`에서 `text_fn`이 있으면 사용, 없으면 더미 사용

## ⚠️ 추가 확인 필요 사항

### 1. Config 수정 필요
```json
"act_head": {
    "window_size": 4,  // 1 → 4로 변경 필요
    "fwd_pred_next_n": 10,  // 1 → 10으로 변경 필요
}
```

### 2. text_fn 전달 확인
- `GRDataModule`의 `kwargs`에 `text_fn`이 포함되는지 확인
- `get_text_function`이 올바르게 호출되는지 확인

### 3. 액션 정규화
- 현재: `torch.clamp(actions_tensor, -1.0, 1.0)`
- 데이터: `linear_x, linear_y = ±1.15`
- **1.15가 1.0으로 클램핑됨** - 정상 (정규화 과정)

## 📝 다음 단계

1. ✅ `collater` 메서드 추가 완료
2. ✅ Config의 `act_head` 수정 완료 (`window_size: 4`, `fwd_pred_next_n: 10`)
3. ✅ `text_fn` 초기화 추가 완료 (`tokenizer`, `tokenizer_config`에서 생성)
4. ⚠️ 실제 실행 테스트 필요

## ✅ 수정 완료 사항

### 1. collater 메서드 추가
- 배치 데이터 처리 구현
- 2D 액션 텐서 스택
- Chunk 데이터 생성
- 언어 토크나이징 지원

### 2. text_fn 초기화
- `__init__`에서 `tokenizer`와 `tokenizer_config`를 받아서 `text_fn` 생성
- `get_text_function`을 사용하여 kosmos tokenizer 지원

### 3. Config 수정
- `act_head.window_size`: 1 → 4
- `act_head.fwd_pred_next_n`: 1 → 10
- 최상위 레벨과 일치시킴

### 4. attention_mask 추가
- `__getitem__`에서 `attention_mask` 반환 추가

## 🔍 데이터셋 수집 방식과 학습 코드 호환성 상세 분석

### 데이터 수집 방식 (`mobile_vla_data_collector.py`)

**에피소드 구조:**
- **고정 길이:** 18프레임 (`fixed_episode_length = 18`)
- **이미지:** `(18, 720, 1280, 3)` - uint8, BGR 형식
- **액션:** `(18, 3)` - `[linear_x, linear_y, angular_z]`
  - `linear_x, linear_y = ±1.15` (WASD 키 입력)
  - `angular_z = 0.0` (사용하지 않음)
- **이벤트 타입:** `(18,)` - 문자열 (`'episode_start'`, `'start_action'`, `'stop_action'`)

**수집 패턴:**
- Frame 0: `episode_start` (정지)
- Frame 1-17: `start_action` (WASD 키 입력)
- 각 액션은 0.4초 동안 실행 후 자동 정지

### 학습 코드 요구사항

**필요 프레임 수:**
- `window_size + action_chunk_size = 4 + 10 = 14` 프레임
- **18프레임 ≥ 14프레임** ✅ 충분함

**액션 처리:**
- 입력: `(18, 3)` - `[linear_x, linear_y, angular_z]`
- 사용: `[:2]` 슬라이싱 → `(18, 2)` - `[linear_x, linear_y]`
- 정규화: `torch.clamp(actions_tensor, -1.0, 1.0)`
  - `±1.15` → `±1.0` 클램핑 (정상)

**이미지 처리:**
- 입력: `(720, 1280, 3)` - uint8
- 리사이즈: `224x224` (PIL Image.BILINEAR)
- 정규화: `/255.0` → `[0, 1]` 범위
- 변환: `(H, W, C)` → `(C, H, W)`

### ⚠️ 잠재적 문제점

#### 1. generate_chunck_data 요구사항
```python
# data_utils.py:256
assert seq_len == window_size + chunk_size
```

**문제:** 
- `generate_chunck_data`는 `seq_len == window_size + chunk_size`를 요구
- 현재 데이터셋은 `window_size` 프레임만 반환
- **Chunk 생성 시 shape 불일치 가능성**

**확인 필요:**
- `action_tensors` shape: `(B, window_size, action_chunk_size, 2)`
- `generate_chunck_data` 입력: `(B, window_size + action_chunk_size, ...)`
- **불일치!** 수정 필요

#### 2. 액션 Chunk 구조
**현재 구현:**
- 각 window frame마다 `action_chunk_size`만큼의 future action을 로드
- Shape: `(window_size, action_chunk_size, 2)`

**RoboVLMs 기대:**
- `generate_chunck_data`는 `(window_size + chunk_size)` 길이의 시퀀스를 기대
- 현재는 `window_size` 길이만 제공

**해결 방안:**
- `generate_chunck_data` 호출 전에 액션 시퀀스를 확장해야 함
- 또는 `generate_chunck_data`를 사용하지 않고 직접 chunk 생성

## 🚨 중요: generate_chunck_data 수정 필요

`generate_chunck_data`는 `seq_len == window_size + chunk_size`를 요구하지만, 현재 데이터셋은 `window_size`만 반환합니다. 

**수정 방안:**
1. `collater`에서 `generate_chunck_data` 사용 전에 시퀀스 확장
2. 또는 직접 chunk 생성 (더 안전)

