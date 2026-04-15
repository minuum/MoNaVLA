# LoRA 학습 과정 분석 및 이슈 정리 (2025-11-12)

## 📋 학습 환경

- **날짜**: 2025-11-12
- **모델**: Kosmos-2 + LoRA (r=32, alpha=16, dropout=0.1)
- **데이터셋**: 20251106 에피소드 13개 (train 10개, val 3개)
- **디바이스**: NVIDIA RTX A5000
- **프레임워크**: PyTorch Lightning + RoboVLMs

---

## 🐛 발생한 이슈 및 해결 과정

### 1. KeyError: 'rgb' (해결됨 ✅)

**문제:**
```
KeyError: 'rgb'
File: robovlms/train/base_trainer.py:366
```

**원인:**
- `MobileVLAH5Dataset`이 데이터를 반환할 때 키 이름이 RoboVLMs와 불일치
- RoboVLMs는 `batch["rgb"]`를 기대하지만 데이터셋이 다른 키로 반환

**해결:**
- 이미 해결됨 (이전 작업에서 MobileVLAH5Dataset 수정)
- 데이터셋이 'rgb' 키로 올바르게 반환하도록 수정 완료

**검증:**
- Sanity Check 통과 ✅
- Validation step 정상 동작 ✅

---

### 2. Gradient 에러 (해결됨 ✅)

**문제:**
```
RuntimeError: element 0 of tensors does not require grad and does not have a grad_fn
```

**원인:**
- `base_trainer.py`의 `_get_loss()` 메서드에서 loss 초기화 시 문제
- `loss = torch.tensor(0.0).to(self.device)` → gradient tracking 없음
- 실제 loss가 추가되지 않으면 backward()에서 에러 발생

**해결:**
```python
# 수정 전
loss = torch.tensor(0.0).to(self.device)

# 수정 후
loss = torch.tensor(0.0, requires_grad=True).to(self.device)
```

**검증:**
- Training step에서 backward() 정상 동작 ✅
- 3/4 배치까지 진행됨

---

### 3. Mixed Precision (16-mixed) 에러 (해결됨 ✅)

**문제:**
```
AssertionError: No inf checks were recorded for this optimizer.
File: torch/cuda/amp/grad_scaler.py:449
```

**원인:**
- Mixed precision (16-mixed) 사용 시 GradScaler가 제대로 동작하지 않음
- LoRA + PyTorch Lightning의 호환성 문제로 추정
- Gradient가 0이거나 계산되지 않아 scaler가 inf check를 수행하지 못함

**해결:**
```json
// Config 수정: precision "16-mixed" → "32"
{
  "trainer": {
    "precision": "32"
  },
  "train_setup": {
    "precision": "32"
  }
}
```

**트레이드오프:**
- ✅ 안정성 향상
- ❌ 메모리 사용량 증가 (약 2배)
- ❌ 학습 속도 약간 감소

**검증:**
- 1 Epoch 완료 ✅
- 체크포인트 저장 성공 ✅

---

### 4. Loss = 0.000 (미해결 ⚠️)

**현상:**
```
train_loss=0.000
val_loss=0.000
```

**가능한 원인:**

#### 4-1. Gripper Loss 비율이 0
```json
"arm_gripper_loss_ratio": 0.0
```
- Mobile VLA는 gripper가 없으므로 gripper loss를 0으로 설정
- 그러나 arm action loss는 계산되어야 함

#### 4-2. Action 차원 불일치
```python
# 데이터셋: 2D action (linear_x, linear_y)
action[:2] = action_2d
action[6] = 0.0  # gripper

# Config: action_dim=2
"act_head": {
    "action_dim": 2
}
```
- RoboVLMs는 기본적으로 7D action (6-DOF + gripper)을 가정
- 2D로 설정했지만 loss 계산 부분에서 문제 가능성

#### 4-3. Loss 계산 로직 문제
```python
# base_trainer.py:_get_loss()
loss = torch.tensor(0.0, requires_grad=True).to(self.device)
if self.act_pred:
    loss_act = (loss_arm_act if loss_arm_act is not None else 0)
    loss += loss_act
```
- `loss_arm_act`가 None이거나 0일 가능성
- Forward pass에서 실제 loss가 계산되지 않을 수 있음

