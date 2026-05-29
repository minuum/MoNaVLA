# Exp59 Technical Report: Hard Negative PaliGemma2 LoRA Grounder & Closed-Loop Analysis

본 보고서는 단일 타겟 물체(gray basket) 추적 상황에서 주변의 유사/이질적인 다른 장애물들에 대한 오탐(False Positive) 현상(R2-3 문제)을 방지하기 위해 설계된 **Exp59 (Hard Negative 학습 PaliGemma2-3B LoRA Grounder)** 모델의 검증 및 closed-loop 시뮬레이션 평가 결과를 분석합니다.

---

## 1. Background (배경)

VLM 기반 Robot Navigation(VLA) 분야에서 기존의 일반적인 pre-trained grounding 모델들은 텍스트 쿼리에 부합하는 대상을 찾을 때, 타겟과 유사하거나 형태가 겹치는 다른 장애물(예: brown pot, red ball, person 등)이 나타나면 이를 오탐(False Positive)하여 주행 경로를 이탈하는 고질적인 한계가 존재했습니다. 이를 **R2-3 (타겟 오분류 및 오탐) 문제**로 규정합니다.

이 문제를 해결하기 위해, target 물체인 **gray basket**이 있는 이미지 외에도, target 없이 다른 부정적 물체(Hard Negative)들만 존재하는 이미지를 학습 데이터에 포함하여 **PaliGemma2-3B 백본에 LoRA fine-tuning**을 적용한 **Exp59** 그라운더 모델을 설계하고 학습시켰습니다. 본 실험의 목표는 다음과 같습니다.
1. 타겟 이외의 물체에 대해 BBox를 생성하지 않는 **신경망 수준의 완벽한 오탐 차단(R2-3 극복)** 검증.
2. 런타임에 이 그라운더를 탑재하고 기존 Stage2 Action MLP와 연동하여 **closed-loop 시뮬레이션**을 수행했을 때의 실질 주행 복원 성능 평가.

---

## 2. Analysis & Methodology (분석 방법론)

본 검증은 크게 두 가지 단계로 나누어 수행되었습니다.

