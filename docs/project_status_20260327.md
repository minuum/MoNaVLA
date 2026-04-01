# MoNaVLA 프로젝트 현황 및 향후 계획 분석
> **SCP 전송 완료**: `last_v4_counterfactual_weights.pth` → `soda@100.85.118.58:~/MoNaVLA/` ✅ (6.6GB, 10:45 소요)
> 작성일: 2026-03-27 | 기준 실험: `v4-counterfactual-stop-v1` (진행 중)

---

## 📌 주요 질문별 현황 답변

---

### 1. 로봇 - 비동기 데이터 수집 가능한지?

| 항목 | 현황 |
|------|------|
| 현재 수집 방식 | ROS 노드 → HDF5 저장 (동기, 에피소드 단위) |
| 비동기 가능 여부 | **가능** (ROS topic 구조상 publish/subscribe가 이미 비동기) |
| 병목 지점 | `h5py.File` 쓰기가 single-threaded → 수집 중 잠금 발생 가능 |
| 구현 방안 | `asyncio` + 별도 스레드에서 버퍼 큐 → HDF5 flush 방식으로 구현 가능 |
| 예상 난이도 | ⭐⭐⭐☆☆ (ROS 노드 수정 + 파일I/O 비동기화) |

**결론**: 기술적으로 가능하나, ROS 콜백 큐를 분리하고 HDF5 flush 전략을 수정해야 함. 실제 로봇에서는 데이터 손실 없는 버퍼 큐 설계가 중요.

---

### 2. 원격에서 비동기 개발

| 항목 | 현황 |
|------|------|
| 현재 원격 서버 | `soda@100.85.118.58` (Tailscale 기반) |
| 브랜치 동기화 | `inference-integration`, `monavla-driving` 방금 푸시 완료 ✅ |
| 체크포인트 동기화 | SCP로 수동 전송 중 (`last_v4_counterfactual_weights.pth`) |
| 개선 방안 | git-lfs or rsync cron job으로 자동 동기화 |

**결론**: 원격 개발 환경은 현재 구성되어 있음. 가중치 파일이 크기 때문에 정기적 rsync 또는 서버 용량 확보 필요.

---

### 3. 256 bin Action Tokenizer 문제

| 항목 | 현황 |
|------|------|
| 현재 학습 방식 | **Continuous Regression** (`discrete_action: false`) |
| 256 bin tokenizer 사용 여부 | ❌ **현재 사용 안 함** (base RoboVLMs backbone은 내부적으로 있을 수 있으나 nav head에서 우회됨) |
| 실제 출력 | `[linear_x, angular_z]` 연속값 2차원 regression |
| 문제점 | 256 bin은 기존 Kosmos-2 arm action용 설계 → navigation에 직접 적용 시 해상도 부족, 범위 불일치 |
| 결론 | ✅ **현재 구조는 올바름** - Continuous로 학습 중이고 bin tokenizer를 nav에 쓸 이유 없음 |

---

### 4. 6 Classes Instruction이 실제 학습에 적용되는지?

> 핵심 질문: **로봇이 장면만으로 판단하는가? 아니면 텍스트(액션 정보) +  장면 함께 학습하는가?**

| 구분 | 내용 |
|------|------|
| 현재 Instruction 방식 | `action_aware_train` - GT action 기반으로 텍스트 자동 생성 |
| 6 classes | Stop / Forward / Left / Right / Diag-FL / Diag-FR |
| 학습 데이터 연결 | 각 스텝의 GT action → 텍스트 instruction → 모델 입력 |
| **잠재적 문제** | ⚠️ GT action으로 instruction을 만들면, 모델이 텍스트를 통해 정답을 "미리 알게" 됨 |
| Counterfactual 대응 | 20% 확률로 "Stop" 명령 + zero action 강제 주입 → 텍스트 무시 불가능하게 함 |
| **현재 상태** | 학습 텍스트는 **실제로 loss에 영향을 주고 있음** (lang이 KV attention에 들어감) |

**결론**: `action_aware_train`으로 텍스트+액션값 **모두** 학습에 반영되어 있음. 단, Counterfactual 실험 없이는 모델이 장면만 보고 행동할 위험이 있었고, 현재 이를 교정 중.

---

### 5. 대각선 값(Diagonal Action)이 모델에서 출력이 안 되는 이유

