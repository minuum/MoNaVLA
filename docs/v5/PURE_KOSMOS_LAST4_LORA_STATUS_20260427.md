# Pure Kosmos Last-4 LoRA Status (2026-04-27)

## What Changed

- Added `train_setup.lora_decoder_layers`
  - meaning: inject LoRA only into the last `N` text decoder blocks
- Reused `train_setup.train_decoder_layers`
  - meaning: unfreeze original decoder weights only for the last `N` blocks
- Added dataset key `include_path_families`
  - meaning: include exact path families without unsafe substring matching

## New Monday Configs

| Exp | Backbone | Trainable Scope | Data Scope | Epochs |
| --- | --- | --- | --- | --- |
| `exp32` | pure HF Kosmos-2 | head only | left-start 50 episodes | 5 |
| `exp33` | pure HF Kosmos-2 | last 4 decoder blocks + LoRA on same slice | left-start 50 episodes | 5 |
| `exp34` | pure HF Kosmos-2 | last 4 decoder blocks + LoRA on same slice | full 150 episodes | 5 |

## Expected Interpretation

- `exp32 -> exp33` tests whether the professor's last-4 adaptation recipe is necessary.
- `exp33 -> exp34` tests whether a left-only gain survives the full-path regime.

## Current Status (2026-04-24)

- code path for exact last-4 LoRA targeting: implemented
- code path for exact left-start family filtering: implemented
- configs for `exp32~34`: added
- training/evaluation outputs: pending

## Immediate Commands

```bash
python3 robovlm_nav/train.py configs/mobile_vla_v5_exp32_pure_hf_head_only_left50_5ep.json
python3 robovlm_nav/train.py configs/mobile_vla_v5_exp33_pure_hf_last4_lora_left50_5ep.json
python3 robovlm_nav/train.py configs/mobile_vla_v5_exp34_pure_hf_last4_lora_allpath_5ep.json
```
