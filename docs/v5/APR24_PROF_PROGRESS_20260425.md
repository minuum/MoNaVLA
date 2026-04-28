# April 24 Professor Feedback Progress Check - 2026-04-25

Source transcript:
`docs/v5/11_08 AM - In-Person meeting April 24_transcript.txt`

Grounded TODO list:
`docs/v5/APR24_PROF_TODO_FROM_TRANSCRIPT.md`

## Current Status

### TODO 1: Object recognition proof

Status: prepared, not proven.

Implemented artifacts:
- `scripts/analysis/build_initial_grounding_proof_report.py`
- `docs/v5/initial_grounding_proof/index.html`
- `docs/v5/initial_grounding_proof/summary.json`

Current limitation:
- `docs/v5/bbox_truth_initial18.json` has 18 rows, but all remain pending human review.
- Therefore this can show overlays and candidate model/seed boxes, but cannot yet support the professor-facing claim that the VLM reliably recognizes the gray basket.

Transcript basis:
- Lines 10-18: professor asks what proves object recognition.
- Lines 50-60: student admits the proof experiment has not been done and commits to prove it.
- Lines 132-135: plan to test initial frames directly.

### TODO 2: Raw inference log audit on initial frames

Status: partially implemented for PM/DM action logits; still missing grounding output on the same initial frames.

Why:
- The professor asks what X/Y/Z or action values are logged when the robot goes straight.
- The expanded PM/DM JSON now includes prompt, episode/frame, GT class/action, logits, softmax, chosen class, and decoded dataset action.
- It does not yet include the predicted grounding/bbox output in the same row, so the recognition-to-action chain is not fully closed.

Artifact:
- `docs/v5/pm_eval/exp35_leftfamily_trainval_eval_t0.json`
- `docs/v5/pm_eval/exp35_leftfamily_trainval_eval_t0_audit.md`

Transcript basis:
- Lines 136-143.

### TODO 3: Minimal left-only training/inference sanity

Status: trained, sanity check failed.

Run:
- Config: `configs/mobile_vla_v5_exp35_pure_hf_last4_lora_left50_fixed_5ep.json`
- Checkpoint: `runs/v5_nav/kosmos/mobile_vla_v5_exp35/2026-04-25/v5-exp35-pure-hf-last4-lora-left50-fixed-5ep/epoch_epoch=epoch=04-val_loss=val_loss=6.535.ckpt`

Training result:
- Completed 5 epochs.
- Best validation checkpoint: epoch 4, `val_loss=6.535`.
- Train/val data at training time: 40 train episodes / 336 sequences, 10 val episodes / 86 sequences.

PM/DM full train+val evaluation:
- Output: `docs/v5/pm_eval/exp35_leftfamily_trainval_eval_t0.json`
- Split: train+val, left-family only.
- Total: 422 sequences, 0 errors.
- PM: 56.16% (237/422).
- Prediction distribution: FORWARD 422/422, every other class 0.
- GT distribution: FORWARD 237, LEFT 45, FWD+L 30, FWD+R 90, TURN_R 20.
- Non-FORWARD GT frames: 185/422, all predicted FORWARD.

Interpretation:
- This directly confirms the professor's sanity concern.
- The left-family minimal run still collapses to FORWARD even on the training split.
- The logits are also nearly constant across frames, so this should be treated as a pipeline/action-supervision/action-head issue until disproven, not as a reason to start broad full-dataset training.

Non-diagnostic check:
- `eval_t=-1` gives PM 100%, but all 422 GT labels at `t=-1` are FORWARD, so it cannot validate left/right behavior.

Transcript basis:
- Lines 102-119 and 185-194.

### TODO 4: Last-4 decoder LoRA

Status: implemented and verified for Exp35.

Important correction:
- The first attempted run, Exp33, inherited `lora_target_modules` and therefore did not actually restrict LoRA to last-4 decoder layers.
- Exp33 was stopped early.

Fixed run:
- Exp35 explicitly sets `lora_target_modules: null`.
- Log confirms: `Restricting LoRA to last 4 decoder layers (24 exact linear modules).`
- Trainable parameter count: 42.5M.
- Trainable names are limited to text decoder layers 20-23 plus action head/action token.

Transcript basis:
- Lines 73-95 and 126-131.

### TODO 6: Action head / LSTM / supervision check

Status: issue found; fix applied; verification run started.

Finding:
- Exp35 used `act_head.fwd_pred_next_n=1`, while the dataset labels were built with `fwd_pred_next_n=3`.
- The classification loss aligned sequence length `L`, but did not align the chunk axis `n`.
- When logits had `n=1` and labels had `n=3`, the previous fallback flattened both tensors and trimmed by total length. That can mix target time/chunk positions instead of comparing `logits[:, t, 0]` with `labels[:, t, 0]`.

Patch:
- `robovlm_nav/models/policy_head/nav_policy_impl.py` now aligns the chunk axis before flattening.
- `robovlm_nav/serve/inference_server.py` now uses the V5 dataset 8-class decode mapping for `num_classes=8`.
- New config: `configs/mobile_vla_v5_exp36_pure_hf_last4_lora_left50_lossfix_5ep.json`
- Exp36 keeps the Exp35 setup, but sets train/val dataset `fwd_pred_next_n=1` to match the inherited action head.

Started run:
- Command in `tmux v5train`: `python3 robovlm_nav/train.py configs/mobile_vla_v5_exp36_pure_hf_last4_lora_left50_lossfix_5ep.json`
- Log: `runs/v5_nav/kosmos/mobile_vla_v5_exp36/2026-04-25/v5-exp36-pure-hf-last4-lora-left50-lossfix-5ep/train.log`
- Startup verified: last-4 LoRA still active, trainable params 42.5M, train/val left-family datasets loaded with `fwd_pred_next_n=1`.

Transcript basis:
- Lines 169-176: professor asks to inspect the action head/LSTM side if the minimal sanity check fails.

## Current Conclusion

We are following the professor's elimination order, and the left-family sanity check now fails clearly.

What is done:
- Last-4 LoRA left-family training completed correctly.
- Object-recognition proof tooling exists.
- Full train+val PM/DM action audit was run on the completed checkpoint.
- The audit shows 422/422 predictions are FORWARD despite 185 non-FORWARD GT labels.
- A concrete action-supervision mismatch was found after the failed sanity check.
- Exp36 loss-fix verification training has been started.

What is still missing:
- Human-reviewed object recognition proof for initial frames.
- Raw inference rows that join grounding/bbox output with the action output for the same initial frames.
- Exp36 completion and the same full train+val PM/DM audit.
- Runtime inference-server 8-class decode mapping has been corrected in code, but still needs a deployment-side smoke test before robot driving.

## Next Step

Do not start broad full-dataset training yet.

Next concrete step should be TODO 6, while closing the remaining TODO 1/2 evidence gap:
- monitor Exp36 to completion and rerun the full train+val PM/DM audit;
- if Exp36 still collapses, run a tiny overfit check where non-FORWARD logits must move;
- inspect/fix runtime 8-class decode mapping before any robot deployment test;
- join grounding output with action logits on the initial-frame proof set.
