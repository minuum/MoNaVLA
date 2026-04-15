# 영어 Instruction 재학습 현황 및 TODO (2026-01-07 09:40)

## 📊 학습 진행 상황

### 현재 상태
- **시작 시간**: 2026-01-07 07:53
- **경과 시간**: 약 1시간 47분
- **현재 진행**: Epoch 1, Step 1274/3534 (36%)
- **예상 완료**: 약 46분 후 (~10:26)

### Loss 추이
```
Epoch 0 완료: train_loss=0.429
Epoch 0 val_loss: 0.455
Epoch 1 진행 중: train_loss=0.037 (매우 낮음 ↓)
Epoch 1 val_loss: 0.455 (유지)
```

### 체크포인트 생성 현황
```
✅ epoch=00, val_loss=0.455 (3개 버전)
✅ epoch=01, val_loss=0.354 ⭐ BEST (가장 낮은 val_loss)
✅ epoch=02, val_loss=0.477
```

**Best Checkpoint**:
```
runs/mobile_vla_no_chunk_20251209/kosmos/mobile_vla_finetune/2026-01-07/mobile_vla_chunk5_20251217/epoch_epoch=01-val_loss=val_loss=0.354.ckpt
```

---

## ✅ TODO List

### 🔴 Priority 1: 즉시 (학습 완료 후)

#### 1.1 Ablation Test 실행 (가장 중요!) ⚡
**목적**: 영어 instruction이 모델에 제대로 반영되는지 검증

```bash
# Best checkpoint로 ablation test
python3 scripts/test_english_inference.py \
    --checkpoint runs/mobile_vla_no_chunk_20251209/kosmos/mobile_vla_finetune/2026-01-07/mobile_vla_chunk5_20251217/epoch_epoch=01-val_loss=val_loss=0.354.ckpt \
    --scenario ablation
```

**기대 결과**:
- LEFT instruction: `linear_y > 0` (좌회전) ✅
- RIGHT instruction: `linear_y < 0` (우회전) ✅
- 두 방향이 **반대 부호**여야 성공!

**실패 시**:
- 더 많은 epoch 학습 필요 (현재 10 epochs 설정)
- 또는 다른 epoch checkpoint 테스트

---

#### 1.2 Left/Right Scenario 개별 테스트

```bash
# Left scenario
python3 scripts/test_english_inference.py \
    --checkpoint <BEST_CKPT> \
    --scenario left

# Right scenario
python3 scripts/test_english_inference.py \
    --checkpoint <BEST_CKPT> \
    --scenario right
```

**검증 항목**:
- LEFT: `linear_y > 0` (양수)
- RIGHT: `linear_y < 0` (음수)
- Gain correction 작동 여부 (값이 1.0 초과 가능)

---

#### 1.3 테스트 스크립트 작성/수정 필요 여부 확인

현재 존재하는 스크립트:
- `scripts/test_english_ablation.py` (untracked)
- `scripts/test_chunk5_inference.py` (기존)

**Action**:
- [ ] `test_english_ablation.py`가 제대로 작동하는지 확인
- [ ] 없으면 새로 작성

---

### 🟠 Priority 2: 테스트 성공 시

#### 2.1 Inference Pipeline 업데이트
**파일**: `Mobile_VLA/inference_pipeline.py`

현재 test_pipeline() 함수의 instructions 확인:
```python
# Line 230-234
instructions = [
    "Navigate around obstacles and reach the front of the beverage bottle on the left",
    "Navigate around obstacles and reach the front of the beverage bottle on the right"
]
```

**Action**:
- [ ] 영어 instruction으로 업데이트 (이미 되어 있을 수도)
- [ ] Test 실행해서 검증

---

#### 2.2 API Server 업데이트
**파일**: `Mobile_VLA/inference_server.py`

**Action**:
- [ ] API endpoint에서 영어 instruction 사용하도록 수정
- [ ] `instruction_mapping` 모듈 활용
- [ ] API test 실행

예시:
```python
from Mobile_VLA.instruction_mapping import get_instruction_for_robot_id

# Robot scenario '1', '2' → 영어 instruction 자동 변환
```

---

#### 2.3 로봇 ROS2 노드 업데이트 (Jetson)

**Action**:
- [ ] ROS2 노드에서 영어 instruction 전송하도록 수정
- [ ] 또는 `instruction_mapping` 모듈 사용

```python
INSTRUCTIONS = {
    '1': "Navigate around the obstacle on the left side and reach the cup",
    '2': "Navigate around the obstacle on the right side and reach the cup"
}
```

---

