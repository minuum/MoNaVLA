# Pure HF Controlled Ablation (2026-04-21)

## 목적

현재 root-cause 결론은 여기까지 닫혀 있다.

- `Pure HF Kosmos-2`: text attention 약 `22.6%`
- `Google-Robot + head-only (Exp15)`: text attention `0.000%`
- `Google-Robot + LoRA (Exp11)`: text attention `0.000%`
- `Google-Robot + LoRA + instr_proj (Exp13)`: text attention `0.000%`

즉 `LoRA`는 collapse의 필요조건이 아니다.

하지만 아직 남은 질문은 하나다.

> `Pure HF` 기준에서도 head-only / LoRA / both를 같은 split, 같은 8-class 설정으로 돌리면 text path가 살아남는가?

이 문서는 그 질문을 닫기 위한 **controlled ablation 실행 기준**이다.

---

## 실험 정의

모든 실험은 다음 공통 조건을 유지한다.

- dataset: `mobile_vla_dataset_v5`
- split regime: `Exp11`과 동일 (`center_straight` 제외)
- task: 8-class discrete action
- window: `8`
- learning rate: `5e-5`
- max epochs: `20`
- backbone source: **raw HF Kosmos-2**

### Exp21 — Pure HF head-only

- config: [configs/mobile_vla_v5_exp21_pure_hf_head_only.json](/home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v5_exp21_pure_hf_head_only.json:1)
- 의미:
  - Google-Robot post-train 제거
  - backbone frozen
  - LoRA off
  - projector / resampler frozen
  - action head만 학습

질문:

> 건강한 pure HF backbone을 얼린 상태에서도 text attention이 유지되는가?

### Exp22 — Pure HF LoRA

- config: [configs/mobile_vla_v5_exp22_pure_hf_lora.json](/home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v5_exp22_pure_hf_lora.json:1)
- 의미:
  - Google-Robot post-train 제거
  - backbone frozen
  - LoRA on
  - 나머지 조건은 Exp11과 동일

질문:

> raw HF foundation 위에서는 LoRA가 text path를 보존하는가, 아니면 다시 collapse시키는가?

### Exp23 — Pure HF both

- config: [configs/mobile_vla_v5_exp23_pure_hf_both.json](/home/billy/25-1kp/MoNaVLA/configs/mobile_vla_v5_exp23_pure_hf_both.json:1)
- 의미:
  - Google-Robot post-train 제거
  - backbone unfreeze
  - LoRA on
  - VLM + action head 동시 적응

질문:

> fully trainable pure HF path에서도 text attention이 유지되는가?

---

## 실행 순서

가장 먼저 돌릴 것은 `Exp21`이다.

이유:

- GPU 리스크가 상대적으로 낮다
- `Pure HF`만으로도 text path가 살아남는지 가장 빠르게 확인할 수 있다
- `Exp15(head-only)`와 직접 대응되는 통제군이 된다

권장 순서:

1. `Exp21`
2. `Exp22`
3. `Exp23`

---

## 실행 명령

```bash
python3 robovlm_nav/train.py configs/mobile_vla_v5_exp21_pure_hf_head_only.json
python3 robovlm_nav/train.py configs/mobile_vla_v5_exp22_pure_hf_lora.json
python3 robovlm_nav/train.py configs/mobile_vla_v5_exp23_pure_hf_both.json
```

---

## 필수 평가

각 실험마다 아래 3개를 반드시 남긴다.

1. `text_understanding`
2. `attention analysis`
3. `PM`

가능하면 그다음:

4. `short rollout`
5. `closed-loop`

---

## 판정 기준

### Root-cause 관점 성공

다음 중 하나라도 나오면 큰 진전이다.

- `Exp21`에서 text attention이 `0%`가 아니게 유지
- `Exp22`에서 pure HF가 Google-Robot 계열과 다르게 text path를 유지
- `Exp23`에서 PM과 text attention이 동시에 유지

### 실패 패턴

다음이면 기존 가설을 수정해야 한다.

- pure HF 3축 모두 다시 text `0.000%`
- 즉 Google-Robot checkpoint가 아니라 현재 action training objective 자체가 collapse를 유도

---

## 현재 기대 해석

현 시점의 가장 그럴듯한 가설은 이렇다.

- `Google-Robot post-train`은 이미 image-dominant
- 그래서 `Exp15`와 `Exp11`이 둘 다 text `0.000%`
- 반면 raw HF는 text `22.6%`가 살아 있음

따라서 가장 중요한 분기점은:

> `pure HF`에서도 head-only부터 바로 죽는가, 아니면 Google-Robot과 달리 살아남는가?

이 한 줄이 다음 backbone 전략을 정한다.

---

## 다음 결론 분기

### 경우 A

- `Exp21/22/23` 중 하나라도 text path 유지

그러면:

- backbone 전략을 `pure HF` 중심으로 재설계
- Google-Robot 계열은 practical baseline 비교용 branch로만 유지

### 경우 B

- `Exp21/22/23` 모두 text collapse

그러면:

- backbone 문제가 아니라 `action objective / data shortcut / decoder routing` 문제가 더 큼
- 이후에는 `objective redesign` 쪽으로 가야 한다

