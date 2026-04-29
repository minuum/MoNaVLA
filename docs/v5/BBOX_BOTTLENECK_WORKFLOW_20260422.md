# V5 BBox Bottleneck Workflow

Current V5 bottleneck splitting uses three layers of artifacts:

1. Raw route/task metrics
- `docs/v5/shortterm_eval/summary.json`
- `docs/v5/rollout_degradation/degradation_summary.json`

2. Pseudo bbox baseline
- `docs/v5/bbox_nav_step1/bbox_dataset.json`
- `docs/v5/bbox_nav_step1/summary.json`

3. Human-review scaffold and truth eval
- `docs/v5/bbox_truth_mini.json`
- `docs/v5/bbox_truth_eval/summary.json`

## Important constraint

`bbox_nav_step1/bbox_dataset.json` is **not** human ground truth.
It is a pseudo bbox cache built from Pure-HF Kosmos-2 grounding.

Therefore:
- use it as a proxy baseline
- do not use it as final perception truth

## Mini truth review procedure

Generate the scaffold:

```bash
python3 scripts/analysis/generate_v5_bbox_truth_mini.py
```

Then review `docs/v5/bbox_truth_mini.json` and fill these fields per row:

- `review_status`: `complete`
- `target_visible`: `true` or `false`
- `bbox_xyxy_norm`: normalized `[x1, y1, x2, y2]` when visible
- `coarse_position`: `left | center | right | ambiguous | not_visible`
- `goal_near`: `true` or `false`

After review:

```bash
python3 scripts/analysis/evaluate_v5_bbox_truth.py
python3 scripts/analysis/evaluate_v5_bottleneck_split.py
```

## Outputs

- `docs/v5/bbox_truth_eval/summary.json`
- `docs/v5/bottleneck_split/summary.json`
- `docs/v5/bottleneck_split/index.html`
