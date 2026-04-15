# Mobile_VLA V3 Experiments Summary

본 문서는 Mobile_VLA V3 시리즈의 각종 실험(Exp01 ~ Exp06)에 대한 세부 설정 및 실험 목적을 비교 분석하기 위해 작성되었습니다.

## 1. Overview of V3 Experiments

V3 실험 시리즈는 주로 **Forward 동작 편향성(Collapse) 해소**, **시각적 일반화(Visual Generalization) 개선**, **메모리 암기 방지(Preventing Sequence Memorization)** 등의 목적을 위해 점진적으로 파라미터를 조정하여 진행되었습니다.

### 1-1. Summary Table

| Experiment ID | Model Name          | Primary Goal                                          | LoRA  | Rank (r) | Augmentation              | Class Weights (Key Changes)                                                               | Additional Configs (Filter, Dropout)          | Max Epochs |
| :-----------: | :------------------ | :---------------------------------------------------- | :---: | :------: | :------------------------ | :---------------------------------------------------------------------------------------- | :-------------------------------------------- | :--------: |
|   **Exp01**   | `v3-exp01-aug`      | 시각적 일반화 개선 (Baseline + Augmentation 도입)     |   ❌   |    -     | Color Jitter, Random Crop | None (Uniform)                                                                            | -                                             |     -      |
|   **Exp02**   | `v3-exp02-baseline` | 베이스라인 비교 테스트 (Augmentation 없는 원복 세팅)  |   ❌   |    -     | None                      | None (Uniform)                                                                            | -                                             |     -      |
|   **Exp03**   | `v3-exp03-weighted` | 불균형 데이터셋 해소를 위한 가중치(Class Weight) 도입 |   ❌   |    -     | Color Jitter, Random Crop | `[2.0, 0.2, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0]`<br>*Forward(1): 0.2로 패널티*             | -                                             |     10     |
|   **Exp04**   | `v3-exp04-lora`     | Weight/Aug 세팅에 **LoRA** Fine-Tuning 적용 검증      |   ✅   |    16    | Color Jitter, Random Crop | 동일 (Fwd: 0.2)                                                                           | -                                             |     10     |
|   **Exp05**   | `v3-exp05-lora`     | Forward Collapse 해결 - (Left/FwdLeft 강제 가중치)    |   ✅   |    16    | Color Jitter, Random Crop | `[2.0, 0.1, 5.0, 10.0, 2.0, 1.5, 1.0, 5.0, 5.0]`<br>*L(3): 10.0, Fwd(1): 0.1*             | -                                             |     12     |
|   **Exp06**   | `v3-exp06-lora`     | 스텝 시퀀스 암기 방지 및 이미지-언어 바인딩 강화      |   ✅   |    32    | Color Jitter, Random Crop | `[1.5, 0.08, 5.0, 15.0, 5.0, 2.5, 3.5, 5.0, 5.0]`<br>*L: 15.0, Fwd: 0.08, FR: 3.5 패널티* | **Filter:** `"left"`<br>**History DO:** `0.3` |     15     |

---

## 2. Detailed Configuration Analysis

### 2.1. Exp01 & Exp02 (Baseline & Augmentation)
- **Exp01**: V2 모델의 시각적 과적합 문제를 해결하기 위해 `Color Jitter`와 `Random Crop` 등의 Vision Augmentation 기법들을 전면 도입하여 일반화 성능을 높이려 한 모델.
- **Exp02**: 모든 Augmentation을 제거하여 기본적인 데이터만 학습한 후, Exp01의 Augmentation 도입 효용성을 비교 평가하기 위해 세팅된 대조군(Baseline).

### 2.2. Exp03 & Exp04 (Class Weighting & LoRA Integration)
- **Exp03**: 데이터 분포가 50% 이상 "Forward"에 편향된 문제를 교정하기 위해, 처음으로 Loss Function 부분에 `Class Weights` 배열을 명시적으로 투입. Forward는 0.2의 낮은 비율만 주어 패널티를 부여.
- **Exp04**: Exp03의 환경에서 파라미터 업데이트의 효율성을 높이고자 **LoRA (Rank 16)**를 본격적으로 활용. 전체 파라미터 최적화 대비 컴퓨팅 효율 및 성능 최적화 검증 목적. 추후 1차적인 V3 기준 모델이 됨.

### 2.3. Exp05 (Overcoming Forward Collapse)
- **배경**: Exp04까지의 테스트 결과, 0.2의 패널티에도 불구하고 모델 구조가 여전히 "Forward" 예측으로 수렴(Collapse)하는 거대한 편향 파악.
- **해결 방안**: 역빈도 기반(Inverse Frequency)으로 가중치를 대폭 조정.
  - Forward (과다 비율): 0.1로 추가 억제.
  - Left (최소 비율, 2.9%): 기존 5.0에서 10.0으로 2배 강화.

### 2.4. Exp06 (Anti-Memorization & Modality Binding)
- **배경**: 이전 실험들이 과거 프레임 기록(History)을 통해 단순히 시퀀스(진행 순서)를 암기해버리는 문제를 분석 결과 확인.
- **해결 방안**:
  1. **History Dropout (0.3)**: 과거 프레임의 정보(히스토리)를 일정 확률로 무작위 마스킹. 모델이 과거 정보에만 의존하지 않고 현재 시야 정보와 지시(언어)를 바인딩 하도록 강제.
  2. **LoRA Rank 향상 (16 -> 32)**: 시각-언어 매핑 복잡도를 수용하기 위해 임베딩 모델의 처리 능력을 상승시킴.
  3. **데이터 필터링**: 가장 해결이 어려운 `left` 에피소드만 집중적으로 타겟하는 커리큘럼 러닝 도입.
  4. **FR 클래스 조정**: FR 클래스가 초반 수렴 공간을 지배하지 않도록 3.5로 추가 규제.

---
*Report generated on: 2026-02-26*