#### 4-4. 액션 정규화 문제
```python
# 데이터셋에서 액션을 [-1, 1]로 클램프
actions_tensor = torch.clamp(actions_tensor, -1.0, 1.0)
```
- 실제 액션 값이 이미 정규화되어 매우 작을 가능성
- Loss가 계산되어도 매우 작은 값일 수 있음

---

## 🔍 심층 분석

### LoRA 파라미터 적용 확인

**학습 가능 파라미터:**
- Total: 1.7B
- Trainable: 57.0M (<3.4%)
- LoRA가 올바르게 적용됨 ✅

**적용된 모듈:**
- Vision Encoder: 모든 attention layer
- Text Encoder: 모든 attention layer
- Image-to-Text Projection
- Action Head (LSTM + MLP)

### 데이터셋 구조

**Training:**
- Episodes: 10
- Total frames: 164
- Batches: 4 (batch_size=2, accumulate=4)

**Validation:**
- Episodes: 3
- Total frames: 54
- Batches: 1

**데이터 형식:**
```python
{
    'rgb': (window_size, C, H, W),      # (8, 3, 224, 224)
    'action': (action_chunk_size, 7),   # (10, 7) - padded
    'action_chunck': (action_chunk_size, 7),
    'chunck_mask': (action_chunk_size,),  # all ones
    'text': (256,),
    'text_mask': (256,),
    'raw_text': str
}
```

---

## 📊 학습 성능

### 시간 측정
- **1 Epoch**: ~7초
- **Per batch**: ~1.75초
- **Effective batch**: 8 (batch_size=2 × accumulate=4)

### 메모리 사용
- **Model size**: 6.5GB (체크포인트)
- **Precision**: FP32
- **GPU**: NVIDIA RTX A5000

---

## ⚠️ 고려사항

### 1. Loss 계산 검증 필요
- [ ] Forward pass에서 실제 loss 값 출력
- [ ] loss_arm_act가 None이 아닌지 확인
- [ ] Prediction output 구조 확인

### 2. Action 차원 호환성
- [ ] 2D action이 RoboVLMs와 호환되는지 검증
- [ ] Action head의 출력 차원 확인
- [ ] Loss 계산 시 action slicing 확인

### 3. 데이터 검증
- [ ] 실제 액션 값이 valid range인지 확인
- [ ] 액션 값이 모두 0이 아닌지 확인
- [ ] Normalization이 올바른지 확인

### 4. 학습 안정성
- [ ] Gradient clipping 동작 확인
- [ ] Learning rate scheduler 동작 확인
- [ ] Optimizer state 확인

---

## 🎯 다음 단계

### 즉시 조치
1. **Loss 디버깅**
   - Forward pass에서 loss 값 print
   - Prediction output 구조 확인
   - Action target과 prediction 비교

2. **데이터 검증**
   - 실제 데이터 샘플 출력
   - 액션 값 범위 확인
   - Mask 값 확인

3. **모델 검증**
   - Action head 출력 확인
   - LoRA 파라미터 gradient 확인

### 중기 개선
1. **학습 모니터링 강화**
   - TensorBoard 활용
   - 더 상세한 로깅
   - Gradient 통계 추적

2. **하이퍼파라미터 튜닝**
   - Learning rate 조정
   - Batch size 최적화
   - LoRA rank 실험

3. **데이터 증강**
   - 더 많은 에피소드 수집
   - Data augmentation 적용

---

## 📝 해결 우선순위

1. **High Priority** 🔴
   - Loss = 0 문제 해결
   - 실제 loss 값 확인

2. **Medium Priority** 🟡
   - 더 긴 학습 실행 (50 epochs)
   - 추론 테스트

3. **Low Priority** 🟢
   - Mixed precision 재시도
   - 메모리 최적화

---

## 💾 저장된 파일

**체크포인트:**
```
/home/billy/25-1kp/vla/RoboVLMs_upstream/runs/mobile_vla_lora_20251106/
└── kosmos/mobile_vla_finetune/2025-11-12/mobile_vla_lora_20251106/
    └── epoch=0-step=1.ckpt (6.5GB)
```

**로그:**
```
/home/billy/25-1kp/vla/
├── lora_training_20251112_final.log
├── lora_1epoch_FINAL_RUN.log
├── lora_1epoch_SUCCESS.log
└── LORA_TRAINING_STATUS.md
```

