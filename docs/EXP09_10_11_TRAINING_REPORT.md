# EXP-09, 10, 11 학습 결과 종합 보고서
**실험 기간**: 2026-02-07 03:18 ~ 04:40 (약 1시간 22분)  
**기준 모델**: EXP-06 (Visual Resampler, 82.5% 정확도)  
**목표**: LoRA 없이 구조적 개선을 통한 성능 향상

---

## 📊 전체 실험 결과 요약

| 실험 ID | 주요 변경 | 상태 | Val Loss (Final) | 학습 시간 | 체크포인트 |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **EXP-06** | Baseline (Resampler 64) | ✅ | 0.000141 | - | ✅ |
| **EXP-09** | **Latents 128** | ✅ | **0.000141** | 76분 | ✅ 4개 |
| **EXP-10** | **Window 16** | ⚠️ | **0.1488** | 4분 | ✅ 5개 |
| **EXP-11** | Discrete (Classification) | ❌ | N/A | 8초 | ❌ |

---

## ✅ EXP-09: Latent Density Scaling (128 Latents)

### 설정
```json
{
  "vision_resampler": {
    "num_latents": 128  // 64 → 128 (2배 증가)
  },
  "window_size": 12,
  "fwd_pred_next_n": 6
}
```

### 결과
- **최종 Val Loss**: `0.000141` (EXP-06과 동일!)
- **최종 Train Loss**: `7.65e-5`
- **학습 완료**: 10 Epochs (약 76분)
- **체크포인트**: 
  - `epoch=06-val_loss=0.0001.ckpt` (7.7GB)
  - `epoch=07-val_loss=0.0001.ckpt` (7.7GB)
  - `epoch=08-val_loss=0.0001.ckpt` (7.7GB)
  - `last.ckpt` (7.7GB)

### 분석
✅ **성공**: Visual Token을 2배로 늘렸음에도 Val Loss가 **EXP-06과 동일** (0.000141)  
✅ **안정성**: 학습이 정상적으로 수렴했고, Overfitting 없음  
⚠️ **의문점**: 토큰을 2배 늘렸는데 왜 성능 개선이 없을까?

**가설 1**: 64개 토큰으로도 이미 충분한 시각 정보 추출 완료  
**가설 2**: 추론 테스트를 해봐야 실제 PM/DA 차이가 드러날 수 있음  
**가설 3**: LSTM의 Hidden Size(1024)가 병목일 가능성 (더 많은 토큰을 소화 못함)

---

## ⚠️ EXP-10: Extended Temporal Window (Window 16)

### 설정
```json
{
  "window_size": 16,  // 12 → 16
  "act_head": {
    "window_size": 16
  },
  "train_dataset": {
    "window_size": 16
  }
}
```

### 결과
- **최종 Val Loss**: `0.1488` (EXP-06 대비 **1000배 높음!**)
- **최종 Train Loss**: `0.155`
- **학습 완료**: 10 Epochs (약 4분 30초)
- **이상 징후**: 
  - Epoch별 **단 1 스텝**만 실행! (정상은 474 스텝)
  - 학습 속도 비정상적으로 빠름 (474 스텝 → 1 스텝)

### 분석
❌ **데이터셋 문제**: Window Size 16으로 변경 시 데이터가 거의 생성되지 않음  

**원인 추정**:
1. **짧은 에피소드 길이**: 대부분의 에피소드가 16 프레임 미만일 가능성
2. **데이터셋 필터링**: Window 16을 만족하는 샘플이 거의 없음
3. **Batch 구성 실패**: 충분한 샘플이 없어서 1 스텝만 생성됨

**해결 방안**:
- 에피소드 길이 확인 필요
- Window Size를 14 정도로 중간값 시도
- 또는 더 긴 에피소드 데이터 수집

⚠️ **현재 체크포인트는 사용 불가** (학습이 제대로 안 됨)

---

## ❌ EXP-11: Discrete Training (Classification)

