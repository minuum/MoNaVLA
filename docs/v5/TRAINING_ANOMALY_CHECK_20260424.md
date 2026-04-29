# Training Anomaly Check (2026-04-24)

## Scope

- reviewed log:
  - `runs/v5_nav/kosmos/mobile_vla_v5_exp31/2026-04-24/v5-exp31-step3-grounding-turnboost-learnedmix-5ep/train.log`
- live smoke run:
  - `exp32` left-start 50ep head-only run is currently in progress

## Observed Facts

- `exp31` training itself finished normally.
  - log ends with `Trainer.fit stopped: max_epochs=5 reached`
- the navigation trainer consistently enters the discrete branch.
  - repeated log: `DEBUG: [NavTrainer] Discrete branch taken. arm_action shape: torch.Size([4, 10])`
- no visible `NaN`, `OOM`, or crash signal appears in the inspected log slice.
- live `exp32` left-only smoke run is active with the intended left-start filter.
  - train episodes: `40`
  - val episodes: `10`
  - trainable params: `37.8M`
  - params with `requires_grad=True`: `19`
  - epoch 0 early `train_loss_step`: roughly `8.18 ~ 8.34`

## Main Suspicious Signal

- early in `exp31` and also in the live `exp32` startup, PyTorch emits:
  - `torch.utils.checkpoint: None of the inputs have requires_grad=True. Gradients will be None`

## Interpretation

- for a fully frozen backbone or head-only run, this warning can be partially expected.
- for a run that is supposed to learn through LoRA or selective decoder adaptation, this warning is load-bearing and should be treated as a real check item.
- the immediate question is not "did training crash?" but "is the intended trainable path actually receiving gradient?"

## Monday Checkpoints

- verify trainable parameter count by run:
  - `exp32`: head only should be fine if backbone grad is absent
  - `exp33`: last-4 decoder + LoRA must show real trainable decoder-side params
- inspect one backward pass or gradient norm dump for:
  - action head
  - LoRA layers
  - last 4 decoder blocks

## Current Bottom Line

- there is no evidence yet of a runtime failure.
- there is evidence of a possible gradient-flow mismatch between intended adaptation scope and actual active graph.
- this is the main training-process anomaly worth reporting right now.
- separately, `exp32` has at least started with the correct left-only data slice and head-only trainability, so the run itself is a valid Monday proof run.
