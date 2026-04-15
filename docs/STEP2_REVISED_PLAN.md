# Step 2: Quantized 모델 API 통합 계획

**작성일**: 2025-12-23  
**목표**: INT8/INT4 quantized 모델을 dual strategy API에 통합

---

## 현재 상황

### Quantized 모델 존재 확인

**위치**: `quantized_models/batch_ptq_20251222_200041/`

**구조**:
```
batch_ptq_20251222_200041/
├── left_chunk10/
│   ├── model_quantized.pt (5.5GB)
│   ├── config.json
│   └── model_info.json
├── left_chunk5/
├── right_chunk10/
└── quantization_summary.txt
```

### 문제점 분석

**Issue**: Quantized 모델 크기가 여전히 큼 (5.5GB)
- 원본: 6.4GB
- Quantized: 5.5GB
- 압축률: ~14% only

**원인 추정**:
1. Dynamic quantization (INT8)이 제한적
2. Embedding/Vision tower는 float으로 유지
3. Linear layer만 quantize됨

### 결정사항

**Option 1**: 현재 quantized 모델 skip ❌
- 압축 효과가 미미함
- API 복잡도 증가
- 성능 향상 불명확

**Option 2**: 성능 벤치마크 먼저 진행 ✅ (추천)
- FP32 모델 성능 먼저 완벽히 측정
- Quantized 모델은 Jetson 배포 시 필요하면 추가
- 현재는 dual strategy만으로 충분

**Option 3**: TensorRT/ONNX 변환 고려
- 더 aggressive한 최적화
- Jetson에 최적화됨
- 나중에 시도 가능

---

## 새로운 계획

### Step 2 수정: 성능 벤치마크로 변경

**목적**: 현재 dual strategy API 성능을 완벽히 문서화

**작업**:
1. ✅ Chunk Reuse 성능 측정 (완료)
2. ✅ Receding Horizon 성능 측정 (완료)
3. ⏳ **정량적 벤치마크 표 작성** (다음)
   - 다양한 시나리오
   - Left vs Right 모델
   - Chunk5 vs Chunk10
   - 성능 메트릭스 정리

### Step 3: 문서화 및 발표 준비

**작업**:
1. Performance benchmark table
2. 비교 그래프/차트
3. 교수님 미팅 자료
4. Jetson 배포 가이드

---

## Quantized 모델 통합 (보류)

### 보류 이유

1. **압축 효과 미미**: 6.4GB → 5.5GB (14%)
2. **복잡도 증가**: API 코드 복잡해짐
3. **우선순위 낮음**: FP32로도 충분히 빠름
4. **Jetson에서 재검토**: 실제 필요시 TensorRT 사용

### 나중에 재검토 조건

- Jetson에서 메모리 부족 발생 시
- 실시간 성능 부족 시 (현재는 20 FPS 달성 중)
- TensorRT 변환 시도 시

---

## 업데이트된 Priority 1 작업

### 완료 ✅
1. [x] API 서버 실제 테스트
   - Dual strategy 작동 확인
   - Chunk reuse 88.9% 달성
   - 2 inferences for 18 frames

### 진행 중 ⏳
2. **성능 벤치마크 문서화** (Step 2 수정)
   - 다양한 모델 테스트
   - 성능 메트릭스 수집
   - 비교 표 작성
   
3. **문서화 및 발표 준비** (Step 3)
   - README 업데이트
   - 교수님 미팅 자료
   - Performance guide

---

## 다음 액션

**Step 2 (수정)**: 성능 벤치마크 자동화 스크립트 작성

```bash
# 다음 작업: benchmark 스크립트
scripts/benchmark_all_models.py
  --models left_chunk10,right_chunk10,left_chunk5
  --strategies chunk_reuse,receding_horizon
  --output docs/PERFORMANCE_BENCHMARK.md
```

**예상 소요**: 1-2시간 (자동화)

---

**결론**: Quantized 모델 통합은 보류하고, 성능 벤치마크로 진행합니다.
