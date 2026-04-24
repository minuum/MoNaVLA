# 2026-04-24 교수님 미팅 슬라이드 문구

## Slide 1. 현재 상태

### 제목

`exp25` is the current practical baseline

### 본문 포인트

- 현재 최근 후보 중 practical baseline은 `exp25`
- closed-loop success `55.6%`
- mean FPE `0.382`
- 직진/센터 정렬 계열은 이미 동작

### 발표 멘트

현재는 `exp25`가 가장 실전적인 baseline입니다. 목표를 보며 직진하고 정렬하는 시나리오는 이미 안정적으로 통과합니다. 그래서 지금 문제는 전체 실패가 아니라, 특정 failure slice가 남아 있는 상태라고 보는 게 맞습니다.

## Slide 2. 이미 되는 path

### 제목

Straight and center-alignment are already working

### 본문 포인트

- closed-loop `100%`
  - `center_left`
  - `center_right`
  - `center_straight`
  - `left_straight`
  - `right_straight`

### 발표 멘트

이 다섯 path는 이미 closed-loop가 전부 100%입니다. 즉 perception이나 기본 전진 제어가 완전히 안 되는 상황은 아닙니다.

## Slide 3. 남은 병목

### 제목

Turning commitment collapses early

### 본문 포인트

- closed-loop `0%`
  - `left_left`
  - `left_right`
  - `right_left`
  - `right_right`
- 핵심 병목: early turn decision inconsistency

### 발표 멘트

실패는 turning family에 집중돼 있습니다. 따라서 지금 핵심 병목은 accuracy 부족이 아니라, 초반에 어느 방향으로 돌기 시작할지에 대한 정책 일관성이 무너지는 점입니다.

## Slide 4. 왜 offline만 보면 안 되는가

### 제목

Offline strength does not guarantee rollout

### 표

| Model | PM/DM | Closed-loop |
| --- | ---: | ---: |
| `exp25` | `52.38%` | `55.6%` |
| `exp26` | `70.24%` | `0.0%` |
| `exp27` | `15.48%` | `33.3%` |

### 발표 멘트

`exp26`은 offline metric만 보면 가장 좋지만 rollout은 0입니다. 그래서 이번 단계에서는 모델 선택 기준을 정확도보다 rollout에 두는 게 맞습니다.

## Slide 5. bbox GT를 넣으면 바로 해결되는가

### 제목

Human-reviewed GT alone was not enough

### 표

| Model | Setting | IoU@0.3 | PM/DM |
| --- | --- | ---: | ---: |
| `exp29` | coarse-only, 5ep | `0.0%` | `21.43%` |
| `exp30` | bbox+coarse, 5ep | `0.0%` | `14.29%` |

### 발표 멘트

사람이 검수한 bbox GT를 넣어도 현재 short ablation에서는 usable bbox와 policy recovery가 나타나지 않았습니다. 이건 GT가 틀렸다는 뜻이 아니라, 현재 head와 loss 구조로는 GT를 넣어도 shared feature를 충분히 바꾸지 못한다는 뜻입니다.

## Slide 6. 현재 해석

### 제목

The issue is not GT quality, but loss competition

### 본문 포인트

- `exp28~30`도 실제 validation loss 기준으로 거의 action-dominant
- bbox/coarse supervision이 실제 학습 경쟁에서 너무 약함
- 결과:
  - bbox collapse to tiny center box
  - center bias 강화
  - left/right recovery 실패

### 발표 멘트

현재 evidence는 GT 품질 문제보다 loss competition 문제를 더 강하게 가리킵니다. auxiliary supervision이 설정에는 들어가 있지만 실제 학습에서는 너무 약하게 작동하고 있습니다.

## Slide 7. 현재 수정 방향

### 제목

Keep `exp25`, fix the weakest slice directly

### 본문 포인트

- `exp28`
  - `exp25` 기반
  - grounding auxiliary
  - turning-family oversampling
- `exp31`
  - learned loss mixing
  - 2026-04-24 short run 완료
  - rollout eval pending

### 발표 멘트

그래서 현재는 `exp25`를 버리는 게 아니라, 가장 약한 turning slice를 직접 보강하는 방향으로 가고 있습니다. 오늘 기준으로는 `exp25 baseline + exp28~31 active fix in progress`가 가장 정확한 정리입니다.

## Slide 8. 마무리

### 제목

Takeaway

### 본문 포인트

1. `exp25` is the current practical baseline
2. Remaining bottleneck is turning commitment
3. Offline metric alone is insufficient
4. Human GT alone did not fix the problem
5. Current work is focused on making auxiliary grounding actually compete

### 발표 멘트

정리하면, 현재는 baseline이 분명히 있고, 병목도 분명히 보입니다. 그래서 이제는 막연히 새 모델을 찾기보다, weakest slice를 정확히 겨냥한 수정 실험을 이어가는 것이 맞습니다.
