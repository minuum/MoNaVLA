# V5 Dataset Reframing and Signal Design

**Date:** 2026-04-21  
**Scope:** `ROS_action/mobile_vla_dataset_v5` only  
**Goal:** Re-examine what the current V5 dataset actually contains, how it is currently consumed, and what additional signals can be derived from it without collecting new data.

Companion artifacts:

- [`v5_proxy_signal_stats.json`](./v5_proxy_signal_stats.json)
- [`V5_PROXY_SIGNAL_SPEC.md`](./V5_PROXY_SIGNAL_SPEC.md)

## 1. Executive Summary

The current V5 dataset is best understood as an **approach trajectory dataset**, not a full goal-completion dataset.

What it clearly contains:

- Target-directed motion trajectories across 9 fixed path types
- Strong forward-biased navigation behavior with diagonal corrections
- High-quality geometric target signals derivable from grounding (`cx`, `cy`, `area`, `has_bbox`)

What it does **not** clearly contain:

- Explicit `STOP` supervision
- A direct `arrival` or `done` label
- Reliable text-conditioned action supervision

This means the next step should not be "make the model magically learn arrival from raw action labels."  
The correct next step is to define **goal-near / stop-near proxy signals** from the existing V5 data, then decide how to use them in a model or controller.

## 2. Raw Dataset Structure

Sample H5 file structure:

- `actions`: shape `(T, 3)`
- `language_instruction`: shape `(1,)`
- `observations/images`: shape `(T, H, W, C)`

Observed dataset-level statistics:

- Total episodes: `150`
- Total frames: `2626`
- Mean episode length: `17.51`
- Min episode length: `14`
- Max episode length: `19`

Path-type episode counts:

- `center_straight`: `20`
- `left_straight`: `20`
- `right_straight`: `20`
- `center_left`: `15`
- `center_right`: `15`
- `left_left`: `15`
- `left_right`: `15`
- `right_left`: `15`
- `right_right`: `15`

Interpretation:

- V5 is balanced at the **episode family** level, but not at the **frame-level action** level.
- The extra 5 episodes on each `*_straight` family materially affect action imbalance.

## 3. Current Action Label Reality

Using the current 8-class discretization in [`robovlm_nav/datasets/nav_h5_dataset_impl.py`](../../robovlm_nav/datasets/nav_h5_dataset_impl.py), the frame-level distribution over all `2626` frames is:

- `STOP`: `0`
- `FORWARD`: `1955` (`74.4%`)
- `LEFT`: `60` (`2.3%`)
- `RIGHT`: `46` (`1.8%`)
- `FWD+L`: `255` (`9.7%`)
- `FWD+R`: `270` (`10.3%`)
- `ROT_L`: `20` (`0.8%`)
- `ROT_R`: `20` (`0.8%`)

### Key finding

**There are effectively no STOP labels in V5.**

This is the most important fact for future design:

- The current dataset does not directly teach the model when to stop.
- Therefore, any downstream stop behavior must come from:
  - geometric proxies,
  - controller logic,
  - auxiliary signals,
  - or future data collection.

## 4. Path-Type Behavioral Meaning

Frame-level top actions by path family:

- `center_straight`: `FORWARD` only
- `left_straight`: mostly `FORWARD`, small `ROT_R`
- `right_straight`: mostly `FORWARD`, small `ROT_L`
- `center_left`: `FORWARD` + `FWD+L` + `FWD+R` + small `LEFT`
- `center_right`: `FORWARD` + `FWD+R` + `FWD+L` + small `RIGHT`
- `left_left`: mostly `FORWARD`, then `LEFT` / `FWD+L`
- `left_right`: mostly `FORWARD`, then `FWD+R`
- `right_left`: mostly `FORWARD`, then `FWD+L`
- `right_right`: mostly `FORWARD`, then `RIGHT` / `FWD+R`

Interpretation:

- The dataset mostly supervises **approach and correction**, not completion.
- Even curved paths are still dominated by `FORWARD`.
- This makes plain end-to-end policy learning especially vulnerable to forward bias.

## 5. Current Consumption Pipeline

### 5.1 End-to-end VLM path

Current dataset usage:

- H5 episodes are cut into fixed-length sliding windows
- Each sample uses `window_size` frames
- The model predicts next action labels / chunks

Practical consequence:

- Episode length is variable
- Training sample length is fixed
- The task is framed as **local action prediction**, not explicit success prediction

### 5.2 Decomposition path

The current best-performing practical track is the bbox-based decomposition pipeline.

Derived dataset file:

- [`docs/v5/bbox_nav_step1/bbox_dataset.json`](./bbox_nav_step1/bbox_dataset.json)

Observed statistics from the current extracted bbox dataset:

- Episodes: `45`
- Frames: `794`
- Path families: `9`
- `has_bbox` ratio: `0.9937`

Per-frame derived fields:

- `cx`
- `cy`
- `area`
- `has_bbox`
- `gt_class`

Interpretation:

- V5 already contains a highly usable geometric intermediate representation.
- This is a major reason the decomposition track works better than plain end-to-end learning.

## 6. What the Dataset Actually Supervises

The current V5 dataset strongly supervises:

