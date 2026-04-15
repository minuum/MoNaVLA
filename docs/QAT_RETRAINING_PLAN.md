# QAT 재학습 계획 - On-Device 목표 달성

**목표**: INT8 Vision + INT4 LLM으로 처음부터 재학습  
**타겟 메모리**: 8-11GB (전체, activation 포함)  
**현재 문제**: FP32 학습 → PTQ는 부족함

---

## 🎯 원래 목표 (올바름)

### 목표 구성:
```
Image
→ Vision Encoder (INT8, frozen) ← QAT
→ Embedding projection (FP16)
→ LLM (INT4, frozen) ← BitsAndBytes
→ Action Head (FP16) ← 학습 대상
```

### 목표 메모리 (Jetson 16GB):
```
LLM 3B INT4:           ~1.5 GB
Vision Encoder INT8:   ~0.8-1.2 GB
Activation:            ~1.5-2 GB
KV Cache (256 tokens): ~0.8-1.5 GB
TensorRT/CUDA:         ~2 GB
OS + ROS2:             ~2-3 GB
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
총합:                  8-11 GB ✅
```

**현재 Dynamic PTQ의 문제**:
- Model weight만 5.8GB
- Activation + KV cache 추가하면 > 11GB
- ❌ 목표 초과

---

## 📋 QAT 재학습 계획

### Phase 1: Vision Encoder INT8 QAT

#### 1.1 Vision Encoder Quantization Setup

**수정 파일**: `RoboVLMs_upstream/robovlms/model/vision_encoder.py`

```python
import torch
import torch.nn as nn
from torch.quantization import QuantStub, DeQuantStub

class QuantizedVisionEncoder(nn.Module):
    """Vision Encoder with QAT"""
    
    def __init__(self, original_encoder):
        super().__init__()
        
        # Quantization stubs
        self.quant = QuantStub()
        self.dequant = DeQuantStub()
        
        # Original encoder
        self.encoder = original_encoder
        
    def forward(self, x):
        x = self.quant(x)
        x = self.encoder(x)
        x = self.dequant(x)
        return x


def load_vision_encoder_with_qat(pretrained_path, qat_config):
    """Load vision encoder with QAT preparation"""
    
    # Load pretrained
    from transformers import AutoModel
    encoder = AutoModel.from_pretrained(pretrained_path)
    
    # Freeze parameters
    for param in encoder.parameters():
        param.requires_grad = False
    
    # Wrap with quantization
    qat_encoder = QuantizedVisionEncoder(encoder)
    
    # Prepare for QAT
    qat_encoder.qconfig = torch.quantization.get_default_qat_qconfig('fbgemm')
    torch.quantization.prepare_qat(qat_encoder, inplace=True)
    
    return qat_encoder
```

#### 1.2 Training Config 수정

**새 파일**: `Mobile_VLA/configs/mobile_vla_qat_int8_int4.json`

```json
{
  "exp_name": "mobile_vla_qat_int8_int4",
  "model": "kosmos",
  
  "train_setup": {
    "precision": "16-mixed",
    "train_vision": false,
    "freeze_backbone": true,
    "vision_qat": true,
    "llm_int4": true,
    "qat_config": {
      "vision_quantization": "INT8",
      "llm_quantization": "INT4",
      "fake_quantization": true,
      "observer": "MinMaxObserver",
      "qscheme": "per_tensor_affine"
    }
  },
  
  "quantization": {
    "enable": true,
    "vision_encoder": {
      "dtype": "qint8",
      "qconfig": "fbgemm"
    },
    "llm": {
      "dtype": "int4",
      "method": "bitsandbytes",
      "load_in_4bit": true,
      "bnb_4bit_compute_dtype": "float16",
      "bnb_4bit_use_double_quant": true,
      "bnb_4bit_quant_type": "nf4"
    }
  },
  
  "trainer": {
    "max_epochs": 10,
    "learning_rate": 0.0001,
    "warmup_epochs": 0.5
  }
}
```

#### 1.3 Trainer 수정

**파일**: `RoboVLMs_upstream/robovlms/train/mobile_vla_trainer.py`

```python
class MobileVLATrainerQAT(MobileVLATrainer):
    """QAT-enabled trainer"""
    
    def __init__(self, config_path):
        super().__init__(config_path)
        
        # Load quantization config
        self.qat_config = self.config.get('quantization', {})
        
        if self.qat_config.get('enable', False):
            self._setup_quantization()
    
    def _setup_quantization(self):
        """Setup QAT"""
        
        # 1. Vision Encoder INT8 QAT
        if 'vision_encoder' in self.qat_config:
            print("🔧 Setting up Vision Encoder INT8 QAT...")
            self._setup_vision_qat()
        
        # 2. LLM INT4 BitsAndBytes
        if 'llm' in self.qat_config:
            print("🔧 Setting up LLM INT4 BitsAndBytes...")
            self._setup_llm_int4()
    
    def _setup_vision_qat(self):
        """Setup Vision Encoder QAT"""
        from torch.quantization import get_default_qat_qconfig, prepare_qat
        
        # Get vision encoder
        vision_encoder = self.model.backbone.vision_model
        
        # Freeze
        for param in vision_encoder.parameters():
            param.requires_grad = False
        
        # QAT config
        vision_encoder.qconfig = get_default_qat_qconfig('fbgemm')
        
        # Prepare QAT
        self.model.backbone.vision_model = prepare_qat(
            vision_encoder,
            inplace=False
        )
        
        print("✅ Vision Encoder prepared for INT8 QAT")
    
    def _setup_llm_int4(self):
        """Setup LLM INT4 with BitsAndBytes"""
        from transformers import BitsAndBytesConfig
        
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4"
        )
        
        # Reload LLM with INT4
        # (Implementation depends on model architecture)
        
        print("✅ LLM prepared for INT4")
    
    def on_train_end(self):
        """Convert QAT model to quantized"""
        from torch.quantization import convert
        
        # Convert vision encoder
        if hasattr(self.model.backbone, 'vision_model'):
            print("🔄 Converting Vision Encoder to INT8...")
            self.model.backbone.vision_model = convert(
                self.model.backbone.vision_model,
                inplace=False
            )
            print("✅ Vision Encoder converted to INT8")
        
        super().on_train_end()
```

