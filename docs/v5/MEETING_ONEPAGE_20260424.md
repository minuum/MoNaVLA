# 2026-04-24 교수님 미팅 1페이지 요약

## 한 줄 결론

현재 가장 정확한 보고는 다음입니다.

`exp25`가 현재 practical baseline이고, 남은 핵심 병목은 전체 실패가 아니라 `turning commitment` failure slice입니다.  
`exp26`은 offline이 좋아도 rollout이 `0.0%`였고, human-reviewed bbox GT를 붙인 `exp29/30`도 바로 해결책은 아니었습니다.  
따라서 오늘 메시지는 `exp25 baseline + exp28~31 active fix in progress`가 맞습니다.

## 지금 제일 잘 되는 모델

- 현재 best practical baseline: `exp25`
- 핵심 수치
  - closed-loop success: `55.6%`
  - mean FPE: `0.382`
  - mean TLD: `0.936`
  - PM/DM: `52.38%`
- 이미 되는 slice
  - `center_left`, `center_right`, `center_straight`, `left_straight`, `right_straight` closed-loop `100%`

## 남아 있는 병목

- 실패 slice
  - `left_left`, `left_right`, `right_left`, `right_right` closed-loop `0%`
- 해석
  - 목표를 보며 직진/정렬하는 것은 이미 가능
  - 하지만 초반 turn decision이 필요한 family에서 `turning commitment collapse`가 남아 있음

## 왜 accuracy만 보면 안 되는가

| 모델 | PM/DM | Closed-loop | 해석 |
| --- | ---: | ---: | --- |
| `exp25` | `52.38%` | `55.6%` | 현재 best practical baseline |
| `exp26` | `70.24%` | `0.0%` | offline strong, rollout fail |
| `exp27` | `15.48%` | `33.3%` | letterbox 가설 악화 |

- `exp26`은 이번 미팅에서 반드시 반례로 써야 한다.
- 즉 지금 목표는 accuracy 숫자를 더 올리는 것이 아니라, rollout 중 일관된 turn policy를 회복하는 것이다.

## GT bbox를 붙이면 바로 해결되는가

- 현재 short ablation 결과는 `아니오`에 가깝다.

| 모델 | 설정 | IoU@0.3 | PM/DM | 해석 |
| --- | --- | ---: | ---: | --- |
| `exp29` | coarse-only, 5ep | `0.0%` | `21.43%` | bbox 없이 coarse만 본 short ablation |
| `exp30` | bbox+coarse, 5ep | `0.0%` | `14.29%` | bbox까지 넣었지만 더 악화 |

- 둘 다 `FORWARD`, `LEFT`, `RIGHT` 회복 실패
- 따라서 맞는 해석은:
  - GT가 틀린 것이 아니라
  - **현재 head/loss 구조로는 GT를 줘도 usable bbox와 left/right policy가 살아나지 않는다**

## 현재 해결 방향

- `exp28`
  - `exp25` 기반
  - grounding auxiliary + turning-family oversampling 추가
  - rollout 개선은 아직 확인 못함
- `exp31`
  - 2026-04-24 당일 follow-up
  - action/bbox/coarse 비율을 고정 lambda가 아니라 learned mixing으로 조정
  - short 5-epoch training 완료, 평가 대기

## 오늘 교수님께 드릴 핵심 문장

1. 현재 best baseline은 `exp25`입니다.
2. 남은 문제는 전체 failure가 아니라 turning family에서의 early commitment 붕괴입니다.
3. `exp26`이 보여주듯 offline metric은 rollout을 보장하지 않습니다.
4. human-reviewed bbox GT를 붙인 `exp29/30`도 바로 해결되지 않았습니다.
5. 그래서 지금은 `exp25`를 유지하면서, aux loss가 실제로 작동하도록 `exp28~31` 보강 실험을 진행 중입니다.
