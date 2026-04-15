# 📊 VLA V3 학습 현황 및 실험 이력 보고서

## 1. 개요
본 보고서는 Vision-Language-Action (VLA) 모델의 Phase 2 (Regression)에서 Phase 3 (Classification)으로의 전환 과정과 현재 V3-EXP-01의 학습 결과 및 향후 계획을 요약합니다.

## 2. 실험 이력 요약 (Phase 2 -> Phase 3)

| 실험 ID              | 주요 설정                                           | 결과/성능         | 주요 인사이트                                                  |
| :------------------- | :-------------------------------------------------- | :---------------- | :------------------------------------------------------------- |
| **EXP-17 (V2)**      | Window 8, Regression, No Aug                        | **94.72% (Best)** | Window 8이 모델 반응성에 최적임을 확인 (PM/DA 1위)             |
| **V3-EXP-01**        | Window 8, Classification, Aug(Jitter/Crop), LR 5e-5 | Val Acc 88.6%     | Classification 방식의 유효성 확인. 단, 에폭 4 이후 과적합 징후 |
| **V3-EXP-02 (Plan)** | Window 8, Classification, No Aug, **LR 1e-4**       | -                 | EXP-17의 성공 하이퍼파라미터를 V3에 이식하여 베이스라인 재정립 |

## 3. V3-EXP-01 학습 상세 분석
- **최적 지점**: Epoch 3 (Validation Loss: 0.455, Accuracy: 88.6%)
- **현상**:
  - Epoch 4 이후 Train Loss는 지속적으로 감소하나 Validation Loss가 상승하는 전형적인 **과적합(Overfitting)** 발생.
  - 적용된 강한 Augmentation(Color Jitter, Random Crop)이 학습 초기에는 도움이 되었으나, 데이터셋 규모 대비 복잡도를 높여 수렴을 방해했을 가능성 존재.
- **조치**: 가장 성능이 좋은 Epoch 3 체크포인트를 별도 보관 및 추론 서버용으로 준비.
  - 경로: `RoboVLMs_upstream/runs/v3_classification/kosmos/mobile_vla_v3_classification/2026-02-19/v3-exp01-aug/epoch_epoch=03-val_loss=val_loss=0.455.ckpt`

## 4. 향후 계획 및 변화 과정
1. **성공 요인 이식 (V3-EXP-02)**:
   - V2 최상위 모델인 EXP-17의 설정(`LR 1e-4`, `Accumulate 8`, `No Aug`)을 V3 Classification 모델에 적용.
   - Augmentation이 배제된 환경에서의 Classification 성능 순수 비교 진행.
2. **Resampler 통합**:
   - 향후 실험에서 EXP-12의 강점이었던 Vision Resampler를 결합하여 시각 정보 효율화 도모.
3. **체크포인트 관리**:
   - 우수 체크포인트를 원격 서버(`soda@100.85.118.58`)로 전송하여 실로봇 테스트 대기.

## 5. 진행 중인 이슈
- **샌드박스 설정 오류**: 에이전트 실행 환경 내의 `sandbox-exec` 부재로 인해 Git push 및 스크립트 실행이 제한됨. 해당 작업은 사용자 터미널에서 수동 실행 권장.

---
*최종 업데이트: 2026-02-20*
*작성자: Antigravity*
