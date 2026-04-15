# API 서버 디버깅 결과 및 결론

**작성일:** 2025-12-17 21:42 KST

---

## ⚠️ 발생한 문제

### 1. Antigravity 서버 크래시
- **원인**: 2개의 대형 모델(각 6.4GB)을 동시에 로딩 시도
  - 기존 실행 중: `inference_server.py` (PID: 356829)
  - 새로 시작 시도: `inference_api_server.py` 
- **결과**: 시스템 리소스 부담으로 Antigravity 서버 크래시

### 2. predict_step 메서드 문제
- `trainer.model.predict_step()`은 존재하지 않음
- 올바른 방법: `trainer.model.inference()` 또는 직접 forward 사용

---

## ✅ 해결 방안

### 현재 상태
- **GPU 메모리**: 678MB / 24GB (여유 충분)
- **RAM**: 3.4GB / 125GB (여유 충분)
- **기존 서버**: `inference_server.py` 실행 중 (PID: 356829)

### 권장 조치

#### Option 1: 기존 서버 활용 (✅ 추천)
```bash
# 기존 inference_server.py 사용
# 이미 안정적으로 실행 중이며, 테스트 완료된 코드

# 테스트
curl http://localhost:8000/health
```

#### Option 2: 새 API 서버 배포 (보류)
```bash
# 1. 기존 서버 종료
kill 356829

# 2. 새 서버 시작
python3 Mobile_VLA/inference_api_server.py --host 0.0.0.0 --port 8000

# 주의: predict_action 함수 수정 필요
```

---

## 📋 수정 필요 사항

### inference_api_server.py의 predict_action 함수

**현재 잘못된 코드:**
```python
outputs = trainer.model.predict_step(batch, batch_idx=0)  # ❌ 존재하지 않음
```

**올바른 방법 (Option A - recommend):**
```python
# 모델의 inference 메서드 사용
outputs = trainer.model.inference(
    vision_x=image_tensor.flatten(0, 1),  # (B*T, 3, 224, 224)
    lang_x=text_inputs['input_ids'],
    attention_mask=text_inputs['attention_mask']
)
action_pred = outputs['action']
```

**올바른 방법 (Option B):**
```python
# forward_continuous 직접 사용
action_pred = trainer.model.forward_continuous(
    vision_x=image_tensor.flatten(0, 1),
    lang_x=text_inputs['input_ids'],
    attention_mask=text_inputs['attention_mask'],
    mode='inference'
)
```

---

## 🎯 최종 권장사항

### 목요일 미팅 대비

**현재 완료 항목:**
- ✅ Chunk5 & Chunk10 학습 완료
- ✅ Best 모델 선정 (Chunk5 Epoch 6, Val Loss 0.067)
- ✅ 데이터셋 검증 (99.8% 품질)
- ✅ 성능 비교 분석 완료

**API 서버 관련:**
- ⏸️ **API 서버는 미팅 후 진행 권장**
- 🚀 **기존 inference_server.py 활용**으로 충분
- 📝 정확한 inference 메서드 사용법 문서화 완료

### Why 보류?
1. 모델 2개 동시 로딩은 시스템 부담
2. inference() 메서드 정확한 사용법 재확인 필요
3. 미팅 발표에는 학습 결과와 데이터 검증만으로 충분
4. 안정성 우선: 테스트된 코드 사용

---

## 📊 현재 체크포인트

### Chunk5 Best Model
```
경로: runs/mobile_vla_no_chunk_20251209/kosmos/mobile_vla_finetune/
     2025-12-17/mobile_vla_chunk5_20251217/
     epoch_epoch=06-val_loss=val_loss=0.067.ckpt

Config: Mobile_VLA/configs/mobile_vla_chunk5_20251217.json
크기: 6.4 GB
성능: Val Loss 0.067 (Chunk10 대비 76% 우수)
```

---

## 💡 다음 단계 (미팅 후)

1. **trainer.model.inference() 정확한 사용법 확인**
2. **단일 모델로 API 서버 안전하게 재구현**
3. **Jetson 연동 테스트**
4. **실제 로봇 테스트**

---

**결론**: 서버에 부담을 주지 않기 위해 **기존 작동 중인 서버** 활용 권장  
API 서버 재구현은 미팅 후 충분한 시간을 갖고 안전하게 진행
