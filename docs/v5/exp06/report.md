# V5-Exp06: Pure HuggingFace Alignment

## 1. Goal
- Ensure compatibility with generic KosMos-2 tokenizers and HuggingFace ecosystems.

## 2. Method
- Switched from custom `<action>` tokens to standard `<grounding>` and `<phrase>` tokens.
- Aligned dataset metadata with HF `datasets` library expectations.

## 3. Result
- **Finding**: Better generalization to out-of-distribution instructions.
- Easier to integrate with other pre-trained VLM models in the future.
