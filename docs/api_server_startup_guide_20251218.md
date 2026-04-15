# API 서버 시작 가이드 (Billy 서버)
**날짜**: 2025-12-18 14:30  
**상태**: ✅ API 서버 정상 실행 중 (테스트 통과)  
**PID**: 630600  
**포트**: 8000  
**GPU 메모리**: 13.6GB (모델 로드됨)

---

## 📋 수행한 작업

### 1. 경로 수정 완료 ✅
- `.vla_aliases` 및 `manage_api_server.sh` 경로 수정 (`/home/soda/vla` → `/home/billy/25-1kp/vla`)

### 2. API 서버 코드 수정 ✅
- `api_server.py`: `verify_api_key` 함수에서 `None` 타입 에러 수정 (API Key 없이 요청 시 500 에러 → 403 Forbidden으로 정상 처리)

### 3. 테스트 스크립트 수정 ✅
- `scripts/test_inference_api.py`: API Key(`VLA_API_KEY`)를 환경 변수에서 읽어 헤더에 포함하도록 수정

### 4. 서버 시작 및 테스트 완료 ✅
- **서버 시작**:
  ```bash
  export VLA_API_KEY="qkGswLr0qTJQALrbYrrQ9rB-eVGrzD7IqLNTmswE0lU"
  export VLA_MODEL_NAME="chunk5_epoch6"
  ./scripts/manage_api_server.sh restart
  ```
- **테스트 결과**:
  - `python3 scripts/test_inference_api.py` → **All PASS** ✅
  - 모델 로딩 성공 (Chunk5 Epoch 6)

---

## 🔧 현재 서버 상태

### Health Check
```json
{
    "status": "healthy",
    "model_loaded": true,  <-- 모델 로드됨!
    "device": "cuda",
    "gpu_memory": { ... }
}
```

### 실행 중인 모델
- **Model**: `chunk5_epoch6`
- **Checkpoint**: `.../mobile_vla_chunk5_20251217/epoch_epoch=06-val_loss=val_loss=0.067.ckpt`
- **Action Space**: [linear_x, linear_y]

---

## 🚀 API 사용법

### 1. 추론 요청 (Python 예시)
```python
import requests
import base64

# 이미지 인코딩
with open("image.jpg", "rb") as f:
    img_base64 = base64.b64encode(f.read()).decode('utf-8')

# API 요청
response = requests.post(
    "http://localhost:8000/predict",
    headers={"X-API-Key": "mobile_vla_secret_key_billy_2025"},
    json={
        "image": img_base64,
        "instruction": "Navigate to the left bottle"
    }
)

print(response.json())
# {'action': [0.5, 0.1], 'latency_ms': 85.2, ...}
```

---

## 🎯 다음 단계

### 1. Jetson 연동
- Jetson 서버에서 `export VLA_API_SERVER="http://BILLY_IP:8000"` 설정
- `ros2 run mobile_vla_package api_client_node` 실행하여 연동 확인

### 2. 실제 데이터셋 테스트 (선택)
- `python3 scripts/test_api_real_data.py` 실행하여 L/R 정확도 검증

### 3. 성능 최적화 (필요 시)
- 현재 Latency 모니터링
- 필요 시 `torch.compile` 등 적용 검토

---

**트러블슈팅**:
- **403 Forbidden**: Header에 `X-API-Key`가 없는 경우입니다. 클라이언트 코드를 확인하세요.
- **500 Internal Server Error**: 서버 로그(`logs/api_server.log`)를 확인하세요.
