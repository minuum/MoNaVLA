# Exp25-30 Factor Breakdown (2026-04-24)

이 문서는 `exp25~30`에서 바뀐 요소를 "학습에 얼마만큼 걸어둔 가중치인가"와 "실제 로그에서 얼마나 반영됐는가" 두 층으로 나눠 정리한다.

중요:

- 이 값은 **모델 내부 추론 기여도**가 아니다.
- 대신 **학습 objective / 샘플링 / class weighting** 기준의 정량 요약이다.

## 1. Objective-Level Weighting

기본 구조:

- total loss = `action loss` + `grounding_total`
- grounding_total = `lambda_bbox * bbox_loss + lambda_coarse * coarse_loss`

`predict_forward=False`, `predict_caption=False`라서 `fwd_loss_ratio`, `cap_loss_ratio`는 현재 실험들에서 실질 기여가 없다.

| Model | Action | BBox | Coarse | Normalized Action | Normalized BBox | Normalized Coarse |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `exp25` | 1.00 | 0.00 | 0.00 | 1.0000 | 0.0000 | 0.0000 |
| `exp26` | 1.00 | 0.00 | 0.00 | 1.0000 | 0.0000 | 0.0000 |
| `exp27` | 1.00 | 0.00 | 0.00 | 1.0000 | 0.0000 | 0.0000 |
| `exp28` | 1.00 | 0.05 | 0.10 | 0.8696 | 0.0435 | 0.0870 |
| `exp29` | 1.00 | 0.00 | 0.10 | 0.9091 | 0.0000 | 0.0909 |
| `exp30` | 1.00 | 0.05 | 0.10 | 0.8696 | 0.0435 | 0.0870 |

## 2. Observed Effective Loss Share

TensorBoard final validation scalars 기준.

| Model | `val_loss` | `val_loss_base` share | effective bbox share | effective coarse share |
| --- | ---: | ---: | ---: | ---: |
| `exp28` | 8.7493 | 0.995663 | 0.000036 | 0.004301 |
| `exp29` | 10.7452 | 0.996411 | 0.000000 | 0.003589 |
| `exp30` | 11.1925 | 0.996526 | 0.000028 | 0.003446 |

해석:

- 설정상으로는 `bbox/coarse`가 4~9%처럼 보인다.
- 실제 final validation loss에서는 `base action`이 `99.6%` 안팎이다.
- 즉 `exp28~30`도 실질적으로는 거의 전부 action objective가 지배한다.

## 3. Action-Class Weight Pressure

`FORWARD=1` 기준 상대 가중치.

### `exp25~27`

원 가중치:

- `[1.0, 0.4, 10.0, 10.0, 4.0, 4.0, 50.0, 50.0]`

`FORWARD=1` 환산:

- `STOP`: `2.5`
- `LEFT`: `25`
- `RIGHT`: `25`
- `FWD+L`: `10`
- `FWD+R`: `10`
- `TURN_L`: `125`
- `TURN_R`: `125`

### `exp28~30`

원 가중치:

- `[1.0, 0.25, 12.0, 12.0, 6.0, 6.0, 60.0, 60.0]`

`FORWARD=1` 환산:

- `STOP`: `4`
- `LEFT`: `48`
- `RIGHT`: `48`
- `FWD+L`: `24`
- `FWD+R`: `24`
- `TURN_L`: `240`
- `TURN_R`: `240`

해석:

- `exp28~30`은 `exp25~27`보다 turning / side class를 훨씬 세게 민다.
- 그 대신 실제 결과는 `FORWARD` 회복 없이 `FWD+L/FWD+R` bias가 더 강해졌다.

## 4. Data Sampling Pressure

### `exp25~27`

`path_type_weights`:

- `left=0.33`
- `straight=0.33`
- `right=0.34`

즉 좌/중/우 대분류만 균형화.

### `exp28~30`

`path_family_weights`:

- `center_straight=0.07`
- `center_left=0.10`
- `center_right=0.10`
- `left_straight=0.07`
- `left_left=0.17`
- `left_right=0.16`
- `right_straight=0.07`
- `right_left=0.13`
- `right_right=0.13`

즉 turning family를 더 자주 보게 만든 구조.

## 5. Factor vs. Outcome

| Model | Main changed factor | PM/DM | Rollout / ETE | BBox-truth takeaway |
| --- | --- | ---: | --- | --- |
| `exp25` | balanced objective baseline | `52.38%` | best practical rollout (`55.6%`) | no bbox aux |
| `exp26` | direct 224 preprocessing | `70.24%` | rollout `0.0%` | no bbox aux |
| `exp27` | letterbox 224 preprocessing | `15.48%` | rollout `33.3%` | no bbox aux |
| `exp28` | + grounding aux + turn-family boost | `38.10%` | rollout `0.0%` | bbox collapse to tiny center box |
| `exp29` | `exp28` minus bbox, coarse-only, 5ep | `21.43%` | not promoted | IoU `0.0`, coarse `58.3%`, left `1/7` |
| `exp30` | `exp28` bbox+coarse, 5ep | `14.29%` | not promoted | IoU `0.0`, coarse `54.9%`, left `0/12` |

## 6. Bottom Line

- `exp25~27`: 사실상 `action-only` 계열
- `exp28~30`: 이름은 grounding aux 실험이지만, **실제 loss 기준으로는 여전히 거의 전부 action-driven**
- `exp28~30`에서 새로 들어간 강한 요소는:
  - side/turn class reweighting
  - turn-family oversampling
  - tiny-weight bbox/coarse aux
- 실제 결과상 가장 크게 드러난 건:
  - usable bbox 회복 실패
  - center bias 강화
  - `FORWARD` 회복 실패

그래서 현재 데이터는 이렇게 읽는 게 맞다:

- "bbox/coarse를 넣었다"는 사실보다
- "여전히 action objective가 99% 이상 지배했고, 새 aux는 성능을 뒤집을 만큼 강하지 않았다"

