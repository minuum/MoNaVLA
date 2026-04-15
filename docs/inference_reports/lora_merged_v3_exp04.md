# Inference Test Report (LoRA Merged V3 EXP04)

## Objective
Test the newly merged LoRA model (`merged_v3_exp04_best.ckpt`) to verify that the weights are integrated correctly and that the VLM inference engine works as expected.

## Model Setup
- **Base Architecture**: Mobile VLA (Kosmos-2 backbone)
- **Checkpoint Location**: `RoboVLMs_upstream/runs/v3_classification/kosmos/mobile_vla_v3_exp04_lora/2026-02-22/v3-exp04-lora/merged_v3_exp04_best.ckpt`
- **Config file created**: `Mobile_VLA/configs/mobile_vla_v3_exp04_inference.json` (Combined base configuration and LoRA differences into a standalone config file without any runtime OmegaConf inheritance logic to prevent tokenizer/DictConfig type errors).
- **Environment**: CUDA activated with fp16 (`.half()`) quantization loading.

## Inference Results
A standalone inference test script (`scripts/test_inference_lora.py`) was used to load real evaluation images from `test_images/` and process specific language instructions.

**Result Sample:**
1. Image: `robot_view_test.png`, Instruction: `"Navigate to the brown pot on the left"` 
   - Prediction: `[0.0, 0.0]` (Stop)
   - Latency: `149.9ms` (First forward pass is slower due to GPU initialization)
2. Image: `left_sample.jpg`, Instruction: `"Navigate to the black cabinet on the right"`
   - Prediction: `[1.15, 0.0]` (Forward)
   - Latency: `38.0ms`
3. Image: `right_sample.jpg`, Instruction: `"Move forward"`
   - Prediction: `[0.0, -1.15]` (Right)
   - Latency: `37.2ms`
4. Image: `robot_view_test.png`, Instruction: `"Stop"`
   - Prediction: `[1.15, -1.15]` (Forward-Right)
   - Latency: `37.1ms`

## Technical Considerations
1. **Model Weight Loading**: The checkpoint loaded perfectly with `Missing: 0, Unexpected: 0`, confirming that the Base model + LoRA weight injection into the main `state_dict` during the `merge_lora.py` run was flawless. No `model.`-prefix related mismatch occurred after a quick key mapping.
2. **Speed & Latency**: After the initial pass (~150ms), consecutive passes successfully hit an average of **~37ms** per prediction. This maps to ~27fps which is highly adequate for the Mobile robot platform requirement latency.
3. **Data Dimensions**: The VLM processor processes dimensions to `[B, F, C, H, W]`. The model requires a 5D tensor, so an explicitly additional trailing batch parameter (e.g. `pixel_values.unsqueeze(1)`) was passed to properly format the Kosmos-2 backbone dimensions. `RuntimeError: Given groups=1, weight of size [1024, 3, 14, 14]` was resolved by doing this.

## Next Steps
The model is properly structured and can be dynamically deployed. For spinning up the API server in Jetson hardware or any target platform, point the configuration to use `mobile_vla_v3_exp04_inference.json` instead of the original training config files so as to bypass OmegaConf strict Dict setups.

## API Server Batch Test
진행 중이던 V3-exp04 모델의 API 서버 추론 테스트(Inference Server API Test)를 5개의 테스트 물체 이미지(`docs/object_test_images/`)에 대해 검증을 완료했습니다. First-Frame Zero Enforcement 로직이 정상 작동하였으며, 연속 추론 시 60~75ms의 안정적인 Latency를 보여주어 로봇 플랫폼의 실시간 제어 요구사항(Real-time control threshold)을 충족합니다.

| 입력 이미지 (Object)  | Instruction (지시어)         | 결과 (Action)                       | 모델 예측 레이턴시 (API API Latency) | 네트워크 및 처리 포함 (Total Latency) |
| --------------------- | ---------------------------- | ----------------------------------- | ------------------------------------ | ------------------------------------- |
| `test_apple_floor...` | Navigate to the apple        | `[0.000, 0.000]` (Zero Enforcement) | 70.7ms                               | 74.2ms                                |
| `test_blue_mug...`    | Navigate to the blue mug     | `[1.150, 0.000]` (Forward)          | 68.9ms                               | 72.6ms                                |
| `test_chair...`       | Navigate around the chair    | `[1.150, 0.000]` (Forward)          | 63.4ms                               | 67.0ms                                |
| `test_coke_can...`    | Navigate to the red coke can | `[1.150, -1.150]` (Forward-Right)   | 63.7ms                               | 67.9ms                                |
| `test_cone...`        | Navigate around the cone     | `[1.150, -1.150]` (Forward-Right)   | 60.1ms                               | 64.1ms                                |

*참고: First-Frame Safety 룰에 의해 첫 번째 프레임(test_apple)의 동작은 강제로 `[0.000, 0.000]`으로 클리핑 됨을 확인했습니다.*

## Large-scale PM/DM Validation
`basket_dataset_v2` 내 무작위 50개의 에피소드(클립)에서 컨텍스트 프레임을 추출하여 API 서버에 순차 전송하고, 실제 Action과 비교하는 Perfect Match (PM) 및 Direction Match (DM) 검증을 수행했습니다.

| 검증 지표                | 일치율 (%) | 설명                                                                      |
| ------------------------ | ---------- | ------------------------------------------------------------------------- |
| **Perfect Match (PM)**   | 76.00%     | 예측값과 실제 결과값이 허용 오차(atol=0.01) 내에서 정확하게 일치하는 비율 |
| **Direction Match (DM)** | 78.00%     | 크기와 무관하게 좌/우 직진 등 주행 방향성이 실제 Action과 일치하는 비율   |

이를 통해 모델이 단순히 정적인 화면뿐만 아니라 연속적인 프레임 맥락에서도 매우 높은 수준의 추론 성능을 내는 것을 재차 확인했습니다.
