# BitsAndBytes INT8 - 체크포인트 설명

**중요**: BitsAndBytes는 별도 양자화 체크포인트 불필요!

---

## 핵심 개념

### BitsAndBytes INT8 = Post-Training Quantization (PTQ)

**작동 방식**:
```python
# 1. FP32 checkpoint 로드
checkpoint = torch.load("model.ckpt")  # FP32 그대로

# 2. BitsAndBytes config로 양자화 (자동)
bnb_config = BitsAndBytesConfig(load_in_8bit=True)
model = Model.from_pretrained(quantization_config=bnb_config)

# 3. 로딩 시점에 INT8로 변환 (메모리에서)
# 체크포인트는 FP32 그대로 유지!
```

**결론**: 
- ✅ **FP32 checkpoint 그대로 사용**
- ✅ **로딩 시 자동 INT8 변환**
- ✅ **별도 양자화 파일 불필요**

---

## 보내야 할 체크포인트

### ✅ 정답: FP32 Checkpoint (원본)

```
파일: epoch_epoch=06-val_loss=val_loss=0.067.ckpt
크기: 6.4 GB (FP32)
경로: runs/.../mobile_vla_chunk5_20251217/
```

**이것이 맞습니다!**
- Jetson에서 이 FP32 checkpoint를 로드
- `inference_server.py`가 BitsAndBytes config로 INT8 변환
- GPU에서 1.8GB만 사용 (6.4GB → 1.8GB)

---

## 왜 별도 양자화 파일이 없는가?

### PyTorch Static INT8 (이전 시도)
```python
# 별도 양자화 파일 생성 필요
model_int8 = quantize(model_fp32)
torch.save(model_int8, "model_int8.ckpt")  # 별도 저장

# Jetson에서 로드
model = torch.load("model_int8.ckpt")  # INT8 파일
```
❌ **이 방법은 실패했음** (CUDA 미지원)

---

### BitsAndBytes INT8 (현재 방법)
```python
# 양자화 파일 생성 불필요!
checkpoint = torch.load("model_fp32.ckpt")  # FP32 그대로

# 로딩 시 자동 변환
bnb_config = BitsAndBytesConfig(load_in_8bit=True)
model = MobileVLATrainer(config, quantization_config=bnb_config)
model.load_state_dict(checkpoint)  # 자동 INT8 변환
```
✅ **이 방법 사용 중**

---

## 실제 코드 확인

### inference_server.py (현재 구현)

```python
# Line 143-150
logger.info(f"\nLoading checkpoint: {self.checkpoint_path}")
checkpoint = torch.load(self.checkpoint_path, map_location='cpu')
# ↑ FP32 checkpoint 로드

# Line 146-152
bnb_config = BitsAndBytesConfig(
    load_in_8bit=True,
    llm_int8_threshold=6.0
)
# ↑ INT8 config

# Line 153-159
self.model = MobileVLATrainer(
    self.config,
    quantization_config=bnb_config  # ← 여기서 INT8 변환!
)
# ↑ 로딩 시점에 FP32 → INT8 자동 변환
```

**결과**:
- Checkpoint: 6.4 GB (FP32)
- GPU Memory: 1.8 GB (INT8)
- 차이: 자동 압축!

---

## 다른 양자화 방법과 비교

| 방법 | Checkpoint | 로딩 방식 |
|------|-----------|----------|
| **PyTorch Static** | INT8 별도 저장 | INT8 파일 로드 |
| **QAT** | INT8 별도 저장 | INT8 파일 로드 |
| **BitsAndBytes** | **FP32 원본** | **로딩 시 INT8 변환** |

**BitsAndBytes 장점**:
- ✅ 추가 파일 불필요
- ✅ FP32 checkpoint 재사용
- ✅ 동적 변환 (빠름)

---

## Jetson 배포 시나리오

### 1. Billy 서버
```bash
# FP32 checkpoint 전송
./scripts/transfer_to_jetson.sh jetson@ip

# 전송되는 것:
# - FP32 checkpoint (6.4 GB)
# - Config (10 KB)
```

### 2. Jetson
```bash
# Git clone
git clone ... && cd vla
git checkout inference-integration

# Checkpoint 압축 해제
tar -xzf checkpoint.tar.gz

# 서버 시작 (자동 INT8 변환)
python3 -m uvicorn Mobile_VLA.inference_server:app --host 0.0.0.0 --port 8000
```

### 3. 자동 변환
```python
# inference_server.py 내부에서:
# 1. FP32 checkpoint 로드
# 2. BitsAndBytes로 INT8 변환
# 3. GPU에 1.8GB로 로딩
```

**결과**:
- Disk: 6.4 GB (FP32 checkpoint)
- GPU: 1.8 GB (INT8 in memory)

---

## 검증

### Billy 서버에서 확인
```bash
# 현재 사용 중인 checkpoint
ls -lh runs/.../epoch_epoch=06-val_loss=val_loss=0.067.ckpt
# 6.4G (FP32)

# 이것을 그대로 전송!
```

### Jetson에서 확인
```bash
# 서버 시작 후
curl http://localhost:8000/health

# 결과:
{
    "gpu_memory": {
        "allocated_gb": 1.8  # ← INT8으로 자동 변환됨!
    }
}
```

---

## 요약

### ❌ 잘못된 생각
"양자화된 INT8 checkpoint를 별도로 만들어서 보내야 한다"

### ✅ 올바른 방법
"FP32 checkpoint를 그대로 보내면, Jetson의 inference_server.py가 로딩 시 자동으로 INT8로 변환한다"

### 보내야 할 파일
1. ✅ **FP32 Checkpoint** (6.4 GB)
   - `epoch_epoch=06-val_loss=val_loss=0.067.ckpt`
   
2. ✅ **Config** (10 KB)
   - `mobile_vla_chunk5_20251217.json`

3. ✅ **Code** (Git)
   - `inference_server.py` (BitsAndBytes config 포함)

### 별도로 필요 없는 것
- ❌ INT8 양자화된 checkpoint
- ❌ 양자화 스크립트
- ❌ 변환 과정

---

## 왜 이렇게 작동하는가?

### BitsAndBytes의 마법

```python
# transformers 라이브러리 내부
def from_pretrained(..., quantization_config):
    # 1. 원본 weights 로드 (FP32)
    weights = load_checkpoint(checkpoint_path)
    
    # 2. BitsAndBytes가 weights를 INT8로 변환
    if quantization_config.load_in_8bit:
        weights = convert_to_int8(weights)  # 자동!
    
    # 3. INT8 weights를 모델에 로딩
    model.load_state_dict(weights)
    
    return model  # INT8 model in GPU
```

**핵심**:
- Disk: FP32 (6.4 GB)
- Memory: INT8 (1.8 GB)
- 변환: 자동 (런타임)

---

**결론**: 
**FP32 checkpoint 그대로 보내면 됩니다!**
**Jetson의 inference_server.py가 알아서 INT8로 만듭니다!**
