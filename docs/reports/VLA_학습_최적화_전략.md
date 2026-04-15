# VLA 모델 학습 최적화 전략 비교 분석

## 📚 논문별 핵심 전략 요약

### 1. RT-2 (Google DeepMind)
| 항목 | 전략 |
|:---|:---|
| **Action 표현** | Text tokens로 변환 (action tokenization) |
| **학습 방식** | VLM + 로봇 데이터 co-fine-tuning |
| **핵심 요소** | Web 지식 → 로봇 제어로 transfer |
| **장점** | 새로운 객체/명령에 일반화 |

### 2. OpenVLA (Stanford)
| 항목 | 전략 |
|:---|:---|
| **Action 표현** | Discrete tokens (256 bins) |
| **Learning Rate** | **2e-5 고정** (warmup 없음) |
| **Epochs** | **27 epochs** (action token accuracy 95% 달성까지) |
| **Fine-tuning** | LoRA (r=32, 1.4% 파라미터만 업데이트) |
| **최신 OFT** | Continuous action + L1 regression |

### 3. RoboFlamingo
| 항목 | 전략 |
|:---|:---|
| **구조** | Frozen VLM + Policy Head |
| **학습** | Imitation Learning + Sequential history |
| **Co-training** | VQA/COCO 데이터와 함께 (VLM 기능 유지) |
| **장점** | 단일 GPU로 학습 가능, 비용 효율적 |

### 4. FAST (Physical Intelligence)
| 항목 | 전략 |
|:---|:---|
| **Action Tokenization** | DCT (Discrete Cosine Transform) 기반 |
| **효과** | 더 적은 토큰, 빠른 학습, 정확한 action |
| **스케일업** | VLA 학습 5배 가속 |

---

## 🔬 학습 효율 향상을 위한 실험 케이스

### Case 1: 기존 방식 (Baseline)
```json
{
  "action_space": "continuous",
  "action_dim": 2,
  "learning_rate": 1e-4,
  "epochs": 10,
  "abs_action": false
}
```
**결과**: 방향 구분 실패 (언어 조건부 학습 안 됨)

### Case 2: action_token Xavier 초기화
```json
{
  "modification": "action_token zeros → Xavier",
  "learning_rate": 1e-4,
  "epochs": 10
}
```
**결과**: Loss 개선 (0.429→0.034), 방향 구분 여전히 실패

### Case 3: 방향 제거 (abs_action) [현재 진행 중]
```json
{
  "abs_action": true,
  "note": "linear_y 절대값만 학습, 방향은 언어에서 추출"
}
```
**예상**: 태스크 단순화로 학습 효율 향상

### Case 4: OpenVLA 스타일 (높은 LR + 더 많은 Epochs)
```json
{
  "learning_rate": 2e-5,
  "epochs": 27,
  "warmup": false
}
```
**근거**: OpenVLA에서 27 epochs로 95% accuracy 달성

### Case 5: 방향을 Classification으로 분리
```json
{
  "action_space": "hybrid",
  "magnitude_head": "regression (continuous)",
  "direction_head": "classification (left/right)"
}
```
**근거**: 방향(discrete) + 크기(continuous) 분리

### Case 6: Action Chunking 제거
```json
{
  "fwd_pred_next_n": 1,
  "note": "단일 action 예측으로 단순화"
}
```
**근거**: Chunking이 학습 복잡도 증가시킬 수 있음

---

## 📊 비교 분석 매트릭스

| 케이스 | 학습 목표 | 방향 처리 | 복잡도 | 예상 효과 |
|:---|:---|:---|:---:|:---:|
| **Baseline** | linear_y 전체 | 모델 학습 | 높음 | ❌ |
| **Xavier init** | linear_y 전체 | 모델 학습 | 높음 | ⚠️ |
| **abs_action** | \|linear_y\| | 언어 추출 | **낮음** | ⭐⭐⭐ |
| **OpenVLA style** | linear_y 전체 | 모델 학습 | 높음 | ⭐⭐ |
| **Hybrid** | 크기+방향 분리 | Classification | 중간 | ⭐⭐⭐ |
| **No chunking** | 단일 action | 모델 학습 | **낮음** | ⭐⭐ |

---

## 💡 권장 실험 우선순위

### 1순위: abs_action (현재 진행 중)
- 가장 단순한 접근
- 방향은 언어 파싱으로 100% 정확

### 2순위: Hybrid (Classification + Regression)
- 방향: Binary classification (left/right)
- 크기: Continuous regression
- 두 손실 함수 조합

### 3순위: Action Chunking 제거
- `fwd_pred_next_n: 1`로 변경
- 단일 time step action 예측

### 4순위: OpenVLA 스타일
- LR 2e-5, 27 epochs
- 더 긴 학습으로 수렴 확인

---

## 🚀 추가 실험 Config 생성

### Config 4: OpenVLA 스타일
```json
{
  "exp_name": "mobile_vla_openvla_style_20251209",
  "learning_rate": 2e-5,
  "trainer": {
    "max_epochs": 27
  }
}
```

### Config 5: Hybrid (Classification + Regression)
구현 필요:
- `DirectionClassifier` 헤드 추가
- Loss 함수 수정: `L_total = L_magnitude + λ * L_direction`

### Config 6: No Chunking
```json
{
  "exp_name": "mobile_vla_no_chunk_20251209",
  "fwd_pred_next_n": 1,
  "act_head": {
    "fwd_pred_next_n": 1
  }
}
```

---

## 📈 학습 성공 지표

| 지표 | 목표치 | 측정 방법 |
|:---|:---:|:---|
| **train_loss** | < 0.05 | TensorBoard |
| **val_loss** | < 0.10 | Validation set |
| **방향 정확도** | > 90% | sign(pred) == sign(GT) |
| **MAE** | < 0.2 | \|pred - GT\| 평균 |
| **언어 반응성** | 차이 > 0.5 | 동일 이미지, 다른 언어 |

---

## 🎯 12월 10일 미팅 발표 포인트

### 핵심 발견
1. RoboVLMs의 action_token 구조적 한계 발견
2. 다양한 해결 접근법 실험

### 비교 분석
| 접근법 | 구현 난이도 | 예상 성능 | 상태 |
|:---|:---:|:---:|:---|
| **언어 방향 추출** | ⭐ | 100% 정확 | ✅ 완료 |
| **abs_action** | ⭐⭐ | 높음 예상 | 🔄 진행 중 |
| **Hybrid head** | ⭐⭐⭐ | 높음 예상 | 📋 계획 |
| **OpenVLA style** | ⭐⭐ | 중간 예상 | 📋 계획 |

### 결론
> "VLA 모델에서 언어 조건부 action 학습의 핵심은 태스크 설계입니다.
> 방향(discrete)과 크기(continuous)를 분리하거나,
> 방향을 언어에서 직접 추출하는 방식이 효과적입니다."

---

작성일: 2025-12-09 07:35