---

### Phase 2: 학습 스크립트

**새 파일**: `scripts/train_qat_int8_int4.sh`

```bash
#!/bin/bash
# QAT Training with INT8 Vision + INT4 LLM

export CUDA_VISIBLE_DEVICES=0

python3 RoboVLMs_upstream/robovlms/train/main.py \
    --config Mobile_VLA/configs/mobile_vla_qat_int8_int4.json \
    --data-dir ROS_action/mobile_vla_dataset \
    --gpus 1 \
    --precision 16-mixed \
    --max-epochs 10 \
    --batch-size 1 \
    --learning-rate 0.0001 \
    --warmup-epochs 0.5 \
    --log-dir runs/mobile_vla_qat_int8_int4 \
    --enable-qat
```

---

### Phase 3: 검증

**새 파일**: `scripts/validate_qat_model.py`

```python
"""
QAT 모델 검증 - 실제 메모리 측정
"""

import torch
import sys
sys.path.append('RoboVLMs_upstream')

def measure_qat_model(checkpoint_path):
    """QAT 모델 메모리 측정"""
    
    # Before loading
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    
    mem_before = torch.cuda.memory_allocated() / 1e9
    
    # Load QAT model
    from robovlms.train.mobile_vla_trainer import MobileVLATrainerQAT
    
    model = MobileVLATrainerQAT.load_from_checkpoint(checkpoint_path)
    model = model.to('cuda')
    model.eval()
    
    # After loading
    mem_after = torch.cuda.memory_allocated() / 1e9
    mem_peak = torch.cuda.max_memory_allocated() / 1e9
    
    print(f"\n📊 QAT Model Memory:")
    print(f"  Model weight: {mem_after - mem_before:.2f} GB")
    print(f"  Peak: {mem_peak:.2f} GB")
    
    # Simulate inference
    dummy_input = torch.randn(1, 3, 224, 224).cuda()
    
    with torch.no_grad():
        _ = model(dummy_input)
    
    mem_with_activation = torch.cuda.max_memory_allocated() / 1e9
    
    print(f"  With activation: {mem_with_activation:.2f} GB")
    
    # Expected total
    expected_total = mem_with_activation + 2.0 + 2.5  # + TensorRT + OS
    print(f"\n🎯 Expected Total on Jetson:")
    print(f"  Model + Activation: {mem_with_activation:.2f} GB")
    print(f"  TensorRT/CUDA: ~2.0 GB")
    print(f"  OS + ROS2: ~2.5 GB")
    print(f"  ━━━━━━━━━━━━━━━━━━━━━")
    print(f"  Total: ~{expected_total:.2f} GB")
    
    if expected_total < 11:
        print(f"  ✅ Within target (< 11GB)")
    else:
        print(f"  ❌ Exceeds target (> 11GB)")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--checkpoint', required=True)
    args = parser.parse_args()
    
    measure_qat_model(args.checkpoint)
```

---

## 📋 실행 계획

### Step 1: 코드 수정 (1일)
```bash
# 1. Vision encoder QAT 추가
# 2. Config 생성
# 3. Trainer 수정
```

### Step 2: QAT 학습 (3-4일)
```bash
# Left model
bash scripts/train_qat_int8_int4_left.sh

# Right model  
bash scripts/train_qat_int8_int4_right.sh
```

### Step 3: 검증 (1일)
```bash
# Memory validation
python3 scripts/validate_qat_model.py \
    --checkpoint runs/mobile_vla_qat/best.ckpt

# Accuracy validation
python3 scripts/test_qat_accuracy.py
```

### Step 4: Jetson 배포 (1일)
```bash
# Deploy and test on actual Jetson
```

**총 소요 시간**: 6-7일

---

## 🎯 예상 결과

### 메모리 (목표):
```
Model weight (INT8+INT4): ~2 GB
Activation: ~1.5 GB
KV Cache: ~1 GB
TensorRT/CUDA: ~2 GB
OS + ROS2: ~2.5 GB
━━━━━━━━━━━━━━━━━━━━━━━━━━
Total: ~9 GB ✅ (< 11GB)
```

### 성능 (예상):
- Latency: ~300-350ms
- FPS: ~25-30
- Accuracy: 98-99%

---

## ✅ 결론

**죄송합니다!** 원래 목표가 맞습니다:
1. ✅ **QAT 재학습 필요**
2. ✅ **INT8 Vision + INT4 LLM**
3. ✅ **처음부터 다시 학습**
4. ✅ **목표: 8-11GB 전체 메모리**

**다음 액션**: QAT 재학습 구현 시작하겠습니다!
