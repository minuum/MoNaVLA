# April 24 Professor Meeting TODOs From Transcript

Source: `docs/v5/11_08 AM - In-Person meeting April 24_transcript.txt`

This TODO list is grounded only in the transcript. It does not infer extra experiment claims that are not stated there.

## Professor's Core Diagnosis

The meeting repeatedly narrows the problem to basic eliminations, not broad new model variants.

1. Prove whether the model actually recognizes the target object.
   - The professor asks what test proves object recognition and says there is no current exact evidence that the model recognizes the object.
   - Transcript lines: 10-18, 40-60, 126-135.

2. If object recognition is proven, then test whether recognition maps to the correct action.
   - The professor separates "object recognized" from "left / straight / right action chosen".
   - Transcript lines: 61-68.

3. Run minimal left-only / curved-only tests to expose whether straight collapse is a real learning failure or a pipeline bug.
   - The professor says that if only left/curved paths are trained, straight-only inference is not plausible and means something else is wrong.
   - Transcript lines: 102-119, 185-194.

4. Do not tune LoRA across all decoder blocks by default.
   - The professor asks how many transformer/decoder blocks are used, identifies 24 decoder blocks, and suggests using only the last roughly 4 blocks rather than all 24.
   - Transcript lines: 1-2, 73-95, 126-131, 154-159.

5. If the above still fails, inspect the action head / LSTM side next.
   - The professor asks what the action head is and mentions checking the LSTM part if needed.
   - Transcript lines: 169-176.

## Ordered TODOs

### TODO 1: Object Recognition Proof

Goal: Answer only this question first: "Does the current VLM path identify the gray basket under the frames we use?"

Required output:
- A small report with sampled frames from collected data.
- For each frame: input image, prompt text, predicted bbox or grounding output, human/GT bbox if available, IoU or pass/fail.
- Split cases by viewpoint/visibility:
  - full object visible
  - side/front view changes
  - partial object visible
  - distractors present
- Explicit conclusion:
  - "recognition reliable enough"
  - "recognition fails in these cases"
  - or "cannot conclude"

Transcript basis:
- "객체를 인식하는지 안하는지 정확한 어떤 근거가 없는 거잖아요" lines 10-12.
- "어떤 테스트를 통해서 증명을 한 거지?" lines 15-18.
- "증명을 해서 오겠습니다" lines 57-60.
- "초기 프레임 위주로" test plan lines 132-135.

### TODO 2: Raw Inference Log Audit On Initial Frames

Goal: See the actual model outputs without rollout ambiguity.

Required output:
- Load model and run frame-by-frame on collected initial frames.
- Log:
  - prompt
  - predicted grounding/bbox output
  - action logits/softmax
  - chosen class
  - decoded x/y/z or class output used by inference
- Confirm whether "straight" is coming from the model output, decode logic, class mapping, or post-processing.

Transcript basis:
- The professor asks whether X/Y/Z values are logged and what comes out when it goes straight, lines 136-143.
- Student says softmax/action values are logged and inference changes at about 2 Hz, lines 138-143.

### TODO 3: Minimal Left-Only Training/Inference Test

Goal: Test the professor's central sanity check: if trained only on left-family data, does the model still output straight?

Required output:
- Train/evaluate on left-only or left-start family only.
- Report class distribution, especially:
  - LEFT
  - FWD+L
  - TURN_L
  - FORWARD/STRAIGHT
- Include confusion matrix and first-N-frame predictions.
- If output is still straight, classify the failure as a pipeline/action-supervision issue, not just insufficient training.

Transcript basis:
- "왼쪽 것만 해도 ... 스트레이트로 간다면 뭔가 이상한 거잖아" lines 118-119.
- "얘만 50개를 해가지고 ... 이거는 무조건 가야 되는 거잖아요" lines 185-186.
- "기본적인 걸 먼저" lines 189-194.

### TODO 4: Last-4 Decoder LoRA Experiment

Goal: Run the professor's requested limited LoRA adaptation instead of all decoder blocks.

Required output:
- Verify exact decoder block count and trainable parameter names.
- Configure LoRA only on the last approximately 4 decoder blocks, not all 24.
- Keep the test minimal, preferably paired with left-only data first.
- Report trainable parameter count and gradient presence for the intended blocks.

Transcript basis:
- The professor asks to check transformer block count, lines 73-75.
- Student reports 24 transformer/decoder blocks, lines 84-95.
- Professor suggests last blocks only, around 20-24 / 4 blocks, lines 94-95 and 126-131.
- Student restates "21에서 24 레이어 정도만 학습", lines 154-155.

### TODO 5: Remove Confounds Before Full Experiments

Goal: Avoid mixing many causes before the sanity checks pass.

Required output:
- Start from pure/original Kosmos where possible.
- Avoid Google-robot-specific assumptions during the minimal sanity check.
- Avoid adding full-dataset/full-objective complexity until TODO 1-4 are answered.

Transcript basis:
- Student says to remove other factors and use original Kosmos without Google-robot first, lines 154-159.
- Professor says full experiment is unlikely to help because there are few samples and the basic issue is unresolved, lines 160-162.

### TODO 6: Action Head / LSTM Check If Minimal Tests Fail

Goal: If left-only + last-block LoRA still produces straight, inspect whether the action head/LSTM path is preventing learning.

Required output:
- Confirm action head architecture used in the current run.
- Run a head-only overfit check on a tiny left-only subset.
- Verify gradients and logits change for left classes.
- Check class-id mapping and decode mapping.

Transcript basis:
- Professor asks what the action head uses and whether it is LSTM, lines 169-176.
- This is explicitly a later check, after the more basic tests.

### TODO 7: Expand Ground-Truth Frame Review Only After Recognition Failure Is Characterized

Goal: Do not label more data blindly; use labeling to answer the recognition question.

Required output:
- If TODO 1 shows recognition ambiguity, expand GT frames from the existing review tool.
- Prioritize frames that represent viewpoint/visibility/distractor failure cases.
- Report per-case recognition pass/fail, not just aggregate IoU.

Transcript basis:
- Student proposes self-review / dataset evaluation and 15-30 GT samples per target sample set, lines 181-184.
- Professor's preceding concern is still whether the current model recognizes the object, lines 160-166 and 177-180.

## Priority Order

1. TODO 1: Object recognition proof.
2. TODO 2: Raw inference log audit.
3. TODO 3: Minimal left-only training/inference test.
4. TODO 4: Last-4 decoder LoRA test.
5. TODO 6: Action head/LSTM check only if TODO 3-4 fail.
6. TODO 7: More GT review only if TODO 1 shows recognition uncertainty.

## Non-TODOs From This Transcript

These are not directly requested as next actions in the transcript:

- Broad full-dataset training before the sanity checks.
- More resize experiments.
- More aggregate PM/rollout runs without raw object/action diagnostics.
- Using YOLO as evidence that the VLM itself recognizes the object. The professor explicitly rejects YOLO as the relevant proof because the current model is not YOLO.

