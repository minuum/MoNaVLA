# 교수님 반박 Talk Track (2026-04-24)

## 한 줄 주장

**사람이 검수한 bbox GT를 붙이면 바로 해결된다는 가설은 현재 데이터로는 지지되지 않습니다.  
문제는 GT 품질이 아니라, 현재 head/loss 설계가 그 GT를 usable bbox와 left/right policy 회복으로 전달하지 못한다는 점입니다.**

## 30초 버전

- 현재 practical baseline은 `exp25`입니다.
  - closed-loop `55.6%`
  - PM/DM `52.38%`
- 그래서 지금 문제는 "전체 모델이 안 된다"가 아니라, `turning commitment`가 남아 있는 상태입니다.
- 이 상태에서 사람 검수 GT를 붙인 `exp29/30`을 짧게 검증했는데:
  - bbox IoU는 둘 다 `0.0`
  - `FORWARD/LEFT/RIGHT`도 회복되지 않았습니다
- 즉 현재 데이터는 "GT를 더 넣으면 바로 해결된다"보다, "현재 설계로는 GT를 줘도 안 살아난다"를 지지합니다.

## 2분 버전

### 1. baseline을 먼저 고정

- 현재 기준 model selection은 offline이 아니라 실제 `ETE/closed-loop` 기준입니다.
- 그 기준에서 `exp25`가 현재 best practical baseline입니다.
  - closed-loop success `55.6%`
  - mean FPE `0.382`
  - PM/DM `52.38%`

### 2. 교수님 가설에서 맞는 부분과 아닌 부분을 분리

- 맞는 부분:
  - `bbox_truth_mini`는 사람 검수 GT입니다.
  - 따라서 GT 품질 자체를 문제 삼을 이유는 없습니다.
- 아닌 부분:
  - "사람 GT를 붙였으니 bbox와 policy가 같이 좋아질 것"은 현재 결과로는 확인되지 않았습니다.

### 3. 반박의 직접 증거

- 먼저 퓨어 bbox baseline이 더 높습니다.
  - pure grounding seed:
    - mean IoU `0.264`
    - IoU@0.3 `20.8%`
- 그런데 GT를 넣은 짧은 학습 실험은 bbox를 못 살렸습니다.
  - `exp29`:
    - mean IoU `0.000`
    - IoU@0.3 `0.0%`
    - PM/DM `21.43%`
  - `exp30`:
    - mean IoU `0.000`
    - IoU@0.3 `0.0%`
    - PM/DM `14.29%`
- 그리고 둘 다 정책 핵심 실패가 그대로 남았습니다.
  - `FORWARD 0/44`
  - `LEFT 0/3`
  - `RIGHT 0/3`

### 4. 왜 이런가

- 현재 실험은 이름상 grounding aux가 들어가 있지만, 실제 학습은 거의 전부 action objective가 지배합니다.
- final validation loss 기준으로:
  - `exp28`: base share 약 `99.57%`
  - `exp29`: base share 약 `99.64%`
  - `exp30`: base share 약 `99.65%`
- 즉 bbox/coarse는 config에는 들어가 있어도, 실제로는 너무 약해서 shared feature를 못 바꿉니다.
- 그 결과:
  - bbox head는 tiny center box로 collapse
  - coarse는 center bias만 강화
  - left/right policy는 회복 실패

### 5. 결론

- 현재 데이터로는:
  - "human GT가 틀렸다"는 말도 맞지 않고
  - "human GT를 붙이면 바로 해결된다"도 맞지 않습니다.
- 가장 정확한 표현은:
  - **GT는 맞지만, 현재 학습 설계로는 그 GT가 bbox/policy 회복으로 전달되지 않는다** 입니다.

## 짧은 반박 문장

### 문장 1

```text
bbox mini GT는 사람이 검수한 정답이 맞습니다.
그런데 이번 5-epoch ablation에서는 그 GT를 붙여도 bbox IoU가 0으로 붕괴했고,
policy의 FORWARD/LEFT/RIGHT도 회복되지 않았습니다.
```

### 문장 2

```text
즉 현재 결과는 "GT가 틀렸다"가 아니라,
"현재 head/loss 구조로는 GT를 줘도 left/right와 usable bbox가 안 살아난다"를 의미합니다.
```

### 문장 3

```text
그래서 지금 단계에서 bbox+coarse를 성공 사례로 말하는 건 어렵고,
exp25를 baseline으로 유지하는 게 맞습니다.
```

## 예상 질문에 대한 답

### 왜 `exp25`를 계속 유지하나

- 최근 후보 중 실제 closed-loop가 가장 높고, rollout이 가장 안정적이기 때문입니다.

### 그러면 GT supervision은 무의미한가

- 완전히 무의미하다고 보긴 어렵습니다.
- 다만 현재 설계에서는 coarse center-vs-side 정도만 조금 흔들고, usable bbox나 left/right policy 회복으로는 이어지지 않았습니다.

### 백본이 문제인가

- 현재 데이터만으로 백본이 유일한 문제라고 말하긴 어렵습니다.
- 오히려 지금은 aux head, loss weighting, shared feature competition 쪽 문제가 더 직접적입니다.

## 마지막 15초 후속 카드

```text
그래서 지금은 고정 lambda가 아니라 action/bbox/coarse 비율 자체를 학습하게 하는 follow-up 실험 exp31을 돌리고 있습니다.
다만 결과가 아직 없기 때문에, 오늘 결론은 기존 실측 데이터까지만 기준으로 말씀드리는 게 맞습니다.
```

## 근거 문서

- `docs/v5/PROF_MEETING_BRIEF_20260424.md`
- `docs/v5/GROUNDING_AUX_ABLATION_20260424.md`
- `docs/v5/EXP25_30_FACTOR_BREAKDOWN_20260424.md`