- approach direction
- lateral correction
- diagonal approach behavior
- short-horizon geometric alignment

The current V5 dataset weakly or not at all supervises:

- explicit goal completion
- explicit arrival state
- explicit stopping timing
- robust text-conditioned behavior

This is the central reframing:

> V5 is a motion-to-target dataset, not a motion-and-completion dataset.

## 7. Why STOP Must Be Reframed as a Proxy Problem

Since `STOP = 0` never appears in the frame-level action labels:

- the model cannot reliably learn stop timing from direct supervision
- a future stop-capable policy must rely on **derived state signals**

The correct question is not:

> "How do we make the model learn STOP from current labels?"

The correct question is:

> "What measurable cues inside V5 correlate with being close enough to stop?"

## 8. Candidate Signals Derivable from V5

All signals below can be derived from the current dataset without collecting new episodes.

### 8.1 Geometric signals

1. `bbox_center_error_x`
- Definition: `abs(cx - 0.5)`
- Meaning: horizontal alignment error
- Value: strong proxy for "is target centered?"

2. `bbox_center_error_y`
- Definition: distance from target vertical center to desired stopping band
- Meaning: vertical alignment / proximity proxy
- Value: useful because the prompt historically referenced "centered" and "lower half"

3. `bbox_area`
- Definition: normalized bbox area
- Meaning: coarse distance-to-target proxy
- Value: larger area usually means closer target

4. `has_bbox`
- Definition: binary grounding validity
- Meaning: whether the target is visually trackable
- Value: useful gating signal, but not sufficient by itself

5. `lower_half_occupancy`
- Definition: how much of the bbox lies in the lower image region
- Meaning: proxy for near-target completion state
- Value: explicitly aligned with prior prompt phrasing

### 8.2 Temporal-change signals

6. `delta_area`
- Definition: change in bbox area over recent frames
- Meaning: approaching vs plateauing
- Value: separates "still moving toward target" from "already close"

7. `delta_cx`
- Definition: recent change in horizontal center
- Meaning: alignment improvement / oscillation
- Value: detects whether the robot is still correcting

8. `delta_cy`
- Definition: recent change in vertical center
- Meaning: upward/downward drift in the frame
- Value: useful for phase recognition

9. `bbox_velocity`
- Definition: recent magnitude of bbox center movement
- Meaning: visual stabilization proxy
- Value: can help distinguish "close and stable" from "close but still moving"

10. `recent_bbox_consistency`
- Definition: fraction of recent frames with valid bbox and low geometric jitter
- Meaning: target stability
- Value: strong candidate for stop-near confidence

### 8.3 Episode-context signals

11. `path_type`
- Source: filename / known dataset family
- Meaning: coarse route prior
- Value: useful for analysis and offline stratification
- Warning: risky as a deploy-time feature unless available online

12. `trajectory_phase_proxy`
- Definition: derived from geometry progression, not raw frame index
- Meaning: early / middle / late approach phase
- Value: safer than using absolute frame number

## 9. Recommended First Signal Pack

If we want a compact first pass, the most defensible signal pack is:

- `bbox_center_error_x`
- `bbox_center_error_y`
- `bbox_area`
- `delta_area`
- `delta_cx`
- `has_bbox`
- `recent_bbox_consistency`

Why this pack:

- all signals are derivable from existing V5 assets
- they do not depend on future leakage
- they directly target the missing stop / arrival information
- they are compatible with the current decomposition track

## 10. Signals That Should Not Be Used as Primary Learning Inputs

### 10.1 GT-action-derived instruction signals

Examples:

- action-aware instructions built from the target action
- synthetic instruction variants directly tied to the label

Why not:

- this introduces label leakage
- it is not a deployable input source
- it can inflate PM without improving actual control

### 10.2 Exact frame index / end-of-episode position

Why not:

- the model may learn "late in the episode = stop-like behavior"
- this does not transfer outside the collection pattern

### 10.3 Future-derived geometry

Examples:

- next-frame area
- future bbox center
- completion label built from future trajectory unless strictly marked auxiliary/offline analysis

Why not:

- this is direct target leakage

## 11. Immediate Analysis Tasks Before Model Design

Before touching model architecture, the dataset analysis should be completed in this order:

1. Summarize full-V5 geometry trajectories
- path-type-wise mean `cx`, `cy`, `area`
- early / middle / late frame trends

2. Quantify stop-near proxy ranges
- last-3-frame / last-5-frame distributions of `area`, `center_error`, `bbox stability`

3. Define threshold candidates
- e.g. area above threshold
- center error below threshold
- recent change below threshold

4. Measure proxy quality
- how cleanly these signals separate "late stable approach" from "still approaching"

5. Decide how the signal will be used
- analysis-only
- rule layer
- auxiliary target
- gating feature
- separate stop head

## 12. Final Reframing

The present V5 dataset should be described as follows:

> The dataset is well-suited for learning **target-directed approach behavior** and geometric correction, but it does not directly supervise **goal completion or stop timing**. Therefore, stop-capable behavior must be built on top of derived geometric proximity signals rather than expected to emerge from the raw action labels alone.

That reframing is the correct foundation for all next experiments.
