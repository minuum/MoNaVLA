# V5-Exp01: Baseline Discrete Action Model

## 1. Objective
- Transition from continuous regression to discrete classification.
- Verify if the Classification Head converges on V4 data.

## 2. Config Detail
- **Base**: KosMos-2 + LoRA (resumed from V4)
- **Dataset**: Full V4 (Straight 75%, Curves 25%)
- **Action Space**: 9-Class Discrete
- **Head**: Classification MLP

## 3. Results
- **Val Loss**: 2.270
- **PM (Accuracy)**: 68.1%
- **Behavior**: Always predicted "Forward" regardless of instruction.

## 4. Findings
- **Class Imbalance**: The 75% distribution of straight-ahead data dominated the softmax.
- **Backbone Pollution**: Previous V4 weights biased the vision-to-action mapping.
