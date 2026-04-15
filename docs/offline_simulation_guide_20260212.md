# Offline Simulation 사용 가이드

**날짜**: 2026-02-12  
**목적**: 실제 로봇 없이 데이터셋으로 추론 테스트

---

## 🎯 기능

- ✅ H5 데이터셋에서 이미지 시퀀스 로드
- ✅ 모델 추론 실행 (First-Frame Safety 포함)
- ✅ Ground Truth vs Prediction 비교
- ✅ MSE, MAE 메트릭 계산
- ✅ 2D Trajectory 시각화
- ✅ 프레임별 액션 로그

---

## 📦 사용법

### 1. 기본 실행 (첫 번째 에피소드)

```bash
cd /home/soda/vla
python scripts/simulate_offline.py
```

### 2. 랜덤 에피소드 선택

```bash
python scripts/simulate_offline.py --random
```

### 3. 특정 에피소드 지정

```bash
python scripts/simulate_offline.py \
  --episode episode_20260129_010041_basket_1box_hori_left_core_medium.h5
```

### 4. 시각화 포함

```bash
python scripts/simulate_offline.py --random --visualize
```

### 5. INT8 vs FP16 비교

```bash
# INT8 모드
export VLA_QUANTIZE=true
python scripts/simulate_offline.py --random --visualize

# FP16 모드
export VLA_QUANTIZE=false
python scripts/simulate_offline.py --random --visualize
```

---

## 📊 출력 예시

```
🚀 Loading model...
  Checkpoint: /home/soda/vla/runs/unified_regression_win12/kosmos/epoch=epoch=09-val_loss=val_loss=0.0013.ckpt
  Config: /home/soda/vla/Mobile_VLA/configs/mobile_vla_exp17_win8_k1.json
✅ Model loaded successfully!

📂 Loading episode: episode_20260129_010041_basket_1box_hori_left_core_medium.h5
  Images: (180, 720, 1280, 3)
  Actions: (180, 2)
  Instruction: Navigate to the brown pot on the left

🎬 Episode Simulation Started
📝 Instruction: Navigate to the brown pot on the left
🖼️ Total Frames: 180
============================================================
Simulating: 100%|████████████████████| 180/180 [01:23<00:00,  2.16it/s]
  Frame   0 | GT: [+0.000, +0.000] | Pred: [+0.000, +0.000] | Latency: 5611ms
  Frame   5 | GT: [+1.150, +0.000] | Pred: [+1.150, +0.000] | Latency: 3820ms
  Frame  10 | GT: [+1.150, +1.150] | Pred: [+1.150, +0.000] | Latency: 3650ms
  ...
============================================================
📊 Simulation Results:
  MSE:  0.234567
  MAE:  0.345678
  Avg Latency: 3821.5ms

📊 Visualization saved to: /tmp/vla_simulation_result.png
✅ Simulation completed!
```

---

## 🔍 확인할 수 있는 것들

### 1. First-Frame Safety 작동 여부

```
Frame   0 | GT: [+0.000, +0.000] | Pred: [+0.000, +0.000]  ← ✅ 정상
Frame   0 | GT: [+0.000, +0.000] | Pred: [+1.150, +0.000]  ← ❌ 문제!
```

### 2. 액션 다양성

```
Frame   5 | Pred: [+1.150, +0.000]  ← 전진
Frame  10 | Pred: [+1.150, +1.150]  ← 전진+좌회전
Frame  15 | Pred: [+0.000, +1.150]  ← 좌회전만
```

**문제 증상**:
```
Frame   5 | Pred: [+1.150, +0.000]
Frame  10 | Pred: [+1.150, +0.000]  ← 계속 같은 값!
Frame  15 | Pred: [+1.150, +0.000]
```

### 3. History Window 효과

- 첫 8프레임: 히스토리 누적 중
- 9프레임 이후: 8프레임 윈도우 슬라이딩

### 4. INT8 vs FP16 성능 비교

| 모드 | MSE | MAE | Latency | 메모리 |
|:---|:---:|:---:|:---:|:---:|
| INT8 | ? | ? | ~3.8s | ~2GB |
| FP16 | ? | ? | ~5.0s | ~5GB |

---

## 🐛 디버깅 팁

### 문제 1: 모든 프레임에서 같은 액션

**증상**:
```
Frame   0 | Pred: [+1.150, +0.000]
Frame   5 | Pred: [+1.150, +0.000]
Frame  10 | Pred: [+1.150, +0.000]
```

**원인**:
- Denormalization 오류
- 히스토리 관리 문제
- 모델 체크포인트 문제

**해결**:
- 로그에서 `⏭️ Skipped denormalization` 확인
- `🔍 [HISTORY] Current frames in memory` 증가 확인

---

### 문제 2: First Frame이 [0,0]이 아님

**증상**:
```
Frame   0 | GT: [+0.000, +0.000] | Pred: [+1.150, +0.000]
```

**원인**:
- `policy_head.history_memory` 체크 실패

**해결**:
- 로그에서 `🛡️ First-Frame Zero Enforcement` 메시지 확인
- 없으면 `❌ Cannot find policy_head` 에러 확인

---

### 문제 3: MSE/MAE가 너무 높음

**기준**:
- MSE < 0.5: 양호
- MSE > 1.0: 문제

**원인**:
- 모델이 제대로 학습되지 않음
- Instruction이 학습 데이터와 다름
- 이미지 전처리 불일치

---

## 📈 시각화 그래프 설명

생성된 `/tmp/vla_simulation_result.png`에는 4개 그래프가 포함됩니다:

1. **Linear X Velocity**: 전진/후진 속도 비교
2. **Linear Y Velocity**: 좌/우 속도 비교
3. **2D Trajectory**: 누적 이동 경로
4. **Prediction Error**: 프레임별 오차

---

## 🔧 고급 옵션

### 다른 체크포인트 테스트

```bash
python scripts/simulate_offline.py \
  --checkpoint /path/to/other/checkpoint.ckpt \
  --random --visualize
```

### 특정 시나리오만 테스트

```bash
# Left 시나리오만
python scripts/simulate_offline.py \
  --episode episode_*_left_*.h5 \
  --visualize

# Right 시나리오만
python scripts/simulate_offline.py \
  --episode episode_*_right_*.h5 \
  --visualize
```

---

**작성**: 2026-02-12  
**다음**: 시뮬레이션 실행 후 결과 분석
