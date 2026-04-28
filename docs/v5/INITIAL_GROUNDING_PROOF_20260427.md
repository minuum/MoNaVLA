# Initial Grounding Proof (2026-04-27)

## Goal

Prove or falsify the first branch of the 2026-04-24 professor feedback:

- Does raw pure-HF Kosmos-2 see the gray basket at all on early frames?
- If perception is alive, the action collapse is a downstream policy-learning problem.
- If perception is already broken, policy experiments should not be the main focus.

## Fixed Evaluation Slice

- Truth scaffold: `docs/v5/bbox_truth_initial18.json`
- Scope: `9 path families x 2 initial frames = 18 frames`
- Frame policy: nearest available frames to `0` and `2`
- Output expectation:
  - quantitative JSON summary
  - overlay images or HTML viewer
  - one-page conclusion for the meeting

## Runbook

```bash
python3 scripts/analysis/generate_v5_bbox_truth_initial18.py
python3 scripts/analysis/evaluate_v5_bbox_truth.py --truth docs/v5/bbox_truth_initial18.json
```

## Success Criteria

- `target_visible` is explicitly reviewed for all 18 frames.
- Visible frames have coarse position labels (`left / center / right`).
- Visible frames have GT bbox rows filled in.
- Evaluation produces:
  - `detection_recall`
  - `false_positive_rate`
  - `mean_iou`
  - `wrong_side_rate`

## Current Status (2026-04-24)

- Implementation status: scaffold generator added
- Truth file status: pending review until `bbox_truth_initial18.json` is filled
- Evaluation status: pending human review completion

## Meeting Use

- If early-frame perception is non-trivial, say: "객체 인식은 살아 있고, 현재 병목은 action commitment 쪽입니다."
- If early-frame perception is weak, say: "현재 문제는 행동 학습 이전에 perception evidence가 부족한 상태입니다."
