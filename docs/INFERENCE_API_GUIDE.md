# Mobile VLA Inference API 사용 가이드

## 📋 개요

Chunk10 Epoch 8 모델을 사용한 실시간 인퍼런스 API 서버입니다.

**모델 정보:**
- Model: Mobile VLA Chunk10
- Checkpoint: Epoch 8 (val_loss=0.312)
- Action Chunking: 10 steps
- Frozen VLM: Kosmos-2

## 🚀 서버 시작

### 기본 실행
```bash
cd /home/billy/25-1kp/vla
python3 Mobile_VLA/inference_api_server.py
```

### 옵션 지정
```bash
python3 Mobile_VLA/inference_api_server.py \
    --host 0.0.0.0 \
    --port 8000 \
    --reload  # 개발 모드 (자동 리로드)
```

### 백그라운드 실행
```bash
nohup python3 Mobile_VLA/inference_api_server.py > logs/api_server.log 2>&1 &
```

## 📡 API Endpoints

### 1. Health Check
```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "device": "cuda"
}
```

### 2. Model Info
```bash
curl -H "X-API-Key: vla_mobile_robot_2025" \
     http://localhost:8000/model/info
```

**Response:**
```json
{
  "model_name": "mobile_vla_chunk10_20251217",
  "fwd_pred_next_n": 10,
  "window_size": 8,
  "freeze_backbone": true,
  "lora_enable": false,
  "device": "cuda"
}
```

### 3. Action Prediction
```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -H "X-API-Key: vla_mobile_robot_2025" \
  -d '{
    "image": "base64_encoded_image_here",
    "instruction": "Navigate to the left bottle"
  }'
```

**Response:**
```json
{
  "linear_x": 0.1234,
  "linear_y": -0.5678,
  "instruction": "Navigate to the left bottle",
  "model_name": "mobile_vla_chunk10_epoch08"
}
```

## 🧪 테스트

### 자동 테스트 스크립트
```bash
python3 scripts/test_inference_api.py

# 커스텀 설정
python3 scripts/test_inference_api.py \
    --host localhost \
    --port 8000 \
    --api-key vla_mobile_robot_2025
```

### Python 클라이언트 예제
```python
import requests
import base64
from PIL import Image
import io

# Load image
image = Image.open("test_image.jpg").convert('RGB')

# Convert to base64
buffered = io.BytesIO()
image.save(buffered, format="PNG")
img_b64 = base64.b64encode(buffered.getvalue()).decode()

# API Request
response = requests.post(
    "http://localhost:8000/predict",
    json={
        "image": img_b64,
        "instruction": "Navigate to the left bottle"
    },
    headers={"X-API-Key": "vla_mobile_robot_2025"}
)

result = response.json()
print(f"Linear X: {result['linear_x']}")
print(f"Linear Y: {result['linear_y']}")
```

## 🔐 보안

### API Key 설정
**기본 API Key:** `vla_mobile_robot_2025`

**변경 방법:**
`Mobile_VLA/inference_api_server.py` 파일에서:
```python
API_KEY = "your_new_api_key_here"
```

### 프로덕션 배포 시
- 환경 변수로 API Key 관리
- HTTPS 사용
- Rate limiting 추가
- 로깅 강화

## 📊 성능

**예상 Latency:**
- 모델 로딩: ~5초 (최초 1회)
- Inference: ~50-100ms/request (GPU)

**GPU 메모리 사용:**
- ~10GB VRAM

## 🔧 문제 해결

### 모델 로딩 실패
```bash
# 체크포인트 경로 확인
ls runs/mobile_vla_no_chunk_20251209/kosmos/mobile_vla_finetune/2025-12-17/mobile_vla_chunk10_20251217/

# 권한 확인
chmod 644 runs/mobile_vla_no_chunk_20251209/kosmos/mobile_vla_finetune/2025-12-17/mobile_vla_chunk10_20251217/*.ckpt
```

### Port 충돌
```bash
# 다른 포트 사용
python3 Mobile_VLA/inference_api_server.py --port 8001
```

### CUDA Out of Memory
```bash
# CPU 모드로 실행
CUDA_VISIBLE_DEVICES= python3 Mobile_VLA/inference_api_server.py
```

## 📝 로그 확인

### 실시간 로그
```bash
tail -f logs/api_server.log
```

### 프로세스 확인
```bash
ps aux | grep inference_api_server
```

## 🤖 Jetson 연동

### Tailscale로 연결
```bash
# Billy 서버 주소 확인
tailscale ip

# Jetson에서 접속
curl http://BILLY_TAILSCALE_IP:8000/health
```

### ROS2 Client 예제
`ros2_client/vla_api_client.py` 참조

## 📚 추가 자료

- **API Documentation:** http://localhost:8000/docs (자동 생성)
- **OpenAPI Spec:** http://localhost:8000/openapi.json
- **Secure API Guide:** `SECURE_API_GUIDE.md`

---

**작성일:** 2025-12-17  
**Model:** Chunk10 Epoch 8  
**Status:** ✅ Ready for deployment
