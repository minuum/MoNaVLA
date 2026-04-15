# Turn Bias Analysis Report
**일자**: 2026-02-25  
**모델**: V3-exp04-LoRA (mobile_vla_v3_exp04_inference, Classification 9-class)  
**서버**: `Mobile_VLA/inference_server.py` (PID: 64930)

---

## Background

이전 대화에서 hard-turn 에피소드에서 PM/DM 점수가 낮아 `turn_bias` 파라미터로 방향성을 강제 주입하려 했음.  
이번 세션에서 실제 sweep 테스트를 수행해 효과를 검증함.

---

## 실험 결과

### 파라미터 Sweep (Hard-Turn Episode)
**파일**: `episode_20251203_143945_1box_hori_left_core_medium.h5`  
**총 스텝**: 18 (사용 가능: 10)

| 설정                              | PM        | DM        | 결론          |
| --------------------------------- | --------- | --------- | ------------- |
| **Bias=0.0, Temp=1.0** (Baseline) | 40.0%     | 40.0%     | 기준          |
| Bias=0.5, Temp=1.0                | 40.0%     | 40.0%     | 효과 없음     |
| Bias=1.0, Temp=1.0                | 40.0%     | 40.0%     | 효과 없음     |
| **Bias=2.0, Temp=1.0**            | **30.0%** | **30.0%** | ❌ 오히려 하락 |
| Bias=0.0, Temp=0.7                | 40.0%     | 40.0%     | 효과 없음     |
| Bias=0.5, Temp=0.7                | 40.0%     | 40.0%     | 효과 없음     |
| Bias=1.0, Temp=0.5                | 40.0%     | 40.0%     | 효과 없음     |

**결론: Turn Bias 접근법은 효과 없음.**

---

## 근본 원인 분석

### 1. 모델 예측 분포 (50회 inference)

```
CLASS_ARGMAX 결과:
  Class 1 (Forward):   42회 (84%)  ← 압도적 bias
  Class 4 (Right):      7회 (14%)
  Class 5 (FwdLeft):    1회 ( 2%)
```

### 2. GT 액션 분포 (해당 에피소드)

```
Class 1 (Forward):    6개 (33.3%)
Class 5 (FwdLeft):    7개 (38.9%)  ← 가장 많아야 하지만 모델은 2%
Class 6 (FwdRight):   3개 (16.7%)
Class 3 (Left):       1개 ( 5.6%)
Class 0 (Stop):       1개 ( 5.6%)
```

### 3. 학습 데이터 분포 (basket_dataset_v2, 20 에피소드)

```
Class 1 (Forward):    50.0% ← 절반이 Forward
Class 6 (FwdRight):   19.7%
Class 5 (FwdLeft):    16.7%
Class 4 (Right):       5.6%
Class 0 (Stop):        5.6%
Class 3 (Left):        2.5% ← 거의 없음
```

### 4. Logit 분석

실제 서버 로그에서 확인된 대표 logit:
```
logits=[-0.67  8.55  -3.11  -3.16   0.96   5.96  -1.92  -2.74  -3.5]
          Stop   Fwd    Bck    L      R     FL     FR     BL    BR
```
- **Class 1 (Forward) logit ≈ 8.5** — 압도적으로 높음
- **Class 5 (FwdLeft) logit ≈ 5.9** — 두 번째로 높지만 역전 안됨
- Turn Bias +1.0 추가 시: Class 5 → 6.9, 여전히 Class 1(8.5)에 못 미침
- **Bias ≥ 3.0 이상** 줘야 역전 가능하지만, 그러면 다른 스텝에서 오히려 악화됨

---

## 왜 Turn Bias가 안 되는가

1. **Class 1 collapse**: 50% Forward 데이터로 학습한 모델이 Forward에 극단적으로 편향
2. **Logit gap 너무 큼**: Class 1 vs Class 5 gap이 약 2~3 → bias로 역전 불가
3. **에피소드 단위 일관성 없음**: 어떤 스텝에선 bias가 도움, 다른 스텝에선 해악

---

## 전체 데이터셋 평가 결과 (2026-02-25)

### basket_dataset_v2 (20 에피소드, 360 프레임)

| 지표                     | 결과      |
| ------------------------ | --------- |
| **PM (Perfect Match)**   | **79.7%** |
| **DM (Direction Match)** | **79.7%** |

**클래스별 예측 오차:**

| 클래스       | GT 비율 | Pred 비율 | 오차             |
| ------------ | ------- | --------- | ---------------- |
| 0 (Stop)     | 5.6%    | 2.2%      | -3.4%            |
| 1 (Forward)  | 50.0%   | 56.7%     | +6.7% (과예측)   |
| 3 (Left)     | 4.2%    | 0.3%      | **-3.9% (심각)** |
| 4 (Right)    | 5.6%    | 7.2%      | +1.6%            |
| 5 (FwdLeft)  | 16.7%   | 13.6%     | -3.1%            |
| 6 (FwdRight) | 18.1%   | 20.0%     | +1.9%            |

**해석**: 전체 PM 79.7%는 양호하나, Hard-turn 케이스(Class 3, 5)에서 Forward로 collapse됨.

---

## 권장 개선 방향

### 단기 (데이터단)
1. **Class Rebalancing**: basket_dataset_v2에서 Class 1 비율을 20% 이하로 제한
   - Forward-heavy 에피소드 undersampling 또는 Left/Right heavy 에피소드 augmentation
2. **추가 데이터 수집**: Left-turn heavy 에피소드 추가 (현재 Left 에피소드 Class 3이 5.6%, 너무 적음)

### 중기 (학습단)
3. **Class Weight 조정**: 현재 `class_weights: [2.0, 0.2, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0]`
   - Class 1 (Forward) weight를 0.1로 더 낮추고, Class 3 (Left)를 10.0으로 높이기
4. **Focal Loss 도입**: 쉬운 클래스(Forward)에 낮은 가중치, 어려운 클래스에 높은 가중치

### 장기 (모델단)
5. **Regression으로 전환**: Classification의 이산화로 인한 정보 손실 문제 → Continuous action prediction
6. **더 많은 LoRA 레이어 학습**: FwdLeft/Left 클래스 representation이 약함

---

## 현재 서버 설정

```bash
# 실행 명령
uvicorn Mobile_VLA.inference_server:app --host 0.0.0.0 --port 8000

# 환경 변수
VLA_API_KEY=vla-mobile-fixed-key-20260205
VLA_CHECKPOINT_PATH=/home/billy/25-1kp/vla/v3-exp04-lora/merged_v3_exp04_best.ckpt
VLA_CONFIG_PATH=/home/billy/25-1kp/vla/Mobile_VLA/configs/mobile_vla_v3_exp04_inference.json
```

**Note**: `v3-exp04-lora/merged_v3_exp04_best.ckpt`는 실제 경로(`RoboVLMs_upstream/runs/...`)의 심볼릭 링크임.
