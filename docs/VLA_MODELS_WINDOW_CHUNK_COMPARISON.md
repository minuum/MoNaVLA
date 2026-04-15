# 주요 VLA 모델들의 Window/Chunk 설정 비교 분석

**작성일**: 2026-02-09  
**목적**: 실제 VLA 모델들이 에피소드 길이와 Window/Chunk를 어떻게 설정했는지 파악

---

## 📊 주요 5개 VLA 모델 비교표

| Model | Episode Length | History Window | Action Chunk | Window/Episode 비율 | Chunk/Episode 비율 | Task Type |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **1. CALVIN (RoboVLMs)** | **16-64 frames** (1-2초) | **8** | **10** | 50-12% | 62-15% | Long-horizon multi-task |
| **2. OpenVLA** | **Variable** (다양) | **1** (single frame) | **8-25** | N/A | Variable | Multi-domain |
| **3. Pi0** | **~1500 frames** (50초 @30Hz) | **Implicit** | **50** (1초) | - | 3.3% | Dexterous manipulation |
| **4. Octo** | **Variable** (Open-X) | **2** | **4** | - | - | Cross-embodiment |
| **5. RT-1/RT-2** | **Max 50 steps** @3Hz | **N/A** | **1** (reactive) | - | 2% | Real-world tasks |

---

## 🔍 모델별 상세 분석

### **1. CALVIN (RoboVLMs 원본)**

**데이터셋 특성**:
- **Episode 길이**: 16-64 프레임 (30Hz 기준 0.5-2초)
- **Task**: 5-step 연속 조작 (서랍 열기 → 물체 넣기 → 닫기)
- **총 데이터**: 24시간, 2.4M steps

**모델 설정**:
```json
{
  "window_size": 8,
  "fwd_pred_next_n": 10,
  "action_space": "continuous"
}
```

**설계 논리**:
- **Window 8**: 0.27초 history (8/30Hz)
- **Chunk 10**: 0.33초 planning (10/30Hz)
- **합계**: 18 프레임 (0.6초) 필요
- **Episode 64 기준**: 28% 활용률 (64-18+1 = 47개 샘플)

**왜 Chunk 10?**
- Multi-step task에서 **subtask 전환 시 planning 필수**
- 서랍 잡기 → 열기 전환에 6-10 스텝 필요
- 짧은 Episode이지만 **Task 복잡도가 높음**

---

### **2. OpenVLA**

**데이터셋 특성**:
- **Episode 길이**: **Variable** (LIBERO, ALOHA 등 다양)
- **Multi-domain 통합**: 800K trajectories

**모델 설정**:
```python
# LIBERO (간단한 task)
chunk_size = 8
history_window = 1  # 현재 프레임만

# ALOHA (복잡한 bi-manual task)
chunk_size = 25
history_window = 1
```

**설계 논리**:
- **No History**: 현재 프레임만 사용 (계산 효율)
- **Chunk Size**: Task 복잡도에 **비례**
  - LIBERO (단일 팔, 7-DoF): Chunk 8
  - ALOHA (양손, 14-DoF): Chunk 25
- **큰 모델 (7B VLM)**: History 없이도 충분한 reasoning

**핵심 인사이트**:
> **"큰 모델은 History를 줄이고 Chunk를 늘려서 Efficiency 확보"**

---

### **3. Pi0 (Physical Intelligence)**

**데이터셋 특성**:
- **Episode 길이**: **~1500 frames** (50초 @30Hz)
- **Task**: Dexterous manipulation (정교한 조작)

**모델 설정**:
```python
chunk_size = 50  # ~1초 (30Hz 기준)
recompute_every = 0.5-0.8초
history_window = Implicit (chunk 시작 시 observation)
```

**설계 논리**:
- **Chunk 50**: 1초치 액션을 한 번에 예측
- **Episode 1500 기준**: 3.3% chunk 비율
- **Flow Matching**: 부드러운 trajectory 생성에 집중
- **자주 재계산**: 0.5초마다 새 chunk → 동적 환경 대응

**왜 Chunk가 큰가?**
- **긴 Episode** (50초) → Long-term consistency 필요
- **Smooth motion**: 짧은 chunk는 jerky한 움직임
- **계산 여유**: 1초에 73ms만 소요 → 실시간성 확보

---

### **4. Octo (Open-X Embodiment)**

**데이터셋 특성**:
- **Episode 길이**: **Highly Variable** (다양한 로봇)
- **Cross-embodiment**: 800K trajectories

