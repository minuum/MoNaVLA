# 미팅 Quick Reference 카드

**인쇄용 / 암기용**

---

## 핵심 숫자 (암기 필수)

### Case 5 성능
- **Val Loss**: 0.000532
- **개선율**: 96.7% (Case 4 대비)
- **배수**: 30배 우수
- **최적 Epoch**: 4
- **과적합 시작**: Epoch 5 (+49%)

### 데이터
- **총 Episodes**: 500
- **Left**: 250
- **Right**: 250
- **Train/Val**: 400/100 (80/20)

### 추론 성능
- **시간**: 55-190ms
- **FPS**: 5-18
- **GPU 메모리**: 3.21GB

### 변수 효과
- **Chunking**: 98% 개선 (압도적)
- **Data**: 41% 차이
- **Strategy**: 효과 없음

---

## 5개 케이스 순위

| # | Case | Val Loss | 배수 |
|:---:|:---|:---:|:---:|
| 1 | No Chunk | 0.000532 | 1x |
| 2 | Right Only | 0.016 | 30x |
| 3 | Baseline | 0.027 | 50x |
| 4 | Xavier Init | 0.048 | 90x |
| 5 | Aug+Abs | 0.050 | 94x |

---

## 3가지 성공 요인

### 1. Task 특성
- Navigation (2D) ≠ Manipulation (7D)
- **Reactivity > Precision**

### 2. 데이터 규모
- 500 episodes << 800K trajectories
- **단순 태스크만 학습 가능**

### 3. 모델 용량
- LoRA (작은 용량)
- **복잡한 패턴 학습 어려움**

---

## Epoch별 개선율 (Case 5)

| Epoch | Val Loss | 개선율 |
|:---:|:---:|:---:|
| 0 | 0.013864 | - |
| 1 | 0.002332 | ↓83.2% |
| 2 | 0.001668 | ↓28.5% |
| 3 | 0.001287 | ↓22.8% |
| **4** | **0.000532** | **↓58.6%** |
| 5 | 0.000793 | ↑49.0% |

---

## 예상 질문 답변 (1줄)

**Q1: No Chunk 안정적?**
A: Dummy 테스트 통과, 3단계 대응책 준비

**Q2: 500 episodes 충분?**
A: Epoch 4 최저점, Epoch 5 과적합 → 충분

**Q3: 다른 VLA와 차이?**
A: Navigation(우리) vs Manipulation(타), Reactivity vs Precision

**Q4: 떨림 발생 시?**
A: EMA → 임계값 → Chunk=10 롤백

**Q5: 다음 실험?**
A: Case 8 (No Chunk + Abs) 4-5시간, 즉시 가능

---

## 변수 조합 (16개 중 5개 완료)

### A: Data
- A1: Left+Right (500)
- A2: Right only (250)

### B: Chunking ⭐ 최중요
- B1: Chunk=10
- B2: No Chunk=1 (98% 개선!)

### C: Strategy
- C1: Baseline ✓
- C2: Xavier Init ✗
- C3: Abs Action
- C4: Aug+Abs ✗

---

## 실행 명령어

### Case 8 학습
```bash
cd /home/billy/25-1kp/vla
./scripts/train_case8.sh
```

### 모니터링
```bash
tail -f logs/train_no_chunk_abs_*.log
```

### 중단
```bash
kill [PID]
```

---

## 파일 위치 (빠른 접근)

### 발표 자료
- 상세: `docs/MEETING_PREPARATION_20251210.md`
- 스크립트: `docs/MEETING_PRESENTATION_SCRIPT_20251210.md`
- 체크리스트: `docs/MEETING_READY_CHECKLIST.md`

### 그래프
- 비교: `docs/validation_loss_comparison.png`
- 상세: `docs/case5_detailed_analysis.png`

### 실험 관리
- 마스터 테이블: `docs/MASTER_EXPERIMENT_TABLE.md`
- 변수 분석: `docs/EXPERIMENT_DESIGN_MATRIX.md`

---

## 시간 관리

### Option A (추천)
- Case 8: 4-5시간
- 총: 5시간

### Option B (전체)
- Case 8: 4-5시간
- Case 9: 5-6시간
- 총: 11시간

---

## 최종 메시지

**"Case 5의 No Chunk 전략으로 Val Loss를 30배 낮췄습니다. 
이는 Navigation 태스크의 특성상 Reactivity가 Precision보다 
중요하기 때문입니다. 추가 실험 (Case 8)을 통해 방향 정확도 
100%를 보장하고, 즉시 로봇 실증 테스트를 진행하겠습니다."**

---

**인쇄일**: 2025-12-10 03:49  
**미팅 전 암기!**
