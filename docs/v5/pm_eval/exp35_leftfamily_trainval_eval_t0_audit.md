# Exp35 Left-Family Train+Val Action Audit

Date: 2026-04-25

Source:
- Transcript-derived TODOs: `docs/v5/APR24_PROF_TODO_FROM_TRANSCRIPT.md`
- Raw JSON: `docs/v5/pm_eval/exp35_leftfamily_trainval_eval_t0.json`
- Model: `runs/v5_nav/kosmos/mobile_vla_v5_exp35/2026-04-25/v5-exp35-pure-hf-last4-lora-left50-fixed-5ep/epoch_epoch=epoch=04-val_loss=val_loss=6.535.ckpt`
- Config: `configs/mobile_vla_v5_exp35_pure_hf_last4_lora_left50_fixed_5ep.json`

## Result

This fails the professor's minimal left-family sanity check.

- Evaluated sequences: 422
- Errors: 0
- Split: train 336, val 86
- Path families: left_right 135, left_left 127, left_straight 160
- PM: 56.16% (237/422)
- Prediction distribution: FORWARD 422/422

GT distribution:

| GT class | Count | Correct | Predicted as |
|---|---:|---:|---|
| FORWARD | 237 | 237 | FORWARD |
| LEFT | 45 | 0 | FORWARD |
| FWD+L | 30 | 0 | FORWARD |
| FWD+R | 90 | 0 | FORWARD |
| TURN_R | 20 | 0 | FORWARD |

Non-FORWARD GT frames: 185/422. All 185 were predicted as FORWARD.

## Raw-Output Pattern

The model output is not just biased toward FORWARD; the logits are nearly constant across all 422 frames.

Mean/range by class:

| Class | Min logit | Max logit | Mean logit |
|---|---:|---:|---:|
| STOP | -0.0606 | -0.0563 | -0.0587 |
| FORWARD | 0.0704 | 0.0763 | 0.0736 |
| LEFT | 0.0090 | 0.0102 | 0.0096 |
| RIGHT | 0.0009 | 0.0015 | 0.0012 |
| FWD+L | 0.0353 | 0.0373 | 0.0364 |
| FWD+R | 0.0196 | 0.0212 | 0.0204 |
| TURN_L | -0.0281 | -0.0249 | -0.0267 |
| TURN_R | -0.0213 | -0.0185 | -0.0199 |

Example row from the raw JSON:

```json
{
  "idx": 0,
  "split": "train",
  "episode": "episode_260409_123044_target_left_right_path__core__fixed_center.h5",
  "start_frame": 0,
  "eval_frame": 0,
  "path_family": "left_right",
  "raw_text": "<grounding>Navigate straight forward to the gray basket. 바구니를 향해 직진해.",
  "gt_name": "FWD+R",
  "gt_action_3d": [1.15, -1.15, 0.0],
  "pred_name": "FORWARD",
  "pred_action_3d": [1.15, 0.0, 0.0]
}
```

Top classes for that row:

```json
[
  {"class_idx": 1, "class_name": "FORWARD", "logit": 0.0736083984375, "prob": 0.13385386190853724, "action_3d": [1.15, 0.0, 0.0]},
  {"class_idx": 4, "class_name": "FWD+L", "logit": 0.036376953125, "prob": 0.12896192125908487, "action_3d": [1.15, 1.15, 0.0]},
  {"class_idx": 5, "class_name": "FWD+R", "logit": 0.0202789306640625, "prob": 0.12690251005186431, "action_3d": [1.15, -1.15, 0.0]}
]
```

## Interpretation

This is no longer a small-val-set artifact. The model predicts FORWARD on every left-family train and val sequence, including 185 non-FORWARD labels.

Given the professor's ordering, the next technical check should be action head/LSTM/class-mapping and a tiny overfit test. More broad training should wait until this collapse is explained.

Remaining evidence gap: this action audit does not yet attach predicted grounding/bbox output to the same rows. The initial-frame recognition proof still needs human-reviewed bbox pass/fail or a joined grounding/action report.