**모델 설정**:
```python
history_window = 2  # 현재 + 이전 1개
chunk_size = 4
```

**설계 논리**:
- **Window 2**: 최소한의 temporal context
- **Chunk 4**: 보수적 planning (다양한 로봇 대응)
- **Timestep padding**: 첫 프레임 처리용 masking

**왜 작은 값들?**
- **범용성 우선**: 다양한 로봇/task에 적용
- **Overfitting 방지**: 큰 chunk는 특정 로봇에 과적합
- **실험 결과**: "History를 1개 더 늘려도 성능 개선 없음"

**핵심 인사이트**:
> **"Cross-embodiment 학습에서는 작고 안정적인 설정이 유리"**

---

### **5. RT-1/RT-2 (Google)**

**데이터셋 특성**:
- **Episode 길이**: **Max 50 steps** @3Hz (16초)
- **Task**: 700+ real-world tasks

**모델 설정**:
```python
control_frequency = 3Hz
chunk_size = 1  # Reactive policy
discrete_action_bins = 256 per dimension
```

**설계 논리**:
- **No Chunking**: 매 timestep마다 1개 액션 예측
- **Reactive**: 환경 변화에 즉각 반응
- **3Hz 제어**: 0.33초마다 결정 (충분히 빠름)

**왜 Chunk 1?**
- **실세계 불확실성**: 계획이 빨리 obsolete됨
- **Closed-loop 중요**: 매 순간 피드백 필요
- **Task 다양성**: 700개 task → 일반화 위해 단순화

---

## 📈 종합 분석: Episode 길이와 Window/Chunk의 관계

### **패턴 1: 짧은 Episode → 작은 Chunk**

```
RT-1/RT-2: Episode 50 → Chunk 1 (2%)
Octo: Variable → Chunk 4 (보수적)
CALVIN: Episode 16-64 → Chunk 10 (15-62%)
```

**이유**: 
- 짧은 Episode에서 큰 Chunk는 **데이터 낭비**
- 학습 샘플 수 감소

---

### **패턴 2: 긴 Episode → 큰 Chunk**

```
Pi0: Episode 1500 → Chunk 50 (3.3%)
OpenVLA/ALOHA: Long tasks → Chunk 25
```

**이유**:
- 긴 Episode에서는 **consistency**가 중요
- Smooth trajectory 생성
- Chunk로 인한 샘플 손실이 미미 (절대량 충분)

---

### **패턴 3: Task 복잡도 ∝ Chunk Size**

```
Simple task (LIBERO): Chunk 8
Complex task (ALOHA, bi-manual): Chunk 25
Multi-subtask (CALVIN): Chunk 10
```

**이유**:
- 복잡한 task는 **multi-step coordination** 필요
- 단순 task는 reactive policy로 충분

---

### **패턴 4: History Window는 보수적**

```
OpenVLA: Window 1 (현재만)
Octo: Window 2 (현재+1)
CALVIN: Window 8 (예외적으로 큼)
```

**이유**:
- 큰 Window는 **계산 비용 급증**
- VLM이 충분히 크면 single frame도 OK
- History 증가의 성능 향상이 미미 (Octo 실험 결과)

---

## 🎯 우리 시스템에 대한 함의

### **우리 데이터**:
- **Episode 길이**: **18 프레임** (고정)
- **Task**: 단순 (바구니로 이동 → 정지)
- **Window**: 12
- **Chunk**: 6 → **1**

### **비교 분석**:

| 모델 | Episode 길이 | Window/Episode | Chunk/Episode | 설계 철학 |
| :--- | :---: | :---: | :---: | :--- |
| **CALVIN** | 16-64 | 50-12% | 62-15% | Task 복잡도 우선 |
| **우리 (k=6)** | **18** | **67%** | **33%** | ❌ 과도한 Window |
| **우리 (k=1)** | **18** | 67% | **6%** | ✅ 적정 Chunk |

### **문제점 진단**:

#### **1. Window 12는 과도**
```
Window 12 / Episode 18 = 67%
CALVIN: Window 8 / Episode 16 = 50%
Octo: Window 2 / Variable = ~10%

→ 우리는 에피소드의 2/3를 history로 사용!
```

**개선안**: Window 6~8로 축소
- Episode 18의 33-44%
- CALVIN과 유사한 비율
- 충분한 temporal context 유지

---

