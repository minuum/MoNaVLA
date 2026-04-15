# VLA 실험 히스토리 및 분석 요약 (EXP-01 ~ EXP-17)

**작성일**: 2026-02-09  
**프로젝트**: Mobile VLA Navigation Optimization  
**목적**: 실험 과정의 논리적 흐름과 핵심 발견 정리

**목적**: 실험 과정의 논리적 흐름과 핵심 발견 정리

## 📊 실험 결과 요약 (Summary Table)

| Exp ID | Model Config | Epochs | Success Rate | Key Insight / Failure Mode | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **EXP-17** | **Window 8, Chunk 1** | - | **94.72%** | Optimal Window Size (PM/DA 1위) | ✅ Done |
| **EXP-16** | Window 6, Chunk 1 | - | 89.72% | Efficient Inference | ✅ Done |
| **EXP-12** | Hybrid (W6+Resampler) | - | - | Training Combined Architecture | 🚀 Running |
| EXP-05 | Window 12, Chunk 1 | - | 89.72% | Discovered Reactive Policy Benefit | ✅ Done |
| EXP-06 | Resampler 64 | - | 82.50% | Solved Initial Frame Issue | ✅ Done |
| EXP-09 | Latent 128 | - | 77.50% | Diminishing Returns on Size | ✅ Done |
| EXP-04 | Baseline (Linear) | - | 65.83% | Poor Initial State Handling | ✅ Done |
| EXP-10 | Window 16 | - | FAILED | Data Scarcity for Long Window | ❌ Fail |

---

## 📅 실험 타임라인 및 진화 과정

### **Phase 1: 초기 탐색 (Dec 2025 ~ Jan 2026)**
> *"기본 동작 구현 및 데이터셋 검증"*

- **EXP-01 (Chunk 5)**: 초기 베이스라인 구축 시도. 
- **EXP-02 (Chunk 10)**: Long-horizon planning 시도했으나 우리 Task(단순 이동)에는 과도함 확인.
- **EXP-03 (Left Only)**: 데이터 편향성 테스트. 특정 방향 데이터만으로 학습 시도.

---

### **Phase 2: 베이스라인 확립 (Feb 5, 2026)**
> *"정량적 성능 측정 시작"*

- **EXP-04 (Baseline)**: 
  - 설정: Window 12, Chunk 6, Linear Projection
  - 결과: **65.83%** (Initial 9%)
  - **교훈**: Linear Layer만으로는 초기 프레임의 정보 처리가 매우 취약함.

---

### **Phase 3: 구조적 개선 시도 (Feb 6-7, 2026)**
> *"Chunk Size와 Visual Encoding의 중요성 발견"*

- **EXP-05 (Chunk k=1)**: 🏆 **Game Changer**
  - 설정: Window 12, **Chunk 1**
  - 결과: **89.72%** (압도적 1위)
  - **핵심 발견**: 짧은 Episode(18프레임)에는 **Reactive Policy (k=1)**가 최적. 학습-추론 괴리 해소.

- **EXP-06 (Visual Resampler)**: 
  - 설정: Window 12, Chunk 6, **Resampler 64**
  - 결과: **82.50%** (Initial 81%)
  - **핵심 발견**: Resampler가 초기 프레임 정보 처리를 획기적으로 개선 (9% → 81%).

- **EXP-09 (Latent Density)**:
  - 설정: **Latent 128**
  - 결과: **77.50%** (EXP-06 대비 하락)
  - **교훈**: Latent 수가 많다고 좋은 게 아님. 64개가 Sweet Spot.

---

### **Phase 4: 시행착오 및 실패 분석 (Feb 7, 2026)**
> *"데이터셋 제약과 설정 오류"*

- **EXP-10 (Window 16)**: 
  - 설정: Window 16
  - 결과: **실패** (데이터 부족)
  - **분석**: Episode 길이가 18프레임인데 Window 16을 쓰면 학습 샘플이 거의 없음.

