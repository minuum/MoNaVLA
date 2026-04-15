# Mobile VLA 학습 설정 및 입출력 구조 브리핑 (2025-11-19)

## 학습 설정 요약

### 기본 설정
- **모델**: Kosmos-2 (Vision-Language-Action)
- **학습 방법**: LoRA Fine-tuning
- **Max Epochs**: 10 (변경됨, 이전 20)
- **Batch Size**: 1
- **Gradient Accumulation**: 8 (Effective batch size = 8)
- **Learning Rate**: 1e-4
- **Weight Decay**: 0.01
- **Optimizer**: AdamW
- **Precision**: 16-mixed (FP16)

### 데이터셋 설정
- **데이터셋 타입**: MobileVLAH5Dataset
- **데이터 경로**: `/home/billy/25-1kp/vla/ROS_action/mobile_vla_dataset`
- **에피소드 패턴**: `episode_2025111*.h5`
- **에피소드 수**: 231개
- **Train/Val 분할**: 80% / 20% (약 185개 / 46개)
- **Window Size**: 8 (관찰 프레임 수)
- **Forward Prediction**: 10 (예측할 미래 프레임 수)

### LoRA 설정
- **LoRA 활성화**: true
- **LoRA rank (r)**: 32
- **LoRA alpha**: 16
- **LoRA dropout**: 0.1
- **Backbone Freeze**: true (Kosmos-2 백본 고정)
- **Trainable**: LoRA weights + Policy Head만

### 체크포인트 설정 (변경됨)
- **save_top_k**: 3 (최고 성능 3개만 저장)
- **every_n_epochs**: 1 (매 epoch 체크)
- **monitor**: "val_loss" (validation loss 기준)
- **save_last**: true (마지막 epoch도 저장)
- **예상 저장량**: 최대 4개 = 27.6GB

---

## 입출력 데이터 구조

### 1. 데이터셋 레벨 (MobileVLAH5Dataset.__getitem__)

**입력 (HDF5 파일에서 로드)**:
- 이미지: 18개 프레임 (window_size=8 + fwd_pred_next_n=10)
- 액션: 18개 프레임의 2D 속도 [linear_x, linear_y]
- 언어 명령: "Navigate to the target location" (기본)

**출력 (개별 샘플)**:
```python
{
    'rgb': (18, C, H, W),              # 이미지 시퀀스
    'hand_rgb': (18, C, H, W),         # 더미 gripper 이미지
    'actions': (18, 2),                 # 2D 속도 [linear_x, linear_y]
    'action_mask': (18,),               # 액션 마스크
    'image_mask': (18,),                # 이미지 마스크
    'text': (256,),                     # 토크나이징된 텍스트
    'text_mask': (256,),                # 텍스트 마스크
    'lang': str,                        # 원본 언어 명령
    'raw_text': str,
    'data_source': 'mobile_vla_action',
    'attention_mask': (18,)
}
```

### 2. 배치 레벨 (collater)

**입력**: 개별 샘플 리스트

**출력 (배치)**:
```python
{
    "rgb": (B, window_size, C, H, W),                    # [B, 8, 3, 224, 224]
    "hand_rgb": (B, window_size, C, H, W),               # [B, 8, 3, 224, 224]
    "action": (B, window_size + fwd_pred_next_n - 1, 2), # [B, 17, 2]
    "text": (B, seq_len),                                 # [B, 256]
    "text_mask": (B, seq_len),                            # [B, 256]
    "fwd_rgb_chunck": (B, seq_len, fwd_pred_next_n, C, H, W),  # [B, 7, 10, 3, 224, 224]
    "fwd_hand_rgb_chunck": (B, seq_len, fwd_pred_next_n, C, H, W),
    "fwd_mask": (B, seq_len, fwd_pred_next_n),           # [B, 7, 10]
    "action_chunck": (B, seq_len, fwd_pred_next_n, 2),   # [B, 7, 10, 2]
    "chunck_mask": (B, seq_len, fwd_pred_next_n),        # [B, 7, 10]
    "raw_text": List[str],
    "data_source": "mobile_vla_action"
}
```

