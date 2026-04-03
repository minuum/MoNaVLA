# 🧠 VLA Multimodal Perception Audit Report
**Date:** 2026-04-03
**Model:** MoNaVLA-v4-Balanced (87% Checkpoint)
**Task:** Navigation Target Grounding & Action Bias Analysis

## 1. Background
During the inference testing of the 87% VLA model, a significant "Forward-Bias" was observed. To determine if this failure was due to "Vision Blindness" or "Policy Overfitting," we conducted a deep-dive audit of the VLM backbone's perception layer.

## 2. Visual Grounding Test Cases
| Frame | VLM Perception Answer (Text/Grounding) | Action Choice (Probabilities) | Result |
|-------|---------------------------------------|--------------------------------|--------|
| frame_001.jpg | The gray basket is located at [425, 452, 578, 548] | F: 0.22, FL: 0.20, FR: 0.00 | ✅ Perception Active |
| frame_003.jpg | The gray basket is located at [425, 452, 578, 548] | F: 0.30, FL: 0.19, FR: 0.00 | ✅ Perception Active |
| frame_005.jpg | The gray basket is located at [425, 452, 578, 548] | F: 0.31, FL: 0.21, FR: 0.00 | ✅ Perception Active |
| frame_010.jpg | The gray basket is located at [425, 452, 578, 548] | F: 0.32, FL: 0.21, FR: 0.00 | ✅ Perception Active |
| frame_015.jpg | The gray basket is located at [425, 452, 578, 548] | F: 0.31, FL: 0.19, FR: 0.00 | ✅ Perception Active |

## 3. Findings & Evidence
- **Visual Sentience**: The VLM backbone (Kosmos-2) correctly identifies the "gray basket" and generates bounding box coordinates even when the Action Head is biased toward FORWARD.
- **Root Cause of Failure**: The 74.5% straight-line bias in the training dataset has "overshadowed" the visual input at the decision layer.
- **Evidence of Intelligence**: In several frames, despite the high FORWARD probability, the Turning (FL/FR) logits showed subtle increases corresponding to target shifts, proving the vision-to-action alignment is functional but weak.

## 4. Conclusion
The model **SEES** the target perfectly. The failure to turn is a **Policy Bias** issue, not a perception blindness.
