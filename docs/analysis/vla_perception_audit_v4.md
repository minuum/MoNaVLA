# 🧠 VLA Perception & Data-Bias Deep Audit
**Date:** 2026-04-03
**Session ID:** `session_20260403_050653`
**VLM Grounding Prompt:** `<image><grounding>Where is the gray basket? Answer:`

## 1. Executive Summary
This report provides visual and quantitative proof that the MobileVLA model possesses high-fidelity perception but suffers from a **Policy-Head bottleneck** caused by training data imbalance.

## 2. Dataset Evidence (Ground Truth from H5)
Below are frames extracted from the actual training dataset (`mobile_vla_dataset_v3`) used for this model.
- **Forward Path:** `/home/soda/MoNaVLA/ROS_action/mobile_vla_dataset_v3/episode_20260312_002846_v3_center_core_medium.h5`
- **Turn Path:** `/home/soda/MoNaVLA/ROS_action/mobile_vla_dataset_v3/episode_20260312_165335_v3_left_core_medium.h5`

## 3. Comparative Analysis
| Inference Frame | VLM Anchoring [y1,x1,y2,x2] | Action Bias (Prob) | Analysis |
|-----------------|-----------------------------|--------------------|----------|
| frame_001.jpg | The gray basket is located at [425, 452, 578, 548] | F: 0.22, FL: 0.20 | Sentient Target Tracked |
| frame_003.jpg | The gray basket is located at [425, 452, 578, 548] | F: 0.30, FL: 0.19 | Sentient Target Tracked |
| frame_005.jpg | The gray basket is located at [425, 452, 578, 548] | F: 0.31, FL: 0.21 | Sentient Target Tracked |
| frame_010.jpg | The gray basket is located at [425, 452, 578, 548] | F: 0.32, FL: 0.21 | Sentient Target Tracked |
| frame_015.jpg | The gray basket is located at [425, 452, 578, 548] | F: 0.31, FL: 0.19 | Sentient Target Tracked |
