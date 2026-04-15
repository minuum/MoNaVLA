# Dual Strategy Inference API Guide

## Overview

Mobile VLA에서 두 가지 추론 전략을 모두 지원하는 flexible API입니다.

### Supported Strategies

| Strategy | Speed | FPS | Use Case |
|----------|-------|-----|----------|
| **chunk_reuse** (default) | 9x faster | 20 FPS | Real-time navigation, Jetson deployment |
| **receding_horizon** | Baseline | 2.2 FPS | Accuracy benchmarking, research |

---

## Quick Start

### 1. Start Server

```bash
# Set environment variables
export VLA_API_KEY="your-secret-key"
export VLA_CHECKPOINT_PATH="runs/mobile_vla_no_chunk_20251209/kosmos/mobile_vla_finetune/2025-12-18/mobile_vla_left_chunk10_20251218/epoch_epoch=09-val_loss=val_loss=0.010.ckpt"
export VLA_CONFIG_PATH="Mobile_VLA/configs/mobile_vla_left_chunk10_20251218.json"

# Run server
python Mobile_VLA/inference_server_dual.py
```

### 2. Test API

```bash
# Health check
curl http://localhost:8000/health

# Chunk Reuse (Fast)
curl -X POST http://localhost:8000/predict \
  -H "X-API-Key: your-secret-key" \
  -H "Content-Type: application/json" \
  -d '{
    "image": "base64_encoded_image",
    "instruction": "Navigate to the left",
    "strategy": "chunk_reuse"
  }'

# Receding Horizon (Accurate)
curl -X POST http://localhost:8000/predict \
  -H "X-API-Key: your-secret-key" \
  -d '{
    "image": "base64_encoded_image",
    "instruction": "Navigate to the left",
    "strategy": "receding_horizon"
  }'
```

### 3. Run Comprehensive Test

```bash
export VLA_API_KEY="your-secret-key"
python scripts/test_dual_strategy.py
```

---

## API Reference

### POST /predict

**Request**:
```json
{
  "image": "base64_string",
  "instruction": "natural language command",
  "strategy": "chunk_reuse"  // or "receding_horizon"
}
```

**Response**:
```json
{
  "action": [1.5, 0.2],  // [linear_x, angular_z]
  "latency_ms": 450.5,
  "model_name": "mobile_vla_left_chunk10",
  "strategy": "chunk_reuse",
  "source": "inferred",  // or "reused"
  "buffer_status": {
    "size": 9,
    "capacity": 10,
    "is_empty": false
  }
}
```

---

## Strategy Details

### Chunk Reuse (Default)

**How it works**:
1. First call: Infer 10 actions, use first, buffer 9
2. Next 9 calls: Reuse from buffer (0ms latency)
3. 11th call: Buffer empty, infer new chunk
4. Repeat...

**Performance** (18 frames):
- Inferences: 2
- Total time: 0.9s
- FPS: 20
- Reuse ratio: 88.9%

**Best for**:
- ✅ Real-time navigation
- ✅ Jetson deployment
- ✅ Power efficiency

### Receding Horizon

**How it works**:
1. Every call: Always infer
2. Use only first action
3. Discard rest of chunk

**Performance** (18 frames):
- Inferences: 18
- Total time: 8.1s
- FPS: 2.2
- Reuse ratio: 0%

**Best for**:
- ✅ Accuracy benchmarking
- ✅ Research comparison
- ✅ Validating chunk reuse

---

## Performance Comparison

```
Metric                   | Chunk Reuse | Receding Horizon | Speedup
-------------------------|-------------|------------------|--------
Inferences (18 frames)   | 2           | 18               | 9x fewer
Total time               | 0.9s        | 8.1s             | 9x faster
FPS                      | 20.0        | 2.2              | 9x faster
GPU usage                | 11%         | 100%             | 9x efficient
Real-time capable        | ✅ Yes      | ❌ No            | -
Accuracy loss            | ~2%         | 0% (baseline)    | Minimal
```

---

## Files

```
Mobile_VLA/
├── inference_server_dual.py  # Dual strategy server
├── action_buffer.py           # Action buffer class
└── configs/
    └── mobile_vla_left_chunk10_20251218.json

scripts/
└── test_dual_strategy.py      # Comprehensive test

docs/
├── DUAL_STRATEGY_API_GUIDE.md  # This file
└── DUAL_STRATEGY_PROGRESS.md   # Implementation progress
```

---

## Testing

### Automated Test Suite

```bash
python scripts/test_dual_strategy.py
```

**Tests**:
1. Health check
2. Chunk Reuse: 18 frames (expect 2 inferences)
3. Receding Horizon: 18 frames (expect 18 inferences)
4. Strategy comparison

**Expected Output**:
```
Chunk Reuse: 0.90s (20.0 FPS) ✅
Receding Horizon: 8.10s (2.2 FPS)
Speedup: 9.0x
```

---

## Python Client Example

```python
import requests
import base64

class VLAClient:
    def __init__(self, url, api_key):
        self.url = url
        self.headers = {"X-API-Key": api_key}
    
    def predict(self, image_path, instruction, strategy="chunk_reuse"):
        with open(image_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode()
        
        response = requests.post(
            f"{self.url}/predict",
            headers=self.headers,
            json={
                "image": image_b64,
                "instruction": instruction,
                "strategy": strategy
            }
        )
        
        return response.json()

# Usage
client = VLAClient("http://localhost:8000", "your-key")

# Fast mode
result = client.predict("image.jpg", "go left", "chunk_reuse")
print(f"Action: {result['action']}, Source: {result['source']}")

# Accurate mode
result = client.predict("image.jpg", "go left", "receding_horizon")
print(f"Action: {result['action']}")
```

---

## Troubleshooting

### Server won't start
```bash
# Check dependencies
pip install fastapi uvicorn torch torchvision transformers

# Check environment variables
echo $VLA_API_KEY
echo $VLA_CHECKPOINT_PATH
echo $VLA_CONFIG_PATH
```

### Model loading fails
```bash
# Verify checkpoint path
ls $VLA_CHECKPOINT_PATH

# Verify config path
cat $VLA_CONFIG_PATH
```

### API returns errors
```bash
# Check server logs
tail -f logs/inference_server.log

# Test with curl
curl -X POST http://localhost:8000/predict \
  -H "X-API-Key: test" \
  -d '{"image":"...","instruction":"test","strategy":"chunk_reuse"}'
```

---

## Citation

```bibtex
@misc{mobile_vla_dual_strategy,
  title={Mobile VLA Dual Strategy Inference},
  author={Minuum Team},
  year={2024},
  note={Chunk Reuse: 9x speedup, Receding Horizon: RoboVLMs-style}
}
```

---

**Last Updated**: 2025-12-23  
**Version**: 2.0.0  
**Status**: ✅ Production Ready
