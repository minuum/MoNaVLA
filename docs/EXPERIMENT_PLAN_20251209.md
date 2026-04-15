# VLA 실험 계획 및 상태 (2025-12-09)

## 🔬 실험 케이스 현황

| 케이스 | Config | 상태 | 특징 |
|:---|:---|:---:|:---|
| **Case 1: Baseline** | mobile_vla_kosmos2_frozen_lora_leftright_20251204 | ✅ 완료 | 기존 방식, 방향 구분 실패 |
| **Case 2: Xavier init** | mobile_vla_kosmos2_fixed_20251209 | ✅ 완료 | action_token 수정, val_loss 0.048 |
| **Case 3: abs_action** | mobile_vla_kosmos2_abs_action_20251209 | 🔄 진행 중 | 절대값 학습, 방향 언어 추출 |
| **Case 4: OpenVLA style** | mobile_vla_openvla_style_20251209 | 📋 대기 | LR 2e-5, 27 epochs |
| **Case 5: No chunking** | mobile_vla_no_chunk_20251209 | 📋 대기 | fwd_pred_next_n=1 |
| **Case 6: Hybrid head** | (구현 완료, config 필요) | 📋 구현 | Classification + Regression |

---

## 📊 현재 학습 결과

### Case 1: Baseline
```
train_loss: 0.027 (final)
val_loss: 0.027
방향 정확도: 50% (랜덤 수준)
LEFT-RIGHT 차이: ~0.01
```

### Case 2: Xavier init
```
train_loss: 0.034 (final)
val_loss: 0.048
방향 정확도: 50% (개선 없음)
LEFT-RIGHT 차이: ~0.01
```

### Case 3: abs_action [진행 중]
```
train_loss: 0.0556 (Epoch 0)
val_loss: 0.0616
예상 효과: 언어+모델 조합으로 100% 방향 정확도
```

---

## 🎯 핵심 가설

### 가설 1: 태스크 분리
> "방향(discrete)과 크기(continuous)를 분리하면 각각 더 잘 학습됨"

| 접근법 | 방향 처리 | 크기 처리 |
|:---|:---|:---|
| abs_action | 언어에서 추출 | 모델 학습 |
| Hybrid head | Classification | Regression |

### 가설 2: VLM-Action 연결
> "action_token 구조보다 직접적인 언어 처리가 효과적"

| 접근법 | 언어 처리 | 효과 |
|:---|:---|:---:|
| action_token | VLM self-attention | ❌ |
| 언어 파싱 | 직접 추출 | ✅ |
| Hybrid head | Classification | 예상 ✅ |

---

## 📈 다음 단계

### 즉시 (오늘)
1. [x] abs_action 학습 시작
2. [x] Hybrid head 구현
3. [ ] abs_action 학습 완료 후 테스트
4. [ ] 비교 분석 실행

### 단기 (내일까지)
5. [ ] OpenVLA style 학습 (27 epochs)
6. [ ] No chunking 실험
7. [ ] 결과 종합 분석

### 12/10 미팅
- 각 케이스 비교 결과 발표
- 최적 접근법 제안
- 로봇 실증 계획

---

## 🚀 학습 명령어 모음

### Case 3: abs_action (진행 중)
```bash
# 이미 실행 중 (PID: 1412688)
tail -f logs/train_abs_action_20251209_073008.log
```

### Case 4: OpenVLA style
```bash
nohup python3 RoboVLMs_upstream/main.py \
    Mobile_VLA/configs/mobile_vla_openvla_style_20251209.json \
    > logs/train_openvla_style_$(date +%Y%m%d_%H%M%S).log 2>&1 &
```

### Case 5: No chunking
```bash
nohup python3 RoboVLMs_upstream/main.py \
    Mobile_VLA/configs/mobile_vla_no_chunk_20251209.json \
    > logs/train_no_chunk_$(date +%Y%m%d_%H%M%S).log 2>&1 &
```

### 비교 분석
```bash
python3 scripts/compare_experiments.py
```

---

## 📁 관련 파일

### Configs
- `Mobile_VLA/configs/mobile_vla_kosmos2_abs_action_20251209.json`
- `Mobile_VLA/configs/mobile_vla_openvla_style_20251209.json`
- `Mobile_VLA/configs/mobile_vla_no_chunk_20251209.json`

### 코드
- `RoboVLMs_upstream/robovlms/model/policy_head/hybrid_action_head.py`
- `scripts/compare_experiments.py`
- `scripts/inference_with_direction_fix.py`

### 문서
- `docs/reports/VLA_학습_최적화_전략.md`
- `docs/reports/VLA_모델_비교분석.md`
- `docs/reports/문제진단_해결방안_20251209.md`

---

작성일: 2025-12-09 07:40
