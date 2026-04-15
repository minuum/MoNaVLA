# RoboVLMs Validation

## Context Vector Analysis
- **Goal**: Analyze the context vector output of the pretrained RoboVLMs model when fed with collected data.
- **Status**: Planning
- **Key Questions**:
    - What does the context vector look like? (Shape, values)
    - How to hook into the model to extract this vector?
    - Is 500 samples enough? Need sampling strategy.

### 2. Technical Analysis (Context Vector)
- **Location**: `RoboVLMs/robovlms/model/backbone/base_backbone.py` -> `forward_continuous` -> `action_hs`
- **Extraction Method**: PyTorch Forward Hook on `model.act_head`
- **Findings (2025-12-03)**:
    - **Shape**: `(1, 1, 2048)` (Batch, Sequence, Feature Dim)
    - **Feature Dimension**: 2048 (Likely 1024 Vision + 1024 Text concatenation)
    - **Statistics (Single Sample)**:
        - Mean: ~ -0.02
        - Std: ~ 1.01
        - Range: [-6.40, 32.05]
    - **Note**: The input feature dimension to the Action Head (`MobileVLALSTMDecoder`) is 2048, not 1024 as initially assumed. This suggests a concatenation of features (e.g., Kosmos-2 Vision + Text) before the action head.

### 3. Sampling Strategy
- **Goal**: Verify if the context vector distribution is consistent across a larger dataset.
- **Results (Local Model, 2025-12-03)**:
    - **Samples**: 499 frames from 100 episodes
    - **Shape**: `(499, 2048)`
    - **Global Statistics**:
        - Mean: -0.0196
        - Std: 1.0056
        - Min: -7.43
        - Max: 34.31
    - **Stability**: No dead or constant neurons found. The distribution is well-behaved (normalized).

