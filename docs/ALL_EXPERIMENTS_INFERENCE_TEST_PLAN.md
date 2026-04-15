# 전체 실험 추론 테스트 계획 및 기록

**목표**: 모든 학습된 모델의 정확도(PM/DA)를 동일한 테스트셋으로 비교  
**방법**: API 서버에 각 모델을 로드하고 `detailed_error_analysis.py` 실행  
**테스트셋**: `ROS_action/basket_dataset_v2/test` (20 episodes, 343 frames)

---

## 📋 전체 실험 목록

| EXP ID | 실험명 | Window | Chunk | Visual | Action | Status | Checkpoint |
| :--- | :--- | :---: | :---: | :--- | :--- | :---: | :--- |
| **EXP-04** | Unified Baseline | 12 | 6 | Linear | Continuous | ✅ | `unified_regression_win12_20260205/epoch=9-step=600.ckpt` |
| **EXP-05** | Chunk k=1 | 12 | 1 | Linear | Continuous | ✅ | `unified_finetune_k1/...` |
| **EXP-06** | Visual Resampler | 12 | 6 | **Resampler 64** | Continuous | ✅ | `unified_reg_win12_k6_resampler_20260205/last.ckpt` |
| **EXP-09** | Resampler Latent 128 | 12 | 6 | **Resampler 128** | Continuous | ✅ | `exp09_resampler_latent128/last.ckpt` |
| **EXP-10** | Window 16 | **16** | 6 | Resampler 64 | Continuous | ⚠️ | `exp10_resampler_win16/last.ckpt` (Invalid) |

---

## 🔧 테스트 프로세스 (기존 방법 재현)

### 1단계: API 서버에 모델 등록

`api_server.py`의 `model_configs` 딕셔너리에 각 실험 추가:

```python
model_configs = {
    "exp04_baseline": {
        "checkpoint": "runs/.../unified_regression_win12_20260205/epoch=9-step=600.ckpt",
        "config": "Mobile_VLA/configs/mobile_vla_unified_regression_win12.json"
    },
    "exp05_chunk1": {
        "checkpoint": "runs/.../unified_finetune_k1/.../last.ckpt",
        "config": "Mobile_VLA/configs/mobile_vla_unified_reg_win12_k1.json"
    },
    "exp06_resampler": {
        "checkpoint": "runs/.../unified_reg_win12_k6_resampler_20260205/last.ckpt",
        "config": "Mobile_VLA/configs/mobile_vla_unified_reg_win12_k6_resampler.json"
    },
    "exp09_latent128": {
        "checkpoint": "runs/.../exp09_resampler_latent128/last.ckpt",
        "config": "Mobile_VLA/configs/mobile_vla_exp09_latent128.json"
    }
}
```

### 2단계: 각 모델별 API 서버 시작 및 테스트

```bash
# EXP-04 테스트
export VLA_MODEL_NAME="exp04_baseline"
pkill -f api_server.py && sleep 3
nohup python3 api_server.py > logs/api_server_exp04.log 2>&1 &
sleep 15
python3 scripts/test/detailed_error_analysis.py 2>&1 | tee logs/exp04_accuracy_test.log

# EXP-05 테스트
export VLA_MODEL_NAME="exp05_chunk1"
pkill -f api_server.py && sleep 3
nohup python3 api_server.py > logs/api_server_exp05.log 2>&1 &
sleep 15
python3 scripts/test/detailed_error_analysis.py 2>&1 | tee logs/exp05_accuracy_test.log

# ... (EXP-06, 09 반복)
```

### 3단계: 결과 추출

각 로그에서 전역 통계 추출:
```bash
grep -A 30 "📊 전역 통계" logs/exp04_accuracy_test.log
```

---

## 📊 과거 테스트 결과 (참고)

### EXP-04 (Baseline Linear)
- **PM/DA**: 65.83%
- **Initial**: 9.00%
- **Middle**: 97.37%
- **Final**: 70.53%

### EXP-06 (Visual Resampler 64)
- **PM/DA**: 82.50%
- **Initial**: 81.00%
- **Middle**: 83.55%
- **Final**: 80.00%

---

## 🚀 실행 계획

1. ✅ **체크포인트 경로 확인** (완료)
2. ⏳ **API 서버 설정 업데이트** (진행 중)
3. ⏳ **순차적 테스트 실행**
4. ⏳ **결과 종합 및 문서화**

---

**작성일**: 2026-02-09  
**테스트 시작**: 예정  
**예상 소요 시간**: ~2시간 (모델당 ~30분)
