# V5-Exp09: Full 8-Class Integration (Current)

## 1. Objective
- Integrate all previous breakthroughs: Google-Robot base + 8-class system + Center-goal awareness.
- Achieve stable 3DOF navigation `[lx, ly, az]`.

## 2. Config Detail
- **Base**: Google-Robot Pretrained
- **Dataset**: Balanced V5 (150+ Epochs)
- **Action Space**: **8-Class** (Forward, L, R, FL, FR, Stop, Turn-L, Turn-R)
- **Instruction**: "Navigate until centered in the frame"
- **Weights**: [5.0, 1.0, 10.0, 10.0, 5.0, 5.0, 15.0, 15.0]

## 3. Final Results (As of April 15)
- **Epoch**: 15 / 15 (Completed)
- **Val Loss**: **1.203** (Best)
- **Val Accuracy (Trainer)**: **83.0%**
- **Offline Eval (PM/DM)**: **85.7%** (42/49 samples)
- **Behavior**: While Val Accuracy is high, offline evaluation reveals a persistent **Forward Bias**. The model predicts "Forward" for almost all validation samples.

## 4. Findings & Analysis
- **Forward Bias**: Even with class weights (Forward=1.0, others=5.0~15.0), the model tends to collapse to the "Forward" action. This is likely due to the overwhelming frequency of Forward transition in the dataset.
- **8-Class Integration**: The architecture successfully supports 8 discrete actions, but the policy head requires stronger regularization or a more balanced curriculum to learn rotation and stopping.
- **Next Steps**: 
    1. Implement **Sampling Weight Adjustment** (weighted sampling) in the data loader.
    2. Re-introduce **Counterfactual Stop** data specifically for V5-8class.
    3. Explore **Action-Conditional Instruction** tuning (Track 2 from V4 plan).
