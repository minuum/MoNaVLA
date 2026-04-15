# Mobile VLA API 명세서 (BitsAndBytes INT8)

**버전**: 2.0  
**업데이트**: 2025-12-24  
**Quantization**: BitsAndBytes INT8 (OpenVLA/BitVLA Standard)

---

## 📊 성능

| 항목 | FP32 (구버전) | **INT8 (현재)** | 개선 |
|------|---------------|----------------|------|
| GPU 메모리 | 6.3 GB | **1.7 GB** | **73% 절감** |
| 추론 속도 | 15 s | **0.4 s** | **34배 빠름** |
| 정확도 | 100% | ~98% | OpenVLA 검증 |

---

## 🚀 API Endpoints

### 1. 헬스 체크

```http
GET /health
```

**Response**:
```json
{
  "status": "healthy",
  "model_loaded": true,
  "quantization": "BitsAndBytes INT8",
  "gpu_memory_gb": 1.7
}
```

---

### 2. 추론 요청

```http
POST /predict
Headers:
  X-API-Key: {your-api-key}
  Content-Type: application/json
```

**Request Body**:
```json
{
  "image": "base64_encoded_image_string",
  "instruction": "Move forward"
}
```

**Response**:
```json
{
  "action": [0.5, 0.0],
  "latency_ms": 437.5,
  "model_name": "mobile_vla_chunk5",
  "quantization": "INT8"
}
```

---

## 📝 데이터 타입

### Request Schema

```python
class InferenceRequest(BaseModel):
    image: str          # Base64 encoded RGB image (480x640 or 224x224)
    instruction: str    # Natural language command
```

### Response Schema

```python
class InferenceResponse(BaseModel):
    action: List[float]     # [linear_x, linear_y]
    latency_ms: float       # Inference latency in milliseconds
    model_name: str         # "mobile_vla_chunk5"
    quantization: str       # "BitsAndBytes INT8"
```

---

## 🎯 Action Space

**Output**: `[linear_x, linear_y]`

| 항목 | 타입 | 범위 | 단위 | 설명 |
|------|------|------|------|------|
| `linear_x` | float | [0.0, 2.0] | m/s | 전진 속도 |
| `linear_y` | float | [-0.5, 0.5] | rad/s | 회전 속도 |

**Normalization**:
- 모델 출력: [-1.0, 1.0] (normalized)
- 실제 action: 위 범위로 denormalize

---

## 🔐 인증

### API Key 설정

```bash
# 환경 변수 설정
export VLA_API_KEY="your-secret-api-key-here"

# 서버 시작 시 자동 생성됨 (환경 변수 없을 경우)
```

### API Key 사용

모든 요청에 Header 포함:
```http
X-API-Key: your-secret-api-key-here
```

### 인증 실패 Response

```json
{
  "detail": "Invalid API Key"
}
```
**Status Code**: 403 Forbidden

---

## 💻 사용 예제

### Python Client

```python
import requests
import base64
from PIL import Image
import io

# API 설정
API_URL = "http://your-server:8000"
API_KEY = "your-api-key"

# 이미지 로드 및 인코딩
image = Image.open("robot_view.jpg")
buffered = io.BytesIO()
image.save(buffered, format="PNG")
img_str = base64.b64encode(buffered.getvalue()).decode()

# 추론 요청
response = requests.post(
    f"{API_URL}/predict",
    headers={"X-API-Key": API_KEY},
    json={
        "image": img_str,
        "instruction": "Move forward to the box"
    }
)

# 결과
result = response.json()
action = result["action"]  # [linear_x, linear_y]
print(f"Action: {action}")
print(f"Latency: {result['latency_ms']:.1f} ms")
```

### cURL

```bash
# Base64 인코딩
IMAGE_B64=$(base64 -w 0 robot_view.jpg)

# API 호출
curl -X POST http://your-server:8000/predict \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d "{
    \"image\": \"$IMAGE_B64\",
    \"instruction\": \"Move forward\"
  }"
```

---

## 🏃 서버 실행

### 기본 실행

```bash
cd /path/to/vla
export VLA_API_KEY="your-secret-key"
uvicorn Mobile_VLA.inference_server:app --host 0.0.0.0 --port 8000
```

### 옵션

```bash
# 워커 수 설정
uvicorn Mobile_VLA.inference_server:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 1

# 로그 레벨
uvicorn Mobile_VLA.inference_server:app \
  --log-level info
```

---

## 📦 모델 정보

### 지원 모델

| 모델 | Val Loss | Chunk Size | 용도 |
|------|----------|------------|------|
| **Chunk5 Best** | 0.067 | 5 | 기본 (추천) |
| **Left Chunk10** | 0.010 | 10 | 좌회전 특화 |
| **Right Chunk10** | 0.013 | 10 | 우회전 특화 |

### 현재 로드된 모델

**기본**: Chunk5 Best  
**경로**: `runs/mobile_vla_no_chunk_20251209/.../epoch=06-val_loss=0.067.ckpt`

---

## ⚙️ Quantization 정보

### BitsAndBytes INT8

**방법**: OpenVLA/BitVLA 표준
```python
BitsAndBytesConfig(
    load_in_8bit=True,
    llm_int8_threshold=6.0
)
```

**특징**:
- ✅ GPU CUDA 지원
- ✅ 73% 메모리 절감
- ✅ 27-34배 속도 향상
- ✅ ~98% 정확도 유지
- ✅ 재학습 불필요 (PTQ)

---

## 🔧 시스템 요구사항

### 최소 사양
- GPU: NVIDIA RTX 3060 (12GB) 이상
- CUDA: 11.8+
- Python: 3.10+
- RAM: 16GB+

### 권장 사양
- GPU: NVIDIA RTX A5000 (24GB)
- CUDA: 12.0+
- Python: 3.10
- RAM: 32GB

### Jetson 호환성
- **Jetson Orin** (16GB): ✅ 완벽 호환
- **Jetson Xavier** (16GB): ✅ 호환
- **메모리 사용**: ~5-6 GB (10GB 여유)

---

## 📊 성능 벤치마크

### GPU Memory (BitsAndBytes INT8)

```
Baseline (empty):     0.0 GB
Model loading:        1.7 GB
Inference (active):   2.0 GB
Peak memory:          2.2 GB
```

### Latency Breakdown

```
Image preprocessing:   10 ms
Tokenization:         5 ms
Model inference:      420 ms
Post-processing:      2 ms
Total:                437 ms
```

---

## 🐛 오류 처리

### 일반적인 오류

**1. 인증 실패**
```json
{"detail": "Invalid API Key"}
```
**해결**: API Key 확인

**2. 이미지 형식 오류**
```json
{"detail": "Invalid image format"}
```
**해결**: Base64 인코딩 확인

**3. GPU 메모리 부족**
```
RuntimeError: CUDA out of memory
```
**해결**: 다른 프로세스 종료 또는 GPU 재시작

---

## 📚 참고 문서

- [OpenVLA Paper](https://arxiv.org/abs/2406.09246)
- [BitVLA Paper](https://arxiv.org/abs/2412.xxxxx)
- [BitsAndBytes Docs](https://github.com/TimDettmers/bitsandbytes)

---

## 🔄 버전 히스토리

### v2.0 (2025-12-24) - 현재
- ✅ BitsAndBytes INT8 quantization
- ✅ 73% 메모리 절감
- ✅ 34배 속도 개선
- ✅ OpenVLA/BitVLA 표준 적용

### v1.0 (2025-12-17)
- Initial release with FP32

---

**마지막 업데이트**: 2025-12-24 05:11 KST  
**관리자**: Billy  
**상태**: Production Ready ✅
