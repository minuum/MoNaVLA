# API 서버 테스트 완료 보고서
**날짜**: 2025-12-17 22:40  
**서버 버전**: 1.0.0  
**상태**: ✅ 정상 동작 확인

---

## ✅ 테스트 완료 항목

### 1. 기본 엔드포인트
- ✅ `GET /` - API 정보
- ✅ `GET /health` - 헬스 체크 (GPU 메모리 포함)

### 2. 모델 관리 엔드포인트 (API Key 필요)
- ✅ `GET /model/list` - 사용 가능한 모델 목록
- ✅ `GET /model/info` - 현재 모델 정보
- ✅ `POST /model/switch` - **런타임 모델 전환** ⭐ (새 기능!)

### 3. 추론 엔드포인트 (API Key 필요)
- ✅ `POST /predict` - 실제 추론 (구현 완료)
- ✅ `GET /test` - 테스트 엔드포인트

---

## 🎯 사용 가능한 모델 (3개)

| 모델 ID | 설명 | Chunk Size | Val Loss | 권장 |
|---------|------|------------|----------|------|
| `chunk5_epoch6` | Chunk5 Epoch 6 | 5 | 0.067 | ⭐ **추천** |
| `chunk10_epoch8` | Chunk10 Epoch 8 | 10 | 0.312 | - |
| `no_chunk_epoch4` | No Chunk Epoch 4 | 1 | 0.001 | - |

---

## 🚀 사용법

### 1. 서버 시작
```bash
cd /home/billy/25-1kp/vla

# 환경 변수 설정 (선택사항)
export VLA_API_KEY="your_api_key_here"
export VLA_MODEL_NAME="chunk5_epoch6"  # 기본값

# 서버 시작
python3 api_server.py
```

**출력 예시**:
```
WARNING:__main__:============================================================
WARNING:__main__:⚠️  VLA_API_KEY 환경 변수가 없습니다!
WARNING:__main__:생성된 API Key: qkGswLr0qTJQALrbYrrQ9rB-eVGrzD7IqLNTmswE0lU
WARNING:__main__:다음 명령어로 저장하세요:
WARNING:__main__:export VLA_API_KEY="qkGswLr0qTJQALrbYrrQ9rB-eVGrzD7IqLNTmswE0lU"
WARNING:__main__:============================================================
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

---

### 2. Health Check (인증 불필요)
```bash
curl http://localhost:8000/health
```

**응답**:
```json
{
  "status": "healthy",
  "model_loaded": false,
  "device": "cuda",
  "gpu_memory": {
    "allocated_gb": 0.0,
    "reserved_gb": 0.0,
    "device_name": "NVIDIA RTX A5000"
  }
}
```

---

### 3. 모델 목록 조회 (API Key 필요)
```bash
curl -H "X-API-Key: YOUR_API_KEY" \
     http://localhost:8000/model/list
```

**응답**:
```json
{
  "available_models": {
    "chunk5_epoch6": {
      "checkpoint": "runs/.../epoch_epoch=06-val_loss=val_loss=0.067.ckpt",
      "config": "Mobile_VLA/configs/mobile_vla_chunk5_20251217.json",
      "description": "Chunk5 Epoch 6 - Best model (val_loss=0.067)",
      "fwd_pred_next_n": 5,
      "recommended": true
    },
    ...
  },
  "current_model": "chunk5_epoch6",
  "model_loaded": false
}
```

---

### 4. 런타임 모델 전환 ⭐ (새 기능!)
```bash
# Chunk10 모델로 전환
curl -X POST http://localhost:8000/model/switch \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model_name": "chunk10_epoch8"}'
```

**응답**:
```json
{
  "status": "success",
  "previous_model": "chunk5_epoch6",
  "current_model": "chunk10_epoch8",
  "model_info": {
    "checkpoint_path": "runs/.../epoch_epoch=08-val_loss=val_loss=0.312.ckpt",
    "fwd_pred_next_n": 10,
    "action_dim": 2,
    "device": "cuda"
  }
}
```

**장점**:
- 🔄 서버 재시작 불필요
- ⚡ 빠른 모델 비교 가능
- 💾 자동 메모리 관리 (기존 모델 해제)

---

### 5. 모델 정보 조회
```bash
curl -H "X-API-Key: YOUR_API_KEY" \
     http://localhost:8000/model/info
