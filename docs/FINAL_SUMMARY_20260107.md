# 최종 요약 및 다음 단계 (2026-01-07 10:00)

## 📊 오늘 발견한 핵심 사항

### 1. ✅ **Instruction이 코드상으로는 정상 전달됨**
- Dataset → VLM → Action head 모든 경로에서 instruction 전달 확인
- Window size (8) 및 chunk size (5) 설정 정상 작동

### 2. ❌ **Frozen VLM의 구조적 한계 (Ablation Test로 확인)**
```
LEFT instruction  → VLM (frozen) → 같은 embedding
RIGHT instruction → VLM (frozen) → 같은 embedding
                                      ↓
                              linear_y = -0.3274 (both!)
```

**근본 원인**: VLM이 frozen이라 instruction별로 다른 embedding 생성 불가

### 3. ❌ **LoRA Fine-tuning 시도 → OOM 실패**
```
Gradient checkpointing: ✅ 활성화
LoRA rank: 16 (32→16로 감소)
결과: 여전히 OOM (19.52GB / 23.67GB 사용)
```

**결론**: A5000 24GB로는 LoRA fine-tuning 불가능

---

## 🎯 **남은 옵션**

### 옵션 1: Frozen VLM으로 더 많은 Epoch 학습 ⭐ 권장
**현재 상태**: Epoch 1에서 실패
**시도**: Epoch 3, 5, 7에서 재테스트

**근거**:
- Loss는 낮아지고 있음 (0.0885)
- 혹시나 더 학습하면 instruction grounding이 될 수 있음
- 메모리 문제 없음

**Action**:
```bash
# Frozen VLM 학습 재개
cd /home/billy/25-1kp/vla
nohup python3 RoboVLMs_upstream/main.py \
    Mobile_VLA/configs/mobile_vla_chunk5_20251217.json \
    > logs/train_frozen_continue_$(date +%Y%m%d).log 2>&1 &
```

---

### 옵션 2: 더 작은 VLM 사용
**대안 VLM**:
- CLIP-based smaller model
- Smaller vision encoder

**단점**: 처음부터 다시 시작

---

### 옵션 3: LoRA를 다른 GPU에서 (권장하지 않음)
- 더 큰 GPU 필요 (V100 32GB, A100 40GB)
- 현재 환경에서 불가능

---

## 📋 **생성된 문서들**

### 분석 문서
1. `docs/INSTRUCTION_FLOW_ANALYSIS.md` - Instruction 전달 경로 분석
2. `docs/TRAINING_VS_INFERENCE_ANALYSIS.md` - 학습 vs 추론 비교
3. `docs/WINDOW_SIZE_VERIFICATION.md` - Window size 환각 없는 검증
4. `docs/ABLATION_TEST_EPOCH1_RESULT.md` - Epoch 1 테스트 결과

### 전략 문서
5. `docs/LORA_FINETUNING_STRATEGY.md` - LoRA 전략 (실패)
6. `docs/INSTRUCTION_FINAL_STATUS.md` - 전체 상황 정리

### Config & Scripts
7. `Mobile_VLA/configs/mobile_vla_lora_chunk5.json` - LoRA config
8. `scripts/train_active/train_lora_chunk5.sh` - LoRA 학습 스크립트
9. `scripts/test_english_ablation.py` - Ablation test 스크립트 (수정됨)
10. `scripts/monitor_training.sh` - 모니터링 스크립트

---

## 🎯 **권장 다음 단계**

### 즉시 실행
**Frozen VLM 학습 Epoch 10까지 완료 후 주기적 테스트**

1. 학습 재개:
```bash
bash scripts/train_active/train_english_chunk5.sh
# 또는 이미 실행 중이라면 계속 진행
```

2. Epoch 3 완료 시 테스트:
```bash
# Checkpoint 경로 업데이트 후
python3 scripts/test_english_ablation.py
```

3. **만약 Epoch 5-7에서도 실패하면**:
   - Frozen VLM 전략의 한계 인정
   - 논문에 "instruction grounding limitation" 명시
   - Vision-only baseline과 비교

---

## 💡 **핵심 Insight**

### Frozen VLM의 문제
```python
# 모든 timestep에서 동일한 instruction embedding
for i in range(window_size):  # 8번
    instruction_embedding = VLM.encode("Navigate LEFT")  # 항상 같음!
    hidden_state[i] = VLM(image[i], instruction_embedding)
```

**이게 문제인 이유**:
- Image만 바뀌고 instruction은 고정
- VLM이 frozen → instruction마다 다른 embedding 못 만듦
- **결과**: LEFT/RIGHT 구분 못 함

### LoRA가 해결할 수 있었던 이유
```python
# LoRA면 instruction별로 다른 embedding 생성 가능
instruction_embedding_LEFT = VLM("Navigate LEFT")  # ΔW_LEFT 적용
instruction_embedding_RIGHT = VLM("Navigate RIGHT")  # ΔW_RIGHT 적용
# → 다른 hidden state → 다른 action!
```

**하지만**: 메모리 부족으로 불가능

---

## 📊 **비교표: 시도한 방법들**

| 방법 | 상태 | 결과 | 이유 |
|------|------|------|------|
| 한국어 Instruction | ❌ 실패 | instruction 무시 | Kosmos-2 영어 중심 |
| 영어 Instruction (Frozen, Epoch 1) | ❌ 실패 | instruction 무시 (`linear_y=same`) | Frozen VLM 한계 |
| LoRA Fine-tuning | ❌ OOM | 메모리 부족 (19.5GB/24GB) | A5000 24GB 부족 |
| 영어 Instruction (Frozen, Epoch 3+) | ⏳ 대기 | 테스트 필요 | 현재 권장 옵션 |

---

## ✅ **TODO**

### 즉시
- [ ] Frozen VLM 학습 상태 확인
- [ ] Epoch 2-3 완료 후 ablation test
- [ ] 성공 여부에 따라 다음 결정

### Epoch 3+ 성공 시
- [ ] Best checkpoint Jetson 전송
- [ ] API server 업데이트
- [ ] 실물 로봇 테스트

### Epoch 7까지도 실패 시
- [ ] Frozen VLM 한계 인정
- [ ] 논문에 limitation 명시
- [ ] Vision-only baseline 고려

---

**Status**: LoRA 불가능 확인, Frozen VLM으로 장기 학습 필요  
**Next Action**: Epoch 3 완료 후 ablation test 재실행  
**Updated**: 2026-01-07 10:00
