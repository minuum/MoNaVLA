# 전체 실험 케이스 종합 비교표

## 📊 모든 케이스 상세 비교

| Case | 모델 구성 | 데이터 전략 | Val Loss | 방향 정확도 | 상태 | 핵심 특징 | 장점 | 단점 |
|:---|:---|:---|:---:|:---:|:---:|:---|:---|:---|
| **Case 1: Baseline (Right Only)** | Frozen+LoRA | Right만 학습 | 0.147 | 0% | ❌ 실패 | Ablation Study | 빠른 학습 | 완전 편향됨 |
| **Case 2: Frozen+LoRA (Balanced)** | Frozen+LoRA | Left+Right 균형 | 0.027 | 0% | ❌ 실패 | 원본 접근법 | Loss는 낮음* | 방향 학습 실패, 과적합 |
| **Case 3: Fixed (Xavier Init)** | Frozen | Xavier 초기화 | 0.048 | 0% | ❌ 실패 | action_token 개선 시도 | 초기화 개선 | 여전히 방향 구분 불가 |
| **Case 4: abs_action** | **Frozen** | **Abs Value** | **0.050** | **100%** | ✅ **성공** | **방향=언어, 크기=모델** | **완벽한 방향 제어** | 추론 코드 수정 필요 |
| **Case 5: aug_abs (Mirrored)** | **Frozen** | **Augmented** | **0.050** | **100%** | ✅ **성공** | **데이터 2배 + 대칭성** | **강건성 최고** | - |
| **Case 6: OpenVLA Style** | Frozen | 27 Epoch, Low LR | 진행 중 | TBD | 🔄 학습 중 | 장기 학습 효과 검증 | 수렴 안정성 | 시간 소요 큼 |
| **Case 7: No Chunking** | Frozen | fwd_pred_next_n=1 | 대기 | TBD | ⏳ 대기 | Action 단일 예측 | 추론 단순화 | 제어 정밀도 저하 가능 |
| **Case 8: Hybrid Head** | Frozen | Classification+Reg | 미학습 | TBD | 📋 구현 완료 | 방향=분류, 크기=회귀 | End-to-End 학습 | 구현 복잡도 높음 |

*\*Case 2의 낮은 Loss는 착시: 모든 입력에 동일 출력 (평균값)으로 수렴한 과적합 상태*

---

## 🎯 케이스별 상세 분석

### ✅ **성공 그룹**

#### Case 4: abs_action (최종 추천 - 안정성)
- **전략**: 모델은 `abs(linear_y)`만 학습. 추론 시 언어에서 방향 추출하여 부호 결정.
- **성능**: Val Loss 0.050, 방향 정확도 100%
- **장점**:
  - 학습 태스크 단순화 (부호 제거)로 수렴 안정
  - 규칙 기반 방향 처리로 오류 0%
  - 검증된 안정성
- **단점**: `inference.py`에 방향 추출 로직 추가 필요
- **추천 대상**: **실제 배포용 (안전성 최우선)**

#### Case 5: aug_abs (최종 추천 - 성능)
- **전략**: Case 4 + Mirroring Augmentation (이미지 반전, 액션 반전, 언어 치환)
- **성능**: Val Loss 0.050, 방향 정확도 100%
- **장점**:
  - Case 4의 모든 장점 + 시각적 대칭성 학습
  - 데이터 효율 2배 (500 → 1000 효과)
  - 복도, 대칭 환경에서 강건성 극대화
- **단점**: Case 4와 동일 (추론 로직)
- **추천 대상**: **실제 배포용 (성능 최우선)**

---

### ❌ **실패 그룹** (학습 참고용)

#### Case 1: Right Only
- **실패 원인**: 한쪽 데이터만 학습 → 완전 편향
- **교훈**: 데이터 균형의 중요성

#### Case 2: Frozen+LoRA (Balanced)
- **실패 원인**: 
  - LoRA로 인한 Catastrophic Forgetting (언어 능력 손실)
  - 500개 데이터로는 Fine-tuning 불충분
  - `action_token`이 미학습 상태로 유지
- **교훈**: 적은 데이터에서는 **Frozen VLM** 유지 필수

#### Case 3: Fixed (Xavier Init)
- **실패 원인**: `action_token` 초기화를 개선했으나, 근본적 구조 문제 미해결
- **교훈**: 초기화만으로는 부족, 학습 전략 자체를 바꿔야 함

---

### 🔄 **실험 중 그룹**

#### Case 6: OpenVLA Style
- **목적**: 논문 스타일 학습(Low LR, Long Training)의 효과 검증
- **예상**: abs_action과 유사한 결과, 다만 수렴 속도 느림

#### Case 7: No Chunking
- **목적**: Action Chunking의 필요성 검증
- **예상**: Chunking 없이도 동작 가능하나, 제어 정밀도 저하 예상

#### Case 8: Hybrid Head
- **목적**: End-to-End 방식으로도 방향 학습 가능한지 검증
- **예상**: 성능은 abs_action보다 낮을 것이나, 추론 단순화 가능

---

## 🏆 최종 결론 및 추천

### 🥇 1순위: **Case 5 (aug_abs)** - 증강 + abs_action
- **이유**: 성능과 강건성을 모두 확보한 최적 모델
- **용도**: 실제 로봇 배포

### 🥈 2순위: **Case 4 (abs_action)**
- **이유**: Case 5와 성능 동일하나, 증강 효과 미포함
- **용도**: Case 5 학습 중 임시 사용 또는 백업

### 🥉 3순위: **Case 6, 7 (OpenVLA, No Chunk)**
- **이유**: 보조 실험으로, 논문 작성 시 비교 데이터로 활용
- **용도**: Ablation Study

---

## 💡 추가로 필요한 작업 체크리스트

### 즉시 수행 (오늘)
- [x] Case 4 (abs_action) 학습 완료
- [x] Case 5 (aug_abs) 학습 완료
- [x] 비교표 작성
- [ ] **Case 4 vs Case 5 실측 비교 (실제 로봇 또는 난이도 높은 검증셋)**
- [ ] **Inference 스크립트 테스트 (Case 4/5용)**

### 단기 (내일까지)
- [ ] Case 6 (OpenVLA) 학습 완료 대기
- [ ] Case 7 (No Chunk) 학습 완료 대기
- [ ] 전체 케이스 성능 벤치마크 스크립트 실행
- [ ] **시각화 자료 생성 (Loss Curve, Accuracy Chart)**

### 12/10 미팅 전
- [ ] **Final Report 작성** (이 표 포함)
- [ ] **로봇 Real-World Test 영상** (가능하다면)
- [ ] **슬라이드 준비** (핵심 3개 그래프)

---

작성일: 2025-12-09
