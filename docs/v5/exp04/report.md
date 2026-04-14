# V5-Exp04: Google-Robot Foundation Shift

## 1. Objective
- Replace "polluted" V4 weights with clean **Google-Robot pretrained** vision-language bridge.
- Validate the effect of foundation weights on training speed and grounding.

## 2. Config Detail
- **Base**: Google-Robot Pretrained (KosMos-2 modified)
- **Dataset**: Curved paths only (Left/Right)
- **Action Space**: 6-Class Discrete
- **Special**: `load_vlm_only=True` (Initialized head from scratch)

## 3. Results
- **Val Loss**: **0.776** (Dramatic drop from 2.21)
- **PM (Accuracy)**: **82%** (validation)
- **Behavior**: Strong sensitivity to instructions. Rotation commands are now distinct from forward commands.

## 4. Findings
- Foundation models matter more than extra data in low-data regimes.
- V4 regression training had "broken" the vision tower's ability to communicate with the action decoder.
- Success in this experiment led to the adoption of Google-Robot weights as the new project standard.
