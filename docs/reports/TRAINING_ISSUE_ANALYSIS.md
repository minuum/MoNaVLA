# LoRA Fine-tuning 문제 분석

## 🔴 발생한 오류

```
RuntimeError: element 0 of tensors does not require grad and does not have a grad_fn
```

## 📊 학습 추이

### 성공한 단계:
1. ✅ 모델 로드 성공
2. ✅ LoRA 적용 (57.01M trainable params)
3. ✅ 데이터셋 로드 성공
4. ✅ Sanity Check 통과
5. ✅ Training 시작

### 실패한 단계:
- ❌ **Epoch 0, Step 0**: Backward pass 실패
- ❌ **원인**: Gradient 계산 불가

## 🔍 문제 원인 분석

### 1. 파라미터 상태
```
Trainable params: 57.01M (LoRA + LSTM)
Non-trainable params: 1.7B (Frozen Backbone)
Total params: 1.7B
```

### 2. 가능한 원인들

#### A. LoRA 파라미터가 실제로 requires_grad=False
- LoRA 적용은 되었지만, `requires_grad` 플래그가 제대로 설정되지 않음
- `get_peft_model` 후 파라미터 상태 확인 필요

#### B. Loss가 frozen 파라미터만 사용
- Loss 계산 시 LoRA 파라미터를 거치지 않음
- Forward pass에서 LoRA 레이어가 bypass됨

#### C. LSTM Policy Head 문제
- LSTM head가 제대로 초기화되지 않음
- LSTM의 gradient가 backbone으로 전파되지 않음

#### D. Mixed Precision 문제
- FP16 사용 시 gradient underflow
- Autocast 설정 문제

## 🔧 해결 방안

### 방안 1: LoRA 파라미터 확인 및 수정

```python
# base_backbone.py의 _trainable_params_setup 수정
if self.train_setup_configs["lora_enable"]:
    from robovlms.utils.lora_utils import find_all_linear_names
    from peft import LoraConfig, get_peft_model
    
    lora_config = LoraConfig(...)
    self.model = get_peft_model(model, lora_config)
    
    # LoRA 파라미터 명시적으로 requires_grad=True 설정
    for name, param in self.model.named_parameters():
        if 'lora' in name.lower():
            param.requires_grad = True
            print(f"LoRA param: {name}, requires_grad={param.requires_grad}")
```

### 방안 2: LSTM Policy Head 확인

```python
# LSTM head가 학습 가능한지 확인
for name, param in self.act_head.named_parameters():
    param.requires_grad = True
    print(f"LSTM param: {name}, requires_grad={param.requires_grad}")
```

### 방안 3: Gradient Checkpointing 비활성화

```json
{
  "train_setup": {
    "gradient_checkpointing": false  // 이미 false
  }
}
```

### 방안 4: Precision 변경

```json
{
  "trainer": {
    "precision": "32"  // FP16 -> FP32로 변경
  }
}
```

## 📝 디버깅 단계

### 1단계: 파라미터 상태 확인
```bash
# main.py에 디버깅 코드 추가
for name, param in model.named_parameters():
    if param.requires_grad:
        print(f"Trainable: {name}, shape={param.shape}")
```

### 2단계: Forward Pass 확인
```python
# Loss가 계산되는지 확인
print(f"Loss: {loss}, requires_grad={loss.requires_grad}")
```

### 3단계: Backward Pass 확인
```python
# Gradient가 계산되는지 확인
loss.backward()
for name, param in model.named_parameters():
    if param.requires_grad and param.grad is not None:
        print(f"Gradient: {name}, grad_norm={param.grad.norm()}")
```

## 🎯 즉시 시도할 해결책

### 우선순위 1: LoRA 파라미터 명시적 활성화
RoboVLMs upstream 코드에서 LoRA 적용 후 파라미터 상태를 명시적으로 설정

### 우선순위 2: FP32로 변경
Mixed precision 문제 가능성 배제

### 우선순위 3: 간단한 테스트
- 배치 크기 1로 줄여서 테스트
- Window size 줄여서 테스트
- Action chunk size 줄여서 테스트

## 📌 참고사항

### RoboVLMs 원본 설정
```json
{
  "lora_enable": true,
  "lora_r": 8,  // 우리는 32
  "lora_alpha": 16,  // 동일
  "freeze_backbone": true,  // 동일
  "train_vision": false  // 동일
}
```

### 차이점
- **lora_r**: 8 → 32 (더 큰 rank)
- **action_dim**: 7 → 2 (우리는 2D, 패딩으로 7D)

## 🚀 다음 액션

1. **즉시**: LoRA 파라미터 requires_grad 확인
2. **다음**: FP32로 변경하여 재시도
3. **마지막**: RoboVLMs 원본 설정으로 되돌려서 테스트

---

**작성**: 2025-11-06 16:30
**상태**: 문제 분석 완료, 해결 방안 수립

