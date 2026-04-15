# Checkpoint Structure Documentation

## Overview
This document provides detailed analysis of PyTorch checkpoint structures used in the Mobile-VLA project, comparing Kosmos-2 and RoboVLMs checkpoints.

## Checkpoint Locations

### 1. Kosmos-2 (Finetuned on Mobile Data)
- **Path**: `RoboVLMs_upstream/runs/mobile_vla_lora_20251203/kosmos/mobile_vla_finetune/2025-12-03/mobile_vla_lora_20251203/epoch_epoch=09-val_loss=val_loss=0.013.ckpt`
- **Type**: PyTorch Lightning checkpoint
- **Size**: ~1.8 GB
- **Training**: Finetuned on 250 left-direction mobile navigation episodes

### 2. RoboVLMs Pretrained
- **Expected Path**: `checkpoints/RoboVLMs/checkpoints/kosmos_ph_oxe-pretrain.pt`
- **HuggingFace**: `robovlms/RoboVLMs`
- **Status**: ⚠️ Incomplete download (as of 2025-12-04)
- **Expected Size**: ~7 GB
- **Training**: Pretrained on OXE robot manipulation dataset

### 3. RoboVLMs Finetuned (Mobile)
- **Path**: `best_robovlms_mobile_model_epoch_1.pt`
- **Size**: 7.3 GB
- **Training**: RoboVLMs backbone finetuned on mobile data (1 epoch)

## Checkpoint Structure

### PyTorch Lightning Format (Kosmos-2)
```python
checkpoint = {
    'state_dict': {
        # Model parameters
        'model.model.vision_model.embeddings.patch_embedding.weight': Tensor(...),
        'model.model.text_model.embeddings.word_embeddings.weight': Tensor(...),
        # ... VLM parameters
        'model.act_head.lstm.weight_ih_l0': Tensor(...),
        'model.act_head.lstm.weight_hh_l0': Tensor(...),
        # ... Action head parameters
    },
    'epoch': 9,
    'global_step': ...,
    'pytorch-lightning_version': '...',
    'hyper_parameters': {
        'configs': {...},
        # Training configuration
    },
    'optimizer_states': [...],
    'lr_schedulers': [...]
}
```

### Standard PyTorch Format (RoboVLMs)
```python
checkpoint = {
    'model': {
        # Direct state dict
        'backbone.vision_encoder.conv1.weight': Tensor(...),
        # ... VLM parameters
        'policy_head.lstm.weight_ih': Tensor(...),
        # ... Action head parameters
    },
    'epoch': ...,
    'optimizer': {...}
}
```

## Parameter Groups

### VLM (Vision-Language Model)
The VLM consists of:

1. **Vision Encoder** (~400M params for Kosmos-2)
   - Patch embedding
   - Transformer blocks
   - Layer normalization
   - Key prefix: `vision_model.`, `visual.`, `vision_encoder.`

2. **Text Encoder** (~350M params)
   - Word embeddings
   - Positional encodings
   - Transformer blocks
   - Key prefix: `text_model.`, `language_model.`, `text_encoder.`

3. **Multimodal Connector** (~50M params)
   - Cross-attention layers
   - Projection layers
   - Key prefix: `connector.`, `perceiver.`, `cross_attn.`

**Total VLM params**: ~800M (Kosmos-2) to ~1.5B (RoboVLMs)

### Action Head (Mobile-VLA LSTM Decoder)
The action head consists of:

1. **Input Projection** (~2.1M params)
   - Projects 2048D context vector to latent space
   - `in_features=2048, latent=1024`

2. **LSTM** (~8M params)
   - Hidden size: 1024
   - Sequence modeling for action chunks

3. **Output Projection** (~2K params)
   - Projects to action dimension (2 for mobile: linear_x, angular_z)

**Total Action Head params**: ~10M

## Context Vector Extraction Points

### In RoboVLMs Architecture
```python
# File: robovlms/model/backbone/base_backbone.py
def forward_continuous(self, ...):
    # 1. VLM forward pass
    output = self.vlm_model(...)
    
    # 2. Extract hidden states
    output_hs = output.hidden_states[-1].clone()  # [batch, seq_len, hidden_dim]
    
    # 3. Extract action tokens
    action_hs = output_hs[action_token_mask].reshape(...)  # [batch, n_actions, 2048]
    
    # 4. Pass to action head
    action_logits = self.act_head(action_hs, ...)  # <- Hook point!
    
    return action_logits
```

