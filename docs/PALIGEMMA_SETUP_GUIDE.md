# PaliGemma-3B Mobile VLA Setup Guide

## 📋 **개요**

PaliGemma-3B 기반 Mobile VLA를 위한 새로운 학습 구조입니다.

### 왜 PaliGemma-3B인가?

| 특징 | Kosmos-2 (1.6B) | PaliGemma-3B (2.4B) |
|------|-----------------|---------------------|
| **Parameters** | 1.6B | 2.4B (1.5배) |
| **LoRA 메모리** | ~18 GB ❌ | ~12 GB ✅ |
| **A5000 가능** | ❌ OOM | ✅ 가능 |
| **Vision Encoder** | CLIP ViT-L/14 | SigLIP-So400m (효율적) |
| **Language** | Custom Decoder | Gemma-2B (최적화) |
| **Grounding** | ✅ (복잡) | ❌ (단순) |
| **VLA 검증** | ⚠️ RoboKosMos | ✅ OpenVLA family |

**핵심**: 파라미터는 1.5배지만 메모리는 오히려 적게 사용!

---

## 📂 **파일 구조**

```
/home/billy/25-1kp/vla/
├── Mobile_VLA/
│   └── configs/
│       └── mobile_vla_paligemma_lora.json  ← 새 config
│
├── RoboVLMs_upstream/
│   └── robovlms/
│       ├── model/
│       │   └── backbone/
│       │       └── robopaligemma.py  ← 이미 구현됨 ✅
│       ├── data/
│       │   ├── mobile_vla_action_dataset.py  ← 기존 사용
│       │   └── mobile_vla_h5_dataset.py  ← 기존 사용
│       └── train/
│           └── mobile_vla_trainer.py  ← 기존 사용
│
├── scripts/
│   ├── train_active/
│   │   └── train_paligemma_lora.sh  ← 학습 스크립트
│   └── test_paligemma_ablation.py  ← 테스트 스크립트
│
└── runs/
    └── mobile_vla_paligemma/  ← 학습 결과 저장
```

---

## 🚀 **사용 방법**

### 1️⃣ **모델 다운로드 (선택)**

PaliGemma-3B 사전 학습 모델을 미리 다운로드할 수 있습니다:

```bash
cd /home/billy/25-1kp/vla

# HuggingFace CLI 사용 (권장)
mkdir -p .vlms
cd .vlms

huggingface-cli download google/paligemma-3b-pt-224 \
    --local-dir paligemma-3b-pt-224 \
    --local-dir-use-symlinks False

# 또는 학습 시작 시 자동 다운로드됨
```

---

### 2️⃣ **학습 시작**

```bash
cd /home/billy/25-1kp/vla

# 학습 스크립트 실행
bash scripts/train_active/train_paligemma_lora.sh

# 또는 직접 실행
nohup python3 RoboVLMs_upstream/main.py \
    Mobile_VLA/configs/mobile_vla_paligemma_lora.json \
    > logs/train_paligemma_$(date +%Y%m%d).log 2>&1 &
```

---

### 3️⃣ **학습 모니터링**

```bash
# 실시간 로그
tail -f logs/train_paligemma_*.log

# GPU 사용률
watch -n 5 nvidia-smi

# 모니터링 스크립트
bash scripts/monitor_training.sh
```

---

### 4️⃣ **Ablation Test (Epoch 1 완료 후)**

```bash
# Checkpoint 경로 확인
ls -lht runs/mobile_vla_paligemma/*/*/*/epoch_*.ckpt

# test_paligemma_ablation.py에서 CHECKPOINT_PATH 업데이트

# 테스트 실행
python3 scripts/test_paligemma_ablation.py
```

**성공 기준**:
- LEFT instruction → `linear_y > 0` (좌회전)
- RIGHT instruction → `linear_y < 0` (우회전)
- 두 값의 차이가 명확함 (> 0.3)

---

## ⚙️ **Config 상세 설명**

### 핵심 설정

