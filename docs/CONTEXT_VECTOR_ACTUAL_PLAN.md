# Context Vector 실제 추출 및 비교 체크리스트

## ❌ 현재 상태: **미완료** (이론만, 실행 안 함)

### 체크리스트 검증

| 항목 | 상태 | 비고 |
|:---|:---:|:---|
| RoboVLMs pretrained로 우리 데이터 테스트 | ❌ | 스크립트만 준비, 실행 안 함 |
| 모델 hook/코드 수정 | ❌ | 방법만 제시, 구현 안 함 |
| 실제 값 확인 | ❌ | 예상만, 실제 추출 안 함 |
| Sampling 전략 | ✅ | 문서화 완료 (100 episodes, 5 frames) |
| HuggingFace 로드 | ✅ | Checkpoint 확인완료 |

**결론**: **이론적 분석은 완료, 실제 실행은 0%**

---

## 🚀 실제 실행 계획

### **Step 1: Checkpoint 확인** ✅
```bash
# RoboVLMs
.vlms/RoboVLMs/checkpoints/kosmos_ph_oxe-pretrain.pt
→ 심볼릭 링크 확인됨

# Mobile-VLA (trained)
RoboVLMs_upstream/runs/mobile_vla_lora_20251203/.../epoch_09...ckpt
→ 존재 확인됨
```

### **Step 2: Context Vector 추출 스크립트 작성** ⏳

### **Step 3: 비교 및 시각화** ⏳

---

## 📊 실제 비교 방법 (구조화)

### **방법 1: 직접 값 추출**

```python
#!/usr/bin/env python3
"""
실제 Context Vector 추출 및 비교
"""
import torch
import numpy as np
from pathlib import Path

# 1. 모델 로드
def load_robovlms():
    """RoboVLMs pretrained 로드"""
    ckpt_path = ".vlms/RoboVLMs/checkpoints/kosmos_ph_oxe-pretrain.pt"
    checkpoint = torch.load(ckpt_path, map_location='cpu')
    
    # VLM만 추출
    vlm_state = {k: v for k, v in checkpoint.items() 
                 if 'vision' in k or 'language' in k}
    
    return vlm_state

def load_mobile_vla():
    """Mobile-VLA trained 로드"""
    ckpt_path = "RoboVLMs_upstream/runs/mobile_vla_lora_20251203/.../epoch_09.ckpt"
    
    from robovlms.train.mobile_vla_trainer import MobileVLATrainer
    model = MobileVLATrainer.load_from_checkpoint(ckpt_path)
    model.eval()
    
    return model

# 2. Context Vector 추출
def extract_context(model, images):
    """
    이미지에서 context vector 추출
    
    Args:
        model: VLM model
        images: (batch, frames, C, H, W)
    
    Returns:
        context: (batch, frames, tokens, features)
    """
    with torch.no_grad():
        context = model.encode_images(images)
    
    return context

# 3. 통계 계산
def compute_statistics(context):
    """
    Context vector 통계
    
    Returns:
        dict: {mean, std, min, max, shape}
    """
    return {
        'shape': list(context.shape),
        'mean': float(context.mean()),
        'std': float(context.std()),
        'min': float(context.min()),
        'max': float(context.max()),
        'norm': float(torch.norm(context)),
    }

# 4. 비교
def compare_contexts(ctx1, ctx2, name1='RoboVLMs', name2='Mobile-VLA'):
    """
    두 context vector 비교
    """
    stats1 = compute_statistics(ctx1)
    stats2 = compute_statistics(ctx2)
    
    print(f"\n{'='*60}")
    print(f"Context Vector 비교: {name1} vs {name2}")
    print(f"{'='*60}\n")
    
    # 표 형식 출력
    print(f"{'Metric':<15} | {name1:<20} | {name2:<20} | Difference")
    print("-"*80)
    
    for key in ['mean', 'std', 'min', 'max', 'norm']:
        v1 = stats1[key]
        v2 = stats2[key]
        diff = abs(v1 - v2)
        print(f"{key:<15} | {v1:<20.4f} | {v2:<20.4f} | {diff:.4f}")
    
    # Cosine similarity
    cos_sim = torch.cosine_similarity(
        ctx1.flatten(), ctx2.flatten(), dim=0
    )
    print(f"\nCosine Similarity: {cos_sim:.4f}")
    
    return {
        'stats1': stats1,
        'stats2': stats2,
        'cosine_similarity': float(cos_sim)
    }
```

### **방법 2: Hook 사용 (내부 값 확인)**

```python
def hook_context_extraction(model):
    """
    모델에 hook을 걸어서 중간 layer 값 확인
    """
    activations = {}
    
    def get_activation(name):
        def hook(model, input, output):
            activations[name] = output.detach()
        return hook
    
    # VLM의 특정 layer에 hook 등록
    model.model.vision_model.register_forward_hook(
        get_activation('vision_output')
    )
    
    return activations

# 사용
activations = hook_context_extraction(model)
output = model(images)
vision_context = activations['vision_output']
```

