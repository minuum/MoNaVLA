# V3-EXP-01 Training Log Analysis Report

**작성일**: 2026-02-19  
**분석 대상**: v3-exp01-aug (Classification + Augmentation)  
**상태**: ✅ 학습 완료 (Epoch 6 Early Stop)

## 1. Background
V3-EXP-01 실험은 기존 V2의 Regression 방식에서 벗어나 **Classification Head**를 도입하고, **Color Jitter 및 Random Crop과 같은 Data Augmentation**을 적용하여 모델의 강건성(Robustness)과 인지 성능을 높이는 것을 목적으로 수행되었습니다.

- **주요 설정**:
  - Task: v3_classification
  - Augmentation: Color Jitter, Random Crop
  - Head: Classification (Discrete Action Space)

## 2. Analysis
Training Log (`logs/train_v3_exp01_aug.log`) 분석 결과, 총 7개 Epoch(0~6)가 진행되었으며, validation loss 기반의 Early Stopping에 의해 종료되었습니다.

### 📊 Epoch별 주요 메트릭 변화
| Epoch | Best Val Loss | Val Acc (Velocity) | Val RMSE  | Status         |
| :---: | :-----------: | :----------------: | :-------: | :------------- |
|   0   |     0.943     |       76.6%        |   0.823   | Improved       |
|   1   |     0.802     |       83.0%        |   0.737   | Improved       |
|   2   |     1.140     |       79.2%        |   0.883   | -              |
| **3** |   **0.455**   |     **88.6%**      | **0.499** | **Best Score** |
|   4   |     0.601     |       87.8%        |   0.573   | Degradation    |
|   5   |     1.090     |       84.4%        |   0.935   | Degradation    |
|   6   |     0.539     |       88.4%        |   0.542   | Stopped        |

## 3. Findings
1.  **최고 성능 도달**: Epoch 3에서 **Validation Accuracy 88.6%**, **Validation Loss 0.455**로 최고 성능을 기록했습니다. 
2.  **Overfitting 징후**: Epoch 3 이후 Training Loss는 지속적으로 하락하여 약 `8e-5` 수준까지 도달했으나, Validation Loss는 심하게 출렁이며(0.601 -> 1.090 -> 0.539) 전반적으로 우상향하는 경향을 보였습니다. 이는 모델이 증강된 데이터에 과적합되었을 가능성을 시사합니다.
3.  **Classification의 가능성**: 이전에 실패했던 EXP-11(Discrete)과 달리, 이번 V3-EXP-01에서는 88% 이상의 정확도를 확보하며 Classification 방식이 VLA 모델에서 유효하게 작동함을 확인했습니다.

## 4. Comparison with V2 Baseline
V2의 최고 성능 모델인 EXP-17(Regression)과 비교한 결과입니다.

| Metric          | V2 EXP-17 (Best)          | V3-EXP-01 (Current)        | Difference                  |
| :-------------- | :------------------------ | :------------------------- | :-------------------------- |
| **Approach**    | Regression                | Classification             | -                           |
| **Config**      | Win 8, Chunk 1            | Win 6 (est.), Augmentation | -                           |
| **Performance** | **94.72% (Success Rate)** | **88.6% (Val Acc)**        | -6.12%p (Simple comparison) |

*참고: Success Rate와 Validation Accuracy는 직접 비교가 어려우나, 88.6%의 정확도는 추론 테스트 시 90% 내외의 Success Rate를 보일 것으로 예상되는 양호한 수치입니다.*

## 5. Conclusion & Next Steps
- **결론**: V3-EXP-01은 Classification 방식이 성공적으로 동작함을 입증했으나, Epoch 3 이후 급격한 과적합이 발생했습니다. Augmentation의 강도 조절이나 Regularization 강화가 필요해 보입니다.
- **권장 사항**:
  1.  **Epoch 3 체크포인트**를 사용하여 실제 로봇(또는 시뮬레이션) 추론 테스트 수행.
  2.  V2 EXP-17의 성공 요인인 **Window 8** 설정을 V3 Classification 모델에 이식하여 성능 향상 도모.
  3.  Augmentation이 Validation Loss 변동성에 미치는 영향 추가 분석.

---
**Reported by**: Antigravity (AI Coding Assistant)  
**Source Path**: `/home/billy/25-1kp/vla/logs/train_v3_exp01_aug.log`
