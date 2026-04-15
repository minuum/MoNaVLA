# Kosmos 이미지 임베딩 문제 분석

## 에러 메시지 (진행 순서)

### 1. Shape Mismatch 에러
```
RuntimeError: shape mismatch: value tensor of shape [512, 2048] cannot be broadcast to indexing result of shape [112, 2048]
```

### 2. NoneType 에러
```
AttributeError: 'NoneType' object has no attribute 'to'
```

### 3. Dtype Mismatch 에러 (현재)
```
RuntimeError: Index put requires the source and destination dtypes match, got Float for the destination and Half for the source.
```

## 문제 분석

### Shape Mismatch 문제
1. **`image_embeds` shape**: `[512, 2048]`
   - 512개의 이미지 토큰 (8 배치 * 64 토큰)
   - 각 토큰은 2048차원

2. **`img_input_mask`로 선택된 부분**: `[112, 2048]` 또는 `[8, 2048]`
   - 마스크가 올바르게 설정되지 않음

3. **해결**: `input_ids`를 `num_image_tokens` (64) 길이로 패딩하고, `image_embeds_position_mask`의 처음 64개 위치를 `True`로 설정

### Dtype Mismatch 문제 (현재)
1. **원인**: AMP (Automatic Mixed Precision) 사용 시
   - `inputs_embeds`: Float (float32)
   - `image_embeds`: Half (float16)

2. **위치**: Kosmos 모델 내부 `forward_embedding` 메서드
   - `inputs_embeds[img_input_mask] = image_embeds.to(inputs_embeds.device).view(...)`
   - dtype 변환이 제대로 이루어지지 않음

## 해결 시도

1. ✅ `image_embeds_position_mask`를 `input_ids` 길이에 맞춰 생성
2. ✅ `input_ids`를 `num_image_tokens` (64) 길이로 패딩
3. ✅ `image_embeds_position_mask`의 처음 64개 위치를 `True`로 설정
4. ❌ Dtype 불일치 문제 발생 (Kosmos 모델 내부 문제)

## 현재 상태

- Shape 문제는 해결됨 (input_ids 패딩 및 마스크 생성)
- Dtype 불일치 문제 발생 (AMP 사용 시)

## 다음 단계

1. Kosmos 모델의 `forward_embedding`에서 dtype 변환 확인
2. 또는 AMP를 비활성화하거나 precision 설정 조정
3. 또는 `pixel_values`의 dtype을 조정


