# PTQ 배치 양자화 실행 가이드

**작성일**: 2025-12-22  
**목적**: 모든 best 모델들의 PTQ 양자화 및 비교

---

## 대상 모델 (5개)

| 모델명 | Checkpoint | Val Loss | 설명 |
|--------|-----------|----------|------|
| **left_chunk10** | epoch 9 | 0.010 | 🏆 **Best Overall** |
| **right_chunk10** | epoch 9 | 0.013 | Right turn 전용 |
| **left_chunk5** | epoch 8 | 0.016 | Left + shorter chunk |
| **chunk5** | epoch 6 | 0.067 | Baseline (양방향) |
| **chunk10** | epoch 5 | 0.284 | Baseline (긴 chunk) |

---

## 실행 방법

### 1단계: 배치 양자화 실행

```bash
cd /home/billy/25-1kp/vla

# 모든 모델 자동 양자화 (약 1~2시간)
bash scripts/batch_quantize_all_models.sh
```

**프로세스**:
- 각 모델별로 PTQ 적용 (Vision INT8 + LLM INT4)
- Calibration data 100 샘플 사용
- 결과를 `quantized_models/batch_ptq_YYYYMMDD_HHMMSS/` 저장

**예상 소요 시간**: 
- 모델당 10~15분
- 총 50~75분

---

### 2단계: 검증 및 비교

```bash
# 양자화 완료 후 (OUTPUT_DIR은 위 스크립트가 출력)
OUTPUT_DIR="quantized_models/batch_ptq_YYYYMMDD_HHMMSS"

bash scripts/validate_all_quantized.sh $OUTPUT_DIR
```

**검증 내용**:
- Direction Accuracy (원본 vs 양자화)
- Latency (ms)
- Memory usage (GB)
- Speedup ratio

**결과**:
- `validation_results/comparison_summary.md`: 모든 모델 비교표
- 개별 JSON 결과 파일

---

## 예상 결과

### 정확도 예측

| 모델 | FP16 Acc | PTQ Acc (예상) | 하락 |
|------|----------|----------------|------|
| left_chunk10 | 100% | 95~98% | 2~5%p |
| right_chunk10 | 100% | 95~98% | 2~5%p |
| left_chunk5 | 95% | 92~94% | 1~3%p |
| chunk5 | 90% | 87~89% | 1~3%p |
| chunk10 | 85% | 82~84% | 1~3%p |

---

### 메모리 예측

| 모델 | FP16 | PTQ (INT8/INT4) | 절감 |
|------|------|----------------|------|
| All | ~7.4 GB | ~4.0 GB | -46% |

**참고**: 모델 크기는 모두 동일 (Kosmos-2 1.6B)

---

### Latency 예측

| 모델 | FP16 | PTQ | Speedup |
|------|------|-----|---------|
| All | ~385ms | ~350ms | 1.1x |

---

## 출력 구조

```
quantized_models/batch_ptq_20251222_HHMMSS/
├── quantization_summary.txt           # 전체 요약
├── left_chunk10/
│   ├── model_quantized.pt            # 양자화 모델
│   ├── config.json
│   ├── model_info.json
│   └── quantization.log
├── right_chunk10/
│   └── ...
├── left_chunk5/
│   └── ...
├── chunk5/
│   └── ...
├── chunk10/
│   └── ...
└── validation_results/
    ├── comparison_summary.md         # ⭐ 비교 결과
    ├── left_chunk10_results.json
    ├── right_chunk10_results.json
    └── ...
```

---

## 비교 기준

### Best Model 선정 기준

1. **정확도 우선** (Accuracy > 95%)
   - Direction Accuracy 최소 95% 유지
   - 하락폭 5%p 이내

2. **메모리 효율**
   - 모두 동일 (~4GB)

3. **Latency**
   - 500ms 이하 (모두 충족 예상)

4. **종합 판단**
   - **left_chunk10**: Best 후보 (Val Loss 0.010)
   - PTQ 후에도 최고 성능 예상

---

## 트러블슈팅

### 문제 1: 메모리 부족

```bash
# GPU 메모리 확인
nvidia-smi

# 실행 중인 프로세스 종료
pkill -f python

# 스크립트 재실행
bash scripts/batch_quantize_all_models.sh
```

---

### 문제 2: 특정 모델 실패

**개별 실행**:
```bash
python3 scripts/quantize_for_jetson.py \
    --checkpoint runs/.../model.ckpt \
    --config Mobile_VLA/configs/config.json \
    --data-dir ROS_action/mobile_vla_dataset \
    --vision-int8 --llm-int4 \
    --calib-size 100 \
    --output quantized_models/manual/model_name
```

---

## 다음 단계

양자화 및 검증 완료 후:

1. **Best 모델 선정**
   ```bash
   # comparison_summary.md 확인
   cat quantized_models/batch_ptq_*/validation_results/comparison_summary.md
   ```

2. **Jetson 배포 준비**
   ```bash
   # Best 모델 복사
   cp quantized_models/batch_ptq_*/left_chunk10/* quantized_models/jetson_deploy/
   ```

3. **Inference server 테스트**
   ```bash
   export VLA_USE_QUANTIZATION=true
   export VLA_QUANTIZED_CHECKPOINT="quantized_models/jetson_deploy/model_quantized.pt"
   python Mobile_VLA/inference_server.py
   ```

4. **Jetson 전송** (장비 도착 후)
   ```bash
   rsync -avz quantized_models/jetson_deploy/ jetson@<IP>:/home/jetson/vla/
   ```

---

## 실행 체크리스트

- [ ] Billy 서버 GPU 메모리 확인 (24GB 중 여유 확인)
- [ ] 배치 양자화 실행 (`batch_quantize_all_models.sh`)
- [ ] 양자화 완료 확인 (summary.txt 확인)
- [ ] 검증 실행 (`validate_all_quantized.sh`)
- [ ] 비교 결과 리뷰 (comparison_summary.md)
- [ ] Best 모델 선정
- [ ] Jetson 배포 준비

---

**준비 완료! 실행하시겠습니까?**
