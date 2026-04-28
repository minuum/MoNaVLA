# Grounding Aux 5-Epoch Ablation (2026-04-24)

## Setup

- `exp29`: coarse-only (`lambda_bbox=0.0`, `lambda_coarse=0.1`)
- `exp30`: bbox+coarse (`lambda_bbox=0.05`, `lambda_coarse=0.1`)
- both: `5 epochs`
- goal: check whether human-reviewed `bbox_truth_mini` supervision gives a fast win before longer training

Artifacts:

- `exp29` truth eval: `docs/v5/bbox_truth_eval/exp29_aux_eval.json`
- `exp30` truth eval: `docs/v5/bbox_truth_eval/exp30_aux_eval.json`
- `exp29` ckpt: `runs/v5_nav/kosmos/mobile_vla_v5_exp29/2026-04-23/v5-exp29-step3-grounding-turnboost-coarseonly-5ep/epoch_epoch=epoch=04-val_loss=val_loss=10.745.ckpt`
- `exp30` ckpt: `runs/v5_nav/kosmos/mobile_vla_v5_exp30/2026-04-24/v5-exp30-step3-grounding-turnboost-bboxcoarse-5ep/epoch_epoch=epoch=04-val_loss=val_loss=11.193.ckpt`

## Truth Eval

### Raw matched rows

- `exp29`
  - matched visible GT frames: `36`
  - mean IoU: `0.000`
  - IoU@0.3: `0.0%`
  - mean center L1: `0.197`
  - coarse acc: `58.3%`
  - left acc: `14.3%` (`1/7`)
  - center acc: `90.9%` (`20/22`)
  - right acc: `0.0%` (`0/7`)

- `exp30`
  - matched visible GT frames: `51`
  - mean IoU: `0.000`
  - IoU@0.3: `0.0%`
  - mean center L1: `0.197`
  - coarse acc: `54.9%`
  - left acc: `0.0%` (`0/12`)
  - center acc: `96.6%` (`28/29`)
  - right acc: `0.0%` (`0/10`)

### Intersection-only fair comparison

Because the matched row count differs, compare only the common `33` frames:

- `exp29`
  - mean IoU: `0.000`
  - IoU@0.3: `0.0%`
  - mean center L1: `0.1964`
  - coarse acc: `57.6%`
  - left acc: `16.7%` (`1/6`)
  - center acc: `90.0%` (`18/20`)
  - right acc: `0.0%` (`0/7`)

- `exp30`
  - mean IoU: `0.000`
  - IoU@0.3: `0.0%`
  - mean center L1: `0.1968`
  - coarse acc: `57.6%`
  - left acc: `0.0%` (`0/6`)
  - center acc: `95.0%` (`19/20`)
  - right acc: `0.0%` (`0/7`)

### Reading

- Both models still collapse bbox prediction into tiny center boxes.
- `bbox` supervision did **not** recover usable box regression even after 5 epochs.
- `coarse-only` gave a tiny left-side win (`1/6`) on the common slice.
- `bbox+coarse` mainly made the model even more center-biased.

## PM/DM

- `exp29`: `21.43%` (`18/84`)
- `exp30`: `14.29%` (`12/84`)
- reference `exp28`: `38.10%` (`32/84`)
- reference `exp25`: `52.38%` (`44/84`)

Key class behavior:

- `exp29`
  - `FORWARD`: `0/44`
  - `LEFT`: `0/3`
  - `RIGHT`: `0/3`
  - `FWD+L`: `14/15`
  - `FWD+R`: `4/15`
  - `TURN_R`: `0/4`

- `exp30`
  - `FORWARD`: `0/44`
  - `LEFT`: `0/3`
  - `RIGHT`: `0/3`
  - `FWD+L`: `8/15`
  - `FWD+R`: `4/15`
  - `TURN_R`: `0/4`

## Bottom Line

- The human-reviewed GT is not the problem.
- The quick ablation does **not** support the claim that simply adding bbox GT fixes the policy.
- In this 5-epoch test:
  - `coarse-only` is less bad than `bbox+coarse`
  - but neither recovers `FORWARD` / `LEFT` / `RIGHT`
  - and neither produces usable bbox regression
- Therefore:
  - `exp29` and `exp30` are **not** replacement candidates for `exp25`
  - `bbox+coarse` should not be presented as a success
  - the strongest honest claim is: "GT supervision slightly sharpens coarse center-vs-side behavior, but it still fails to recover left/right grounding or action policy."

## Short Rebuttal Lines

- "사람이 검수한 GT를 붙여도 bbox 회귀는 여전히 IoU 0으로 붕괴했습니다."
- "5-epoch 간이 실험에서는 coarse-only가 bbox+coarse보다 덜 나빴고, bbox를 같이 넣는다고 policy가 좋아지지 않았습니다."
- "즉 이번 결과는 'GT를 더 넣으면 바로 해결된다'가 아니라, '현재 head/loss 설계로는 GT를 줘도 left/right와 usable bbox가 안 살아난다' 쪽입니다."