| 항목 | 내용 |
|------|------|
| 대각선 클래스 | `diag_fl` (tx>0.3, ty>0.3), `diag_fr` (tx>0.3, ty<-0.3) |
| **근본 원인** | 데이터셋에 대각선 sample 비율이 극히 낮음 (대부분 직진/회전) |
| 추가 원인 | `action_aware_train` instruction에서 `diag_fl`, `diag_fr` 변형 텍스트가 추가됐지만 학습 데이터 자체가 부족 |
| 모델 편향 | Regression head가 중앙값([0,0] 또는 [1,0])으로 수렴하려는 경향 |
| 검증 필요 | `curvature_only=True` 필터로 곡선 에피소드만 학습 시 대각선 출력 개선 여부 확인 필요 |

**결론**: 대각선이 안 나오는 이유는 **데이터 불균형**이 주 원인. 직진 데이터가 압도적으로 많아 모델이 대각선을 학습하지 못함.

---

### 6. 곡선(Curvature) 모델만으로 충분한가?

| 항목 | 현황 |
|------|------|
| `curvature_only` 옵션 | ✅ 구현되어 있음 (코드 Line 86~98) |
| 곡선만 학습 시 장점 | 방향 전환 데이터 집중 → 대각선/회전 성능 개선 가능 |
| 곡선만 학습 시 단점 | 직진 구간에서 모델이 불안정해질 수 있음 |
| 실제 로봇 운용 | 직진+회전+정지 모두 필요하므로 단독 사용은 어려움 |
| 권장 방향 | `curvature_only` + 전체 데이터 혼합 학습 or class-weighted loss |

**결론**: 곡선 단독 모델은 분석/실험용으로는 유효하나, 실제 배포용 모델로는 **직진 데이터와 혼합 학습이 필요**.

---

## 📊 현재 실험 현황 요약 테이블

| 실험 이름 | 날짜 | Best Val Loss | 상태 | 핵심 변경 | Action 방식 |
|-----------|------|---------------|------|-----------|-------------|
| `v4-balanced-v1` | 03-24 | ~0.28 | ✅ 완료 | 클래스 균형 학습 | Discrete (6-class) |
| `v4-balanced-v2` | 03-25 | ~0.27 | ✅ 완료 | 증분 개선 | Discrete (6-class) |
| `v4-regression-v1` | 03-26 | **0.066** | ✅ 완료 | Continuous Regression 첫 시도 | **Continuous** |
| `v4-regression-v2-weighted` | 03-26 | **0.259** | ✅ 완료 | Non-forward action weight 5x | **Continuous** |
| **`v4-counterfactual-stop-v1`** | **03-27** | **0.270** | 🔄 **진행 중 (Epoch 4/20)** | Stop Injection 20% + Text Sensitivity | **Continuous** |

---

## 🔍 현재 학습 중인 실험 상세: `v4-counterfactual-stop-v1`

### 학습 설계

| 항목 | 값 |
|------|----|
| 베이스 config | `mobile_vla_v4_regression_v2_weighted.json` |
| 시작 체크포인트 | `v4-regression-v2-weighted-v2/epoch=02-val_loss=0.259.ckpt` |
| 학습률 | `5e-6` |
| Max Epochs | `20` |
| Action Head | `MobileVLALSTMDecoder` (`continuous`, `action_dim=2`) |
| Action 예측 | `[linear_x, angular_z]` 연속값, 5-step chunk |
| Non-forward Weight | `5.0` (회전/정지 샘플 5배 강조) |
| Counterfactual Prob | **`0.20` (학습) / `0.0` (검증)** |
| Instruction Mode | `action_aware_train` (GT action → 텍스트 자동 생성) |
| Augmentation | ✅ Color Jitter + Random Crop + H-Flip |
| Window Size | `8` frames |
| Fwd Pred Next N | `5` steps |

### 에폭별 학습 지표

| Epoch | Train Loss | Val Loss | 비고 |
|-------|-----------|----------|------|
| 0 | 1.490 | 0.273 | - |
| 1 | 1.010 | 0.273 | - |
| 2 | 0.532 | 0.291 | val 일시 상승 (Counterfactual 적응 중) |
| 3 | 0.826 | **0.270** | ✅ New Best (개선 +0.004) |
| 4 | ~0.40 (진행 중) | 0.270 | 🔄 현재 Epoch 4/20 진행 중 |

> ⚠️ Val Loss가 Regression-v2(0.259)보다 높음 → Counterfactual 주입(20%)이 학습 노이즈를 늘리기 때문. **의도된 현상**이며 Text Sensitivity 향상이 목적.

### Regression 방식 요약

```
입력: 이미지 시퀀스 (8 frames) + 텍스트 instruction
출력: [linear_x, angular_z] × 5 steps (action chunk)

Loss: MSE with action weighting
  - forward action: weight 1.0
  - non-forward (회전, 정지): weight 5.0  ← 불균형 교정

Counterfactual Stop (20%):
  - 같은 이미지에 "Stop" 텍스트 주입 + GT action을 0으로 오버라이드
  - 모델이 텍스트를 무시하면 강제로 틀리는 상황 생성
```

