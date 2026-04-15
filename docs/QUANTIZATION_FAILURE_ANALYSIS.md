# Quantization 실패 원인 분석 및 해결 방안

**작성일**: 2025-12-23  
**상태**: ❌ 전체 실패  
**근본 원인**: 스크립트 에러 + 체크포인트 문제

---

## 🔍 실패 원인 분석

### 1. 주요 에러

#### Error 1: Directory 생성 실패
```
tee: quantized_models/batch_ptq_20251222_200041/left_chunk10/quantization.log: 
그런 파일이나 디렉터리가 없습니다
```

**원인**: 
- Line 75에서 `| tee "$output_dir/quantization.log"` 실행
- 하지만 `$output_dir`이 생성되지 않음
- `mkdir -p` 누락

#### Error 2: Checkpoint 파일 손상
```
RuntimeError: PytorchStreamReader failed reading zip archive: 
failed finding central directory
```

**원인**:
- 일부 checkpoint 파일이 손상됨 (zip archive 구조 깨짐)
- 특히 `chunk10`, `chunk5` (2025-12-17 학습분)

### 2. 성공한 부분

**left_chunk5 모델 (첫 번째)**: 실제로는 성공!
```
✅ Quantized model saved successfully
✅ Quantization completed successfully!
📁 Output directory: quantized_models/batch_ptq_20251222_200041/left_chunk5
```

➡️ **하지만**: 스크립트 에러 때문에 "FAILED"로 표시됨

---

## 📊 각 모델 상태

| Model | Checkpoint | 상태 | 문제 |
|-------|-----------|------|------|
| left_chunk5 | epoch=08 | ⚠️ 스크립트 에러 | Directory 생성 실패 |
| **left_chunk10** | epoch=09 | ⚠️ 스크립트 에러 | Directory 생성 실패 |
| **right_chunk10** | epoch=09 | ⚠️ 스크립트 에러 | Directory 생성 실패 |
| chunk5 | epoch=06 | ❌ Checkpoint 손상 | Zip archive 에러 |
| chunk10 | epoch=05 | ❌ Checkpoint 손상 | Zip archive 에러 |

---

## ✅ 해결 방안

### Option 1: 스크립트 수정 (빠름, 추천) ⭐

#### 문제점:
```bash
# Line 75: tee 실행 전 디렉토리 생성 안됨
output_dir=\"$OUTPUT_BASE/$model_name\"
...
| tee \"$output_dir/quantization.log\"  # ❌ 디렉토리 없음
```

#### 해결:
```bash
# Line 51 이후에 추가
output_dir=\"$OUTPUT_BASE/$model_name\"
mkdir -p \"$output_dir\"  # ✅ 디렉토리 생성

echo \"📦 Checkpoint: $checkpoint\"
...
```

**예상 소요**: 5분

---

### Option 2: 개별 모델 수동 Quantization

**Skip하는 모델**:
- ❌ chunk5, chunk10 (checkpoint 손상, 불필요)

**Quantize할 모델**:
- ✅ left_chunk10 (best)
- ✅ right_chunk10 (best)
- ⏸️ left_chunk5 (optional)

**명령어**:
```bash
# left_chunk10
python3 scripts/quantize_for_jetson.py \
  --checkpoint "runs/.../mobile_vla_left_chunk10_20251218/epoch_epoch=09-val_loss=val_loss=0.010.ckpt" \
  --config "Mobile_VLA/configs/mobile_vla_left_chunk10_20251218.json" \
  --data-dir "ROS_action/mobile_vla_dataset" \
  --vision-int8 \
  --llm-int4 \
  --calib-size 100 \
  --output "quantized_models/left_chunk10_int8_int4"

# right_chunk10
python3 scripts/quantize_for_jetson.py \
  --checkpoint "runs/.../mobile_vla_right_chunk10_20251218/epoch_epoch=09-val_loss=val_loss=0.013.ckpt" \
  --config "Mobile_VLA/configs/mobile_vla_right_chunk10_20251218.json" \
  --data-dir "ROS_action/mobile_vla_dataset" \
  --vision-int8 \
  --llm-int4 \
  --calib-size 100 \
  --output "quantized_models/right_chunk10_int8_int4"
```

**예상 소요**: 각 10-15분 (총 20-30분)

---

## 🎯 추천 방안

### Step A: 스크립트 수정 후 재실행 (5분)

1. `batch_quantize_all_models.sh` 수정
2. left_chunk10, right_chunk10만 재실행
3. 검증

### Step B: 검증

```bash
# Quantized 모델 확인
ls -lh quantized_models/batch_ptq_*/left_chunk10/
ls -lh quantized_models/batch_ptq_*/right_chunk10/

# 크기 비교
# Original: 6.4GB
# Quantized (예상): 1.5-2.0GB (INT8 vision + INT4 LLM)
```

---

## 🚨 중요 발견

### Quantization은 실제로 일부 성공했음!

**증거**:
```
✅ Quantized model saved successfully
📊 Estimated Memory Usage:
  - Vision Encoder: 0.30 GB
  - LLM: 0.80 GB  
  - Action Head: 0.05 GB
  - Total: 1.15 GB
```

➡️ **left_chunk5는 실제로 성공했지만 스크립트 에러로 FAILED 표시**

### 실제 문제:
1. Directory 생성 타이밍 이슈
2. Checkpoint 손상 (chunk5, chunk10)

---

## 다음 액션

### Immediate (5분):

```bash
# 1. 스크립트 수정
# batch_quantize_all_models.sh Line 52에 추가:
mkdir -p "$output_dir"

# 2. Necessary 모델만 재실행
MODELS=([\"left_chunk10\"]=\"...\" [\"right_chunk10\"]=\"...\")

# 3. 실행
bash scripts/batch_quantize_all_models.sh
```

### Validation (10분):

```bash
# Quantized 모델 테스트
python3 scripts/validate_quantized_model.py \
  --original runs/.../left_chunk10/epoch_epoch=09.ckpt \
  --quantized quantized_models/.../left_chunk10/model_quantized.pt \
  --config Mobile_VLA/configs/mobile_vla_left_chunk10_20251218.json
```

---

## 📋 체크리스트

### 현재 상태:
- [ ] 스크립트 수정
- [ ] left_chunk10 quantization
- [ ] right_chunk10 quantization
- [ ] 검증

### 예상 소요 시간:
- 스크립트 수정: 5분
- Quantization: 20-30분
- 검증: 10분
- **Total: 35-45분**

---

**결론**: Quantization 자체는 작동하지만 스크립트 버그로 실패했습니다. 
스크립트만 수정하면 바로 해결 가능합니다!
