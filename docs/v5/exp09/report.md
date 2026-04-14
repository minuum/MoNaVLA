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

## 3. Current Live Results (As of April 15)
- **Epoch**: 11 / 15
- **Val Loss**: **1.340**
- **Val Accuracy**: **80.2%**
- **Behavior**: Smooth transitions from rotation to forward as the basket enters the center of the FOV.

## 4. Findings
- **8-Class system** provides much better control over rotation than 6-class.
- **Center-goal instruction** effectively reduced the "Forward Bias" because the model now has a clear reason to STOP.
- **Progress**: Currently the best performing model in project history.