---

## 📁 실행 가능한 스크립트

```python
#!/usr/bin/env python3
"""
extract_and_compare_contexts.py

실제 Context Vector 추출 및 비교 스크립트
"""

import torch
import numpy as np
import h5py
from pathlib import Path
from PIL import Image
import torchvision.transforms as T
import json
import sys

sys.path.insert(0, "RoboVLMs_upstream")

def main():
    print("="*60)
    print("Context Vector 실제 추출 및 비교")
    print("="*60)
    
    # 1. 데이터 로드 (샘플링)
    print("\n[1] 샘플 데이터 로드 (10 episodes)")
    h5_files = list(Path("ROS_action/mobile_vla_dataset").glob("episode*.h5"))[:10]
    
    transform = T.Compose([
        T.Resize((224, 224)),
        T.ToTensor()
    ])
    
    sample_images = []
    for h5_file in h5_files:
        with h5py.File(h5_file, 'r') as f:
            # 첫 8 프레임
            frames = []
            for i in range(min(8, len(f['images']))):
                img = Image.fromarray(f['images'][i].astype(np.uint8))
                frames.append(transform(img))
            
            if len(frames) == 8:
                sample_images.append(torch.stack(frames))
    
    images_batch = torch.stack(sample_images).cuda()  # (N, 8, 3, 224, 224)
    print(f"  샘플 shape: {images_batch.shape}")
    
    # 2. Mobile-VLA (trained) context 추출
    print("\n[2] Mobile-VLA Context 추출")
    from robovlms.train.mobile_vla_trainer import MobileVLATrainer
    
    mobile_ckpt = "RoboVLMs_upstream/runs/mobile_vla_lora_20251203/kosmos/mobile_vla_finetune/2025-12-03/mobile_vla_lora_20251203/epoch_epoch=09-val_loss=val_loss=0.013.ckpt"
    
    mobile_model = MobileVLATrainer.load_from_checkpoint(mobile_ckpt)
    mobile_model.eval().cuda()
    
    with torch.no_grad():
        mobile_context = mobile_model.model.encode_images(images_batch)
    
    print(f"  Mobile-VLA context shape: {mobile_context.shape}")
    print(f"  Mean: {mobile_context.mean():.4f}")
    print(f"  Std: {mobile_context.std():.4f}")
    
    # 3. RoboVLMs (pretrained) context 추출 (TODO: 구현 필요)
    print("\n[3] RoboVLMs Context 추출 (TODO)")
    print("  ⚠️  RoboVLMs checkpoint 구조 분석 필요")
    
    # 4. 결과 저장
    print("\n[4] 결과 저장")
    results = {
        'mobile_vla': {
            'shape': list(mobile_context.shape),
            'mean': float(mobile_context.mean()),
            'std': float(mobile_context.std()),
            'min': float(mobile_context.min()),
            'max': float(mobile_context.max()),
        }
    }
    
    with open('context_comparison.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print("  ✅ context_comparison.json 저장됨")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    main()
```

---

## 🎯 다음 액션

### **지금 바로 실행 가능** (GPU 필요)
```bash
# 1. 스크립트 실행
python3 extract_and_compare_contexts.py

# 2. 결과 확인
cat context_comparison.json
```

### **결과 예상**
```json
{
  "mobile_vla": {
    "shape": [10, 8, 64, 2048],
    "mean": -0.0234,
    "std": 1.0145,
    "min": -12.4567,
    "max": 11.2341
  },
  "robovlms": {
    "shape": [10, 8, 64, 2048],
    "mean": -0.0187,
    "std": 0.9876,
    "min": -11.8923,
    "max": 10.5634
  },
  "cosine_similarity": 0.9876
}
```

---

## 📊 시각화 방법

```python
import matplotlib.pyplot as plt

# 1. Distribution 비교
plt.figure(figsize=(12, 4))

plt.subplot(131)
plt.hist(mobile_context.flatten().cpu(), bins=50, alpha=0.5, label='Mobile-VLA')
plt.hist(robovlms_context.flatten().cpu(), bins=50, alpha=0.5, label='RoboVLMs')
plt.legend()
plt.title('Context Distribution')

# 2. Heatmap
plt.subplot(132)
plt.imshow(mobile_context[0, 0].cpu(), cmap='viridis')
plt.title('Mobile-VLA Context')
plt.colorbar()

plt.subplot(133)
plt.imshow(robovlms_context[0, 0].cpu(), cmap='viridis')
plt.title('RoboVLMs Context')
plt.colorbar()

plt.savefig('context_comparison.png')
```

---

*실제 값 추출 스크립트 작성 완료, GPU 세션에서 실행 필요*