**Chunk 생성 방식**:
- `unfold`를 사용하여 sliding window 방식으로 chunk 생성
- 마지막 프레임 제거 후 chunk 생성
- 예: 18개 프레임 → window_size=8, fwd_pred_next_n=10
  - RGB: (B, 8, C, H, W) - 관찰용
  - RGB chunk: (B, 7, 10, C, H, W) - 미래 예측용
  - Action chunk: (B, 7, 10, 2) - 타겟 속도 시퀀스

### 3. Trainer 레벨 (MobileVLATrainer._process_batch)

**입력**: 배치 딕셔너리

**처리**:
- RGB 이미지 → CUDA로 이동, shape 확인
- 텍스트 토큰 → CUDA로 이동
- 액션 → velocity로 변환 (2D 속도)
- Chunk 데이터 처리

**출력 (튜플)**:
```python
(
    rgb,                    # (B, window_size, C, H, W) - 관찰 이미지
    hand_rgb,              # (B, window_size, C, H, W) - 더미
    attention_mask,        # (B, window_size)
    language,              # (B, seq_len) - 토크나이징된 텍스트
    text_mask,             # (B, seq_len)
    fwd_rgb_chunck,        # (B, seq_len, fwd_pred_next_n, C, H, W) - 미래 이미지
    fwd_hand_rgb_chunck,   # (B, seq_len, fwd_pred_next_n, C, H, W)
    velocity,              # (B, window_size, 2) - 현재 속도
    gripper_action,        # None
    velocity_chunck,       # (B, seq_len, fwd_pred_next_n, 2) - 미래 속도 타겟
    gripper_action_chunck, # None
    chunck_mask,           # (B, seq_len, fwd_pred_next_n)
    fwd_mask,              # (B, seq_len, fwd_pred_next_n)
    instr_and_action_ids,  # None (discrete action 미사용)
    instr_and_action_labels, # None
    instr_and_action_mask,  # None
    raw_text,              # List[str]
    rel_state,             # None
    data_source            # "mobile_vla_action"
)
```

### 4. Backbone 레벨 (BaseRoboVLM.forward_continuous)

**입력**:
- `vision_x`: (B, window_size, C, H, W) - 관찰 이미지
- `lang_x`: (B, seq_len) - 토크나이징된 텍스트
- `attention_mask`: (B, window_size)
- `action_labels`: (velocity_chunck, None) - 타겟 속도

**처리**:
1. **Vision Encoding**: Kosmos-2 Vision Encoder
   - 이미지 → image_embeds (B, num_image_tokens, hidden_dim)
   - image_embeds_position_mask 생성

2. **Text Processing**: 
   - lang_x와 image_embeds 결합
   - Kosmos-2 Text Encoder로 통합 처리

3. **Multimodal Fusion**:
   - Vision + Text → Multimodal embeddings
   - Action token 위치에 action embeddings 삽입

**출력**:
- `output_hs`: (B, seq_len, hidden_dim) - Multimodal hidden states
- `action_hs`: (B, seq_len, hidden_dim) - Action token hidden states

### 5. Policy Head 레벨 (MobileVLALSTMDecoder)

**입력**:
- `tok_seq`: (B, seq_len, latent_num, feature_dim) 또는 (B, seq_len, in_features * latent)
- `h_0`: 초기 hidden state (optional)

**처리**:
1. **Down Sampling**: 
   - `down_sample="none"`: reshape만 수행
   - `tok_seq`: (B, seq_len, in_features * latent)

2. **LSTM Decoder**:
   - History memory 관리 (window_size=8)
   - LSTM으로 시퀀스 처리
   - Hidden state 업데이트

3. **Velocity Prediction**:
   - MLP Head로 속도 예측
   - `velocities`: (B, seq_len, fwd_pred_next_n * action_dim)