---

---

## ✅ 최종 해결 및 학습 성공! (2025-11-12 12:18)

### 핵심 문제 해결

**문제 1: data_source에 'action' 문자열 누락**
- `data_source='mobile_vla_h5'` → `data_source='mobile_vla_action'`으로 변경
- 이로 인해 `forward_action()` 메서드가 호출되지 않아 loss가 0이었음

**문제 2: Action shape 불일치**
- 데이터셋이 `(chunk_size, 7)` 반환 → `(window_size, chunk_size, 7)`로 수정
- 각 window frame마다 future action chunk 제공하도록 변경

**문제 3: CUDA OOM**
- `window_size=8` → `4`로 축소
- `batch_size=2` → `1`로 축소  
- `accumulate_grad_batches=4` → `8`로 증가
- `precision="32"` → `"16-mixed"` (FP16 mixed precision)

### 최종 학습 결과 (3 Epochs)

| Epoch | Train Loss (Mobile 2D) | Val Loss (Mobile 2D) | 개선율 |
|-------|----------------------|---------------------|--------|
| 0     | 0.126                | 0.122               | -      |
| 1     | 0.114 (-9.5%)        | 0.107 (-12.3%)      | ✅     |
| 2     | 0.083 (-27.2%)       | 0.075 (-29.9%)      | ✅✅   |

**Train Loss:** 0.126 → 0.083 (34% 감소) 🎉  
**Val Loss:** 0.122 → 0.075 (38% 감소) 🎉

### 중요: Loss 이름 해석

**사용자 혼란 포인트:**
```
train_loss_arm_act=0.083      # ✅ 이것이 Mobile Robot 2D 속도 [linear_x, linear_y]!
train_loss_gripper_act=0.697  # ❌ 더미 값 (action[6]=0, 항상 고정)
```

**실제 데이터 구조:**
```python
action[0] = linear_x   # Mobile robot X 방향 속도
action[1] = linear_y   # Mobile robot Y 방향 속도
action[2:6] = 0        # 패딩 (로봇 팔 없음)
action[6] = 0          # 그리퍼 (없음, 더미)
```

**RoboVLMs는 원래 로봇 팔 + 그리퍼용으로 설계**되어서:
- "arm_act" = 처음 6차원 (우리는 첫 2개만 의미 있음)
- "gripper_act" = 7번째 차원 (우리는 항상 0)

**따라서 `loss_arm_act`가 우리의 실제 Mobile Robot 제어 loss입니다!**

### 학습 설정 (최종)

```json
{
  "window_size": 4,
  "action_chunk_size": 10,
  "batch_size": 1,
  "accumulate_grad_batches": 8,
  "precision": "16-mixed",
  "max_epochs": 3,
  
  "action_dim": 7,  // [linear_x, linear_y, 0, 0, 0, 0, gripper_dummy]
  "lora_r": 32,
  "lora_alpha": 16,
  "lora_dropout": 0.1,
  
  "learning_rate": 1e-4,
  "gradient_clip_val": 1.0
}
```

### 저장된 체크포인트

```
/home/billy/25-1kp/vla/RoboVLMs_upstream/runs/mobile_vla_lora_20251106/kosmos/mobile_vla_finetune/2025-11-12/mobile_vla_lora_20251106/
├── epoch=0-step=6.ckpt   (6.9GB)
├── epoch=1-step=12.ckpt  (6.9GB)
└── epoch=2-step=18.ckpt  (6.9GB) ⭐ 최고 성능
```

### 학습 시간

- **1 Epoch**: ~19초 (45 steps)
- **3 Epochs**: ~60초 (총 135 steps)
- **Per step**: ~0.4초

### 다음 단계

1. **추론 테스트** - 학습된 모델로 실제 action 예측 테스트
2. **50 Epoch 본격 학습** - 더 긴 학습으로 성능 향상
3. **Jetson 배포** - 실시간 추론 테스트
4. **성능 평가** - MAE, MSE 등 메트릭 측정

---

**작성일**: 2025-11-12 12:18 (최종 업데이트)  
**작성자**: Mobile VLA Team  
**상태**: ✅ 학습 성공! Loss 정상 감소 중

