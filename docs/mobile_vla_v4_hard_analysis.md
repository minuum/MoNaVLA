# Mobile-VLA v4 Hard Navigation Analysis 및 개선 리포트

## 1. Background
현재 Mobile-VLA v4 모델은 정면의 시각 정보에 강하게 편향(Vision-bias)되어, 특정 명령(예: "Stop")이나 장애물 상황에서도 전진을 지속하는 문제가 발견됨. 이는 학습 데이터셋 내 '전진' 데이터의 압도적 비율과 시각적 특징이 액션 결정에 지배적인 영향을 미치기 때문으로 분석됨.

## 2. Analysis of Issues
- **데이터 불균형**: 대부분의 데이터가 전진이며, 정지 또는 급회전 데이터는 상대적으로 매우 적음.
- **시각 편향**: 모델이 "앞이 트여 있으면 간다"는 단순 로직에 매몰되어, 텍스트 명령(Instruction)이나 이전 액션의 맥락을 무시함.
- **Action Decoder 한계**: MLP 기반의 액션 헤드가 역동적인 상황 변화를 충분히 반영하지 못할 가능성.

## 3. Findings & Proposed Solutions
이를 해결하기 위해 **Counterfactual Stop**과 **Action Weighting**전략을 도입함.

| 전략 | 설명 | 기대 효과 |
| :--- | :--- | :--- |
| **Counterfactual Stop** | 학습 중 50% 확률로 시각 정보와 무관하게 "정지" 명령과 액션(0,0)을 주입 | 시각 정보와 액션 사이의 결합을 강제로 끊고(Decoupling), 명령에 따른 액션 변화 유도 |
| **Action Weighting** | 전진 이외의 액션(Stop, Rotate, Hard Turn)에 대해 손실 함수 가중치 10배 적용 | 소수 클래스 데이터에 대한 학습 민감도 극대화 |
| **Weighted Loss** | `MobileVLALSTMDecoder`에 가중치 로직 적용 | 불균형 데이터셋에서의 효과적인 최적화 |

## 4. Implementation Status
- [x] **Dataset**: `counterfactual_stop_prob` 파라미터 추가 및 로직 구현 (`common/nav_dataset.py`)
- [x] **Model**: `MobileVLALSTMDecoder` 내 가중치 기반 MSE Loss 구현 및 가중치 10배 상향 (`models/heads/lstm_decoder.py`)
- [x] **Config**: `mobile_vla_v4_hard_counterfactual.json` 생성
- [x] **Training**: 훈련 시작 및 체크포인트 로딩 (기존 체크포인트와의 레이어 이름 불일치 문제 해결)

## 5. Preliminary Results
훈련 로그 확인 결과, 상향된 가중치로 인해 초기 Loss가 다소 높게 형성되나(`train_loss_step` ~1.5), 안정적으로 하락하는 추세를 확인 중.

---
**Next Steps:**
1. 1 Epoch 종료 후 `val_loss` 추이 분석
2. 체크포인트 저장 후 실제 로봇 환경 또는 시뮬레이션에서 "Stop" 명령 반응성 검증
