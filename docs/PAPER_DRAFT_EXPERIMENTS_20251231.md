# Experiments

We evaluate Mobile VLA on two main criteria: **Control Performance** (Accuracy) and **Deployment Efficiency** (Resource usage).

## 1. Experimental Setup

- **Hardware**: NVIDIA RTX A5000 (24GB VRAM) for training and initial evaluation.
- **Target Edge Device**: NVIDIA Jetson Orin Nano (16GB RAM) simulation (constrained resources).
- **Baselines**:
    - **Random Agent**: Samples actions uniformly from the action space.
    - **RoboVLMs (Qwen-VL 7B)**: The original heavy baseline model.

## 2. Quantitative Results

### 2.1 Action Chunking Analaysis

We compared two action chunk sizes, $k=5$ and $k=10$, to determine the optimal horizon for mobile navigation. Table 1 presents the validation results.

**Table 1: Action Chunking Performance**

| Model | Chunk Size | Val Loss (MSE) | RMSE | Best Epoch |
|-------|:----------:|:--------------:|:----:|:----------:|
| Mobile VLA | **5** | **0.067** | **0.259** | 6 |
| Mobile VLA | 10 | 0.284 | 0.533 | 5 |

**Findings**:
- **Chunk 5 outperforms Chunk 10** significantly, achieving **76% lower validation loss** (0.067 vs 0.284).
- Shorter horizons ($k=5$) allow the model to adapt more quickly to potential path deviations, whereas longer horizons ($k=10$) accumulate errors in the highly dynamic mobile base control.
- [Insert Figure 1: Training Curves Comparison] shows that Chunk 5 converges to a stable minimum at Epoch 6, while Chunk 10 exhibits higher variance and fails to minimize loss effectively.

### 2.2 Comparison with Baselines

We benchmarked Mobile VLA (Chunk 5) against a Random Baseline to verify learning validity.

| Model | RMSE | Improvement |
|-------|:----:|:-----------:|
| Random Baseline | 0.576 | - |
| **Mobile VLA** | **0.259** | **55%** $\downarrow$ |

Mobile VLA demonstrates a **55% reduction in RMSE** compared to random actions, confirming that the model has successfully learned the goal-directed navigation policy from the 500-episode dataset.

### 2.3 Resource Efficiency & Edge Deployment

A key contribution of this work is the feasibility of deploying VLA models on edge devices. We analyzed GPU memory usage and inference latency across different configurations.

**Table 2: Comprehensive Performance Matrix**

| Model Config | Quantization | Val Loss | GPU Mem | Latency | Speedup |
|:---:|:---:|:---:|:---:|:---:|:---:|
| **RoboVLMs (7B)** | FP32 | - | ~14.0 GB | ~15.0s | 1x |
| **Mobile VLA (1.6B)** | FP32 | 0.067 | 6.3 GB | 15.0s* | 1x |
| **Mobile VLA (1.6B)** | **INT8** | **~0.067** | **1.8 GB** | **0.49s** | **30x** |

*\*FP32 latency on unoptimized pytorch code*

**Findings**:
- **87% Memory Reduction**: Compared to the 7B RoboVLMs (14GB), Mobile VLA with INT8 quantization uses only **1.8GB** of VRAM.
- **30x Speedup**: INT8 quantization combined with the smaller backbone reduces inference latency from 15s to **495ms** (approx. 2.0 Hz), making real-time control feasible.
- [Insert Figure 2: GPU Memory & Speed Comparison] visually highlights the drastic reduction in resource requirements, validating applicability for Jetson Orin Nano (16GB).

## 3. Dataset Analysis

The model was trained on a dataset of 500 episodes (9,000 actions).
- **Class Balance**: 250 Left / 250 Right episodes, ensuring unbiased turning behavior.
- **Action Stats**: The model learned to maintain a constant forward velocity (`linear_x` $\approx$ 1.0 m/s) while modulating steering (`linear_y`) to avoid obstacles.

[Insert Figure 3: Dataset Statistics] illustrates the balanced distribution and the focused action space required for the task.
