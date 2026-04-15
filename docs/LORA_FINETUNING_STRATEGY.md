# LoRA Fine-tuning 전략 (2026-01-07)

## 🎯 왜 LoRA Fine-tuning인가?

### Frozen VLM의 한계 (Epoch 1 테스트 결과)
```
LEFT instruction  → linear_y = -0.3274
RIGHT instruction → linear_y = -0.3274
Diff: 0.0000 (완전히 동일)
```

**문제**: VLM이 frozen이라서 instruction에 따라 **다른 embedding을 생성하지 못함**

---

## 📊 Frozen VLM vs LoRA Fine-tuning 비교

| 항목 | Frozen VLM | LoRA Fine-tuning |  결과 |
|------|-----------|------------------|-------|
| **VLM 학습** | ❌ Frozen (고정) | ✅ LoRA 학습 | LoRA 승 |
| **Instruction Embedding** | 고정 (pre-trained) | Instruction별로 학습 | LoRA 승 |
| **메모리 사용** | ~23GB | ~25GB (예상) | Frozen 승 |
| **학습 속도** | 빠름 (~70분/epoch) | 느림 (~90분/epoch 예상) | Frozen 승 |
| **Instruction Grounding** | ❌ 실패 (테스트 확인) | ✅ 성공 기대 | **LoRA 승** |
| **Trainable Parameters** | 12.74M (action head만) | 12.74M + LoRA params | LoRA 승 |

---

## 🔧 Config 변경 사항

### Before (Frozen VLM)
```json
{
  "exp_name": "mobile_vla_chunk5_20251217",
  "train_setup": {
    "freeze_backbone": true,      // VLM frozen
    "lora_enable": false,          // LoRA 비활성화
    "lora_r": 32,
    "lora_alpha": 16
  }
}
```

### After (LoRA Fine-tuning)
```json
{
  "exp_name": "mobile_vla_lora_chunk5",
  "train_setup": {
    "freeze_backbone": false,     // ✅ VLM fine-tuning
    "lora_enable": true,           // ✅ LoRA 활성화
    "lora_r": 32,                  // LoRA rank
    "lora_alpha": 16,              // LoRA scaling factor
    "lora_dropout": 0.1,
    "lora_bias": "none"
  }
}
```

---

## 🎯 LoRA의 작동 원리

### 일반 Fine-tuning
```
VLM (1.6B params) 전체를 업데이트
→ 메모리/시간 많이 필요
→ Overfitting 위험
```

### LoRA (Low-Rank Adaptation)
```
VLM의 일부 weight matrix에만 작은 adapter 추가
W_new = W_frozen + ΔW
ΔW = A × B  (A: rank×d, B: d×rank)

rank=32 → 훨씬 적은 parameters만 학습
→ 효율적 + Overfitting 방지
```

### 구체적 예시
```python
# Frozen VLM
W_query.requires_grad = False  # 고정

# LoRA
W_query.requires_grad = False  # 여전히 고정
lora_A.requires_grad = True    # 학습 (rank × d_model)
lora_B.requires_grad = True    # 학습 (d_model × rank)

# Forward
output = W_query @ input + (lora_A @ lora_B) @ input
         ^^^^^^^^^^^^       ^^^^^^^^^^^^^^^^^^^
         Frozen              Learnable
```

---

## 📈 기대 효과

### 1. Instruction-specific Embeddings
```python
# Before (Frozen)
VLM("Navigate LEFT")  → embedding_A
VLM("Navigate RIGHT") → embedding_A  # 같음!

# After (LoRA)
VLM("Navigate LEFT")  → embedding_A + ΔA
VLM("Navigate RIGHT") → embedding_B + ΔB  # 다름!
```

### 2. Better Action Grounding
```python
# LEFT instruction
VLM embedding_A → Action head → linear_y > 0 (좌회전)

# RIGHT instruction
VLM embedding_B → Action head → linear_y < 0 (우회전)
```

### 3. Trainable Parameters
```
Frozen VLM:
- Action head only: ~12.74M params

LoRA Fine-tuning:
- Action head: ~12.74M params
- LoRA adapters: ~2-3M params (rank=32 기준)
- Total: ~15M params (전체 1.6B 중 1% 미만)
```

---

## 🚀 학습 계획

### 학습 설정
- **Config**: `Mobile_VLA/configs/mobile_vla_lora_chunk5.json`
- **Epochs**: 10
- **Batch size**: 1 (accumulate 8)
- **Learning rate**: 0.0001
- **예상 시간**: ~15시간 (10 epochs × 90분)

### 학습 시작
```bash
bash scripts/train_active/train_lora_chunk5.sh
```

### 모니터링
```bash
# 실시간 로그
tail -f logs/train_lora_chunk5_*.log

# 또는
bash scripts/monitor_training.sh
```

---

## ✅ 검증 계획

### Epoch 1 완료 후
```bash
# Ablation test (LoRA checkpoint)
python3 scripts/test_english_ablation.py
# checkpoint 경로를 LoRA checkpoint로 변경
```

**기대 결과**:
- LEFT instruction → `linear_y > 0` ✅
- RIGHT instruction → `linear_y < 0` ✅
- **차이가 명확히 나타남!**

### Frozen vs LoRA 비교
| Metric | Frozen (Epoch 1) | LoRA (Epoch 1) | 목표 |
|--------|------------------|----------------|------|
| LEFT output | -0.3274 | ? | > 0 |
| RIGHT output | -0.3274 | ? | < 0 |
| Difference | 0.0000 ❌ | ? | > 0.5 ✅ |

---

## ⚠️ 주의사항

### 1. 메모리 사용량 증가
- Frozen: ~23GB
- LoRA: ~25GB (예상)
- 현재 A5000 (24GB): **경계선**

**대책**:
- Batch size=1 유지
- gradient_checkpointing 활성화 (필요 시)

### 2. 학습 시간 증가
- Frozen: ~70분/epoch
- LoRA: ~90분/epoch (예상, 30% 증가)

### 3. Overfitting 가능성
- LoRA는 작은 rank로 제한 → Overfitting 방지
- Validation loss 주의 깊게 모니터링

---

## 📁 관련 파일

### Config
- `Mobile_VLA/configs/mobile_vla_lora_chunk5.json` - LoRA config

### Scripts
- `scripts/train_active/train_lora_chunk5.sh` - 학습 스크립트
- `scripts/test_english_ablation.py` - Ablation test

### Checkpoints
- Frozen: `runs/.../mobile_vla_chunk5_20251217/`
- LoRA: `runs/mobile_vla_lora/mobile_vla_lora_chunk5/`

---

## 🎯 Success Criteria

### 최소 성공 기준
- [ ] Ablation test에서 LEFT/RIGHT 방향 구분 (Epoch 1)
- [ ] 차이 > 0.3 이상

### 완전 성공 기준
- [ ] Ablation test 100% 성공
- [ ] 일관된 방향성 (10번 중 9번 이상)
- [ ] Validation loss 수렴

---

**Status**: LoRA config 준비 완료, 학습 시작 대기  
**Next Action**: `bash scripts/train_active/train_lora_chunk5.sh`  
**Updated**: 2026-01-07 09:52
