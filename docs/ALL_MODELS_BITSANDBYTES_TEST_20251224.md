# All Models BitsAndBytes INT8 Test Results

**일시**: 2025-12-24 04:57 KST  
**방법**: BitsAndBytes INT8 Quantization

---

## 📊 테스트 결과

### Chunk5 Best (Val Loss 0.067)
- ✅ **Status**: SUCCESS
- **GPU Memory**: 1.74 GB
- **Latency**: 515 ms
- **Config**: `mobile_vla_chunk5_20251217.json`

### Left Chunk10 Best (Val Loss 0.010)
- ⏳ **Status**: Config 경로 수정 후 재테스트 필요
- **Config**: `mobile_vla_left_chunk10_20251218.json`

### Right Chunk10 Best (Val Loss 0.013)
- ⏳ **Status**: Config 경로 수정 후 재테스트 필요
- **Config**: `mobile_vla_right_chunk10_20251218.json`

---

## ✅ 현재 성과

**Chunk5 Best 모델**:
- GPU 메모리: **1.74 GB** (FP32 6.3GB 대비 72% 절감)
- Latency: **515 ms** (F P32 15s 대비 96% 개선)
- **완벽하게 작동!** ⭐⭐⭐

---

## 🎯 최종 요약

| Model | Config Found | Test Status | GPU Mem | Latency |
|-------|--------------|-------------|---------|---------|
| **Chunk5** | ✅ | ✅ SUCCESS | 1.74 GB | 515 ms |
| **Left Chunk10** | ✅ | ⏳ Pending | - | - |
| **Right Chunk10** | ✅ | ⏳ Pending | - | - |

**BitsAndBytes INT8 작동 확인!** 🎉
