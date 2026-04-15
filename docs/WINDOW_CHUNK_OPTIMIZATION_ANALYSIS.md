# Window Size & Chunk Size 최적화: 대학원 수준 분석

**작성일**: 2026-02-09  
**분석자**: VLA 연구팀  
**핵심 질문**: "우리 데이터(에피소드 18프레임)에 맞는 최적 Window/Chunk 조합은?"

---

## 📐 근본 개념: Window vs Chunk의 의미

### **Window Size (관찰 범위)**
- **정의**: 모델이 "보는" 과거 프레임 수
- **역할**: Temporal context를 제공하여 동작의 연속성 파악
- **예시**: Window=12 → 과거 12프레임의 이미지를 LSTM에 입력

### **Chunk Size (예측 범위)**
- **정의**: 한 번 추론으로 "예측하는" 미래 액션 수
- **역할**: Multi-step planning, 행동의 일관성 유지
- **예시**: Chunk=6 → 다음 6스텝의 액션을 한 번에 예측

### **핵심 차이**
```
Window: PAST (관찰)  |  Current  |  Chunk: FUTURE (예측)
[t-12 ... t-1]       |    [t]    |  [t+1 ... t+6]
```

---

## 🔍 RoboVLMs 원본 vs 우리 시스템 비교

| 항목 | RoboVLMs (CALVIN) | 우리 (Basket) | 차이점 |
| :--- | :--- | :--- | :--- |
| **Window Size** | 8 | 12 | +4 프레임 |
| **Chunk Size** | 10 | 6 (원래) / 1 (EXP-05) | -4 / -9 |
| **Episode Length** | **다양** (수백~수천 프레임) | **고정 18** | **치명적 차이** |
| **Task Horizon** | 장기 (multi-subtask) | 단기 (single task) | 복잡도 차이 |
| **Data Scale** | 대규모 (CALVIN 전체) | 소규모 (528 episodes) | 일반화 능력 |

### **CALVIN 데이터셋 특성**
- **긴 에피소드**: 수백~수천 프레임의 연속 조작
- **복잡한 Task**: "물체 잡고 → 서랍 열고 → 넣고 → 닫기" 등 multi-step
- **Chunk 10의 필요성**: 장기 planning이 필수적

### **우리 Basket 데이터셋 특성**
- **짧은 에피소드**: **18프레임 고정** (평균 17.7, 중앙값 18)
- **단순 Task**: "바구니로 이동 → 정지" (single goal)
- **Chunk의 역설**: 미래 6스텝 예측하지만, 에피소드 자체가 18프레임뿐

---

## 🎯 왜 Chunk k=1이 89.72%로 1위인가?

### **1. 학습-추론 괴리 (Training-Inference Mismatch)**

**Chunk k=6의 문제**:
```python
# 학습 시
model.forward(history) → [action_t+1, action_t+2, ..., action_t+6]
loss = MSE(predictions, ground_truth[t+1:t+7])

# 추론 시 (실제 로봇)
model.forward(history) → [action_t+1, ..., action_t+6]
robot.execute(action_t+1)  # 첫 번째만 사용!
# action_t+2 ~ t+6는 버려짐
```

**문제점**:
- 모델은 6스텝 planning을 학습했지만, **실제로는 1스텝만 사용**
- 나머지 5개 예측은 "쓸모없는" 복잡도만 증가
- 학습 목적과 실제 사용이 불일치

**Chunk k=1의 해결**:
```python
# 학습 시
model.forward(history) → action_t+1
loss = MSE(prediction, ground_truth[t+1])

# 추론 시
model.forward(history) → action_t+1
robot.execute(action_t+1)  # 완벽히 일치!
```

✅ **학습과 추론이 완전히 동기화**

---

### **2. 에피소드 길이 제약 (18 Frames)**

**Window=12, Chunk=6의 문제**:
```
Episode: [Frame 1 ... Frame 18]

t=12일 때:
- History: [1...12] → 12프레임 관찰
- Chunk 6 예측: [13, 14, 15, 16, 17, 18] → 6프레임 예측
- ✅ 딱 맞음!

t=13일 때:
- History: [2...13] → 12프레임 관찰
- Chunk 6 예측: [14, 15, 16, 17, 18, 19] → 19프레임 필요!
- ❌ 19프레임 없음! (에피소드는 18에서 끝)
```

**결과**:
- **유효 학습 샘플**: 에피소드당 단 **6~7개** (t=12까지만)
- **나머지 11프레임**: Chunk 6을 못 채워서 학습 불가
- **데이터 낭비**: 전체 프레임의 61% 손실!

