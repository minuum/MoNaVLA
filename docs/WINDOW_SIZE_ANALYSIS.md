# Window Size 변경 효과 분석

## 현재 설정 확인

**Config**: `Mobile_VLA/configs/mobile_vla_chunk5_20251217.json`

```json
{
  "window_size": 8,
  "fwd_pred_next_n": 5
}
```

**의미**:
- **window_size = 8**: 과거 8 프레임을 입력으로 사용
- **fwd_pred_next_n = 5**: 미래 5 스텝의 action을 예측 (chunking)

---

## Window Size 변경 시 효과

### 1. Window Size 증가 (8 → 16 or 32)

#### 장점
- **더 많은 Temporal Context**: 
  - 로봇의 과거 궤적을 더 길게 볼 수 있음
  - 장애물 회피 패턴을 더 잘 학습 가능
  - "왼쪽으로 돌기 시작했으니 계속 돌아야 한다"는 시간적 일관성 학습

- **Instruction Grounding 개선 가능성**:
  - 더 많은 프레임 → VLM이 instruction과 vision을 더 잘 연결
  - Cross-attention이 더 많은 샘플로 학습

#### 단점
- **메모리 사용량 증가**: 
  - Window 8 → 16으로 2배 증가 시 메모리도 약 2배
  - GPU 메모리 부족 가능성 (현재 12.6GB 사용 중)
  
- **학습 속도 감소**:
  - 프레임 처리량 증가 → 느려짐
  - Epoch당 40분 → 80분으로 증가 가능

- **Overfitting 위험 증가**:
  - 더 복잡한 모델 → 데이터 500개로는 부족할 수 있음

---

### 2. Window Size 감소 (8 → 2 or 4)

#### 장점
- **빠른 학습**:
  - 메모리 절약 → 더 큰 batch size 가능
  - Epoch 속도 향상
  
- **Reactive Control**:
  - 즉각적인 반응 (현재 상황에만 집중)
  - Octo, OpenVLA도 window 1~2 사용

- **Overfitting 방지**:
  - 모델 복잡도 감소 → 데이터 부족 문제 완화

#### 단점
- **Context 부족**:
  - 시간적 일관성 학습 어려움
  - "지금 돌고 있는 중"인지 판단 못 할 수 있음

---

## 현재 문제 진단

### Val Loss 비교
```
한국어 모델 (window=8): Val Loss = 0.067
영어 모델 (window=8):   Val Loss = 0.354 (5배 높음)
```

### 진짜 문제는 Window Size가 아닐 가능성
1. **Language Understanding 차이**
   - Kosmos-2가 한국어보다 영어를 더 잘 이해해야 하는데 loss가 오히려 높음
   - 이상함 → 다른 원인 가능성

2. **가능한 원인**:
   - **Instruction이 여전히 무시됨**: VLM이 frozen이라 영어든 한국어든 사용 안 함
   - **Data Distribution 변화**: Dataset loader 변경 시 다른 부분도 변경되었을 가능성
   - **학습률 문제**: 영어는 한국어보다 학습이 느릴 수 있음

---

## 추천 조치

### 🥇 Option 1: Window Size 감소 (8 → 2)
**근거**: 
- OpenVLA, Octo 등 최신 논문이 window 1~2 사용
- 메모리 절약 → batch size 증가 가능 → 학습 안정화
- Instruction grounding에 집중 (temporal보다)

**변경 방법**:
```json
{
  "window_size": 2,
  "fwd_pred_next_n": 5
}
```

**기대 효과**:
- Val loss 개선 가능 (모델 단순화)
- 학습 속도 4배 향상 (8→2)
- Instruction 사용 여부 더 명확히 확인 가능

---

### 🥈 Option 2: Batch Size & Learning Rate 조정
**문제**: Window는 괜찮은데 학습 하이퍼파라미터가 문제

**변경**:
```json
{
  "batch_size": 2,  // 1 → 2 (gradient 안정화)
  "learning_rate": 0.00005,  // 0.0001 → 절반 (느리지만 안정적)
  "accumulate_grad_batches": 4  // 8 → 4 (실효 batch 8 유지)
}
```

---

### 🥉 Option 3: Ablation Test 먼저 (현재 Epoch 1 Checkpoint)
**목적**: Window size 문제인지, Instruction 문제인지 먼저 확인

```bash
python3 scripts/test_english_inference.py \
    --checkpoint runs/.../epoch_epoch=01-val_loss=val_loss=0.354.ckpt \
    --scenario ablation
```

**검증 사항**:
- LEFT instruction → +양수 출력?
- RIGHT instruction → -음수 출력?
- 만약 둘 다 같은 출력 → **Instruction 무시됨** (window와 무관)

---

## 실험 계획

### Phase 1: 진단 (지금 바로)
1. Epoch 1 checkpoint로 ablation test
2. Instruction 사용 여부 확인

### Phase 2A: Instruction 사용 안 됨 (예상)
→ **Architecture 문제**: Window size로 해결 불가
→ Vision encoder unfreeze 또는 cross-attention 강화 필요

### Phase 2B: Instruction은 사용되지만 성능 낮음
→ **Window size 실험 가치 있음**
→ Window 2로 재학습 시도

---

## 최종 추천

1. **지금**: Epoch 1 checkpoint로 ablation test 실행
2. **결과에 따라**:
   - Instruction 무시 → Architecture 수정
   - Instruction 사용 → Window size 2로 재학습

**이유**: Window size를 바꾸기 전에 근본 문제(instruction 사용 여부)를 먼저 확인해야 함.

Ablation test부터 하시겠습니까?
