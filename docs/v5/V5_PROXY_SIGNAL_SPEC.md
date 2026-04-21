# V5 Proxy Signal Spec v0

**Date:** 2026-04-21  
**Dataset anchor:** `ROS_action/mobile_vla_dataset_v5`  
**Companion stats:** [`v5_proxy_signal_stats.json`](./v5_proxy_signal_stats.json)  
**Validation file:** [`v5_goal_near_eval.json`](./v5_goal_near_eval.json)  
**Timing file:** [`v5_goal_near_timing.json`](./v5_goal_near_timing.json)  
**Prerequisite context:** [`V5_DATASET_SIGNAL_DESIGN.md`](./V5_DATASET_SIGNAL_DESIGN.md)

## 1. Goal

Define a **first-pass, non-leaky proxy signal spec** for "goal-near / stop-near" state estimation using only the current V5 dataset and its existing grounded bbox cache.

This document is intentionally conservative:

- raw action supervision is taken from the full 150-episode V5 H5 set
- geometry thresholds are taken from the existing 45-episode grounded bbox cache
- therefore this is a **spec v0**, not a final dataset-wide stop rule

## 2. Hard Constraints from the Current Dataset

From [`v5_proxy_signal_stats.json`](./v5_proxy_signal_stats.json):

- full raw V5 episodes: `150`
- full raw V5 frames: `2626`
- frame count summary:
  - mean: `17.51`
  - min: `14`
  - max: `19`
- raw action counts under the current 8-class discretization:
  - `STOP`: `0`
  - `FORWARD`: `1955`
  - `LEFT`: `60`
  - `RIGHT`: `46`
  - `FWD+L`: `255`
  - `FWD+R`: `270`
  - `ROT_L`: `20`
  - `ROT_R`: `20`

### Design implication

The full V5 dataset does **not** provide direct stop supervision.

So the immediate design problem is:

> not "predict STOP from labels", but "estimate when the agent is near enough to stop using proxy signals"

## 3. Geometry Scope Used for Proxy Design

Current grounded subset:

- source: [`bbox_nav_step1/bbox_dataset.json`](./bbox_nav_step1/bbox_dataset.json)
- grounded episodes: `45`
- grounded frames: `794`

This subset is good enough to derive an initial geometry spec, but it is **not** the same thing as full-150 coverage.

All threshold values below should therefore be treated as:

- usable for controlled experiments
- not yet final for full public claims

## 4. Proxy Features to Keep

The following signals are safe, useful, and derivable from current V5 assets.

### 4.1 Primary geometry signals

1. `area`
- meaning: coarse target proximity
- rationale: larger grounded target usually means closer target

2. `center_error_x = abs(cx - 0.5)`
- meaning: horizontal centering quality
- rationale: late-stage frames show much smaller x error than early frames

3. `center_error_y_to_075 = abs(cy - 0.75)`
- meaning: vertical proximity to a stop-near band
- rationale: current data suggests late frames are visually lower in the image, but this is weaker than x-centering

4. `has_bbox`
- meaning: visual target availability
- rationale: useful as a gating signal, but not sufficient on its own

### 4.2 Temporal stabilization signals

5. `abs_delta_area`
- meaning: whether approach is still changing rapidly or starting to plateau

6. `abs_delta_cx`
- meaning: horizontal alignment stability

7. `recent_bbox_consistency`
- meaning: how consistently bbox is observed in the recent tail window

## 5. Signals to Avoid for Now

These are either leaky or too deployment-specific to use as primary learned inputs.

- exact frame index
- normalized episode progress
- future bbox-derived values
- GT action-derived language hints

These may be used for analysis, but not as deployable online signals.

## 6. Empirical Pattern Summary

Using the grounded 45-episode subset:

```text
early area                p25=0.043945  p50=0.050000  p75=0.052734
late3 area                p25=0.309570  p50=0.726562  p75=0.756836
late5 area                p25=0.272461  p50=0.726562  p75=0.756836

early center_error_x      p25=0.000000  p50=0.000000  p75=0.156250
late3 center_error_x      p25=0.000000  p50=0.000000  p75=0.039062
late5 center_error_x      p25=0.000000  p50=0.000000  p75=0.031250

early center_error_y075   p25=0.171875  p50=0.250000  p75=0.250000
late3 center_error_y075   p25=0.250000  p50=0.328125  p75=0.343750
late5 center_error_y075   p25=0.250000  p50=0.328125  p75=0.359375

late3 abs_delta_area      p25=0.030273  p50=0.075195  p75=0.475098
late5 abs_delta_area      p25=0.030273  p50=0.054688  p75=0.498047

late3 abs_delta_cx        p25=0.000000  p50=0.000000  p75=0.093750
late5 abs_delta_cx        p25=0.000000  p50=0.000000  p75=0.062500

late5 bbox consistency    p25=0.250000  p50=0.500000  p75=0.750000
```

### Interpretation

- `area` separates early vs late frames strongly
- `center_error_x` also separates late frames clearly
- `center_error_y_to_075` is less clean than expected and should be treated as a soft cue, not a hard stop rule
- temporal stability is meaningful, but current tail statistics are still broad

## 7. Threshold Candidates v0

These are the current quantile-based candidate thresholds from the grounded subset.

