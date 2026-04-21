# Current Research Plan (2026-04-21)

## 1. Current State

The current strongest practical baseline is still:

- **Exp14 Step2**
  - PM: `75.9%`
  - closed-loop: `66.7%`

The most important end-to-end comparison result is:

- **Exp17**
  - PM: `76.95%`
  - closed-loop: `11.1%`

This establishes the current rule:

> PM is not a model-selection metric by itself.  
> Mainline promotion requires closed-loop improvement.

Exp18 has now finished training and failed the gate evaluation:

- **Exp18**
  - best val loss: `1.325`
  - PM: `27.62%`
  - closed-loop: `11.1%`

This means Exp18 did not promote itself beyond a branch result.

---

## 2. How the Recent Commit Logic Evolved

### Phase A — practical baseline changed

- `49a45c19`
  - closed-loop simulation showed Step2 `66.7%`
  - practical baseline moved away from end-to-end VLM

### Phase B — professor rebuttal got structured

- `f687add1`
  - 5 counter-arguments were organized
  - key claims: text collapse, PM/closed-loop gap, decomposition practicality

### Phase C — Exp17 strengthened the rebuttal

- `f8ff92fb`
  - Exp17 full evaluation landed
  - PM can look good while closed-loop still fails badly
  - decomposition remains the strongest deployable path

### Phase D — V5 dataset was reframed

- `b5f6b456`
  - V5 raw dataset was re-analyzed
  - STOP supervision is effectively absent
  - terminal behavior must be treated as a proxy-signal problem, not a direct label-learning problem

---

## 3. Current Mid Conclusion

The current mid conclusion is:

1. **Exp14 Step2 remains the mainline baseline**
2. **End-to-end VLM branches are now gate-evaluated by closed-loop only**
3. **The next mainline learning path is Step2 + proxy features**
4. **Goal-near / stop-near should first be modeled as state estimation, not as a hard stop rule**

This is why the next queue is ordered as:

1. Exp19: Step2 + proxy feature concat
2. Exp20: Step2 + proxy auxiliary head
3. Controlled analysis of why Exp18 collapsed despite lower val loss

---

## 4. Exp18 Gate Result

Exp18 did not clear the baseline in closed-loop.

### Decision rule

Observed outcome:

- closed-loop `11.1%`
- PM `27.62%`
- dominant PM failure: `FORWARD -> FWD+R`

Therefore Exp18 falls in the final bucket:

- closed-loop `< 30%`
  - another val-loss / end-to-end policy failure case
  - not a co-baseline candidate

### Mandatory evaluation outputs

- PM
- closed-loop success
- FPE
- TLD
- path-wise breakdown
- confusion-level failure pattern

---

## 5. Exp19 — Step2 + Proxy Features

### Goal

Keep the Exp14 Step2 backbone and add the strongest non-leaky proxy signals.

### Input

- bbox history
- 16x16 grayscale image feature
- proxy features:
  - `area`
  - `center_error_x`
  - `abs_delta_cx`
  - `recent_bbox_consistency`

### Current implementation

- training script:
  - [`scripts/test_v5_bbox_nav_exp19_proxy.py`](../../scripts/test_v5_bbox_nav_exp19_proxy.py)
- outputs:
  - `docs/v5/bbox_nav_exp19_proxy/summary.json`
  - `docs/v5/bbox_nav_exp19_proxy/index.html`

### Success criterion

- main criterion: closed-loop `> 66.7%`
- secondary criterion: no catastrophic regression on path-wise PM

---

## 6. Exp20 — Proxy Auxiliary Head

### Goal

If Exp19 does not clearly improve closed-loop, add a lightweight auxiliary target before changing the controller logic.

### Auxiliary target

`goal_near_v0 = has_bbox AND area >= 0.27 AND center_error_x <= 0.03125`

### Current implementation

- training script:
  - [`scripts/test_v5_bbox_nav_exp20_proxy_aux.py`](../../scripts/test_v5_bbox_nav_exp20_proxy_aux.py)
- outputs:
  - `docs/v5/bbox_nav_exp20_proxy_aux/summary.json`
  - `docs/v5/bbox_nav_exp20_proxy_aux/index.html`

### Loss

- action CE
- plus weighted auxiliary BCE

### Success criterion

- same as Exp19: closed-loop improvement over Step2 baseline

---

## 7. Operational Rule

After Exp18 evaluation:

- keep Step2 as the practical baseline
- do not interpret lower val loss as deployment gain
- do not prioritize further end-to-end scaling over proxy-enhanced Step2
- treat proxy signals as soft state estimates first

Until Exp19/20 closed-loop is measured:

- do not claim proxy features solve stopping
- do not use `goal_near_v0` as a global hard stop rule

---

## 8. Commands

```bash
# Run Exp19
python3 scripts/test_v5_bbox_nav_exp19_proxy.py

# Run Exp20
python3 scripts/test_v5_bbox_nav_exp20_proxy_aux.py
```
