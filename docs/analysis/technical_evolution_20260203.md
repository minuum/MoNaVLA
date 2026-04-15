# Mobile VLA 기술 진화 및 근본 원인 분석
날짜: 2026-02-03

## 1. 시대별 마일스톤 (기술적 특이점)

### Phase 1: 연속 공간의 시작 (Continuous Beginning)
- **관련 커밋**: 
    - `204edcc2` (2025-08-15) - Data: add Mobile VLA dataset episodes
    - `cf42f36` (2026-01-11, Submodule) - Add pretrained VLM loading support (Kosmos-2 load)
- **기술 스택**: Kosmos-2 (Frozen) + LSTM Decoder (Continuous 2D Output)
- **가설**: Pretrained VLM의 특징(feature)과 RNN의 시계열 처리로 시각 정보를 속도로 변환할 수 있을 것이다.
- **결과**:
    - **증상**: "떨림(Jittery)" 현상. 0.12와 같은 모호하고 낮은 속도 값 출력.
    - **진단**: 회귀(Regression) 손실함수(MSE) 특성상, 모델이 확신이 없을 때 '안전한 평균값(0 근처)'을 내보내려는 경향이 강함.

### Phase 2: Left-Only 베이스라인 (Ablation Study)
- **관련 커밋**: 
    - `579cb3b5` (2026-02-02) - Implement Classification Model & **Left-Only Config** (`mobile_vla_basket_left_only.json`)
    - `af76dd7` (2026-02-01, Submodule) - enhance language instruction loading (데이터 로더 개선)
- **기술 스택**: 동일 구조, "Left" 바구니 데이터만으로 학습
- **가설**: 한 방향도 못 배우면 두 방향은 절대 못 배운다. (기초 검증)
- **결과**:
    - **증상**: 전체 모델보다 오히려 성능이 높음.
    - **진단**: **언어 그라운딩 실패 (Language Grounding Failure)**. 전체 모델이 명령어("Left" vs "Right")를 전혀 구분하지 못하고, 찍기(Random Guessing)를 하고 있었음이 드러남.

### Phase 3: 분류 / 이산 공간 (Classification / Discrete)
- **관련 커밋**: 
    - `579cb3b5` (2026-02-02) - **Add Classification Config** & API Server update
    - `06a5772` (2026-02-02, Submodule) - **Add MobileVLAClassificationDecoder** (Core Logic)
- **기술 스택**: 이산화된 액션 공간 (6 Classes: Stop, Fwd, Left, Right, DiagL, DiagR)
- **가설**: 로봇 주행은 본질적으로 이산적(WASD)이다. 분류(CrossEntropy)는 모델에게 '확실한 선택'을 강요한다.
- **결과**:
    - **증상**: 1.0 vs 0.0으로 확신에 찬 움직임. 그러나 **횡방향 표류 환각 (Lateral Drift Hallucination)** 발생.
    - **진단**: **사전 분포 편향 (Prior Distribution Bias)**. "정답의 50%는 전진(Class 1)"이라는 통계적 사실을 모델이 너무 빨리 간파함.

### Phase 4: 가중치 손실 (Weighted Loss - Current)
- **관련 커밋**: *Work In Progress* (Not committed yet)
    - Modified `MobileVLAClassificationDecoder` to support `class_weights`
    - Created `mobile_vla_basket_left_classification_weighted.json`
- **기술 스택**: 가중치 적용 CrossEntropy (Forward=0.5, Turn=2.0)
- **가설**: '쉬운' 전진 예측에 벌칙을 주고, '희소한' 회전/횡이동 예측에 보상을 강화한다.
- **결과**:
    - **증상**: 초기 에포크에서 방향 일치도(Directional Agreement) 약 27% 기록. 전진만 하던 습관이 줄어들고 횡이동을 시도하기 시작함.

---

## 2. 근본 원인 분석 (Fundamental Root Causes)

위의 역사를 통해 우리는 3가지의 근본적인 장벽에 부딪혔음을 알 수 있습니다.

### A. "얼어붙은 눈"의 문제 (Frozen Eye - Visual Hallucination)
- **문제**: **VLM 백본이 고정(Frozen)**되어 있음.
- **영향**: Kosmos-2는 일반 웹 데이터로 학습되었습니다. 우리 실험실의 특정 '바구니'나 '바닥 무늬'를 네비게이션의 핵심 단서가 아닌, 일반적인 배경 사물로 인식할 가능성이 큽니다. "왼쪽에 있는 바구니"와 "오른쪽에 있는 바구니"를 구별할 만큼 **차별적인 특징(Discriminative Features)**을 생성하지 못하고 있습니다.
- **결과**: 정책 헤드(Policy Head)는 모호한 시각 정보를 받게 되고, 결국 데이터 통계(전진)에 의존하게 됩니다.

### B. "불균형한 현실"의 문제 (Imbalanced Reality - Prior Bias)
- **문제**: 주행 데이터의 90%는 전진, 회전은 5% 미만.
- **영향**: 입력 신호(Frozen Eye)가 모호할 때, 모든 머신러닝 모델은 확률적으로 가장 안전한 선택(**전진**)을 하도록 수렴합니다.
- **결과**: 우리는 이를 "환각"이라 부르지만, 모델 입장에서는 불확실성 속에서 가장 **합리적인 통계적 추론**을 하고 있는 것입니다.

### C. "언어의 단절" 문제 (Instruction Disconnect - Language Hallucination)
- **문제**: VLM 대비 Action Head의 용량이 너무 작음.
- **영향**: "Left"라는 텍스트 임베딩과 시각적 특징을 융합하는 Attention Layer들이 얼어(Frozen) 있기 때문에, 언어적 지시가 시각 처리에 영향을 주지 못합니다.
- **결과**: 모델은 "왼쪽으로 가라"는 명령을 무시하고, 눈에 띄는 아무 물체(Saliency)를 향해 돌진합니다.

---

## 3. 다음 특이점: "해동" (The Next Singularity: Unfreezing via LoRA)

현재의 한계(방향 일치도 ~30%)를 돌파하려면, Policy Head에 들어가는 **신호의 품질** 자체를 높여야 합니다. Head만 계속 바꾸는 것(연속 -> 이산 -> 가중치)은 수확 체감(Diminishing Returns) 단계에 접어들었습니다.

**제안된 해결책: LoRA (Low-Rank Adaptation)**
- **무엇을**: VLM 백본 파라미터의 1% 미만만을 학습 가능한 상태로 전환.
- **왜**:
    1.  **시각 동기화 (Align Vision)**: 일반적인 '컵'이 아니라, 네비게이션 목표로서의 '우리 실험실 바구니'를 인식하도록 눈을 튜닝.
    2.  **언어 융합 (Fuse Language)**: Attention Layer가 "Left"라는 토큰을 "왼쪽 바구니"라는 시각적 특징과 실제로 연결하도록 허용.