### 4. Original RoboVLMs Model Analysis
- **Goal**: Analyze the context vector of the original `robovlms/RoboVLMs` model from Hugging Face to compare with the local finetuned model.
- **Results (2025-12-03)**:
    - **Model**: `robovlms/RoboVLMs` (Kosmos-2 backbone)
    - **Shape**: `(1, 1, 1, 2048)`
    - **Statistics**:
        - Mean: -0.0196 (Identical to local model)
        - Std: 1.0032 (Very similar to local model's 1.0056)
        - Min: -7.95
        - Max: 9.27 (Significantly lower than local model's 34.31)
    - **Technical Specifications**:
        - **Type**: `torch.Tensor`
        - **Data Type (Dtype)**: `torch.float32`
        - **Device**: `cuda:0` (GPU)
        - **Layout**: `torch.strided`
        - **Memory Stride**: `(2048, 2048, 2048, 1)`
        - **Gradient**: `requires_grad=False` (Inference Mode)
    - **Conclusion**: The context vector structure and central distribution are consistent between the original and finetuned models. The difference in maximum values suggests that finetuning might have pushed some features to more extreme values, or it's an artifact of the specific sample used. The 2048 dimension is confirmed.
- **Context Vector Location**:
    - In `RoboVLMs/robovlms/model/backbone/base_backbone.py`, the method `forward_continuous` computes `output_hs` (hidden states from the LLM).
    - It then extracts `action_hs` (Action Hidden States) which serves as the input to the `act_head` (Action Head).
    - `action_hs` is likely the "context vector" of interest.
    - Code reference:
        ```python
        # base_backbone.py
        output_hs = output.hidden_states[-1].clone()
        # ...
        action_hs = output_hs[action_token_mask].reshape(...)
        # ...
        action_logits, action_loss = self._forward_action_head(action_hs, ...)
        ```

## Implementation Plan
1.  **Hook Strategy**: Use a PyTorch forward hook on `model.act_head` to capture the input (`action_hs`).
    ```python
    def hook_fn(module, input, output):
        context_vector = input[0]
        # save or analyze context_vector
    
    model.act_head.register_forward_hook(hook_fn)
    ```
2.  **Sampling**:
    -   If the dataset is small (~500), we can potentially run all of them or sample 50-100 representative ones.
    -   Need to check the diversity of the collected data.

## ✅ Non-GPU Validation Tasks (2025-12-04)

### **Priority 1: Model Loading Strategy Analysis** ⚡
**Goal**: Understand how to load RoboVLMs pretrained model without GPU
**Status**: 🔍 In Progress

**Tasks**:
1. ✅ Verify checkpoint structure
   - Located: `checkpoints/cache/models--robovlms--RoboVLMs`
   - Status: ⚠️ Incomplete download (only lock files found)
   
2. 📝 **Create checkpoint download script (Non-GPU)**
   ```python
   # Script: download_robovlms_checkpoint.py
   # Download from HuggingFace without loading to GPU
   # Path: docs/RoboVLMs_validation/download_robovlms_checkpoint.py
   ```

3. 📝 **Analyze checkpoint structure (Non-GPU)**
   - Extract state_dict keys
   - Identify VLM parameters vs action head parameters
   - Document parameter shapes and types
   - Compare with Kosmos-2 checkpoint structure

### **Priority 2: Sampling Strategy Planning** ⚡
**Goal**: Design efficient sampling strategy for 500 episodes
**Status**: ✅ Partially Complete (sampling_test.py exists)

**Analysis**:
- ✅ Current approach: 100 episodes × 5 samples = 500 frames
- ✅ Results documented (499 frames, shape (499, 2048))
- 📝 **TODO**: Design stratified sampling
  - By task type (left/right/horizontal/vertical)
  - By difficulty (simple/medium/hard)
  - By trajectory pattern

**Non-GPU Tasks**:
1. 📊 **Dataset statistics script** (Non-GPU)
   ```python
   # Analyze all H5 files without model inference
   # Count episodes by type, extract metadata
   # Generate sampling plan
   ```

2. 📝 **Sampling strategy document**
   - Define criteria for representative samples
   - Balance between diversity and efficiency
   - Document expected distribution

### **Priority 3: Hook Implementation Planning** ⚡
**Goal**: Design robust hook mechanism for context vector extraction
**Status**: ✅ Complete (implemented in analyze_context_vector.py)

**Non-GPU Review Tasks**:
1. 📖 **Code review** (Non-GPU)
   - Review hook_fn implementation
   - Verify tensor detachment and CPU transfer
   - Check memory efficiency

2. 📝 **Documentation** (Non-GPU)
   - Document hook registration points
   - Explain where action_hs is captured
   - Create flowchart: Image → VLM → action_hs → Action Head

### **Priority 4: Comparison Methodology** ⚡
**Goal**: Define how to compare Kosmos-2 vs RoboVLMs context vectors
**Status**: 🆕 New Task

**Non-GPU Planning**:
1. 📊 **Statistical comparison metrics**
   - Distribution comparison (KL divergence, Wasserstein distance)
   - Feature activation patterns
   - Dead neuron analysis
   - Correlation analysis

2. 📝 **Visualization plan**
   - t-SNE/UMAP projection design
   - Heatmap layout
   - Distribution plots

3. 📄 **Report template**
   - Create markdown template for results
   - Define tables and figures structure

### **Priority 5: Checkpoint Download Status** ⚠️
**Current Issue**: RoboVLMs checkpoint incomplete

**Investigation** (Non-GPU):
```bash
# Check cache structure
ls -R checkpoints/cache/models--robovlms--RoboVLMs/
# Expected: snapshots/<hash>/checkpoints/kosmos_ph_oxe-pretrain.pt

# Check existing .pt file
ls -lh best_robovlms_mobile_model_epoch_1.pt
# Size: 7.3GB - This might be a finetuned version
```

**Action Items**:
1. ⬜ Verify if `best_robovlms_mobile_model_epoch_1.pt` is usable
2. ⬜ If not, create HuggingFace download script
3. ⬜ Document checkpoint structure and compatibility

---

## 📋 Immediate Action Plan (No GPU Required)

### **Step 1: Create Dataset Analysis Script** (15 min)
```bash
# File: docs/RoboVLMs_validation/analyze_dataset_stats.py
# Extract metadata from all H5 files
# Output: dataset_statistics.json
```

### **Step 2: Create Checkpoint Download Script** (20 min)
```bash
# File: docs/RoboVLMs_validation/download_robovlms_checkpoint.py
# Download from HuggingFace with progress bar
# Verify integrity
```

### **Step 3: Create Comparison Metrics Script** (30 min)
```bash
# File: docs/RoboVLMs_validation/compare_vectors_metrics.py
# Load two .npy files (Kosmos vs RoboVLMs contexts)
# Compute statistical metrics
# Generate comparison report
```

### **Step 4: Document Checkpoint Structure** (10 min)
```bash
# File: docs/RoboVLMs_validation/CHECKPOINT_STRUCTURE.md
# Document state_dict structure
# List parameter names and shapes
```

### **Step 5: Create Sampling Plan Document** (15 min)
```bash
# File: docs/RoboVLMs_validation/SAMPLING_PLAN.md
# Define stratified sampling strategy
# List selected episodes with justification
```

---

## 🎯 GPU-Required Tasks (For Later)

1. Run `analyze_context_vector.py` with RoboVLMs checkpoint
2. Run `sampling_test.py` with RoboVLMs
3. Execute full comparison with `compare_context_vectors.py`
4. Generate t-SNE visualizations

---

## Next Steps (Prioritized)
1. ✅ **[Non-GPU]** Create dataset statistics script
2. ✅ **[Non-GPU]** Verify existing checkpoint (`best_robovlms_mobile_model_epoch_1.pt`)
3. ✅ **[Non-GPU]** Create checkpoint download script (if needed)
4. ✅ **[Non-GPU]** Document comparison methodology
5. ⏳ **[GPU Required]** Run context vector extraction
6. ⏳ **[GPU Required]** Compare vectors and analyze results