### Hook Registration
```python
def extract_context_vector(model):
    context_vectors = []
    
    def hook_fn(module, input, output):
        # input[0] is action_hs (context vector)
        action_tokens = input[0]
        context_vectors.append(action_tokens.detach().cpu().numpy())
    
    # Register hook on action head
    handle = model.act_head.register_forward_hook(hook_fn)
    
    # Run inference...
    
    # Cleanup
    handle.remove()
    
    return context_vectors
```

## Context Vector Specification

### Shape and Dimension
- **Shape**: `(batch_size, n_action_tokens, feature_dim)`
  - For mobile: `(1, 1, 2048)`
  - Batch size: 1 (single episode)
  - Action tokens: 1 (single prediction point)
  - Feature dim: 2048

### Feature Dimension Breakdown (Hypothesis)
The 2048 dimension likely comes from:
- **Vision features**: 1024D (from vision encoder)
- **Text/Language features**: 1024D (from text encoder)
- **Concatenation**: Vision + Language = 2048D

### Expected Statistics
Based on previous analysis:

**Kosmos-2 (Mobile-VLA trained)**:
- Mean: -0.0196
- Std: 1.0056
- Range: [-7.43, 34.31]
- Distribution: Normalized, no dead neurons

**RoboVLMs (OXE pretrained)** - Expected:
- Mean: ~0.0 (normalized)
- Std: ~1.0 (normalized)
- Range: TBD (likely different from Kosmos)
- Distribution: Should be normalized, adapted to robot manipulation

## Downloading RoboVLMs Checkpoint

### Option 1: Using HuggingFace Hub
```python
from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="robovlms/RoboVLMs",
    local_dir="checkpoints/RoboVLMs",
    allow_patterns=["checkpoints/*.pt"]
)
```

### Option 2: Manual Download
```bash
# Using git-lfs
cd checkpoints
git clone https://huggingface.co/robovlms/RoboVLMs
cd RoboVLMs
git lfs pull
```

### Option 3: Direct URL (if available)
Check HuggingFace model card for direct download links.

## Verification

### Checkpoint Integrity Check
```python
import torch

def verify_checkpoint(path):
    try:
        # Load to CPU
        ckpt = torch.load(path, map_location='cpu')
        
        # Extract state dict
        if 'state_dict' in ckpt:
            state_dict = ckpt['state_dict']
        else:
            state_dict = ckpt
        
        # Count parameters
        total_params = sum(
            p.numel() for p in state_dict.values() 
            if isinstance(p, torch.Tensor)
        )
        
        print(f"✅ Checkpoint valid")
        print(f"   Total params: {total_params:,}")
        print(f"   Keys: {len(state_dict)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Checkpoint corrupted: {e}")
        return False
```

### Expected Parameter Counts
- **Kosmos-2 checkpoint**: ~810M params (VLM + Action Head)
- **RoboVLMs checkpoint**: ~1.5B params (VLM + Action Head)

## Compatibility Notes

### Action Head Compatibility
✅ **Compatible**: Both use MobileVLALSTMDecoder
- Input: 2048D context vector
- Output: 2D action (linear_x, angular_z)
- Configuration: Same hyperparameters

### VLM Compatibility
⚠️ **Different Pretraining**:
- **Kosmos-2**: Pretrained on general vision-language (COCO, Flickr, etc.)
- **RoboVLMs**: Pretrained on robot manipulation (Open-X-Embodiment)

**Key Question**: How does pretraining affect context vector distribution?

## Next Steps

1. ⬜ Download complete RoboVLMs checkpoint
2. ⬜ Run `verify_checkpoint_structure.py` on both checkpoints
3. ⬜ Compare parameter counts and structure
4. ⬜ Verify action head compatibility
5. ⬜ Extract context vectors from both models
6. ⬜ Compare context vector distributions

## References

- RoboVLMs Paper: [arXiv:XXXX.XXXXX](https://arxiv.org/abs/XXXX.XXXXX)
- Kosmos-2: [arXiv:2306.14824](https://arxiv.org/abs/2306.14824)
- Open-X-Embodiment: [arXiv:2310.08864](https://arxiv.org/abs/2310.08864)