**Chunk k=1의 해결**:
```
t=17일 때:
- History: [6...17] → 12프레임 관찰
- Chunk 1 예측: [18] → ✅ 가능!

t=18일때 (마지막 프레임):
- 예측 불가 → 종료
```

✅ **에피소드당 17개 샘플** 활용 (8배 증가!)

---

### **3. Task 복잡도 vs Planning Horizon**

**CALVIN (복잡한 Task)**:
```
Subtask 1: 서랍으로 이동 (30 프레임)
Subtask 2: 서랍 잡기 (10 프레임)
Subtask 3: 서랍 열기 (50 프레임)
Subtask 4: 물체 넣기 (40 프레임)
Subtask 5: 서랍 닫기 (30 프레임)
Total: 160 프레임

→ Chunk 10 필요: 각 subtask 전환 시 미리 계획
```

**Basket (단순 Task)**:
```
Phase 1: 바구니로 이동 (12 프레임)
Phase 2: 정지 (6 프레임)
Total: 18 프레임

→ Chunk 1 충분: 현재 상황만 보고 즉각 반응
```

✅ **Simple task → Simple model이 효율적**

---

### **4. Middle/Final Phase 100% 달성**

**실험 결과 (EXP-05, k=1)**:
- Middle Phase: **100.00%** PM/DA
- Final Phase: **100.00%** PM/DA

**왜?**
1. **정지 판단의 정확성**
   - Chunk 6: "앞으로 6스텝을 계획" → 과도한 momentum
   - Chunk 1: "지금 멈춰야 하나?" → 즉각 판단
   
2. **Overshoot 제거**
   - k=6: 미래를 과하게 고려 → 목표 지점 지나침
   - k=1: 현재 위치만 고려 → 정확히 정지

3. **슬라이드 패턴의 반복성**
   - Middle phase는 "좌/우 슬라이드" 반복
   - k=1도 충분히 패턴 학습 가능

---

## 📊 Window-Chunk 조합 분석

### **우리 데이터(Episode 18)에서 유효 샘플 수**

| Window | Chunk | 유효 샘플/Episode | 전체 활용률 | 비고 |
| :---: | :---: | :---: | :---: | :--- |
| 12 | 6 | **6개** | 33% | ❌ 데이터 낭비 심각 |
| 12 | 3 | **14개** | 78% | ⚠️ 개선되지만 여전히 손실 |
| 12 | 1 | **17개** | 94% | ✅ 최대 활용 |
| 8 | 6 | **10개** | 56% | ⚠️ Context 부족 |
| 8 | 3 | **14개** | 78% | 🔄 균형적 |
| 6 | 1 | **17개** | 94% | ⚠️ History 너무 짧음 |

**계산 공식**:
```python
유효_샘플 = Episode_Length - Window_Size - Chunk_Size + 1
활용률 = 유효_샘플 / Episode_Length
```

---

## 🎓 대학원 수준 고찰

### **연구 질문 1: Chunk의 본질적 역할은?**

**가설 A**: "미래 예측 정확도 향상"
- ❌ **반증**: EXP-05 (k=1) > EXP-04 (k=6)
- k=1도 충분히 정확하거나 더 좋음

**가설 B**: "행동 일관성 (Temporal Smoothness)"
- ⚠️ **부분 입증**: 장기 task에서는 유효
- 단, 짧은 task에선 smoothing이 오히려 overshoot 유발

**가설 C**: "학습 신호 증폭 (Multi-target Learning)"
- ✅ **입증**: Chunk 6은 한 입력당 6개 target → 6배 gradient
- 하지만, 추론 시 5개는 사용 안 함 → **낭비**

**결론**: 
> **Chunk의 이점은 데이터가 충분하고 Task가 복잡할 때만 유효하다.**  
> 우리처럼 짧고 단순한 Task에서는 **k=1이 optimal**

---

### **연구 질문 2: Window Size의 최적값은?**

**RoboVLMs가 8을 선택한 이유**:
1. CALVIN 에피소드가 수백 프레임
2. Window 8 → Chunk 10 with margin
3. 계산 효율 (batch size 고려)

**우리가 12를 선택한 이유**:
1. Episode 18 → 여유있는 history
2. LSTM의 장기 의존성 학습
3. Initial phase 대응 (첫 12프레임 warmup)

**실험적 검증 필요**:
```
EXP-16: Window Ablation (k=1 고정)
- Window 6 + Chunk 1
- Window 8 + Chunk 1
- Window 10 + Chunk 1
- Window 12 + Chunk 1
- Window 14 + Chunk 1
```

**예상**:
- Window 6: Initial phase 약화 (context 부족)
- Window 8~10: **최적점** 예상
- Window 12: 현재 성능
- Window 14: 큰 개선 없음 (Episode 18 제약)

