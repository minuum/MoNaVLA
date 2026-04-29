# V5 Exp10: Next-Token Prediction BBox (Grounding) Report

## 1. Background
기존 Mobile VLA (Exp01-Exp09)는 **액션 회귀(Action Regression)** 또는 **Discrete Classification**에 집중해 왔습니다. 
Exp10의 목표는 VLM 본연의 기능인 **Next-Token Prediction**을 활용하여 시각적 객체(바구니)의 위치를 Bounding Box 형태로 출력하는 **Grounding** 능력을 학습하는 것입니다.

이 실험은 특히 **Track 2 (Navigation/Grounding)** 성능 향상을 위해 설계되었습니다.

## 2. Implementation Details

### Model Architecture
- **Backbone**: RoboKosMos (Kosmos-2 based)
- **Training Strategy**: `predict_caption: true` 모드를 활성화하여 언어 모델의 Cross-Entropy Loss (`loss_vl`)를 학습에 반영하도록 수정하였습니다.
- **Ratios**: `vl_cotrain_ratio: 1.0`, `cap_loss_ratio: 1.0` (VLM Loss 비중 상향)

### Data Preparation
- **Dataset**: `MobileVLAH5Dataset` (V5)
- **BBox Heuristic**: OpenCV를 사용하여 `grayscale` 및 `reddish` 영역(바구니)의 최대 윤곽선을 찾아 BBox를 생성합니다.
- **Target Format**: Kosmos-2의 정규화된 `32x32` 패치 인덱스 형식을 따릅니다.
  - 형식: `<box_2d><patch_index_XXXX><patch_index_YYYY></box_2d>`

## 3. Training Config
- **Path**: `configs/mobile_vla_v5_exp10_bbox.json`
- **Batch Size**: 4
- **Window Size**: 1 (단일 프레임 Grounding 집중)
- **Learning Rate**: 2e-5

## 4. Evaluation Strategy
BBox 예측 정확도를 정량적으로 평가하기 위해 IoU (Intersection over Union) 메트릭을 도입할 예정입니다.
- **Script**: `scripts/test/eval_v5_exp10_bbox_grounding.py` (신규 작성)
- **Metric**: IoU 0.5 이상의 성공률 (Success Rate @ IoU 0.5)

---

## Current Status
- [x] `base_backbone.py` 수정 (VLM Loss 활성화)
- [x] `base_trainer.py` 수정 (caption_labels 전달 로직 개선)
- [x] `configs/mobile_vla_v5_exp10_bbox.json` 생성 및 최적화
- [ ] 학습 시작 (Scheduled)
- [ ] Evaluation 스크립트 작성 및 0-epoch 검증
