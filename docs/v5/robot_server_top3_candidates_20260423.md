# V5 Robot Server Top 3 Candidates (2026-04-23)

Current recommendation is to prepare `exp25`, `exp27`, `exp26` for the robot server, in that order.

## Rank 1: `exp25`

- Role: current best practical baseline
- Checkpoint: `runs/v5_nav/kosmos/mobile_vla_v5_exp25/2026-04-22/v5-exp25-step3-balanced-objective/epoch_epoch=epoch=02-val_loss=val_loss=10.117.ckpt`
- Config: `configs/mobile_vla_v5_exp25_step3_balanced_objective.json`
- Key numbers:
  - closed-loop success: `55.6%`
  - mean FPE: `0.382`
  - mean TLD: `0.936`
  - PM/DM: `52.38%`

## Rank 2: `exp27`

- Role: secondary rollout candidate / letterbox reference
- Checkpoint: `runs/v5_nav/kosmos/mobile_vla_v5_exp27/2026-04-23/v5-exp27-step3-objective-letterbox224/epoch_epoch=epoch=08-val_loss=val_loss=7.932.ckpt`
- Config: `configs/mobile_vla_v5_exp27_step3_objective_letterbox224.json`
- Key numbers:
  - closed-loop success: `33.3%`
  - mean FPE: `0.932`
  - PM/DM: `15.48%`

## Rank 3: `exp26`

- Role: offline-strong reference only
- Checkpoint: `runs/v5_nav/kosmos/mobile_vla_v5_exp26/2026-04-22/v5-exp26-step3-objective-direct224/epoch_epoch=epoch=14-val_loss=val_loss=7.036.ckpt`
- Config: `configs/mobile_vla_v5_exp26_step3_objective_direct224.json`
- Key numbers:
  - closed-loop success: `0.0%`
  - mean FPE: `1.189`
  - PM/DM: `70.24%`

## Excluded For Now

- `exp29`: 5-epoch coarse-only smoke run still training
- `exp30`: queued after `exp29`, not evaluated yet

## Server Note

Robot server loaders in `robovlm_nav/serve/inference_server.py` expect a `checkpoint + config` pair, so both must be transferred together.

Recommended default:

```bash
export VLA_CHECKPOINT_PATH="runs/v5_nav/kosmos/mobile_vla_v5_exp25/2026-04-22/v5-exp25-step3-balanced-objective/epoch_epoch=epoch=02-val_loss=val_loss=10.117.ckpt"
export VLA_CONFIG_PATH="configs/mobile_vla_v5_exp25_step3_balanced_objective.json"
```
