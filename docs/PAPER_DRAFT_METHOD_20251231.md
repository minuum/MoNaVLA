# Method

We propose **Mobile VLA**, a lightweight Vision-Language-Action model designed specifically for edge robotic deployment. Our approach focuses on minimizing resource consumption while maintaining navigation performance through efficient model architecture, quantization, and action chunking strategies.

## 1. Model Architecture

Mobile VLA is built upon the **Kosmos-2** [Ref] architecture, a Multimodal Large Language Model (MLLM) with 1.6 billion parameters. Unlike recent VLA models that utilize large backbones such as Qwen-VL (7B) or LLaVA (7B-13B), we prioritize inference efficiency for mobile robot platforms.

### 1.1 Vision-Language Backbone
The backbone consists of a Vision Encoder (CLIP-ViT-Large) and a Transformer-based Language Model. The vision encoder processes $224 \times 224$ RGB images, extracting visual features which are then projected into the language model's embedding space.
- **Parameters**: 1.6B (vs 7B+ in typical VLAs)
- **Input**: RGB Image ($I$) + Text Instruction ($T$)
- **Output**: Multimodal Embeddings ($E$)

### 1.2 Continuous Action Head
To predict continuous control signals for mobile navigation, we append a specialized **Action Head** to the language model. Instead of autoregressive token generation for actions (like RT-2), we use a multi-layer perceptron (MLP) to regress continuous action values directly.

The action head takes the last hidden state of the language model and predicts a sequence of actions:
$$ \hat{a}_{t:t+k} = \text{MLP}(\text{Backbone}(I_t, T)) $$
where $k$ is the action chunk size. The output action space $\mathcal{A}$ is 2-dimensional:
- `linear_x` (m/s): Forward velocity
- `linear_y` (rad/s): Angular velocity (steering)

## 2. Efficient Quantization

To enable deployment on edge devices like the NVIDIA Jetson Orin Nano (16GB RAM), we apply **Post-Training Quantization (PTQ)** using the BitsAndBytes library.

### 2.1 INT8 Quantization
We convert the trained FP32 model weights to 8-bit integers (INT8) for inference. This process involves:
1.  **Vector-wise Quantization**: Quantizing weights row-wise and activations token-wise to minimize accuracy loss.
2.  **Mixed Precision Decomposition**: Outlier features (detected by a magnitude threshold) are retained in FP16 to preserve performance, while the majority (99.9%) are quantized to INT8.

This strategy reduces the GPU memory footprint from **6.3GB to 1.8GB** (a 71% reduction), allowing the model to coexist with other robot processes (SLAM, Planner) on limited hardware.

## 3. Action Chunking Strategy

Mobile robots require smooth and continuous control. Single-step prediction often leads to jerky motion and latency-induced instability. We adopt **Action Chunking** with a receding horizon control strategy.

### 3.1 Temporal Aggregation
At each time step $t$, the model predicts a chunk of $k$ future actions $\{a_t, a_{t+1}, ..., a_{t+k-1}\}$.
- **Chunk Size ($k$)**: We experiment with $k=5$ and $k=10$.
- **Execution**: We execute the actions in a closed-loop manner, updating the plan at a fixed frequency.

Our experiments (see Sec. 4) demonstrate that a smaller chunk size ($k=5$) is more effective for mobile navigation, balancing trajectory smoothness with responsiveness to environmental changes.

## 4. Dataset and Training

We trained Mobile VLA on a curated dataset of **500 mobile navigation episodes**.
- **Data Source**: Teleoperated demonstrations in a simulated environment.
- **Tasks**: Usage of `linear_x` and `linear_y` to navigate around obstacles (boxes) to a target (cup).
- **Distribution**: Balanced Left/Right turn scenarios (250/250 episodes).
- **Action Space**:
    - `linear_x`: $\mu=1.02 m/s$ (Constant forward motion)
    - `linear_y`: $\mu=-0.03 rad/s$ (Steering corrections)

We fine-tuned the entire model (Full Fine-tuning) for 10 epochs using the AdamW optimizer with a learning rate of $1e-5$ and a batch size of 4.