```text
goal_near_area_min__late3_p25              = 0.309570
goal_near_area_min__late5_p25              = 0.272461
goal_near_center_error_x_max__late3_p75    = 0.039062
goal_near_center_error_x_max__late5_p75    = 0.031250
goal_near_center_error_y_to_075_max__late3_p75 = 0.343750
goal_near_center_error_y_to_075_max__late5_p75 = 0.359375
plateau_abs_delta_area_max__late3_p75      = 0.475098
plateau_abs_delta_area_max__late5_p75      = 0.498047
stability_abs_delta_cx_max__late3_p75      = 0.093750
stability_abs_delta_cx_max__late5_p75      = 0.062500
recent_bbox_consistency_min__late5_p25     = 0.250000
```

## 8. Recommended Signal Pack v0

For the first experimental iteration, use:

```text
required:
- area
- center_error_x

recommended:
- abs_delta_cx
- recent_bbox_consistency

optional / soft:
- center_error_y_to_075
- abs_delta_area
```

### Why this pack

- `area` gives the strongest proximity cue
- `center_error_x` gives the cleanest alignment cue
- `abs_delta_cx` and `recent_bbox_consistency` help distinguish stable near-goal states from transient flashes
- `center_error_y_to_075` should not be over-weighted yet because the current evidence is noisier

## 9. First Operational Rule v0

If a simple handcrafted goal-near detector is needed before model changes, start with:

```text
goal_near_v0 =
    has_bbox
    and area >= 0.27
    and center_error_x <= 0.03125
```

Optional stricter version:

```text
goal_near_v0_strict =
    has_bbox
    and area >= 0.31
    and center_error_x <= 0.039062
    and abs_delta_cx <= 0.0625
```

These are not "stop rules" yet. They are only:

- a first proxy for "visually near goal"
- a candidate auxiliary target
- a candidate controller gate

## 10. Validation on the Current 45-Episode Grounded Cache

From [`v5_goal_near_eval.json`](./v5_goal_near_eval.json):

```text
goal_near_v0
- early positive rate        = 20.39%
- late5 frame hit rate       = 68.89%
- late5 episode-any rate     = 93.33%
- late5 episode-all rate     = 22.22%

goal_near_v0_strict
- early positive rate        = 14.90%
- late5 frame hit rate       = 59.56%
- late5 episode-any rate     = 88.89%
- late5 episode-all rate     = 17.78%
```

### Path-wise risk pattern

The current main false-positive paths are:

- `right_left`
- `right_right`
- then `center_left`

Interpretation:

- `area + center_error_x` is enough to catch many late-stage frames
- but it can still activate too early on some right-biased correction trajectories
- the stricter rule reduces early positives, but noticeably weakens late coverage

### Current recommendation

For now, keep `goal_near_v0` as the main proxy definition, but do **not** treat it as a final stop trigger.

Use it first as:

- an analysis label
- an auxiliary target
- or a soft controller gate

### Timing analysis

From [`v5_goal_near_timing.json`](./v5_goal_near_timing.json), the key issue is not just whether the rule fires, but **how early it begins to fire**.

Most problematic path families:

- `right_left`: mean first-positive norm `0.0118`
- `center_left`: mean first-positive norm `0.0471`
- `right_right`: mean first-positive norm `0.1267`

More stable late-trigger paths:

- `left_straight`: mean first-positive norm `0.5176`
- `left_right`: mean first-positive norm `0.4444`
- `center_straight`: mean first-positive norm `0.3846`

Interpretation:

- the current rule is too eager on several right-biased or center-left correction paths
- the same rule behaves much more like a true late-phase signal on some straight or left-biased paths
- this supports using the proxy as a **soft state estimate**, not as a global hard stop condition

## 11. Geometry Expansion Status

Current geometry assets in the repo are not yet sufficient to claim full-150 grounded coverage.

What exists:

- `docs/v5/bbox_nav_step1/bbox_dataset.json`: `45` grounded episodes used in current bbox experiments
- `ROS_action/v5_data_bak/v5_grounding.json`: `50` top-level episode entries, but it is an earlier grounding dump and not directly basket-clean
- `ROS_action/v5_data_bak/v5_basket_analysis.json`: `11` top-level entries, partial analysis output only

What this means:

- we can validate proxy ideas on the current 45-episode grounded cache
- but we cannot yet say the thresholds are stable for the full 150-episode dataset

There is an extraction path for full coverage:

- [`scripts/test_v5_bbox_nav_step1.py`](../../scripts/test_v5_bbox_nav_step1.py) supports `--full`
- this would produce `bbox_dataset_full.json`

But that path internally re-runs Kosmos-2 generation, so it should be treated as a separate GPU job rather than a lightweight analysis step.

## 12. Next Required Analysis

Before promoting this spec beyond v0, do the following:

1. extend geometry extraction beyond the current 45 grounded episodes if possible
2. inspect false positives on straight-path episodes
3. compare `goal_near_v0` frequency against late-episode frames path-by-path
4. measure whether this proxy improves closed-loop stopping or just creates premature stopping

## 13. Bottom Line

The current V5 dataset does not contain direct stop supervision.

The strongest immediately usable proxy signals are:

- `area`
- `center_error_x`
- then `abs_delta_cx` / `recent_bbox_consistency` as stabilizers

So the next engineering step should be:

> use V5 to model **goal-near state**, not to pretend that direct STOP labels already exist
