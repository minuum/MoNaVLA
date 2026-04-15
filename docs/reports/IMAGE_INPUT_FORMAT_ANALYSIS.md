# 이미지 입력 형식 문제 분석 및 해결

## 문제 요약

```
ValueError: You have to specify either `pixel_values` or `image_embeds`.
```

Kosmos 모델의 `forward` 메서드에서 `pixel_values` 또는 `image_embeds` 중 하나가 필요하지만, `forward_continuous`에서 전달하지 않아 발생하는 에러입니다.

## 원본 vs 수정본 비교

### 1. 원본 RoboVLMs 코드 (`RoboVLMs/robovlms/model/backbone/base_backbone.py`)

**Line 1132-1169**: Kosmos 모델을 위한 에러 핸들링이 **있음**

```python
try:
    output = self.model(
        input_ids=None,
        attention_mask=multimodal_attention_mask,
        position_ids=position_ids,
        past_key_values=past_key_values,
        inputs_embeds=multimodal_embeds,
        use_cache=use_cache,
        output_hidden_states=True,
    )
except ValueError as e:
    # Some backbones (e.g., Kosmos-2) require pixel_values or image_embeds.
    # Fall back to passing pixel_values directly for Kosmos
    if "pixel_values" in str(e) or "image_embeds" in str(e):
        # vision_x is shaped as (bs*seq, 1, C, H, W) for history_type in [pre, post]
        # Use pixel_values pathway for Kosmos
        if vision_x.ndim == 5 and vision_x.shape[1] == 1:
            pixel_values = vision_x.squeeze(1)
        else:
            pixel_values = vision_x
        
        # For Kosmos, use pixel_values only (not both pixel_values and image_embeds)
        # ... (추가 처리 로직)
```

### 2. 우리가 사용하는 코드 (`RoboVLMs_upstream/robovlms/model/backbone/base_backbone.py`)

**Line 1115-1123**: 에러 핸들링이 **없음**

```python
output = self.model(
    input_ids=None,
    attention_mask=multimodal_attention_mask,
    position_ids=position_ids,
    past_key_values=past_key_values,
    inputs_embeds=multimodal_embeds,
    use_cache=use_cache,
    output_hidden_states=True,
)
```

## 이미지 처리 파이프라인

### 1. 데이터셋 → 모델까지의 경로

#### 원본 DiskCalvinDataset
- `__getitem__`: `{"rgb_obs": {"rgb_static": tensor}}` 형태 반환
- `collater`: `image_tensors = torch.stack([s["rgb_obs"]["rgb_static"] for s in sample])`
- Shape: `(B, window_size + fwd_pred_next_n, C, H, W)`

#### 우리 MobileVLAH5Dataset
- `__getitem__`: `{"rgb": tensor}` 형태 반환
- `collater`: `image_tensors = torch.stack([s["rgb"] for s in data], dim=0)`
- Shape: `(B, window_size + fwd_pred_next_n, C, H, W)`
- ✅ **데이터셋은 문제 없음**

### 2. forward_continuous에서의 이미지 처리

#### Line 1007-1008: vision_x reshape
```python
if history_type in ["post", "pre"]:
    vision_x = vision_x.reshape(bs * seq_len, *vision_x.shape[2:]).unsqueeze(1)
    # (bs, seq_len, C, H, W) → (bs * seq_len, C, H, W) → (bs * seq_len, 1, C, H, W)
```

#### Line 1028-1039: merge_multi_modal_input 호출
```python
multimodal_embeds, ... = self.merge_multi_modal_input(
    input_embeds,
    vision_x,  # (bs * seq_len, 1, C, H, W)
    labels=None,
    attention_mask=attention_mask,
    insert_idx=bos_offset,
)
```

#### merge_multi_modal_input (Line 306-315)
```python
if is_image:
    rgb_feats = self.encode_images(multimodal_feats)  # vision_x를 encode_images로 전달
```

#### encode_images (Line 171-204)
```python
if images.ndim == 5:  # (bs * seq_len, 1, C, H, W)
    concat_images = torch.cat([image for image in images], dim=0)
    # (bs * seq_len, 1, C, H, W) → (bs * seq_len, C, H, W)
    image_features = self.model_encode_images(concat_images)
```

#### model_encode_images (RoboKosMos, Line 27-44)
```python
def model_encode_images(self, images):
    vision_model_output = self.model.vision_model(
        pixel_values=images,  # (bs * seq_len, C, H, W)
        ...
    )
    # image_embeds 생성 및 반환
```

### 3. 문제 발생 지점

**Line 1115**: `self.model()` 호출 시
- `inputs_embeds=multimodal_embeds`만 전달
- `pixel_values` 또는 `image_embeds`를 전달하지 않음
- Kosmos 모델은 `inputs_embeds`만으로는 작동하지 않음 (내부적으로 `pixel_values` 또는 `image_embeds` 필요)

## 해결 방법

원본 RoboVLMs 코드의 에러 핸들링을 `RoboVLMs_upstream`에 추가해야 합니다.

### 수정 사항

`RoboVLMs_upstream/robovlms/model/backbone/base_backbone.py`의 `forward_continuous` 메서드에 try-except 블록 추가:

```python
try:
    output = self.model(
        input_ids=None,
        attention_mask=multimodal_attention_mask,
        position_ids=position_ids,
        past_key_values=past_key_values,
        inputs_embeds=multimodal_embeds,
        use_cache=use_cache,
        output_hidden_states=True,
    )
except ValueError as e:
    # Some backbones (e.g., Kosmos-2) require pixel_values or image_embeds.
    # Fall back to passing pixel_values directly for Kosmos
    if "pixel_values" in str(e) or "image_embeds" in str(e):
        # vision_x is shaped as (bs*seq, 1, C, H, W) for history_type in [pre, post]
        # Use pixel_values pathway for Kosmos
        if vision_x.ndim == 5 and vision_x.shape[1] == 1:
            pixel_values = vision_x.squeeze(1)  # (bs*seq, C, H, W)
        else:
            pixel_values = vision_x
        
        # For Kosmos, use pixel_values only (not both pixel_values and image_embeds)
        output = self.model(
            pixel_values=pixel_values,
            input_ids=None,
            attention_mask=multimodal_attention_mask,
            position_ids=position_ids,
            past_key_values=past_key_values,
            inputs_embeds=multimodal_embeds,
            use_cache=use_cache,
            output_hidden_states=True,
        )
    else:
        raise e
```

## 결론

1. **데이터셋**: 문제 없음 ✅
2. **이미지 전처리**: 문제 없음 ✅
3. **Kosmos 모델 호출**: 에러 핸들링 누락 ❌ → **수정 필요**

원본 RoboVLMs에는 이미 이 문제에 대한 해결책이 있지만, 우리가 사용하는 `RoboVLMs_upstream`에는 없습니다. 원본 코드의 에러 핸들링을 추가하면 해결됩니다.