**출력**:
```python
(
    velocities,  # (B, seq_len, fwd_pred_next_n, action_dim) = (B, seq_len, 10, 2)
    None         # gripper 없음
)
```

### 6. Loss 계산 (MobileVLALSTMDecoder.loss)

**입력**:
- `pred_action`: (velocities, None)
  - `velocities`: (B, seq_len, fwd_pred_next_n, 2) - 예측 속도
- `labels`: (velocity_chunck, None)
  - `velocity_chunck`: (B, seq_len, fwd_pred_next_n, 2) - 타겟 속도
- `attention_mask`: (B, seq_len, fwd_pred_next_n) - 마스크

**처리**:
- Huber Loss 계산 (속도 예측과 타겟 비교)
- Attention mask 적용

**출력**:
```python
{
    "loss_velocity": Tensor,  # Huber Loss 값
    "loss_gripper": None,
    "acc_gripper": None
}
```

---

## 전체 데이터 플로우 다이어그램

```
HDF5 파일
  ↓
MobileVLAH5Dataset.__getitem__
  → 이미지 18개, 액션 18개 로드
  ↓
collater
  → 배치 생성, chunk 생성 (unfold)
  → RGB: (B, 8, C, H, W)
  → Action chunk: (B, 7, 10, 2)
  ↓
MobileVLATrainer._process_batch
  → CUDA 이동, velocity 변환
  → (rgb, language, velocity, velocity_chunck, ...)
  ↓
BaseRoboVLM.forward_continuous
  → Vision Encoding (Kosmos-2)
  → Text Processing
  → Multimodal Fusion
  → output_hs: (B, seq_len, hidden_dim)
  ↓
MobileVLALSTMDecoder.forward
  → LSTM Decoder
  → Velocity Prediction
  → velocities: (B, seq_len, 10, 2)
  ↓
MobileVLALSTMDecoder.loss
  → Huber Loss 계산
  → loss_velocity
  ↓
BaseTrainer._get_loss
  → loss_velocity_act → loss_arm_act (호환성)
  → 최종 loss
```

---

## 주요 변경사항 (Git 변경사항 반영)

### 1. main.py 변경사항
- **MPS 지원**: MPS accelerator 감지 시 precision을 "32-true"로 강제
- **모델 경로 통일**: model_url, model_path를 통일된 경로로 업데이트
- **DDP 초기화 조건 개선**: MPS일 때는 process group 초기화 스킵
- **체크포인트 설정 개선**: save_top_k=3, monitor="val_loss" 추가

### 2. 변수명 변경
- `arm_action` → `velocity` (2D 속도)
- `arm_action_chunck` → `velocity_chunck`
- `loss_arm` → `loss_velocity`
- `loss_arm_act` → `loss_velocity_act` (BaseTrainer에서 호환성 유지)

### 3. Config 변경
- `max_epochs`: 20 → 10
- `act_head.type`: "LSTMDecoder" → "MobileVLALSTMDecoder" (실제로는 config에 명시 필요)
- `trainer_type`: "MobileVLATrainer" (config에 명시 필요)

---

## 예상 학습 결과

### Steps per Epoch
- 총 샘플: ~231개 (에피소드 수)
- Effective batch size: 8
- Steps per epoch: ~29 steps
- 총 학습 steps (10 epochs): ~290 steps

### 예상 학습 시간
- 1 epoch: ~1-2분
- 10 epochs: ~10-20분

### 체크포인트 저장
- 최대 4개 체크포인트 저장
- 예상 용량: 27.6GB
- 현재 남은 공간: 394GB (충분)

---

## 학습 시작 준비 완료

✅ Config 파일 업데이트 (max_epochs=10)
✅ 체크포인트 설정 변경 (save_top_k=3)
✅ 디스크 공간 확보 (394GB 남음)
✅ 변수명 변경 완료 (velocity 관련)
✅ Git 변경사항 반영 확인

**학습 시작 가능!**