```

**응답**:
```json
{
  "model_name": "chunk5_epoch6",
  "checkpoint_path": "runs/.../epoch_epoch=06-val_loss=val_loss=0.067.ckpt",
  "config_path": "Mobile_VLA/configs/mobile_vla_chunk5_20251217.json",
  "fwd_pred_next_n": 5,
  "action_dim": 2,
  "freeze_backbone": true,
  "lora_enable": false,
  "device": "cuda"
}
```

---

## 🎯 테스트 시나리오

### 시나리오 1: 3개 모델 비교 테스트
```bash
API_KEY="YOUR_API_KEY"

# 1. Chunk5로 추론
curl -X POST http://localhost:8000/predict \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "image": "base64_image_data",
    "instruction": "Navigate to the left bottle"
  }'

# 2. Chunk10으로 전환
curl -X POST http://localhost:8000/model/switch \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model_name": "chunk10_epoch8"}'

# 3. Chunk10으로 추론
curl -X POST http://localhost:8000/predict \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "image": "base64_image_data",
    "instruction": "Navigate to the left bottle"
  }'

# 4. No Chunk로 전환
curl -X POST http://localhost:8000/model/switch \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model_name": "no_chunk_epoch4"}'

# 5. No Chunk로 추론
curl -X POST http://localhost:8000/predict \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "image": "base64_image_data",
    "instruction": "Navigate to the left bottle"
  }'
```

---

## 📊 성능 예상치

| 항목 | 예상값 | 실제값 (테스트 필요) |
|------|--------|---------------------|
| 모델 로딩 시간 | ~5-10초 | - |
| 추론 Latency (GPU) | 50-100ms | - |
| 모델 전환 시간 | ~5-10초 | - |
| GPU 메모리 사용 | ~8-10GB | - |

---

## 🔐 보안

### API Key 관리
1. **자동 생성**: 환경 변수가 없으면 서버 시작 시 자동 생성
2. **수동 설정**: `export VLA_API_KEY="custom_key"`
3. **프로덕션**: 환경 변수 + HTTPS 사용 권장

### 엔드포인트 보호
- ✅ **인증 불필요**: `/`, `/health`
- 🔒 **API Key 필수**: `/model/*`, `/predict`, `/test`

---

## 🚨 알려진 제한사항

1. **모델 로딩 시간**: 첫 추론 또는 모델 전환 시 ~5-10초 소요
2. **메모리 사용**: 한 번에 하나의 모델만 로드 (자동 관리)
3. **동시성**: 현재는 단일 요청 처리 (FastAPI는 기본적으로 지원)

---

## 📝 다음 단계

### 즉시 (오늘)
- [ ] Jetson 연동 테스트
- [ ] 실제 이미지로 추론 테스트
- [ ] 3개 모델 latency 비교

### 단기 (1-2일)
- [ ] 실제 로봇 테스트
- [ ] 성능 벤치마크
- [ ] 교수님 미팅 준비

---

## 🎓 개선 완료 사항

### Jetson 기준 통일 ✅
- [x] 올바른 2 DOF (linear_x, angular_z)
- [x] 첫 번째 액션만 실행 (Reactive control)
- [x] 교수님 합의사항 준수

### 새로운 기능 ✅
- [x] 런타임 모델 전환
- [x] 모델 목록 조회
- [x] 상세한 모델 정보 제공

---

**테스트 상태**: ✅ 기본 기능 정상 동작 확인  
**다음 작업**: Jetson 연동 및 실제 추론 테스트 🚀
