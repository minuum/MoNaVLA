# V5-Exp09: 8-Class Discrete Navigation Analysis Report

## 1. Background
본 실험(Exp09)은 로봇 내비게이션 환경에서 VLM이 이산적인 액션 클래스(8종)를 예측하는 성능을 평가하고, 특히 **목표 지향적 명령어(Center-goal instruction)**가 행동 예측의 정확도 및 grounding 성능에 미치는 영향을 분석합니다.

## 2. Configuration Summary

| 항목 (Parameter) | 설정값 (Value) | 설명 (Description) |
| :--- | :--- | :--- |
| **Core Architecture** | RoboKosMos (KosMos-2 + LoRA) | LoRA r=32, target: all linear layers |
| **Action Space** | 8-Classes Discrete | Forward, L, R, FL, FR, Stop, Turn-L/R |
| **Prediction Window** | 3 (fwd_pred_next_n) | 미래 3개 스텝 동시 예측 |
| **Context Window** | 8 frames | 과거 히스토리 8프레임 참조 |
| **Task Instruction** | Center-goal aware | "Navigate until centered in the frame" |

## 3. Action Mapping & Weights

| ID | 라벨 (Label) | 결정 로직 (lx, ly, az) | Class Weights |
| :---: | :--- | :--- | :---: |
| 0 | Stop | lx=0, ly=0, az=0 | 5.0 |
| 1 | Forward | lx>0, ly=0, az=0 | 1.0 |
| 2 | Left | lx>0, ly>0 (lateral) | 10.0 |
| 3 | Right | lx>0, ly<0 (lateral) | 10.0 |
| 4 | Diag-FL | Forward + Left combo | 5.0 |
| 5 | Diag-FR | Forward + Right combo | 5.0 |
| 6 | Turn-Left | az > 0 (Rotation) | 15.0 |
| 7 | Turn-Right | az < 0 (Rotation) | 15.0 |

## 4. Inference Methodology

모델의 실제 추론 과정은 다음과 같은 파이프라인으로 구성됩니다:

1. **Input Stage**:
   - `Image`: 8프레임 히스토리 이미지를 채널 방향으로 결합하지 않고 시퀀스로 처리 (Vision Tower 인코딩).
   - `Language`: `instruction_override`를 통해 고정된 명령어를 주입하여 변동성을 최소화.
   - `Format`: `"<grounding>Instruction: {instruction}. Action:"`

2. **Processing Stage**:
   - **Backbone**: Vision-Language-Action 정보를 Cross-attention으로 융합.
   - **Policy Head**: `MobileVLAClassificationDecoder` (LSTM 기반) 가 히스토리 정보를 요약하여 8개 클래스에 대한 Logits 출력.
   - **Windowing**: `fwd_pred_next_n=3` 설정을 통해 시계열적 일관성 강제.

3. **Output Stage**:
   - 예측된 미래 3스텝 중 **첫 번째 스텝(index 0)**의 argmax 값을 최종 액션으로 결정.

## 5. Result Verification (Sample)

| Metric | Value | 비고 |
| :--- | :--- | :--- |
| **Ground Truth** | Forward (Class 1) | 실제 데이터셋 레이블 |
| **Prediction** | Forward (Class 1) | 모델 예측 결과 |
| **Confidence** | **76.6%** | Softmax 확률값 |
| **Result** | **CORRECT** | 입출력 로직 검증 완료 |

---
**작성일**: 2026-04-15  
**실험 담당**: Antigravity AI