```json
{
  "model": "paligemma",
  "model_url": "https://huggingface.co/google/paligemma-3b-pt-224",
  
  "train_setup": {
    "freeze_backbone": false,      // VLM LoRA fine-tuning
    "lora_enable": true,            // LoRA 활성화
    "lora_r": 16,                   // Rank (메모리 최적화)
    "lora_alpha": 32,
    "gradient_checkpointing": true  // 메모리 절약
  },
  
  "optimizer": "adamw",
  "learning_rate": 0.0001,
  
  "window_size": 8,
  "fwd_pred_next_n": 5,
  
  "batch_size": 1,
  "accumulate_grad_batches": 8    // Effective batch = 8
}
```

---

## 📊 **예상 학습 시간 & 메모리**

### 메모리 사용

```
Model weights (FP16): ~4.8 GB
LoRA adapters: ~0.3 GB
Optimizer states: ~0.6 GB
Activations: ~2.4 GB (with gradient checkpointing)
Multi-modal overhead: ~0.8 GB
Misc buffers: ~1.5 GB
-----------------------------------
Total: ~12 GB

A5000 24GB: ✅ 여유 있음 (~50% 사용)
```

### 학습 시간

```
Dataset: ~148 episodes, ~2664 frames
Effective batch size: 8
Steps per epoch: ~3534

예상 속도: ~0.8 it/s
Epoch 당 시간: ~75 분
10 Epochs: ~12.5 시간
```

---

## ✅ **검증 계획**

### Epoch 1 완료 후

```bash
# Ablation test
python3 scripts/test_paligemma_ablation.py
```

**기대 결과**:
- ✅ LEFT/RIGHT 구분 성공 (Kosmos-2는 실패)
- ✅ Instruction grounding 작동

### 비교 분석

| Model | Epoch 1 Test | LEFT output | RIGHT output | 차이 | 성공 |
|-------|-------------|-------------|--------------|------|------|
| Kosmos-2 Frozen | ❌ | -0.33 | -0.33 | 0.00 | ❌ |
| Kosmos-2 LoRA | - | - | - | - | ❌ OOM |
| **PaliGemma-3B LoRA** | **?** | **?** | **?** | **?** | **?** |

---

## 🎯 **다음 단계**

### 성공 시

1. **Best Checkpoint 선택**
   ```bash
   ls -lht runs/mobile_vla_paligemma/*/*/*/epoch_*.ckpt | head -5
   ```

2. **Jetson 전송**
   ```bash
   bash scripts/sync/push_checkpoint_to_jetson.sh [checkpoint_path]
   ```

3. **API Server 업데이트**
   - `Mobile_VLA/inference_pipeline.py` 를 PaliGemma용으로 수정
   - `Mobile_VLA/inference_server.py` 업데이트

4. **실물 테스트**
   - LEFT/RIGHT navigation 검증
   - 성능 측정

### 실패 시 (Epoch 3-5에서도 실패)

1. **Hyperparameter 조정**
   - Learning rate 변경
   - LoRA rank 조정

2. **다른 접근**
   - CLIP + GPT-2 Small 시도
   - 또는 Frozen VLM으로 장기 학습

---

## 🔧 **Troubleshooting**

### OOM 발생 시

```bash
# Isaac Sim 종료
pkill -f isaac-sim

# Config에서 batch size 확인 (이미 1임)
# gradient_checkpointing 활성화 확인 (이미 true임)
```

### 모델 로드 실패

```bash
# HuggingFace token 설정
huggingface-cli login

# 또는 환경변수
export HF_TOKEN=your_token_here
```

### 데이터셋 오류

```bash
# Dataset 경로 확인
ls -lh /home/billy/25-1kp/vla/ROS_action/mobile_vla_dataset/

# Config에서 model_name="paligemma" 확인
```

---

## 📚 **참고 자료**

### PaliGemma 공식 문서
- https://github.com/google-research/big_vision
- https://huggingface.co/google/paligemma-3b-pt-224

### Related Papers
- PaliGemma: https://arxiv.org/abs/2407.07726
- OpenVLA: https://arxiv.org/abs/2406.09246
- Gemma: https://arxiv.org/abs/2403.08295

---

**Created**: 2026-01-07
**Author**: Mobile VLA Team
**Status**: Ready for training
