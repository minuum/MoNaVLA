# Ablation Test 결과 - Epoch 1 (2026-01-07 09:47)

## ❌ **테스트 실패: Instruction 무시됨**

### 테스트 설정
- **Checkpoint**: `epoch=01, val_loss=0.354`
- **Instructions**:
  - LEFT: "Navigate around the obstacle on the left side and reach the cup"
  - RIGHT: "Navigate around the obstacle on the right side and reach the cup"

### 결과
```
LEFT  instruction → linear_y = -0.3274 (우회전)
RIGHT instruction → linear_y = -0.3274 (우회전)  
Difference: 0.0000
```

**문제**: 두 instruction에 대해 **완전히 동일한 출력**

## 🔍 분석

### 문제점
1. **완전히 동일한 출력** (차이 0.0000)
2. 모델이 instruction을 **전혀 사용하지 않음**
3. 영어로 변경했지만 Epoch 1에서는 아직 학습 안 됨

### 가능한 원인
1. **학습이 부족함** - Epoch 1만으로는 instruction grounding 학습 안 됨
2. **Frozen VLM** - Kosmos-2가 frozen 상태라 instruction encoding이 제한적
3. **Learning rate 또는 학습 전략** - Action head만 학습되고 instruction 연결 부족

## 📊 한국어 vs 영어 비교

| Instruction | Language | Epoch | LEFT output | RIGHT output | 차이 | 상태 |
|-------------|----------|-------|-------------|--------------|------|------|
| 이전 테스트 | 한국어 | - | -0.88 | - | - | ❌ 무시 |
| 현재 테스트 | 영어 | 1 | -0.33 | -0.33 | 0.00 | ❌ 무시 |

**결론**: 영어로 변경했지만, Epoch 1에서는 아직 instruction을 학습하지 못함

## 🎯 다음 단계

### 옵션 1: 더 많은 Epoch 학습 후 재테스트 (권장)
학습을 계속 진행하고 Epoch 3, 5, 7 등에서 재테스트

**이유**:
- Instruction grounding은 시간이 걸림
- Frozen VLM 전략이므로 action head가 instruction 정보를 학습해야 함
- 다른 VLA 모델들도 여러 epoch 필요

**Action**:
```bash
# 학습 재개 (나중에)
python3 RoboVLMs_upstream/main.py Mobile_VLA/configs/mobile_vla_chunk5_20251217.json

# Epoch 3, 5, 7에서 테스트
python3 scripts/test_english_ablation.py  # checkpoint 경로 업데이트
```

### 옵션 2: VLM LoRA Fine-tuning 고려
Frozen VLM 대신 LoRA로 VLM도 함께 학습

**장점**: Instruction grounding 성능 향상
**단점**: 학습 시간 증가, 메모리 사용 증가

### 옵션 3: 데이터 증강 또는 Curriculum Learning
- Instruction만 다르고 이미지는 비슷한 데이터 쌍 추가
- Simpler instruction부터 시작해서 점진적 학습

## 📋 TODO

### 즉시
- [ ] Epoch 2 완료 대기
- [ ] Epoch 2 체크포인트로 재테스트
- [ ] 실패 시 Epoch 3, 5에서도 테스트

### Epoch 3+ 이후에도 실패 시
- [ ] Learning rate 조정 고려 (현재: 0.0001)
- [ ] VLM LoRA fine-tuning 고려
- [ ] Instruction format 재검토 (더 명확하게?)

### 성공 시
- [ ] Best checkpoint Jetson 전송
- [ ] API server 업데이트
- [ ] 로봇 노드 업데이트
- [ ] 실물 테스트

## 💡 참고

### 다른 VLA 모델의 학습 전략
- **OpenVLA**: Vision encoder도 함께 fine-tuning
- **RT-2**: Vision-language co-training
- **Octo**: Multi-task learning with shared encoder

**우리 전략 (Frozen VLM)**의 한계:
- VLM이 frozen이므로 instruction encoding이 고정됨
- Action head만으로 instruction grounding 학습해야 함
- **더 많은 epoch 필요** 또는 **VLM도 함께 학습** 필요

## 🔄 현재 계획

**학습 계속 진행하여 Epoch 3, 5, 7에서 재테스트**

이유:
1. Epoch 1은 너무 이름
2. Instruction grounding은 점진적으로 학습됨
3. 다른 checkpoint에서 성공할 가능성 있음

---

**Status**: Epoch 1 실패, 학습 계속 필요  
**Next Action**: Epoch 2-3 완료 후 재테스트  
**Updated**: 2026-01-07 09:47
