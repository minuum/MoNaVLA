# 교수님 미팅 슬라이드 아웃라인 (2026-04-24)

## Slide 1. 현재 상태: 무엇이 지금 제일 잘 되나

### 제목

`exp25` is the current practical baseline

### 핵심 메시지

- 현재 최근 후보 중 실제 closed-loop가 가장 좋은 건 `exp25`
- 직진/센터 정렬 계열은 이미 동작한다
- 아직 turning family가 무너진다

### 넣을 수치

- `exp25`
  - closed-loop success: `55.6%`
  - mean FPE: `0.382`
- path success
  - `center_left`: `100%`
  - `center_right`: `100%`
  - `center_straight`: `100%`
  - `left_straight`: `100%`
  - `right_straight`: `100%`

### 발표 멘트

현재 practical baseline은 `exp25`입니다. 목표를 보면서 직진하고 정렬하는 시나리오는 이미 안정적으로 통과합니다. 그래서 지금 문제는 전체 모델이 안 되는 것이 아니라, 특정 failure slice가 남아 있는 상태라고 보는 게 맞습니다.

## Slide 2. 병목: 왜 아직 실전성이 부족한가

### 제목

Turning commitment collapses early

### 핵심 메시지

- turning family 4개가 전부 closed-loop `0%`
- `FORWARD` 쏠림이 강해서 초반 turn decision이 무너진다
- offline metric만 좋아도 rollout이 보장되지 않는다

### 넣을 수치

- `exp25` failure paths
  - `left_left`: `0%`
  - `left_right`: `0%`
  - `right_left`: `0%`
  - `right_right`: `0%`
- comparison
  - `exp26`: PM/DM `70.24%`, rollout `0.0%`
  - `exp27`: rollout `33.3%`

### 발표 멘트

핵심 병목은 turning commitment입니다. `exp25`는 직진 계열은 되지만, 회전 결심이 필요한 family에서는 전부 실패합니다. 특히 `exp26`은 offline PM/DM는 좋아도 rollout이 0이기 때문에, 지금 목표는 accuracy 자체가 아니라 turning 시점의 정책 일관성을 회복하는 것입니다.

## Slide 3. 현재 해결책: 무엇을 밤새 돌리고 있나

### 제목

`exp28`: grounding auxiliary + turning-family boost

### 핵심 메시지

- `exp25`를 베이스로 유지
- `bbox_truth_mini` 72프레임 GT를 실제 학습 신호로 연결
- turning family oversampling과 reweight 추가

### 넣을 내용

- auxiliary supervision
  - bbox regression head
  - coarse position classification head
- data emphasis
  - `left_left`, `left_right`, `right_left`, `right_right`
- current status
  - training ongoing
  - visible best checkpoint: `epoch 05 / val_loss 10.819`

### 발표 멘트

그래서 현재는 rollout이 가장 나은 `exp25`를 베이스로 두고, weakness인 turning family와 target grounding만 직접 보강하는 `exp28`을 돌리고 있습니다. 이 실험은 이미 학습 파이프라인에 연결되어 현재 진행 중이지만, 아직 rollout 개선이 확인된 상태는 아니므로 내일은 active fix in progress로 보고하는 것이 맞습니다.

## 마무리 질문

### 교수님께 확인받을 의사결정

- `exp28` 계열을 더 밀어도 되는지
- 아니면 `exp25` 기반 짧은 continue fine-tune + hard-mining으로 방향을 단순화할지

## 백업 슬라이드용 한 줄

- why not `exp26`:
  - offline strong, rollout failed
- why not `exp27`:
  - letterbox did not help
- why `exp28`:
  - directly targets the weakest turning slice with grounding supervision
