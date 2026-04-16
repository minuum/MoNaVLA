# V5 평가 갭 분석
작성일: 2026-04-16

> 대상: Exp04, Exp09, Exp10, Exp11 중심. 현재 프로젝트의 의사결정에 직접 영향을 주는 실험만 우선 분석.

## 1. 한 줄 요약

- Exp04는 정책 baseline이지만 evaluation closure가 부족하다.
- Exp09는 수치는 많지만 closed-loop 판정이 빠져 있다.
- Exp10은 perception evidence가 가장 강하지만 policy transfer 증거가 없다.
- Exp11은 설계는 준비됐지만 실행/평가가 비어 있다.

## 2. 현재 보유 지표 vs 누락 지표

| Exp | 학습 Loss | PM/DM | Confusion | Perception | Closed-loop Sim | Real Robot | 현재 결론 상태 |
|-----|-----------|-------|-----------|------------|-----------------|------------|----------------|
| Exp04 | 있음 | 불완전 | 없음/미정리 | 없음 | 없음 | 없음 | baseline이지만 미완료 |
| Exp09 | 있음 | 있음 | 일부 있음 | 없음 | 없음 | 없음 | bias 지속까지는 확인 |
| Exp10 | 있음 | 간접 | 없음 | 강함 | 없음 | 없음 | grounding 성공, transfer 미확정 |
| Exp11 | 계획만 | 없음 | 없음 | 없음 | 없음 | 없음 | 아직 시작 전 |

## 3. 실험별 갭 분석

### Exp04

현재 확보:
- `val_loss 0.776`
- Google-Robot backbone 전환의 효과
- 문서상 현재 정책 baseline 지위

빠진 것:
- 공식 PM/DM 결과표
- class confusion matrix
- stop/turn breakdown
- path type별 성능
- closed-loop rollout success
- 실기 주행 결과

왜 중요한가:
- 현재 baseline인데도 실제로 “곡선을 배웠는가”가 완전히 닫히지 않았다.
- 교수님 Step 1 판단을 내리려면 Exp04의 rollout 결과가 필요하다.

권장 우선순위:
1. `scripts/test_v5_pm_dm.py`를 Exp04 기준으로 고정 실행
2. path type별 breakdown 추가
3. closed-loop simulation 연결

### Exp09

현재 확보:
- `val_loss 1.203`
- trainer accuracy 83%
- offline PM/DM 85.7%
- bias 지속이라는 문서 결론

빠진 것:
- 왜 PM/DM가 높은데 bias가 지속되는지에 대한 episode-level explanation
- stop recall / rotation recall
- path type별 success rate
- rollout success / timeout / overshoot
- 실기 비교

왜 중요한가:
- Exp09는 숫자와 해석이 어긋나는 대표 사례다.
- 지금 필요한 건 추가 loss가 아니라 **episode-level simulation**이다.

권장 우선순위:
1. stop / turn class breakdown 추가
2. rollout success rate 측정
3. forward collapse failure taxonomy 정리

### Exp10

현재 확보:
- BBox grounding 문서
- `val_loss 0.012`
- `Grounding IoU 0.87`
- `Tactical Match ~92%`
- episode / batch / full viewer 산출물

빠진 것:
- 공식 metrics artifact (`metrics.json`, leaderboard row)
- path type별 perception breakdown
- bbox center error 추세
- grounding -> action -> rollout transfer 검증
- Exp10 기반 policy proxy와 expert trajectory 비교

왜 중요한가:
- 최근 가장 강한 성과지만, 이걸 navigation 근거로 쓰려면 한 단계 더 필요하다.
- 현재는 “잘 본다”는 증거지, “잘 간다”는 증거는 아니다.

권장 우선순위:
1. perception metrics 정식 고정
2. bbox center 기반 action proxy rollout 만들기
3. expert trajectory와 terminal error 비교

### Exp11

현재 확보:
- 설계 문서
- config
- 데이터 분포 근거

빠진 것:
- 학습 결과 전부
- PM/DM
- confusion
- rollout
- 실기

왜 중요한가:
- Exp11은 다음 후보라서 지금부터 평가 프로토콜을 미리 걸어야 한다.
- 나중에 또 “loss는 좋았는데 실제론 애매함”이 반복되면 안 된다.

권장 우선순위:
1. 학습 전 leaderboard 템플릿 생성
2. Layer 2/3 필수화
3. Exp04, Exp09와 같은 split에서 직접 비교

## 4. 공통 누락 항목

현재 V5 전반에서 공통으로 비어 있는 것:

- experiment-wide leaderboard
- path type별 표준 breakdown
- stop precision / recall
- rotation recall
- closed-loop success rate
- failure taxonomy 통계
- checkpoint freeze 후 실기 benchmark

## 5. 바로 채워야 할 지표

### 우선순위 P0
- Exp04 PM/DM 정식화
- Exp09 rollout success rate
- Exp10 perception metrics artifact

### 우선순위 P1
- Exp04 / Exp09 / Exp11 공통 simulation harness
- stop / turn failure taxonomy
- path type별 leaderboard

### 우선순위 P2
- real robot benchmark sheet
- scenario-level reproducibility pack

## 6. 의사결정 규칙

앞으로 아래 기준으로만 실험 판정을 내린다.

- Loss만 좋음: 채택 금지
- PM/DM만 좋음: 보류
- PM/DM + rollout 성공: 채택 후보
- rollout + real-world 재현: 공식 채택

## 7. 결론 표

| Exp | 지금 믿어도 되는 결론 | 아직 못 믿는 결론 |
|-----|------------------------|-------------------|
| Exp04 | foundation이 좋고 baseline이다 | 실제 곡선 행동을 안정적으로 배웠다 |
| Exp09 | 8-class 형식 통합은 됐다 | 실제 navigation이 잘 된다 |
| Exp10 | grounding은 강하다 | grounding이 policy 성공으로 이어진다 |
| Exp11 | 설계가 논리적이다 | Exp04/09보다 낫다 |