---

## 📈 PM / DM 평가 결과 이력

> **평가 방식**:
> - **PM (Perfect Match)**: 예측 action class == GT action class (Discrete 6-class 기준)
> - **DM (Directional Match)**: 예측 방향벡터와 GT 방향이 일치하는 비율 (Continuous 기준)
> - **Text Sensitivity**: 동일 이미지에 "Stop" 명령 주입 시 모델이 정지하는 비율 (0% = 텍스트 무시)

### 📊 실험별 평가 결과 비교

| 평가 날짜 | 평가 대상 체크포인트 | 평가 방식 | PM (%) | DM (%) | Text Sensitivity | 비고 |
|-----------|---------------------|-----------|--------|--------|-----------------|------|
| 03-25 | `v4-balanced-v1 / epoch=02 (val=3.193)` | Discrete 6-class | **58.38%** | - | 미측정 | `eval_output_v2.log` |
| 03-25 | `v4-balanced-v1 / epoch=06 (val=3.220)` | Discrete 6-class | **59.54%** | - | 미측정 | `eval_output_v3.log` |
| 03-25 | `v4-balanced-v2 / epoch=04 (val=3.182)` | Discrete 6-class | **58.96%** | - | 미측정 | `eval_output_v4.log` |
| 03-25 | `v4-balanced-v2 / epoch=04 (val=3.182)` | Discrete 6-class | **58.38%** | - | 미측정 | `eval_v4_balanced_v2_results.log` |
| 03-27 | `v4-counterfactual-stop / epoch=03 (val=0.270)` | Continuous (Regression) | - | **63.64%** | **0.00%** ⚠️ | `eval_hard_counterfactual_v1.log` |
| 03-27 | `v4-counterfactual-stop / epoch=03 (val=0.270)` | Continuous (Regression) | - | 측정 중 🔄 | 측정 중 🔄 | `eval_hard_counterfactual_v2.log` |

### 🔍 핵심 관찰

| 항목 | 분석 |
|------|------|
| **PM 58~60% 정체** | Discrete 모델이 Stop/Forward에 편향 → 회전/대각선 거의 예측 안 함 |
| **DM 63.64%** | Continuous 모델이 방향 정확도는 더 높음 (class boundary 없이 부드럽게 예측) |
| **Text Sensitivity 0.00%** ⚠️ | **Stop 명령을 줘도 모델이 여전히 이동** → 텍스트가 아닌 장면만 보고 판단하고 있다는 강력한 증거 |
| **Counterfactual 효과** | 현재 epoch=3 기준으로 Text Sensitivity 개선 미확인 → epoch 진행에 따라 추이 확인 필요 |

### 📌 평가 스크립트 현황

| 스크립트 | 평가 대상 | 비고 |
|---------|----------|------|
| `scripts/vla_pm_dm_balanced_v1.py` | Discrete 6-class (v4-balanced) | PM 측정 |
| `scripts/eval_v4_balanced_final.py` | Discrete (v4-balanced-v2) | PM 측정 |
| `scripts/test/evaluate_v4_regression_latest.py` | Continuous (v4-counterfactual) | DM + Text Sensitivity 측정 |
| `scripts/diagnose_scene_memorization.py` | Scene Memorization 진단 | 미실행 |

---

## 🗂 데이터셋 현황

| 항목 | 값 |
|------|----|
| 데이터셋 버전 | `mobile_vla_dataset_v3` |
| 에피소드 수 | **151개** (`.h5` 파일) |
| 총 크기 | **3.4GB** |
| 수집 기간 | ~2026-03-25 (목표 완료) |
| Window Size | 8 frames |
| Fwd Pred Next N | 5 steps |
| Counterfactual Prob | **0.2 (학습)** / 0.0 (검증) |

---

## 🔜 다음 우선순위 액션 아이템

| 우선순위 | 작업 | 예상 효과 |
|----------|------|-----------|
| 🔴 P1 | Counterfactual 실험 완료 후 PM/DM 평가 | Text Sensitivity 정량 확인 |
| 🔴 P1 | 서버 용량 확보 (현재 여유 부족) | SCP 전송 안정화 |
| 🟡 P2 | 대각선 데이터 추가 수집 | Diagonal action 출력 개선 |
| 🟡 P2 | 비동기 HDF5 수집 파이프라인 구현 | 수집 속도 향상 |
| 🟢 P3 | `curvature_only` 실험 단독 진행 | 회전 성능 벤치마크 확보 |
| 🟢 P3 | rsync 자동 동기화 스크립트 작성 | 원격 개발 편의성 향상 |