### 설정
```json
{
  "act_head": {
    "type": "MobileVLAClassificationDecoder",
    "action_dim": 6,
    "num_classes": 6
  },
  "train_dataset": {
    "discrete_action": true
  }
}
```

### 결과
- **상태**: 초기화 단계에서 **KeyError: 'n_bin'** 발생
- **학습 시간**: 8초 (즉시 실패)

### 에러 로그
```python
KeyError: 'n_bin'
  File "robovlms/model/backbone/base_backbone.py", line 149
    bins=self.act_head_configs["n_bin"],
```

### 분석
❌ **Config 누락**: Classification Head가 필요로 하는 `n_bin` 파라미터가 없음

**해결 방안**:
1. Config에 `n_bin` 파라미터 추가 필요
2. `MobileVLAClassificationDecoder`의 초기화 로직 확인
3. Discrete Action 학습 방식 재설계 필요

---

## 🔍 핵심 발견

### 1. **Latent 수량은 64개가 최적**
- 128개로 늘려도 성능 개선 없음
- 오히려 연산량만 증가 (학습 시간 약간 증가)
- **결론**: EXP-06의 64 latents가 Sweet Spot

### 2. **Window Size 확장은 데이터셋 제약**
- 현재 데이터셋으로는 Window 16 적용 불가
- 짧은 에피소드가 대부분인 것으로 추정
- **결론**: Window 12 유지하거나, 긴 에피소드 데이터 추가 수집 필요

### 3. **Discrete Training은 추가 작업 필요**
- Config 파라미터 불완전
- Classification Head의 초기화 로직 수정 필요
- **결론**: 시간 투자 대비 효과 불투명, 우선순위 낮음

---

## 📈 현재 최고 성능 모델

### **EXP-06 (Visual Resampler, Latents 64) = EXP-09 (Latents 128)**
- **Val Loss**: 0.000141
- **PM/DA**: 82.50%
- **Visual Tokens**: 64 (EXP-06) vs 128 (EXP-09)
- **추천**: **EXP-06 사용** (더 적은 토큰으로 동일 성능)

---

## 🚀 다음 단계 제안

### 우선순위 1: **데이터셋 분석**
EXP-10 실패 원인 규명을 위해 에피소드 길이 분포 확인
```bash
python scripts/analysis/analyze_episode_lengths.py
```

### 우선순위 2: **EXP-06 vs EXP-09 추론 비교**
Val Loss가 같아도 실제 로봇 제어에서는 차이가 날 수 있음
- 두 모델을 API 서버에 로드하여 `detailed_error_analysis.py` 실행
- PM/DA, Phase별 성능 비교

### 우선순위 3: **Window 14 실험** (선택)
데이터셋이 허용한다면 중간값인 Window 14 시도

### 우선순위 4: **LoRA 재고** (장기)
현재까지의 실험으로 구조적 개선이 한계에 도달
LLM Backbone 학습(LoRA)이 다음 돌파구일 가능성

---

## 📂 체크포인트 경로

### EXP-09 (사용 가능 ✅)
```
runs/unified_regression_win12/kosmos/mobile_vla_exp09_resampler_latent128/2026-02-07/exp09_resampler_latent128/
├── epoch=epoch=06-val_loss=val_loss=0.0001.ckpt (7.7GB)
├── epoch=epoch=07-val_loss=val_loss=0.0001.ckpt (7.7GB)
├── epoch=epoch=08-val_loss=val_loss=0.0001.ckpt (7.7GB)
└── last.ckpt (7.7GB)
```

### EXP-10 (사용 불가 ❌)
```
runs/unified_regression_win12/kosmos/mobile_vla_exp10_resampler_win16/2026-02-07/exp10_resampler_win16/
└── [학습이 비정상적으로 진행됨, 체크포인트 무효]
```

---

**작성일**: 2026-02-09  
**작성자**: VLA 연구팀  
**핵심 결론**: **EXP-06 (64 Latents)이 현재 최적 모델**. 추가 구조 개선보다는 **LoRA 또는 더 많은/긴 데이터**가 다음 돌파구.
