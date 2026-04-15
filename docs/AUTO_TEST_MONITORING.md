# VLA 추론 테스트 자동화 실행 가이드

**실행 시각**: 2025-12-09 18:46  
**프로세스 ID**: 1589362

---

## ✅ 백그라운드 실행 완료!

스크립트가 백그라운드에서 실행 중입니다:
- 학습 완료 감지 대기 중 (30초마다 체크)
- 완료 시 자동으로 추론 테스트 시작
- 모든 로그는 `test_results.log`에 저장

---

## 📊 실시간 모니터링 명령어

### 1. 로그 실시간 확인
```bash
tail -f test_results.log
```
- 진행 상황을 실시간으로 볼 수 있음
- Ctrl+C로 종료 (스크립트는 계속 실행됨)

### 2. 최근 로그 확인
```bash
tail -50 test_results.log
```
- 최근 50줄만 확인

### 3. 프로세스 상태 확인
```bash
ps aux | grep wait_and_test | grep -v grep
```
- 스크립트가 여전히 실행 중인지 확인

### 4. 학습 프로세스 상태
```bash
ps aux | grep 1546813 | grep -v grep
```
- 학습이 아직 진행 중인지 확인

### 5. 현재 학습 진행률
```bash
tail -20 logs/train_no_chunk_20251209_160112.log | grep "Epoch"
```

---

## 📈 현재 상황 (18:46)

### 학습 진행
- **Epoch**: 2/10 (100% - 3997/4000)
- **거의 완료**: Epoch 2가 곧 끝남!
- **예상**: 다음 몇 분 내 Epoch 3 시작

### 백그라운드 작업
✅ `wait_and_test.sh` 실행 중 (PID: 1589362)
✅ 학습 완료 감지 대기 중

---

## 🎯 예상 타임라인

1. **현재 (18:46)**: Epoch 2 거의 완료
2. **18:47-19:25**: Epoch 3~10 진행 (~5분/epoch × 8)
3. **19:25**: 학습 완료 감지
4. **19:25-19:28**: 추론 테스트 자동 실행 (~3분)
5. **19:28**: 테스트 완료, 결과 확인 가능

---

## 📋 완료 후 확인 사항

### 테스트 완료 확인
```bash
grep "✅ 완료!" test_results.log
```

### 테스트 결과 확인
```bash
grep -A 20 "Step 1: 모델 로딩 테스트" test_results.log
grep -A 10 "Step 2: 방향 추출" test_results.log  
grep -A 30 "Step 3: Dummy 이미지" test_results.log
```

### 전체 결과 보기
```bash
cat test_results.log
```

---

## 🔧 문제 발생 시

### 스크립트 중단하기
```bash
# PID 확인
ps aux | grep wait_and_test | grep -v grep
# 종료
kill 1589362
```

### 수동으로 테스트 실행
```bash
# 학습 완료 후
export POETRY_PYTHON=/home/billy/.cache/pypoetry/virtualenvs/robovlms-ASlHafON-py3.10/bin/python
export VLA_CHECKPOINT_PATH="$(pwd)/runs/mobile_vla_no_chunk_20251209/kosmos/mobile_vla_finetune/2025-12-09/mobile_vla_no_chunk_20251209/mobile_vla_no_chunk_20251209/version_1/last.ckpt"

$POETRY_PYTHON test_inference_stepbystep.py
```

---

## 💡 유용한 명령어

### GPU 메모리 확인
```bash
nvidia-smi
```

### 체크포인트 확인
```bash
find runs/mobile_vla_no_chunk_20251209 -name "*.ckpt" -type f
```

### CSV 메트릭 최신 확인
```bash
tail -10 runs/mobile_vla_no_chunk_20251209/kosmos/mobile_vla_finetune/2025-12-09/mobile_vla_no_chunk_20251209/mobile_vla_no_chunk_20251209/version_1/metrics.csv
```

---

## 🎉 성공 시나리오

완료되면 다음을 확인할 수 있습니다:

```bash
tail -100 test_results.log
```

**예상 출력**:
```
✅ 학습 완료!
📦 체크포인트 확인 중...
✅ 체크포인트 발견: runs/.../last.ckpt
🚀 추론 테스트 시작...

============================================================
📦 Step 1: 모델 로딩 테스트
============================================================
✅ 모델 로딩 성공!

============================================================
🧭 Step 2: 방향 추출 로직 테스트
============================================================
✅ 모든 테스트 통과

============================================================
🖼️  Step 3: Dummy 이미지 추론 테스트
============================================================
✅ 추론 성공!

🎉 모든 테스트 통과!
✅ 완료!
```

---

**작성일**: 2025-12-09 18:46  
**다음 확인**: 약 40분 후 (19:25 예상)
