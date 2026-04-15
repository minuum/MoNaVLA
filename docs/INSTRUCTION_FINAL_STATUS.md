# Instruction Mismatch - 최종 요약 (2026-01-07 09:50)

## ✅ 완료된 작업

### 1. 문제 진단 및 해결
- [x] 한국어 instruction이 무시됨 확인 (테스트 완료)
- [x] 영어 instruction으로 변경 (VLA 표준 준수)
- [x] 코드 중복 제거 및 정리
- [x] Git commit & push 완료

### 2. 영어 Instruction 재학습
- [x] Dataset loader 수정 (한국어 → 영어)
- [x] Instruction mapping 업데이트
- [x] 재학습 시작 (07:53)
- [x] Epoch 1 완료 (Best: val_loss=0.354)

### 3. 초기 테스트
- [x] 학습 중단 및 GPU 해제
- [x] Epoch 1 checkpoint로 ablation test 실행
- [x] **결과: 실패** - instruction 여전히 무시됨

##❌ Ablation Test 결과 (Epoch 1)

```
LEFT  instruction → linear_y = -0.3274
RIGHT instruction → linear_y = -0.3274
Difference: 0.0000 (완전히 동일)
```

**문제**: 모델이 instruction을 전혀 사용하지 않음

### 분석
- Epoch 1만으로는 instruction grounding 학습 부족
- Frozen VLM 전략이므로 action head만으로 instruction 학습 필요
- 더 많은 epoch 학습 후 재테스트 필요

---

## 🎯 다음 단계

### 🔴 Priority 1: 학습 계속 + 주기적 테스트

#### 학습 재개
학습을 Epoch 10까지 계속 진행하고, 주기적으로 테스트:

```bash
# 학습 재개
cd /home/billy/25-1kp/vla
nohup python3 RoboVLMs_upstream/main.py \
    Mobile_VLA/configs/mobile_vla_chunk5_20251217.json \
    > logs/train_english_continue_$(date +%Y%m%d_%H%M%S).log 2>&1 &

# 진행 모니터링
bash scripts/monitor_training.sh
```

#### 테스트 스케줄
- **Epoch 3**: 첫 재테스트
- **Epoch 5**: 두 번째 테스트
- **Epoch 7**: 세 번째 테스트
- **성공 시**: 학습 중단 및 배포

#### 테스트 명령 (checkpoint 경로 업데이트 필요)
```bash
# 스크립트의 checkpoint 경로를 해당 epoch으로 변경
python3 scripts/test_english_ablation.py
```

---

### 🟠 Priority 2: 대안 전략 (Epoch 5+ 이후에도 실패 시)

#### 옵션 A: VLM LoRA Fine-tuning
Frozen VLM 대신 LoRA로 VLM도 함께 학습

**장점**: Instruction grounding 성능 향상  
**단점**: 학습 시간/메모리 증가

**Config 수정**:
```json
{
  "train_setup": {
    "freeze_backbone": false,  // VLM fine-tuning
    "lora_enable": true,        // LoRA 활성화
    "lora_r": 32,
    "lora_alpha": 16
  }
}
```

#### 옵션 B: Learning Rate 조정
현재 LR: 0.0001 → 더 작게 또는 크게 조정

```json
{
  "learning_rate": 0.0005  // 또는 0.00005
}
```

#### 옵션 C: Instruction Format 재검토
더 명확하고 차별적인 instruction:

```python
LEFT:  "Turn left around the obstacle and approach the cup"
RIGHT: "Turn right around the obstacle and approach the cup"
```

---

### 🟡 Priority 3: 성공 시 배포

#### 1. Best Checkpoint Jetson 전송
```bash
# Checkpoint 확인
BEST_CKPT=$(ls -lh runs/.../epoch_*.ckpt | grep -v "last" | sort -t= -k3 -n | head -1)

# Jetson 전송 (제가 준비하겠습니다)
rsync -avz --progress \
    "$BEST_CKPT" \
    jetson@<IP>:/path/to/checkpoints/
```

#### 2. API Server 업데이트
```python
from Mobile_VLA.instruction_mapping import get_instruction_for_robot_id

# Robot ID → 영어 instruction 자동 변환
instruction = get_instruction_for_robot_id(scenario_id)
```

#### 3. 로봇 ROS2 노드 업데이트
```python
INSTRUCTIONS = {
    '1': "Navigate around the obstacle on the left side and reach the cup",
    '2': "Navigate around the obstacle on the right side and reach the cup"
}
```

#### 4. 실물 테스트
- Left/Right navigation 검증
- 성능 측정

---

## 📊 현재 상황 정리

### 학습 현황
| Item | Status | Detail |
|------|--------|--------|
| 재학습 시작 | ✅ | 2026-01-07 07:53 |
| Epoch 0 완료 | ✅ | val_loss=0.455 |
| Epoch 1 완료 | ✅ | val_loss=0.354 (BEST) |
| Epoch 1 테스트 | ❌ | Instruction 무시됨 |
| 학습 진행 | ⏸️ | 테스트 위해 중단 |

### 체크포인트
```
✨ Best: epoch=01, val_loss=0.354
   epoch=00, val_loss=0.455
   epoch=02, val_loss=0.477 (이미 있음, 과거 학습)
```

### Git Status
- [x] 코드 변경사항 commit & push 완료
- [x] 문서화 완료
- [ ] Ablation test 결과 commit (대기)

---

## 💡 핵심 인사이트

### Frozen VLM 전략의 한계
1. **VLM이 frozen** → instruction encoding 고정
2. **Action head만 학습** → instruction → action 매핑 학습 어려움
3. **더 많은 epoch 필요** 또는 **VLM도 함께 학습** 필요

### 다른 VLA 모델들
- **OpenVLA**: Vision encoder도 fine-tuning
- **RT-2**: Vision-language co-training
- **Octo**: Multi-task learning

**우리의 선택**:
1. 먼저 더 많은 epoch 학습 (Epoch 3, 5, 7 테스트)
2. 실패 시 VLM LoRA fine-tuning 고려

---

## 📋 체크리스트

### 즉시 (현재)
- [x] Ablation test 실행
- [x] 결과 분석 및 문서화
- [ ] 학습 재개 결정

### Epoch 3 완료 후
- [ ] Ablation test 재실행
- [ ] 성공 여부에 따라 다음 Action 결정

### 성공 시
- [ ] Best checkpoint Jetson 전송
- [ ] API/로봇 노드 업데이트
- [ ] 실물 테스트
- [ ] 결과 문서화
- [ ] 논문 작성

### 실패 시 (Epoch 5+ 이후에도)
- [ ] VLM LoRA fine-tuning 시작
- [ ] 또는 Learning rate/Instruction format 조정

---

**현재 상태**: Epoch 1 테스트 실패, 학습 계속 필요  
**Next Action**: 학습 재개 후 Epoch 3에서 재테스트  
**Updated**: 2026-01-07 09:50
