# Mobile VLA: Lightweight Vision-Language-Action Model for Edge Robotic Deployment

## Abstract
We present **Mobile VLA**, a resource-efficient Vision-Language-Action model designed for deploying versatile robotic policies on constrained edge devices. Existing VLA models, typically built on 7B+ parameter backbones, require prohibitive computational resources (e.g., >14GB VRAM), making them unsuitable for mobile robots with limited hardware. By leveraging the compact **Kosmos-2 (1.6B)** backbone and applying **BitsAndBytes INT8 quantization**, we achieve an **87% reduction in GPU memory** (1.8GB) and a **30x improvement in inference speed** (2.0 Hz) compared to standard 7B baselines. Our model, trained on 500 navigation episodes with efficient action chunking ($k=5$), achieves a validation loss of 0.067, demonstrating that lightweight VLAs can maintain competitive control performance while enabling real-time operation on devices like the NVIDIA Jetson Orin Nano.

---

## 1. Introduction

Vision-Language-Action (VLA) models have emerged as a powerful paradigm for general-purpose robotic control, enabling robots to understand multimodal instructions and execute complex tasks. However, state-of-the-art models such as RT-2 and OpenVLA typically rely on massive Language Model backbones (e.g., LLaMA-7B, Qwen-7B), which present significant barriers for deployment:

1.  **High Memory Footprint**: 7B models in FP16 require ~14GB of VRAM, saturating or exceeding the capacity of standard edge accelerators (e.g., Jetson Orin Nano 8GB/16GB).
2.  **Slow Inference**: Large backbones often yield inference rates below 1 Hz on edge hardware, insufficient for dynamic closed-loop control.

To bridge this gap, we propose **Mobile VLA**. Our approach replaces the heavy backbone with **Kosmos-2 (1.6B)**, a multimodal model pre-trained on grounded image-text pairs, and employs aggressive yet accurate **INT8 quantization**. We further optimize control performance through **Action Chunking**, mitigating temporal inconsistencies.

Our contributions are:
- A **lightweight architecture** (1.6B) specifically tailored for edge deployment.
- A valid **quantization pipeline** achieving 1.8GB memory usage with negligible accuracy loss.
- Extensive experiments showing **76% better performance** with short-horizon chunking ($k=5$).

---

## 2. Method

*(See `PAPER_DRAFT_METHOD_20251231.md` for full details)*

### 2.1 Model Architecture
Mobile VLA utilizes the **Kosmos-2** backbone (1.6B parameters). A specialized MLP-based **Action Head** is attached to predict continuous 2-DOF actions (`linear_x`, `linear_y`) directly from multimodal embeddings, avoiding the latency of autoregressive token generation.

### 2.2 Efficient Quantization (INT8)
We apply **Post-Training Quantization (PTQ)** via BitsAndBytes. By converting weights to INT8 and using mixed-precision decomposition for outliers, we reduce model size from 6.3GB (FP32) to **1.8GB (INT8)**. This is critical for fitting the model alongside ROS 2 middleware and sensor drivers on a 16GB shared-memory architecture.

### 2.3 Action Chunking
We employ a receding horizon control strategy with a chunk size $k$. The model predicts $k$ future actions at each step. We experimentally determine $k=5$ to be optimal for our mobile navigation task.

---

## 3. Experiments

*(See `PAPER_DRAFT_EXPERIMENTS_20251231.md` for full details)*

We evaluated Mobile VLA on a validation set of 500 episodes (250 Left / 250 Right turns).

### 3.1 Main Results
**Table 1: Performance Matrix**

| Model Config | Quantization | Val Loss | RMSE | GPU Mem | Latency |
|:---:|:---:|:---:|:---:|:---:|:---:|
| **Mobile VLA (Chunk 5)** | **INT8** | **0.067** | **0.259** | **1.8 GB** | **0.49s** |
| Mobile VLA (Chunk 10) | INT8 | 0.284 | 0.533 | 1.8 GB | 0.50s |
| RoboVLMs (7B) | FP32 | - | - | 14.0 GB | 15.0s |

Our best configuration (Chunk 5, INT8) outperforms the Chunk 10 variant by **76% in validation loss** and reduces resource usage by **87% compared to the 7B baseline**.

### 3.2 Visualization
- **Figure 1 (Training Curves)**: Shows fast and stable convergence for Chunk 5.
- **Figure 2 (Resource Usage)**: Highlights the dramatic efficiency gains of Mobile VLA.
- **Figure 3 (Dataset)**: Confirms balanced training data distribution.

---

## 4. Conclusion

We have successfully developed **Mobile VLA**, a practical solution for embedding VLA capabilities into mobile robots. By combining a 1.6B backbone with INT8 quantization, we unlocked real-time inference (2.0 Hz) and ultra-low memory usage (1.8GB) without compromising control accuracy (Val Loss 0.067). Future work will focus on deploying this model to a physical mobile robot and conducting real-world navigation tests in diverse environments.

---

**References**
1. Kosmos-2: Grounding Multimodal Large Language Models to the World.
2. RT-2: Vision-Language-Action Models with Web-Scale Knowledge.
3. BitsAndBytes: 8-bit Optimizers and Matrix Multiplication.
