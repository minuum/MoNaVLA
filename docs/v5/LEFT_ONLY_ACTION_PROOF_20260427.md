# Left-Only Action Proof (2026-04-27)

## Goal

Answer the professor's second question directly:

- If we train only on left-start family data (`50 episodes`), can the model emit left-family actions at all?
- This isolates whether the current `always straight` failure is caused by mixed-path confusion or a deeper action-learning failure.

## Monday Smoke Matrix

| Exp | Setting | Dataset | Epochs | Purpose |
| --- | --- | --- | --- | --- |
| `exp32` | pure-HF head-only | `left_straight`, `left_left`, `left_right` | 5 | check whether the action head alone can leave straight-collapse |
| `exp33` | pure-HF + last4 train + last4 LoRA | same 50 episodes | 5 | check the professor's proposed last-4 LoRA recipe directly |

## Configs

- `configs/mobile_vla_v5_exp32_pure_hf_head_only_left50_5ep.json`
- `configs/mobile_vla_v5_exp33_pure_hf_last4_lora_left50_5ep.json`

## Evaluation Focus

- PM / DM
- class confusion
- first-5-step left-family action ratio
- whether `LEFT`, `FWD+L`, `TURN_L` become non-zero

## Current Status (2026-04-24)

- exact `include_path_families` dataset filter implemented
- left-start family definition fixed to:
  - `left_straight`
  - `left_left`
  - `left_right`
- experiment runs: not started in this commit

## Talk Track

- If `exp32` already works: "action head 자체는 left 계열을 낼 수 있고, backbone adaptation이 필수는 아닙니다."
- If only `exp33` works: "교수님 말씀대로 마지막 4개 decoder adaptation이 실제로 필요했습니다."
- If both fail: "문제는 mixed-path confusion이 아니라 action supervision 또는 label setup 쪽일 가능성이 큽니다."
