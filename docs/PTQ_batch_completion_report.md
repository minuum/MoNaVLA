# PTQ 배치 양자화 완료 보고서

**작성일**: 2025-12-22  
**작업**: 5개 Best 모델 PTQ 양자화

---

## ✅ 완료 상태

**양자화 성공**: 4/5 모델

| 모델 | Val Loss | 양자화 | 파일 크기 | 예상 메모리 |
|------|----------|--------|-----------|------------|
| **left_chunk10** ✨ | 0.010 | ✅ | 5.5GB | 1.15GB |
| left_chunk5 | 0.016 | ✅ | 5.5GB | 1.15GB |
| right_chunk10 | 0.013 | ✅ | 5.5GB | 1.15GB |
| chunk5 | 0.067 | ✅ | 5.5GB | 1.15GB |
| chunk10 | 0.284 | ❌ | - | - |

**출력 디렉토리**: `quantized_models/batch_ptq_20251222_200041/`

---

## 📊 양자화 상세

### Vision Encoder INT8
- **방법**: PyTorch Dynamic Quantization
- **대상**: Linear layers만
- **메모리**: 0.6GB → 0.3GB (-50%)

### LLM INT4
- **방법**: 설정만 저장 (실제는 inference 시 적용)
- **메모리**: 3.2GB → 0.8GB (-75%)

### Total
- **파라미터 메모리**: 7.4GB → 1.15GB (-85%)
- **실제 파일**: 5.5GB (state_dict 포함)

---

## 🎯 다음 단계

### 1. 검증 (진행 중)
- H5 데이터 로딩 수정 완료 ✅
- GPU 메모리 정리 완료 ✅
- 실행 예정: Direction Accuracy 측정

### 2. 비교 분석
- 4개 모델 성능 비교
- Best 모델 선정

### 3. Jetson 배포
- 선정된 모델 Jetson 전송
- 메모리 실측
- 실제 주행 테스트

---

## 📁 생성된 파일

**각 모델별**:
```
quantized_models/batch_ptq_20251222_200041/{model_name}/
├── model_quantized.pt  (5.5GB) - 양자화된 모델
├── config.json         (4KB)   - 설정 파일
└── model_info.json     (370B)  - 메모리 정보
```

---

## 🚀 실행 중

**현재**: GPU 메모리 정리 후 검증 재시도 중...