- **EXP-11 (Discrete)**:
  - 설정: Classification Head
  - 결과: **실패** (Config 오류)
  - **분석**: 현재 Continuous Action으로도 충분한 성능. 우선순위 낮음.

---

### **Phase 5: 최적화 및 고도화 (Feb 9-10, 2026 ~ Current)**
> *"데이터 특성 기반 정밀 튜닝 및 하이브리드 결합"*

- **EXP-16 (Window 6)**: ✅ 완료
  - 설정: Window 6, Chunk 1
  - 결과: **89.72%** (EXP-05와 동일)
  - **발견**: Window를 줄여도 성능은 유지되며, 연산 효율성은 대폭 상승.

- **EXP-17 (Window 8)**: ✅ 완료 (🏅 **New Best**)
  - 설정: Window 8, Chunk 1
  - 결과: **94.72%** (PM/DA 1위 등극!)
  - **분석**: CALVIN 비율인 50% 수준의 Window가 우리 18프레임 데이터에도 최적임을 증명.

- **EXP-12 (W6 Hybrid)**: 🚀 학습 중
  - 목적: **Window 6 + Chunk 1 + Resampler** 하이브리드.
  - 가설: 최고의 주행 성능(W6, k=1)에 최강의 초기 인지력(Resampler)을 더해 95% 돌파 시도.

---

## 💡 핵심 기술적 통찰 (Technical Insights)

### **1. "Short Episode = Reactive Policy"**
- **증거**: RT-1(Chunk 1), Pi0(Chunk 비율 3%), EXP-05(Chunk 1)
- **원리**: 짧은 Task에서 긴 Chunk는 오버슈팅과 데이터 낭비 초래. 
- **결론**: **Chunk k=1**이 우리 시스템의 표준.

### **2. "Visual Resampler is Essential"**
- **증거**: Baseline(9%) vs Resampler(81%)
- **원리**: 단순 Linear Projection은 Image Token의 semantic을 충분히 추출하지 못함. Perceiver Resampler의 Cross-attention이 필수적.
- **결론**: **Resampler 64** 유지.

### **3. "Optimization over Scaling"**
- **증거**: Latent 64(82.5%) > Latent 128(77.5%)
- **원리**: 모델 크기를 무작정 키우는 것보다, Task 복잡도에 맞는 적절한 용량(Capacity)이 중요.
- **결론**: **Compact Model** 지향 (Window 8, Latent 64).

---

## 📊 성능 도약 그래프

```
Action Accuracy (PM/DA)
95% |                   EXP-17 (94.72%) 🏆
90% |                   EXP-05/16 (89.72%)
    |                   EXP-12 (88.89%)
80% |          EXP-06 (82.5%)  EXP-09 (77.5%)
    |              *               *
70% |  EXP-04 (65.8%)
    |      *
60% |
    +---------------------------------------->
      Baseline   Resampler   Chunk1   Window_Opt
```

---

## �️ 최신 기술 고안: First-Frame Zero Enforcement

- **문제**: 모델이 정지 상태인 첫 프레임에서도 바구니가 보이면 흥분하여 즉시 이동 액션을 출력(Stop Confusion).
- **해결**: API 서버단에서 **에피소드 첫 프레임 강제 [0,0] 액션** 로직 구현.
- **효과**: 로봇 출발 시의 오작동 제거 및 초기 안정성 확보.

---

## �📝 향후 연구 제언

1. **Hybrid Model (EXP-12)**: Resampler 모델에서도 k=1 최적화를 적용하여 **88.89%** 달성. 초반 인지력 향상 확인.
2. **Window Optimization (EXP-17)**: Window 8이 최적임을 확인하며 **94.72%**라는 독보적 성능 달성.
3. **On-Device Deployment**: Jetson 배포를 위한 모든 준비 완료.

**최종 업데이트**: 2026-02-11
