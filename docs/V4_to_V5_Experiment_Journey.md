# MoNaVLA: Development & Experiment History (V4 to V5)

## 1. Background & Motivation (V4 Limitations)
본 프로젝트는 로봇 네비게이션을 위한 Vision-Language-Action (VLA) 모델을 개발하는 과정입니다. 이전 **V4 단계**에서는 LSTM 기반의 Regression Head를 사용해 `[linear_x, linear_y]` 연속형 제어값을 예측했습니다. 하지만 다음과 같은 치명적인 한계가 발생했습니다.

*   **Regression Averaging (회귀 평균화 문제):** 갈림길과 같이 모호한 상황에서 모델이 '좌회전' 또는 '우회전'을 결단하지 못하고, 안전한 직선 주행(평균값)을 예측하는 경향이 발생함.
*   **Visual Override (지시문 무시 및 장면 암기):** 언어 지시문("left" vs "right")보다 화면 상의 코너 형태(Visual bias)에 더 강하게 의존하여, 명령과 반대로 움직이는 현상 발견.

## 2. Hypothesis & Stage 5 (V5) Design
Regression의 한계를 극복하기 위해 **V5:** **Discrete Action Classification (이산 행동 분류)** 모델로 전면 전환을 결정했습니다.

### 주요 아키텍처 변경사항
*   **Action Decoder 변경:** 연속값 예측을 **다중 클래스 분류(Classification)**로 대체하여 모델의 결단력(Decisiveness) 확보.
*   **Action Mapping 정의:** 로봇의 움직임을 9개의 주요 행동 클래스로 정의.
*   **기대 효과:** 모델이 모호한 값을 내뱉지 못하게 '강제 선택' 구조로 변경함으로써 CrossEntropy Loss를 통해 더욱 뚜렷하고 결정적인 행동을 학습하도록 유도.

---

## 3. Breakthrough: The "Label 2 & 8" Discovery
실험 과정에서 모델이 회전 지시문에 대해 **STOP(정지)**으로 반응하는 오동작의 원인을 마침내 규명했습니다.

*   **발견된 치명적 결함:** 데이터 수집 시 **R(우회전)과 T(좌회전) 키**는 각각 **2번과 8번 레이블**로 기록되었으나, 초기 V5 학습 코드의 6클래스 축소 로직에서 이 데이터들이 모두 0번(STOP)으로 강제 매핑되는 정보 손실이 발생했음을 확인.
*   **해결:** 추론 서버 및 향후 학습 세션에서 2번/8번 레이블을 독립적인 회전 액션(`angular_z`)으로 복구하여 모델의 '결정적 회전력'을 확보함.

---

## 4. Experiment Progression (추론 사고 과정)

### 🧪 Exp01: 기본 분류형 모델 테스트 (`v5-exp01`)
*   **목표:** Kosmos-2 VLM 백본 위에 Classification Head가 정상 수렴하는지 검증.
*   **결과:** 학습은 되었으나 Class Imbalance로 인해 직진 편향성 발생.

### 🧪 Exp02: 회전 특화 및 불균형 해소 (`v5-exp02`)
*   **가설:** 직진 대비 회전 데이터 비중을 높여야 한다.
*   **조치:** 회전 데이터 가중치 부여 및 샘플링 조정. 검증 손실 `2.210` 달성.

### 🧪 Exp03: 텍스트-액션 정렬 강제 (CLIP Norm) (`v5-exp03`)
*   **가설:** 시각적 정보에 매몰되지 않도록 텍스트 의미를 물리적으로 주입해야 한다.
*   **조치:** LLM의 Action Hidden State와 CLIP Text Embedding 간의 **Smooth L1 Loss**를 추가하여 지시문 민감도 극대화.

---

## 5. Inference & Serving Evolution
로봇 실구동을 위해 `inference_server.py`를 대대적으로 고도화했습니다.

1.  **3DOF 출력 지원:** `[linear_x, linear_y, angular_z]` 체계로 확장하여 R/T 키 회전 완벽 대응.
2.  **동적 런타임 개입:** Logit Penalization, Temperature Scaling, Action Smoothing(EMA) 적용.
3.  **메모리 최적화:** `BitsAndBytes` INT8 양자화를 통해 VRAM을 **1.7GB** 수준으로 압축하여 모바일 환경 탑재 가능성 확인.

---

## 6. System Architecture & Access
현 시스템은 추론 엔진과 시각화 인터페이스가 분리된 구조로 운영됩니다.

### 🚀 Inference Backend (FastAPI)
*   **Path:** `robovlm_nav/serve/inference_server.py`
*   **Port:** `8000`
*   **Access:** [http://localhost:8000](http://localhost:8000) (API/Swagger: `/docs`)

### 📊 Monitoring Dashboard (Gradio)
*   **Path:** `scripts/gradio_inference_dashboard.py`
*   **Port:** `7865`
*   **Access:** [http://localhost:7865](http://localhost:7865)
*   **기능:** 실시간 모델 예측값(Probability Logits), 카메라 피드, 예측 이동 궤적 시각화 지원.
