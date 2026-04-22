# Current Collection Eval Metrics (2026-04-22)

## Scope

- Branch baseline: `inference-integration`
- Collection tooling inspected:
  - [`scripts/gradio_data_collector.py`](../../scripts/gradio_data_collector.py)
  - [`ROS_action/run_vla_collector.sh`](../../ROS_action/run_vla_collector.sh)
- Related historical notes:
  - [`docs/V5_DATA_COLLECTION_REPORT.md`](../../docs/V5_DATA_COLLECTION_REPORT.md)
  - [`docs/weekly_report_20260403_20260410.md`](../../docs/weekly_report_20260403_20260410.md)
  - [`docs/v5/V5_DATASET_SIGNAL_DESIGN.md`](./V5_DATASET_SIGNAL_DESIGN.md)

This note answers one practical question:

> Given the **actual current collection state**, what evaluation metric is the most appropriate for short-term model selection?

## 1. Collector History Snapshot

The relevant recent collector-side commits are:

1. `78dabd6a`  
   `feat: V5 데이터 수집 최적화 및 Visual Grounding 검증 기능 강화`
   - added `scripts/gradio_data_collector.py`
   - updated `ROS_action/run_vla_collector.sh`
   - added `docs/V5_DATA_COLLECTION_REPORT.md`
   - at that point, the report recorded **54 episodes**

2. `b624de8d`  
   `feat(collector): V5 데이터 수집 최적화 및 UI 싱크로 수정 (rotation 0.2 calibration)`
   - small collector calibration update
   - no new metric protocol was introduced

The weekly report later records that:

- `core_replay_db.json` was expanded
- V5 collection reached **150 episodes**
- professor-server upload was completed

So the collection system matured in two stages:

- early stage: dashboard/collector stabilization at `54ep`
- later stage: core V5 set completion at `150ep`

### 1.1 What `monavla-driving` branch adds

Inspection of the `monavla-driving` branch shows that it preserves an earlier,
collection-heavy line of work centered on the ROS collector:

- [`ROS_action/src/mobile_vla_package/mobile_vla_package/mobile_vla_data_collector.py`](../../ROS_action/src/mobile_vla_package/mobile_vla_package/mobile_vla_data_collector.py)
- [`ROS_action/run_vla_collector.sh`](../../ROS_action/run_vla_collector.sh)

The important branch-only history is:

- `5b5a759f`: add V3 target-reaching-only mode
- `2061b03f`: isolate V3 data into `mobile_vla_dataset_v3`
- `9a61a8f1`: ensure progress matches filesystem on boot
- `7dedc5da`: reduce V3 distance levels to `1m / 2m`
- `b62ac460`: V3 progress update around `96/160`
- `1085d896`: sync latest rebranding and report `151` V3 episodes
- `85529964`: mark V5 `150` collection completion and professor-server upload

This branch matters because it shows the **intended collection philosophy**:

- V3 branch:
  - scenario diversity
  - time-of-day spread
  - target-reaching / recovery-style collection
- V5 branch:
  - fixed 9-path core execution set

In other words:

- `monavla-driving` documents a stronger ambition toward robustness-oriented data collection
- but the currently available V5 set used by the mainline evaluation is still the narrower core route dataset

## 2. Actual Current Dataset State

Filesystem inspection of `ROS_action/mobile_vla_dataset_v5` shows:

- total episodes: `150`
- total frames: `2626`
- episode length: min `14`, max `19`, mean `17.51`
- path counts:
  - `center_straight`: `20`
  - `left_straight`: `20`
  - `right_straight`: `20`
  - `center_left`: `15`
  - `center_right`: `15`
  - `left_left`: `15`
  - `left_right`: `15`
  - `right_left`: `15`
  - `right_right`: `15`

Most important reality checks:

1. The current set is **fully `core__fixed_center` only**.
   - No `far`, `offset`, `no-obstacle`, or other diversity variants are currently present in the H5 filenames.

2. The current set is **effectively single-instruction**.
   - Observed instruction count: `1`
   - Current text:
     - `<grounding>Navigate straight forward to the gray basket. 바구니를 향해 직진해.`

3. Progress-tracking JSON files are **stale**.
   - `scenario_progress.json` and `time_period_stats.json` still show `0` completed.
   - They should **not** be used as the source of truth for current collection status.
   - The source of truth should be:
     - H5 file count
     - H5 filename distribution
     - dataset-level frame statistics

4. Dataset semantics are still those documented in [`docs/v5/V5_DATASET_SIGNAL_DESIGN.md`](./V5_DATASET_SIGNAL_DESIGN.md).
   - This is an **approach trajectory** dataset.
   - It is not a robust stop-supervised or text-diverse benchmark.

### 2.1 Cross-check against `monavla-driving`

The branch history gives two different "current state" signals:

1. **V3 collector state**
   - `scenario_progress.json` on `monavla-driving` records `151 / 160`
   - scenario spread:
     - `v3_left: 30`
     - `v3_center: 50`
     - `v3_right: 31`
     - `v3_recovery: 40`
   - time-period spread is also explicitly tracked there

