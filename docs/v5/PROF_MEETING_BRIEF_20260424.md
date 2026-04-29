# 교수님 미팅 브리프 (2026-04-24)

## 1. 한 줄 요약

- 현재 실전 기준 best baseline은 `exp25`다.
- 핵심 병목은 `turning commitment` 붕괴다.
- 현재 밤새 돌리는 개선 실험은 `exp28`이며, `bbox_truth_mini` 기반 auxiliary grounding + turning-family oversampling을 붙인 상태다.

## 2. 내일 미팅에서 먼저 말할 것

### A. 현재 best practical baseline

- 모델: `exp25`
- checkpoint:
  - `runs/v5_nav/kosmos/mobile_vla_v5_exp25/2026-04-22/v5-exp25-step3-balanced-objective/epoch_epoch=epoch=02-val_loss=val_loss=10.117.ckpt`
- 핵심 수치:
  - closed-loop success: `55.6%`
  - closed-loop mean FPE: `0.382`
  - closed-loop mean TLD: `0.936`

### B. baseline의 강점과 한계

- 강점:
  - `center_left`, `center_right`, `center_straight`, `left_straight`, `right_straight`는 closed-loop `100%`
  - 직진/센터 정렬 계열은 이미 실전성이 있다
- 한계:
  - `left_left`, `left_right`, `right_left`, `right_right`는 closed-loop `0%`
  - 즉 목표를 보면서 직진하는 건 되지만, 초반 회전 결심이 필요한 path family에서 무너진다

## 3. 비교군 해석

| Model | Closed-loop | Mean FPE | 해석 |
|---|---:|---:|---|
| `exp25` | `55.6%` | `0.382` | 현재 best practical baseline |
| `exp26` | `0.0%` | `1.189` | offline 지표는 강하지만 rollout 실패 |
| `exp27` | `33.3%` | `0.932` | letterbox 가설은 현재 악화 |

추가 관찰:

- `exp25` PM/DM는 약 `52.38% (44/84)`이고, `FORWARD` collapse 경향이 강하다.
- `exp26` PM/DM는 약 `70.24% (59/84)`로 offline 분류는 가장 좋지만, 실제 rollout은 `0.0%`다.
- `exp27` PM/DM는 약 `15.48% (13/84)`로 매우 불안정하다.

결론:

- 지금 병목은 단순 accuracy 부족이 아니라 `turning 시점의 정책 일관성 부족`이다.
- 따라서 내일 미팅 메시지는 `exp26/27이 왜 답이 아닌지`까지 같이 설명해야 한다.

## 4. 현재 해결 실험: `exp28`

### 무엇을 바꿨는가

- 베이스: `exp25`
- 추가된 학습 신호:
  - `bbox_truth_mini.json` 72프레임 auxiliary grounding supervision
  - auxiliary bbox regression head
  - auxiliary coarse position classification head
- 데이터 쪽 보강:
  - `left_left`, `left_right`, `right_left`, `right_right` family oversampling
  - `FORWARD` 과다 예측을 누르기 위한 class weighting 강화

### 왜 이 실험이 타당한가

- `exp25`는 rollout은 가장 좋지만 turning family가 무너진다.
- `exp26`은 offline 신호를 올릴 수 있어도 rollout을 망칠 수 있다는 반례다.
- 그래서 `exp28`은 `rollout이 괜찮은 exp25`를 베이스로 두고, 실제 weakness인 turning family와 target grounding만 직접 보강한다.

### 현재 상태

- run dir:
  - `runs/v5_nav/kosmos/mobile_vla_v5_exp28/2026-04-23/v5-exp28-step3-objective-grounding-turnboost`
- live log:
  - `runs/v5_nav/kosmos/mobile_vla_v5_exp28/2026-04-23/v5-exp28-step3-objective-grounding-turnboost/train.log`
- 현재 로그 기준:
  - 학습 진행 중
  - `Epoch 6` 중반대까지 확인
  - latest visible `val_loss`: `10.80`
  - latest visible `train_loss_epoch`: 약 `9.660`
- 현재 저장된 checkpoint:
  - `epoch 02`: `val_loss 11.471`
  - `epoch 04`: `val_loss 11.193`
  - `epoch 05`: `val_loss 10.819`

현재 시점 해석:

- `exp28`은 아직 `성공`이라고 말할 수 없다.
- 다만 설계와 연결은 끝났고, 실제 학습은 정상 진행 중이다.
- 내일 아침까지 rollout 재평가 결과가 없거나 뚜렷한 개선이 없으면, 발표에서는 `active fix in progress`로만 말하는 것이 맞다.

## 5. 내일 발표 구조

### 1분: 현재 상태

- 현재 practical baseline은 `exp25`
- 직진/정렬은 된다

### 2분: 병목

- turning family 4개가 전부 closed-loop `0%`
- `FORWARD` 쏠림이 강해서 초반 turn commitment가 무너진다
- offline metric이 좋아도 rollout이 보장되지 않는 반례가 `exp26`

### 2분: 해결 방향

- `exp28`에서 grounding auxiliary supervision을 실제 학습에 연결했다
- turning-family oversampling과 class reweight를 추가했다
- 목적은 `exp25`의 안정성은 유지하고 turning path만 회복하는 것

### 1분: 교수님께 확인받을 결정 포인트

- `exp28` 계열을 더 밀 것인지
- 아니면 `exp25` 기반 짧은 continue fine-tune + hard-mining으로 갈 것인지

## 6. 아침 체크포인트

- `exp28`이 밤새 정상 진행했는지 확인
- best checkpoint가 더 갱신됐는지 확인
- `val_loss`가 계속 내려가는지 확인
- 아침까지 개선 근거가 약하면:
  - `exp25`를 baseline으로 고정
  - `exp28`은 `진행 중인 보강 실험`으로만 보고
- 아침까지 개선 근거가 보이면:
  - `exp28`을 `next candidate`로 설명
  - 단, rollout 재평가 전에는 배포 후보로 말하지 않음

## 7. 예상 질문에 대한 짧은 답

### 왜 `exp25`가 현재 best인가

- 최근 후보들 중 closed-loop가 가장 높고, full rollout FPE도 가장 낮다.

### 왜 `exp26`이 아닌가

- offline PM/DM는 더 좋지만 실제 rollout `0.0%`라서 실전 기준으로는 탈락이다.

### 왜 `exp27`이 아닌가

- letterbox 가설이 현재 수치상 악화로 보인다.

### 왜 `exp28`이 합리적인 다음 실험인가

- 현재 weakest slice인 turning family를 직접 더 보게 하고, target grounding GT 72프레임을 실제 학습 신호로 연결했기 때문이다.

## 8. 증거 파일

- short-term summary:
  - `docs/v5/shortterm_eval/summary.json`
- rollout degradation:
  - `docs/v5/rollout_degradation/degradation_summary.json`
- exp28 live log:
  - `runs/v5_nav/kosmos/mobile_vla_v5_exp28/2026-04-23/v5-exp28-step3-objective-grounding-turnboost/train.log`
- prior deploy/handoff note:
  - `docs/v5/MONAVLA_DRIVING_HANDOFF_20260422.md`
