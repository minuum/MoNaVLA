# V5-Exp07: Path-Type Grounding

## 1. Goal
- Explicitly classify path types in the visual-language space to reduce turn ambiguity.

## 2. Method
- Task format: `Instruction: Navigate. Path: [Left]`
- Added special path-type grounding tokens.

## 3. Result
- **Finding**: Significant reduction in "Left vs Right" confusion in the earliest training steps.
- Established the base for Exp 08/09 goal-oriented instructions.