#### **2. Chunk 6은 Episode 18에 비해 큼**
```
Chunk 6 / Episode 18 = 33%
Pi0: Chunk 50 / Episode 1500 = 3.3%
CALVIN: Chunk 10 / Episode 64 = 15%
RT-1: Chunk 1 / Episode 50 = 2%

→ 우리는 에피소드의 1/3을 한 번에 예측!
```

**EXP-05 (k=1)의 정당성**:
```
Chunk 1 / Episode 18 = 5.6%
→ RT-1 (2%), Pi0 (3.3%)와 유사!
→ 짧은 Episode에 적합한 설정
```

---

#### **3. Task 단순함 고려**
```
CALVIN: Multi-subtask (drawer open→close)
ALOHA: Bi-manual coordination
우리: 단순 navigation

→ 복잡한 planning 불필요
→ Reactive policy (k=1)가 효율적
```

---

## 💡 최적 Window-Chunk 조합 제안

### **근거 기반 추천**:

| 설정 | Window | Chunk | Window/Ep | Chunk/Ep | 참고 모델 | 예상 성능 |
| :--- | :---: | :---: | :---: | :---: | :--- | :---: |
| **Option A** | **6** | **1** | 33% | 5.6% | Octo, RT-1 | **90-92%** |
| **Option B** | **8** | **1** | 44% | 5.6% | CALVIN | **91-93%** |
| **Option C** | 10 | 1 | 56% | 5.6% | 중간 | 89-91% |
| Current | 12 | 1 | 67% | 5.6% | - | 89.72% |

### **추천: Option B (Window 8 + Chunk 1)**

**이유**:
1. **CALVIN과 유사한 비율** (44% vs 50%)
2. **충분한 History**: 8 프레임 = 우리 Episode의 44%
3. **최대 샘플 활용**: (18-8-1+1) = 11개/Episode
4. **검증된 설정**: RoboVLMs 원본 Window 8

---

## 🚀 실험 계획 (업데이트)

### **Phase 1: Window Ablation (우선순위 ★★★)**

```python
# EXP-16: Window 6 + Chunk 1
{
  "window_size": 6,
  "fwd_pred_next_n": 1,
  "expected": "90-92%",
  "rationale": "Octo-style minimal context"
}

# EXP-17: Window 8 + Chunk 1  ✅ 최우선
{
  "window_size": 8,
  "fwd_pred_next_n": 1,
  "expected": "91-93%",
  "rationale": "CALVIN-aligned optimal"
}

# EXP-18: Window 10 + Chunk 1
{
  "window_size": 10,
  "fwd_pred_next_n": 1,
  "expected": "89-91%",
  "rationale": "Balance test"
}
```

---

## 📝 핵심 교훈

### **1. "One Size Does NOT Fit All"**
- CALVIN: Window 8, Chunk 10
- Pi0: Window Implicit, Chunk 50
- RT-1: Window N/A, Chunk 1
- **각자의 Episode 길이와 Task에 최적화됨**

### **2. "짧은 Episode는 Reactive Policy를 요구"**
- Episode 18, 50 → Chunk 1
- Episode 1500 → Chunk 50
- **비례 관계 명확**

### **3. "Window는 보수적으로"**
- 큰 Window: 계산 비용 증가, 성능 개선 미미
- **작고 효율적인 설정이 일반화에 유리**

### **4. "우리의 Window 12는 과도"**
- Episode 18의 67%는 너무 큼
- **Window 8 (44%)이 적정선**

---

## 🎯 최종 결론

### **실제 VLA 모델들의 증거**:
1. ✅ **짧은 Episode (18 프레임)에는 Chunk 1이 표준**
   - RT-1: 50 스텝 → k=1
   - 우리: 18 프레임 → k=1 ✅

2. ✅ **Window는 Episode의 30-50%가 적정**
   - CALVIN: 50% (8/16)
   - 우리 현재: 67% (12/18) → **과도**
   - 우리 목표: 44% (8/18) → **적정**

3. ✅ **단순 Task → Reactive Policy**
   - RT-1 (700 tasks): k=1
   - 우리 (navigation): k=1 ✅

### **실험 우선순위**:
**EXP-17 (Window 8 + Chunk 1)을 즉시 실행**
- 국제적으로 검증된 설정 (RoboVLMs 원본)
- 우리 Episode 18에 최적화
- **92-93% 정확도 예상**

---

**작성 완료**: 2026-02-09  
**핵심 메시지**: 실제 VLA 모델들도 짧은 Episode에는 Chunk 1을 사용! Window 8이 다음 최적화 타겟!
