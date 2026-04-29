# V5 평가 갭 분석
작성일: 2026-04-16

> 대상: Exp04, Exp09, Exp10, Exp11 중심. 현재 프로젝트의 의사결정에 직접 영향을 주는 실험만 우선 분석.

## 1. 한 줄 요약

- Exp04는 더 이상 baseline이 아니며, loss-good / inference-bad 사례로 정리해야 한다.
- Exp09는 수치는 많지만 closed-loop 판정이 빠져 있다.
- Exp10은 perception evidence가 가장 강하지만 free-form generation transfer가 약하다.
- Exp11은 현재 학습형 기준점이지만 closed-loop와 failure taxonomy가 비어 있다.
- Exp14 Step 2는 strongest지만 split 규모와 closed-loop 검증이 더 필요하다.

## 2. 현재 보유 지표 vs 누락 지표

| Exp | 학습 Loss | PM/DM | Confusion | Perception | Closed-loop Sim | Real Robot | 현재 결론 상태 |
|-----|-----------|-------|-----------|------------|-----------------|------------|----------------|
| Exp04 | 있음 | 있음 (PM 0%) | collapse 수준 | 없음 | 없음 | 없음 | baseline 아님 |
| Exp09 | 있음 | 있음 | 일부 있음 | 없음 | 없음 | 없음 | bias 지속까지는 확인 |
| Exp10 | 있음 | 있음 (34.4%) | generation degenerate | 강함 | 없음 | 없음 | perception strong, transfer 약함 |
| Exp11 | 있음 | 있음 (58.6%) | 일부 sanity evidence | 없음 | 없음 | 없음 | 현재 학습형 기준점 |
| Exp14 Step 2 | 없음 | 있음 (75.9%) | path breakdown 있음 | 간접 | 없음 | 없음 | 현재 strongest, 더 큰 검증 필요 |

## 3. 실험별 갭 분석

### Exp04

현재 확보:
- `val_loss 0.776`
- 재평가 PM `0%`
- Google-Robot backbone 전환의 효과

빠진 것:
- class confusion matrix
- stop/turn breakdown
- path type별 성능
- closed-loop rollout success
- 실기 주행 결과

왜 중요한가:
- 좋은 loss가 실제 inference를 보장하지 않는다는 반례라서 문서상 위치를 정정해야 한다.
- 추가 평가는 baseline 확정보다 failure archetype 정리에 가깝다.

권장 우선순위:
1. collapse failure note를 공식 문서에 반영
2. confusion / path breakdown을 남겨 failure archetype 고정
3. 이후 비교표에서 baseline 표기 제거

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
- rule transfer `34.4%`
- episode / batch / full viewer 산출물

빠진 것:
- 공식 metrics artifact (`metrics.json`, leaderboard row)
- path type별 perception breakdown
- bbox center error 추세
- generation 안정화 후 grounding -> action -> rollout transfer 재검증
- Exp10 기반 policy proxy와 expert trajectory 비교

왜 중요한가:
- perception은 강하지만, 현 generation 경로로는 “잘 본다”와 “잘 간다” 사이가 끊겨 있다.
- 따라서 지금 중요한 건 점수 재과시보다 generation failure를 줄이거나 small-head 우회와 비교하는 것이다.

권장 우선순위:
1. perception metrics 정식 고정
2. generation failure taxonomy 정리
3. bbox center 기반 action proxy와 Step 2를 같은 split에서 비교

### Exp11

현재 확보:
- 학습 결과
- PM `58.6%`
- 일부 sanity evidence
- config

빠진 것:
- confusion
- rollout
- 실기

왜 중요한가:
- Exp11은 지금도 기존 학습형 기준점이라서, Step 2와의 차이를 어디서 만드는지 밝혀야 한다.
- left/right 취약성이 실제 closed-loop failure로 이어지는지 닫아야 한다.

권장 우선순위:
1. confusion / path breakdown 정식화
2. Layer 2/3 필수화
3. Exp14 Step 2와 같은 split에서 직접 비교

### Exp14 Step 2

현재 확보:
- held-out split PM `75.9%`
- path type별 breakdown
- Step 1 대비 개선 근거

빠진 것:
- 더 큰 split 재현
- closed-loop rollout
- real robot

왜 중요한가:
- 현재 strongest practical baseline이지만, 규모가 작은 split에서 얻은 수치라 재현성이 핵심이다.

권장 우선순위:
1. split seed를 바꾼 재평가
2. closed-loop success / timeout / overshoot 측정
3. Exp11과 failure taxonomy 비교

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
- Exp11 confusion/path breakdown
- Exp09 rollout success rate
- Exp10 perception metrics artifact
- Exp14 Step 2 재현성 확인

### 우선순위 P1
- Exp09 / Exp11 / Exp14 공통 simulation harness
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
| Exp04 | foundation 전환 효과는 있었다 | 실제 곡선 행동을 안정적으로 배웠다 |
| Exp09 | 8-class 형식 통합은 됐다 | 실제 navigation이 잘 된다 |
| Exp10 | grounding은 강하다 | 현재 generation 경로로 policy 성공으로 이어진다 |
| Exp11 | 현재 학습형 기준점이다 | Step 2보다 실제로 낫다 |
| Exp14 Step 2 | 현재 strongest practical baseline이다 | 더 큰 split과 closed-loop에서도 유지된다 |