2. **V5 collector state**
   - the later `85529964` commit declares V5 `150` episodes complete
   - but the bundled `mobile_vla_dataset_v5/scenario_progress.json` still shows `0`
   - so for V5, the JSON tracker was not the maintained source of truth

Interpretation:

- `monavla-driving` confirms that the team intended to move toward more diverse and robustness-aware collection
- however, the **actual V5 artifact in use for the current policy work is still the fixed core route set**
- therefore the metric should follow the **artifact actually being evaluated**, not the broader collection intention

## 3. What This Dataset Is Good For

The current V5 collection is best treated as a:

- **controlled 9-path route-selection dataset**
- **short-horizon approach-control dataset**
- **closed-loop navigation gate set**

It is **not yet** a good benchmark for:

- language generalization
- robustness to collection variants
- stop / arrival prediction quality
- environment-shift robustness

Reason:

- all episodes are from the same `core__fixed_center` regime
- text variation is absent in the actual saved H5s
- `STOP` supervision is effectively absent
- frame-level label distribution is strongly forward-biased

If the active dataset were the V3 target-reaching set from `monavla-driving`,
the answer would shift somewhat toward:

- scenario-balanced success
- time-period robustness
- recovery-case success

But for the currently used V5 artifact, that would be premature.

## 4. Metric Choice: What Should Be Primary

### Recommended primary metric

**Episode-level closed-loop success rate**, reported:

- overall
- per `path_type`
- optionally on a path-balanced held-out split

Why this should be primary:

- the dataset is fundamentally about route execution, not text diversity
- frame metrics can over-credit `FORWARD`
- this project already observed repeated PM/closed-loop mismatch
- the current collection regime is narrow enough that fast closed-loop comparison is practical

### Recommended secondary metric

**Short-prefix route commitment metric** on curved paths.

Concrete options:

- `prefix@5 success`
- `prefix@5` / `prefix@10` FPE
- first-turn correctness on non-straight path families only

Why:

- in this dataset, the main early failure is often **wrong initial route commitment**
- short-prefix metrics reveal this faster than full rollout
- they are cheaper and more stable than full long-horizon rollout

### Recommended fast sanity metric

**Path-balanced frame accuracy / PM**, but only as a screening metric.

Use it like this:

- report per-path frame accuracy
- report macro-average over path families
- do **not** use raw aggregate PM over all frames as the main score

Why:

- aggregate PM is heavily distorted by `FORWARD` dominance
- `center_straight` can make a weak policy look stronger than it is

## 5. Metric Choice: What Should Not Be Primary

The following are poor primary metrics for the current collection state:

1. **Text understanding / instruction swap accuracy**
   - current H5 set has effectively one instruction template
   - useful for root-cause analysis, not for short-term model selection

2. **Arrival / STOP metrics**
   - the dataset does not cleanly supervise stopping
   - using stop-centric metrics now would create misleading conclusions

3. **Raw overall PM on the full 150 episodes**
   - too easy to game with `FORWARD`-heavy behavior
   - not reliable as the top-line score

4. **Robustness / domain-shift benchmark scores**
   - current collection has not yet materialized the intended variant regimes
   - robustness claims should wait until actual variant H5s exist

## 6. Best Short-Term Evaluation Stack

For the next 1-2 weeks, the most appropriate evaluation stack is:

1. **Primary gate**
   - closed-loop success rate on held-out V5 episodes

2. **Secondary gate**
   - prefix success / prefix FPE on curved paths

3. **Fast screening**
   - path-balanced frame accuracy / PM

4. **Diagnostics only**
   - FPE
   - TLD
   - transition attractor analysis
   - confusion matrix

This matches the current dataset much better than a benchmark-style VLA scorecard.

## 7. Practical Recommendation

If we must choose **one** metric that is both:

- suitable for the current collected data
- useful in the short term
- aligned with real deployment quality

then the answer is:

> **Path-wise closed-loop success rate** should be the main metric.

If we must choose **one cheap supporting metric** for quick iteration:

> **Prefix@5 success on non-straight path types** is the best short-term companion metric.

If we must choose **one fast offline screening metric** before rollout:

> **Macro-averaged per-path frame accuracy** is the least misleading PM-style metric.

## 8. Bottom Line

Current V5 collection is no longer the old `54ep` partial set.  
It is now a **completed 150-episode core-only route dataset**.

That means:

- evaluate it as a **controlled navigation execution dataset**
- not as a full VLA language/robustness benchmark
- keep `closed-loop success` as the main score
- use `prefix route-commitment` as the short-term accelerator
- keep `PM/frame_acc` only as a subordinate screening metric

## 9. Companion Script

For the current short-term selection stack, use:

```bash
python3 scripts/analysis/summarize_v5_shortterm_eval.py \
  --models exp11,exp17,exp18,exp21
```

Outputs:

- [`docs/v5/shortterm_eval/summary.json`](./shortterm_eval/summary.json)
- [`docs/v5/shortterm_eval/index.html`](./shortterm_eval/index.html)
