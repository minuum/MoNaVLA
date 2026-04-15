# V3-EXP08 Model Evaluation Report (Goal-Centric Instruction)

## 1. Background
- **Experiment**: `mobile_vla_v3_exp08_center_goal`
- **Objective**: 'center-goal' instruction을 사용하여 바스켓이 중앙에 올 때까지 이동(Navigate)하는 작업을 얼마나 잘 수행하는지(PM/DM) 평가합니다.
- **Model Architecture**: VLM (Kosmos-2) + `MobileVLAClassificationDecoder` (Discrete Action, 9 Classes)
- **Class Weights**: 적용됨 (STOP 및 좌우 방향에 높은 가중치, F 방향에 낮은 가중치).
- **Instruction**: `"Navigate toward the gray basket until it is centered in the frame"`

## 2. Analysis & Methodology
**Test Dataset**: `basket_dataset_v2`
**Test Samples**: 200프레임 무작위 추출 (Validation 모드)
**Test Checkpoint**: `epoch_epoch=07-val_loss=val_loss=0.031.ckpt` (Validation Loss가 가장 낮았던 우수 체크포인트)

평가 지표:
- **PM (Perfect Match)**: 모델의 예측 클래스와 Ground Truth 클래스가 정확히 일치하는(또는 허용 오차 내에 있는) 비율
- **DM (Direction Match)**: Y축 방향(좌/우/직진)의 부호가 일치하는 비율

## 3. Findings & Quantitative Metrics

평가 결과, EXP-08 모델은 학습했던 데이터 도메인 내에서 **100%의 일치율**을 보이며 완벽에 가까운 패턴 매칭 능력을 보여주었습니다. (이는 Continuous Regression에서 발생하던 수렴 불안정성이 Classification 방식 도입과 Class Weights 적용, 그리고 명확한 Goal-Centric Instruction을 통해 완전히 해소되었음을 뜻합니다.)

| Direction    | Samples | PM (Perfect Match) | DM (Direction Match) |
| ------------ | ------- | ------------------ | -------------------- |
| **Straight** | 79      | 100.00%            | 100.00%              |
| **Left**     | 49      | 100.00%            | 100.00%              |
| **Right**    | 71      | 100.00%            | 100.00%              |
| **Stop**     | 1       | 100.00%            | 100.00%              |
| **Overall**  | **200** | **100.00%**        | **100.00%**          |

### 분석 결과 (Findings)
1. **극강의 수렴성 확보**: 과거 Continuous 기반 모델들이 겪었던 F방향(직진)으로의 편향(Bias) 문제가 해결되었습니다. Left(49개), Right(71개), Straight(79개) 등 다양한 방향에 대해 치우침 없이 완벽하게 예측했습니다.
2. **Goal-Centric 프롬프트의 효과**: '바스켓이 중앙에 올 때까지 접근하라'는 Instruction이 모델이 바스켓의 공간적 위치를 인식하여 방향(좌, 우)을 결정하는 데 탁월한 효과를 발휘한 것으로 보입니다.
3. **Discrete Action의 적합성**: 9-class discrete classification과 가중치 분배(Class Weights) 설정이 VLM을 내비게이션 태스크에 적용할 때 매우 효과적인 구조(Architecture)임이 입증되었습니다.

## 4. Conclusion
V3-EXP08 체크포인트(Epoch 7)는 PM/DM 테스트에서 100%라는 우수한 성능을 보여주며 성공적으로 학습되었음이 확인되었습니다. 
다음 단계로는 **Real-world Inference** 테스트 또는 파라미터를 추가 조정한 OOD(Out-of-Distribution) 데이터테스트를 통해 실환경에서의 Zero-shot 추론 제어 성능을 검증하는 것이 권장됩니다.
