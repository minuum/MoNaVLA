# 🔍 RoboVLMs 구조 분석 및 18프레임 의도 확인

**Date:** 2025-11-14  
**목적:** RoboVLMs 기본 설정 확인 및 18프레임 수집 의도 검증

## ✅ 확인된 사실

### RoboVLMs 기본 설정
- **window_size:** 8 (히스토리 길이)
- **fwd_pred_next_n:** 10 (예측할 액션 청크 수)
- **총 필요 프레임:** 8 + 10 = **18프레임** ✅

### 18프레임 수집 의도
**데이터 수집 시 18프레임으로 수집한 이유:**
- RoboVLMs의 기본 설정 `window_size=8`, `fwd_pred_next_n=10`에 맞춤
- `window_size + fwd_pred_next_n = 18` 프레임이 필요
- 정확히 18프레임으로 수집하여 RoboVLMs 구조와 완벽히 일치

## 📊 DiskCalvinDataset 구조 분석

### `__getitem__` 반환 구조
```python
# _get_sequences 호출
sequence = self._get_sequences(idx, self.window_size, head=head)
# 실제로는 _load_episode에서 window_size + act_step 길이 로드
```

### `_load_episode` 구조
```python
end_idx = start_idx + window_size + self.act_step - 1
# act_step은 보통 fwd_pred_next_n과 동일
# 즉, window_size + fwd_pred_next_n 길이를 로드
```

### `collater` 구조
```python
# 1. 액션 텐서 스택
action_tensors = torch.from_numpy(
    np.array([np.stack(s["actions"]) for s in sample])
)[:, :-1]  # 마지막 프레임 제거
# Shape: (B, window_size + fwd_pred_next_n - 1, action_dim)

# 2. unfold로 chunk 생성
action_chunck = action_tensors.unfold(1, self.fwd_pred_next_n, 1).permute(0, 1, 3, 2)
# Shape: (B, window_size + fwd_pred_next_n - 2, fwd_pred_next_n, action_dim)

# 3. 이미지도 동일하게 처리
image_chunk = image_tensors.unfold(1, self.fwd_pred_next_n, 1).permute(0, 1, 5, 2, 3, 4)[:, 1:]
image_tensors = image_tensors[:, : self.window_size]
```

## 🔧 MobileVLAH5Dataset 수정 사항

### 1. Config 수정
- `window_size`: 4 → **8** (RoboVLMs 기본값)
- `fwd_pred_next_n`: 10 (유지)
- `act_head.window_size`: 1 (유지, 내부 설정)
- `act_head.fwd_pred_next_n`: 1 (유지, 내부 설정)

### 2. 데이터셋 구조 수정

#### `__getitem__` 수정
- **이전:** `window_size` 프레임만 로드
- **수정:** `window_size + fwd_pred_next_n = 18` 프레임 로드
- **액션:** `(18, 2)` 시퀀스 형태로 반환 (chunk 형태 아님)

#### `collater` 수정
- **이전:** `generate_chunck_data` 사용 (shape 불일치)
- **수정:** `unfold` 사용 (DiskCalvinDataset과 동일)
- **구조:** DiskCalvinDataset과 완전히 동일한 방식

### 3. 반환 키 이름 수정
- `'action'` → `'actions'` (DiskCalvinDataset과 동일)
- `'lang'` 추가 (DiskCalvinDataset과 동일)
- `'action_mask'`, `'image_mask'` 추가

## 📋 최종 구조

### `__getitem__` 반환
```python
{
    'rgb': (18, C, H, W),  # window_size + fwd_pred_next_n
    'hand_rgb': (18, C, H, W),
    'actions': (18, 2),  # 시퀀스 형태
    'action_mask': (18,),
    'image_mask': (18,),
    'lang': str,
    'raw_text': str,
    ...
}
```

### `collater` 반환
```python
{
    'rgb': (B, 8, C, H, W),  # window_size만
    'hand_rgb': (B, 8, C, H, W),
    'action': (B, 17, 2),  # window_size + fwd_pred_next_n - 1
    'action_chunck': (B, 16, 10, 2),  # unfold로 생성
    'fwd_rgb_chunck': (B, 16, 10, C, H, W),
    ...
}
```

## ✅ 검증 완료

1. ✅ **18프레임 의도 확인:** RoboVLMs 기본 설정과 일치
2. ✅ **데이터셋 구조 수정:** DiskCalvinDataset과 동일한 구조
3. ✅ **Config 수정:** window_size=8, fwd_pred_next_n=10
4. ✅ **collater 수정:** unfold 방식으로 chunk 생성

## 🎯 결론

**18프레임 수집은 RoboVLMs의 기본 설정(`window_size=8`, `fwd_pred_next_n=10`)에 맞춘 정확한 설계였습니다.**

이제 데이터셋 구조가 RoboVLMs와 완벽히 호환됩니다.