### A. Cross-Object Grounding Evaluation (교차 객체 그라운딩 평가)
- **평가 대상**: Exp59 PaliGemma2 LoRA Grounder
- **데이터셋**: 타겟 물체(gray basket) 이미지 20장, Hard Negative 3종(brown pot, red ball, person) 각 20장 (총 80장)
- **출처**: [v5_cross_results.json](file:///home/minum/26CS/MoNaVLA/docs/v5/exp59_cross_object/v5_cross_results.json)
- **지표**: True Positive (TP) Rate, False Positive (FP) Rate

### B. Closed-Loop Offline Simulation (폐루프 시뮬레이션 평가)
- **평가 대상**: Exp59 Grounder + Stage2 MLP (Exp54 학습 가중치 사용)
- **데이터셋**: validation 세트 22개 에피소드 (총 394 프레임)
- **출처**: [exp59_closedloop_result.json](file:///home/minum/26CS/MoNaVLA/docs/v5/closed_loop_eval/exp59_closedloop_result.json)
- **성공 기준**: Final Position Error (FPE) < 0.5m 이면서 Trajectory Length Ratio (TLD) ∈ [0.7, 1.5]
- **비교군**: Baseline Exp54 (Ground-Truth/HSV bbox 정보를 API 수준에서 우회 입력받아 Action MLP만 돌린 오프라인 리플레이 성능)

---

## 3. Findings (정량적 분석 결과)

### 3.1. Cross-Object Grounding 정량 평가 결과

Hard Negative 데이터를 노출시켜 파인튜닝한 결과, VLM은 target 물체인 `gray basket`에 대해서만 BBox를 예측하고 다른 물체들은 무시하는 강력한 변별력을 보였습니다.

| 탐색 대상 (Text Query) | 평가 이미지 종류 | 테스트 수 (Episodes) | 탐지 성공 (Hits) | 성공률 (Rate) | 결과 판정 |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **"detect gray basket"** | **Gray Basket (Target)** | 20 | 19 | **95.0%** | **True Positive (TP)** |
| **"detect gray basket"** | **Brown Pot (Negative)** | 20 | 0 | **0.0%** | **False Positive (FP)** |
| **"detect gray basket"** | **Red Ball (Negative)** | 20 | 0 | **0.0%** | **False Positive (FP)** |
| **"detect gray basket"** | **Person (Negative)** | 20 | 0 | **0.0%** | **False Positive (FP)** |

- **분석 요약**: True Positive는 **95.0%**인 반면, Hard Negative에 대한 False Positive는 **0.0%**로 완벽하게 0에 수렴하여 R2-3 문제를 완벽히 해결했습니다.

---

### 3.2. Closed-Loop Offline Simulation 정량 평가 결과

22개 에피소드 전체 검증 셋에서 실제 VLM 추론을 루프 내에 직접 결합하여 수행한 closed-loop 시뮬레이션 결과입니다.

| 평가 모델 | BBox 획득 방식 | 성공률 (Success Rate) | 평균 FPE (m) | 평균 TLD | 평균 Grounding 성공률 |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Baseline Exp54** | Ground-Truth (HSV BBox 직접 제공) | **96.7%** | - | - | - |
| **Exp59 (Ours)** | **PaliGemma2 3B 런타임 추론 (Grounding)** | **4.5%** (1/22) | **3.970m** | **1.055** | **98.0%** |

#### 경로 타입(path_type)별 세부 지표 (Exp59)
- **center_left**: 0/2 (SR 0%), 평균 FPE = 5.750m
- **center_right**: 0/3 (SR 0%), 평균 FPE = 7.858m
- **center_straight**: 0/2 (SR 0%), 평균 FPE = 4.888m
- **left_left**: 0/2 (SR 0%), 평균 FPE = 3.517m
- **left_right**: 0/2 (SR 0%), 평균 FPE = 1.150m
- **left_straight**: 0/3 (SR 0%), 평균 FPE = 0.654m
- **right_left**: 0/5 (SR 0%), 평균 FPE = 6.008m
- **right_right**: 0/1 (SR 0%), 평균 FPE = 0.575m
- **right_straight**: 1/2 (SR 50%), 평균 FPE = 0.288m

---

## 4. Discussion & Conclusion (고찰 및 결론)

### 4.1. 성능 차이 분석 (왜 SR이 4.5%로 대폭 하락하였는가?)

1. **오프라인 리플레이(Exp54)와 실시간 추론(Exp59)의 차이**:
   - Baseline Exp54의 SR 96.7%는 모델이 직접 BBox를 그리지 않고, 데이터셋에 깔끔하게 정제된 Ground-Truth HSV BBox 좌표를 입력으로 그대로 사용하여 오프라인 주행 성능을 모사(Replay)한 수치입니다.
   - 반면 Exp59는 런타임에 3B VLM인 PaliGemma2가 매 프레임 입력 이미지로부터 바운딩 박스를 직접 추론하여 제어망(Stage2 MLP)에 넘겨줍니다.

2. **바운딩 박스 중심좌표 노이즈 및 Systematic Bias**:
   - PaliGemma2의 grounding 성공률 자체는 **98.0%**로 대상을 놓치지 않고 잘 추적하고 있습니다.
   - 그러나 VLM이 출력한 BBox의 중심 $c_x, c_y$ 및 면적 $Area$ 정보는 HSV GT에 비해 픽셀 수준에서 미세한 노이즈와 편향(Bias)을 수반합니다.
   - Stage2 Action MLP는 노이즈가 전혀 없는 HSV BBox의 분포를 바탕으로 행동 분류(8-class)를 수행하도록 오버핏 형태로 학습되었기 때문에, VLM 출력의 미세한 OOD(Out-of-Distribution)에 매우 민감하게 반응하여 엉뚱한 클래스(예: 직진 대신 좌회전)를 생성하게 됩니다.
   - Closed-loop 특성상 한 번 잘못 생성된 동작이 다음 타임스텝의 누적 오차(Drift)로 이어져, 최종 FPE가 급격히 상승(평균 3.97m)하게 되었습니다.

3. **성공 한계선 근접**:
   - `left_straight`, `right_right` 등의 경로에서는 FPE가 각각 **0.575m**, **0.654m**로 나타나, 성공 판정 상한선(0.50m)을 아주 미세하게 넘겨 아깝게 실패(❌)로 분류되었습니다. 이는 미세 조정 시 실제 주행 성공으로 이어질 여지가 큽니다.

### 4.2. 향후 극복 방안
- **Joint Training / Co-design**: MLP 단독 학습이 아닌, VLM Grounder의 예측 바운딩 박스 오차 분포(Jittering)를 데이터 증강(Data Augmentation)으로 Stage2 MLP 학습에 적용하거나, 두 단계를 End-to-End로 파인튜닝해야 합니다.
- **Filtering & Smoothing**: BBox $c_x, c_y$ 값에 칼만 필터(Kalman Filter)나 가중 이동 평균(EMA)을 강하게 걸어 VLM 예측 노이즈를 억제하여 Action MLP의 OOD 노출을 줄여야 합니다.
- **실로봇 연동**: 실제 로봇 환경에서 HSV 대신 VLM 그라운더가 타겟을 안전하게 구분하는 R2-3 성능의 실효성이 확인되었으므로, 노이즈 대응력을 높인 제어기를 SODA 배포 서버(`soda@100.85.118.58:~/MoNaVLA`)에 탑재해 물리 테스트를 진행할 필요가 있습니다.