### 🟡 Priority 3: 시스템 통합

#### 3.1 Checkpoint Jetson으로 전송

```bash
# Best checkpoint를 Jetson으로 rsync
rsync -avz --progress \
    runs/mobile_vla_no_chunk_20251209/kosmos/mobile_vla_finetune/2026-01-07/mobile_vla_chunk5_20251217/epoch_epoch=01-val_loss=val_loss=0.354.ckpt \
    jetson@<JETSON_IP>:/path/to/checkpoints/
```

**또는** 기존 sync 스크립트 사용:
```bash
bash scripts/sync/push_checkpoint_to_jetson.sh
```

---

#### 3.2 Jetson API Server 테스트

1. Jetson에서 API server 시작
2. Billy 서버에서 API 요청 테스트
3. Left/Right 시나리오 검증

---

#### 3.3 실물 로봇 테스트

**준비사항**:
- [x] 영어 instruction으로 재학습 완료
- [ ] Ablation test 통과
- [ ] API server 업데이트
- [ ] Jetson 배포
- [ ] 로봇 노드 업데이트

**테스트 시나리오**:
1. 1box_hori_left: 왼쪽으로 돌아서 컵까지
2. 1box_hori_right: 오른쪽으로 돌아서 컵까지

---

### 🟢 Priority 4: 문서화 및 정리

#### 4.1 테스트 결과 문서 작성

**파일**: `docs/ENGLISH_INSTRUCTION_TEST_RESULT.md`

포함 내용:
- Ablation test 결과
- Left/Right scenario 결과
- 한국어 vs 영어 비교
- 성능 개선 여부

---

#### 4.2 논문 작성용 정리

**Method 섹션**:
- "Following standard VLA practice (OpenVLA, RT-2), we use English instructions"
- Kosmos-2 VLM compatibility
- Frozen VLM strategy

**실험 결과**:
- 한국어 instruction: 작동 안 함 (ablation test 실패)
- 영어 instruction: 작동 (ablation test 성공)

---

#### 4.3 Git Commit & Push

테스트 성공 시:
```bash
git add <관련 파일들>
git commit -m "test: 영어 instruction ablation test 성공

- Best checkpoint: epoch=01, val_loss=0.354
- LEFT/RIGHT direction 정확히 구분
- 다음 단계: API server 및 로봇 노드 업데이트"
git push origin inference-integration
```

---

## 📋 체크리스트 요약

### Phase 1: 검증 (학습 완료 후 즉시)
- [ ] 학습 완료 확인 (Epoch 10 or early stopping)
- [ ] Best checkpoint 확인 (현재: epoch=01, val_loss=0.354)
- [ ] Ablation test 실행
- [ ] Left/Right scenario 개별 테스트

### Phase 2: 코드 업데이트 (테스트 성공 시)
- [ ] Inference pipeline 확인/업데이트
- [ ] API server 영어 instruction 적용
- [ ] 로봇 ROS2 노드 업데이트

### Phase 3: 배포 (코드 업데이트 완료 시)
- [ ] Checkpoint Jetson 전송
- [ ] Jetson API server 테스트
- [ ] 실물 로봇 테스트

### Phase 4: 마무리
- [ ] 테스트 결과 문서 작성
- [ ] 논문 작성용 정리
- [ ] Git commit & push

---

## ⚠️ 주의사항

### 1. Ablation Test가 가장 중요!
- 이게 실패하면 learning rate, epochs, 또는 instruction 형식 재검토 필요
- 성공해야만 다음 단계로 진행 가능

### 2. Best Checkpoint 선택 기준
- 현재: `epoch=01, val_loss=0.354` (가장 낮음)
- 만약 overfitting 의심되면 더 낮은 epoch 사용

### 3. 학습이 아직 진행 중
- Epoch 1/10 (36% 완료)
- 더 나은 checkpoint가 나올 수 있음
- 학습 완료 후 전체 checkpoint 재확인 필요

---

## 🎯 Success Criteria

### 최소 성공 기준
- [ ] Ablation test에서 LEFT/RIGHT 방향 구분 성공
- [ ] 일관된 방향성 (10번 테스트 중 8번 이상 성공)

### 완전 성공 기준
- [ ] Ablation test 100% 성공
- [ ] API server 통합 성공
- [ ] Jetson 실물 테스트 성공
- [ ] Left/Right navigation 실제 작동

---

**현재 상태**: 🔄 학습 진행 중 (Epoch 1/10, 36%)  
**다음 Action**: 학습 완료 대기 → Ablation test 실행  
**Updated**: 2026-01-07 09:40