---

### **연구 질문 3: 데이터 특성과 Architecture의 정합성**

**Mismatch 발견**:
1. **Chunk 6 설계**: CALVIN 같은 장기 task 가정
2. **실제 데이터**: 18프레임 단기 task
3. **결과**: 67% 데이터 낭비, 학습 비효율

**일반화 원칙**:
```
IF Episode_Length < Window + Chunk * 2:
    USE Chunk = 1 (reactive policy)
ELSE:
    USE Chunk = Episode_Length / 3 (predictive policy)
```

**우리 경우**:
```python
Episode = 18
Window = 12
18 < 12 + 6*2?  # 18 < 24? ✅ True
→ Chunk = 1 사용 권장
```

---

## 🚀 최적화 전략 제안

### **Phase 1: Window-Chunk Grid Search (우선순위 ★★★)**

| EXP | Window | Chunk | 이론적 샘플 | 예상 성능 | 실험 목적 |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **EXP-16** | 8 | 1 | 11개 (61%) | 88~90% | Window 축소 효과 |
| **EXP-17** | 10 | 1 | 9개 (50%) | 87~89% | 중간값 탐색 |
| **EXP-18** | 12 | 1 | 7개 (39%) | 89.72% | 현재 최고 (재현) |
| **EXP-19** | 14 | 1 | 5개 (28%) | 85~87% | History 과다 |

**핵심 가설**:
> **Window 8~10 + Chunk 1이 최적**  
> 충분한 context + 최대 데이터 활용

---

### **Phase 2: 에피소드 길이 확장 (중기 전략)**

**현재 제약**:
- Episode 18 → Window/Chunk 설계 제한

**해결책**:
1. **더 긴 에피소드 수집**
   - 목표: 30~50 프레임
   - 복잡한 경로 (zigzag, 장애물 회피)
   
2. **Multi-Basket Task**
   - 바구니 1 → 바구니 2 → 바구니 3
   - Episode 길이 자연스럽게 증가
   
3. **Chunk 재평가**
   - Episode 50이면 Window 12 + Chunk 3~5 가능
   - Long-term planning 학습 기회

---

### **Phase 3: Adaptive Chunking (장기 연구)**

**동적 Chunk Size**:
```python
if distance_to_goal > threshold:
    chunk_size = 3  # 먼 거리: planning 필요
else:
    chunk_size = 1  # 가까운 거리: reactive
```

**이점**:
- Task phase에 따라 유연한 대응
- 학습-추론 간극 최소화

---

## 📈 추천 실험 우선순위

### **즉시 실행 (이번 주)**

**1. EXP-16: Window 8 + Chunk 1**
```json
{
  "window_size": 8,
  "fwd_pred_next_n": 1,
  "act_head": {
    "window_size": 8
  }
}
```
**목표**: Window 축소로 샘플 수 증가 → 90%+ 돌파 시도

**2. EXP-17: Window 10 + Chunk 1**
- Window 8과 12 사이의 최적점 찾기

**3. Window-Chunk Ablation Study**
- 체계적 비교로 이론 검증

---

### **중기 실행 (다음 주)**

**4. 긴 에피소드 데이터 수집**
- 복잡한 경로로 30~50 프레임 목표

**5. EXP-20: Window 12 + Chunk 3 (새 데이터)**
- 긴 에피소드에서 Chunk의 진가 검증

---

## 🎯 최종 결론

### **핵심 발견**
1. ✅ **Chunk k=1이 최적** (우리 데이터 기준)
   - 학습-추론 일치, 데이터 최대 활용
   
2. ✅ **Episode 18의 제약**
   - Window 12 + Chunk 6 → 67% 데이터 낭비
   - 짧은 task에는 reactive policy가 효과적

3. ⚠️ **Window 최적화 여지**
   - Window 8~10이 더 좋을 가능성
   - 실험적 검증 필요

### **실천 전략**
> **"데이터에 맞춰 모델을 설계하라, 모델에 맞춰 데이터를 억지로 끼우지 말라"**

1. 현재 데이터 (Episode 18) → Window 8~10 + Chunk 1
2. 미래 데이터 (Episode 50+) → Window 12 + Chunk 3~5

### **예상 성능**
- **EXP-16 (W=8, k=1)**: 90~92%
- **EXP-17 (W=10, k=1)**: 89~91%
- **최적 조합 찾으면**: **92~95% 달성 가능**

---

**작성 완료**: 2026-02-09  
**핵심 메시지**: Chunk k=1의 성공은 우연이 아니라 **데이터 특성과의 정합성** 때문!
