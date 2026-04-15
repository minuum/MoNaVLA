# Kosmos-2 In-place Operation 오류 및 해결

## 1. 문제 상황
- **오류 메시지**: `RuntimeError: a leaf Variable that requires grad is being used in an in-place operation.`
- **발생 위치**: `transformers/models/kosmos2/modeling_kosmos2.py`의 `forward_embedding` 메서드.
- **원인**:
  - 모델이 내부적으로 `pixel_values`로부터 `image_embeds`를 생성.
  - `input_ids`로부터 `inputs_embeds`를 생성 (`embed_tokens` 사용).
  - `inputs_embeds`의 특정 위치에 `image_embeds`를 **In-place (`inputs_embeds[mask] = ...`)** 로 할당 시도.
  - `freeze_backbone=True` 및 `LoRA` 설정 하에서, `embed_tokens`의 출력이 **Leaf Variable(말단 변수)**이면서 **Gradient가 필요한 상태**로 인식됨.
  - PyTorch는 Gradient가 필요한 Leaf Variable에 대한 In-place 수정을 금지함.

## 2. 해결 방법
RoboVLMs의 `BaseRoboVLM.forward_continuous` 내 Kosmos 처리 분기를 수정.

### 수정 전 (Original / Generic Path)
- `vision_x`와 `lang_x`를 결합하여 `multimodal_embeds`를 생성 후 `inputs_embeds`로 전달.
- Kosmos-2는 이 방식을 거부 (`ValueError: pixel_values or image_embeds required`).

### 수정 후 (Custom Fix)
1. **수동 임베딩 생성**: `self.model` 호출 전, `BaseRoboVLM`에서 직접 `input_ids`를 임베딩하여 `inputs_embeds` 생성.
2. **Non-leaf 변수 변환**: `inputs_embeds = inputs_embeds.clone()`을 수행.
   - `clone()`된 텐서는 계산 그래프 상의 중간 노드(Non-leaf)가 되며, In-place 수정이 허용됨.
3. **모델 전달**: 수정된 `inputs_embeds`와 `pixel_values`를 함께 전달.
4. **Action Token 추가**: `inputs_embeds` 끝에 `action_token`을 수동으로 추가하여 액션 예측 유도.

## 3. 코드 변경 (RoboVLMs_upstream/robovlms/model/backbone/base_backbone.py)
```python
# Create inputs_embeds manually from input_ids
text_model = self.model.text_model
inputs_embeds = text_model.model.embed_tokens(dummy_input_ids)

# Clone inputs_embeds to make it a non-leaf variable (computed variable)
# This is the Key Fix: Cloned tensors can be modified in-place
inputs_embeds = inputs_embeds.clone()

# ... (Action Token 추가 로직) ...

# Pass both pixel_values and inputs_embeds
output = self.model(
    pixel_values=pixel_values,
    inputs_embeds=inputs_embeds,
    # ...
)
```

## 4. 남은 과제
- `action_token_mask` 경고: 이미지(Window size)와 텍스트(Instruction)의 배치 차원으로 인한 마스크 불일치 경고가 뜨지만, Fallback 로직으로 학습은 진행 중.

