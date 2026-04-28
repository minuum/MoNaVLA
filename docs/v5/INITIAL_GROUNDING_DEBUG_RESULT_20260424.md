# Initial Grounding Debug Result (2026-04-24)

## Scope

- input slice:
  - `docs/v5/bbox_truth_initial18.json`
- raw model:
  - pure HF `kosmos-2-patch14-224`
- generated artifacts:
  - `docs/v5/grounding_initial18_debug/index.html`
  - `docs/v5/grounding_initial18_debug/summary.json`
  - `docs/v5/grounding_initial18_debug/overlays/*.png`

## Provisional Result

- processed frames: `18`
- model produced a bbox-like output on: `18 / 18`
- scaffold seed bbox existed on: `6 / 18`
- provisional coarse agreement vs seed: `1.0000`
- provisional detection agreement vs seed: `0.3333`

## What This Means

- raw Kosmos-2 is not "silent"; it always emits some grounding-like answer.
- but early-frame basket detection is not trustworthy yet.
- the current failure pattern is not "no output", but "wrong object with plausible spatial language".

## Frequent Failure Pattern

- most common predicted entities include:
  - `caption:center`
  - `the gray trash can`
  - `the white wall`
  - `the chair`
- this means the model often preserves coarse direction words like `left / center / right`, but binds them to the wrong object.

## Current Interpretation For The Meeting

- stronger statement:
  - "VLM이 완전히 blind인 것은 아닙니다. 위치 표현은 내지만, 초기 프레임에서는 basket-specific grounding이 불안정합니다."
- cautious statement:
  - "현재는 perception이 '살아 있다'고 단정하기보다, coarse spatial response는 있으나 target binding이 약하다고 보는 편이 맞습니다."

## Immediate Next Use

- if we want a strict proof, the next step is still human-reviewed GT fill for the same 18 frames.
- until then, this report should be used as a qualitative / provisional perception check, not as final perception evidence.
