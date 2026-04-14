# V5-Exp05 ~ Exp08: Intermediate Optimizations

## Exp 05: Action-Aware Instructions
- **Goal**: Add past/future context to instructions.
- **Method**: "You were turning left, now navigate forward."
- **Result**: Improved temporal consistency.

## Exp 06: Pure HF Alignment
- **Goal**: Ensure compatibility with generic KosMos-2 tokenizers.
- **Method**: Switched from custom tokens to standard grounding tokens.
- **Result**: Better generalization to out-of-distribution instructions.

## Exp 07: Path-Type Grounding
- **Goal**: Explicitly classify path types.
- **Method**: Task: "<grounding>Instruction: Navigate. Path: [Left]"
- **Result**: Reduced ambiguity in turns.

## Exp 08: Center-Goal Awareness
- **Goal**: Guide the model to the target center.
- **Method**: Prompt: "Navigate until the basket is centered."
- **Result**: First successful "Stop" logic at the target.
