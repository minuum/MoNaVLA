# Dual Strategy Inference API

**Status**: ⏳ In Progress  
**목표**: Chunk Reuse와 Receding Horizon 전략 모두 지원하는 API 구현

---

## 완료된 작업

### ✅ Phase 1: 기반 구현
- [x] ActionBuffer 클래스 생성 (`Mobile_VLA/action_buffer.py`)
- [x] API 요청/응답 스키마 수정 (`strategy` 파라미터 추가)
- [x] InferenceRequest에 `Literal["chunk_reuse", "receding_horizon"]` 추가
- [x] InferenceResponse에 `strategy`, `source`, `buffer_status` 추가

---

## 🚧 진행 중

### Phase 2: 핵심 로직 구현

**파일**: `Mobile_VLA/inference_server_v2.py` (작업 중)

**필요 작업**:
1. `MobileVLAInference.predict()` 메서드 수정
   - `strategy` 파라미터 수용
   - `_predict_chunk_reuse()` 호출 또는  
   - `_predict_receding_horizon()` 호출
   
2. 새 메서드 추가:
   - `_predict_chunk_reuse()`: Buffer 확인 → 재사용 또는 추론
   - `_predict_receding_horizon()`: 항상 추론
   - `_extract_action_chunk()`: 모델 출력에서 action chunk 추출
   - `_do_inference_chunk()`: Chunk 전체 추론 및 buffer 저장
   - `_do_inference_single()`: 단일 action만 추론

3. FastAPI endpoint 수정 (`/predict`):
   - `request.strategy` 전달
   - 4개 반환값 처리 (`action, latency_ms, source, buffer_status`)

---

## 📋 남은 작업

### Phase 3: 테스팅 (예정)
- [ ] `test_dual_strategy.py` 스크립트 작성
- [ ] 18 프레임 테스트 (chunk_reuse: 2회 추론)
- [ ] 18 프레임 테스트 (receding_horizon: 18회 추론)
- [ ] 성능 비교 검증

### Phase 4: 문서화 (예정)
- [ ] API Spec 업데이트
- [ ] Usage examples
- [ ] Performance guide

---

## 💡 다음 단계

**현재 상황**: 파일 수정 중 에러 발생  
**이유**: inference_server.py가 크고 복잡하여 정확한 라인 매칭 어려움

**해결 방안** (선택):

### Option A: 점진적 수정
1. 기존 `predict()` 메서드를 `_old_predict()`로 rename
2. 새로운 `predict()` wrapper 추가
3. Helper 메서드들 하나씩 추가

### Option B: 새 파일

 완전 작성
1. `inference_server_dual.py` 새로 작성
2. 깔끔한 구조로 처음부터
3. 테스트 후 기존 파일 교체

### Option C: 수동 가이드 제공
1. 필요한 변경사항을 명확히 문서화
2. 사용자가 직접 적용
3. 코드 리뷰 후 테스트

---

## 🎯 권장사항

**Option B** 추천: 새 파일 작성
- 깔끔한 코드
- 테스트 용이
- 기존 서버 안전하게 유지

**예상 소요 시간**: 30-60분

사용자 확인 필요: 어떤 방향으로 진행할까요?
