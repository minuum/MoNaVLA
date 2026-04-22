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

## Exp21 결과 (2026-04-22)

첫 번째 controlled ablation인 `Exp21` 결과는 단순하지 않다.

- 학습: 완료
- best checkpoint:
  - `/tmp/monavla_resume_runs/kosmos/mobile_vla_v5_exp21/2026-04-21/v5-exp21-pure-hf-head-only/epoch_epoch=epoch=14-val_loss=val_loss=2.009.ckpt`
- best `val_loss`: `2.009`

### 1. Attention analysis

- 스크립트: [scripts/measure_attention.py](/home/billy/25-1kp/MoNaVLA/scripts/measure_attention.py:1)
- 결과: [docs/v5/attention_analysis/summary.json](/home/billy/25-1kp/MoNaVLA/docs/v5/attention_analysis/summary.json:1)

관측:

- action token last-layer attention:
  - image: `97.7%`
  - text: `0.000%`
- mean-over-layers:
  - image: `60.4%`
  - text: `0.000%`

즉 `Pure HF + head-only`에서도, 우리가 쓰는 attention probe 기준으로는 text region이 다시 `0.000%`였다.

### 2. Text understanding (single-frame sensitivity)

- 스크립트: [scripts/test_v5_text_understanding.py](/home/billy/25-1kp/MoNaVLA/scripts/test_v5_text_understanding.py:1)
- 결과: `/tmp/v5_text_understanding_result.json`

동일 이미지에서 instruction만 바꿨을 때:

- `left_1`  -> `RIGHT`
- `right_1` -> `FWD+R`
- `forward_1` -> `FORWARD`
- `L2(left, right) = 0.9758`

즉 `Exp21`은 최소한 single-frame inference에서는 `left/right/forward`를 완전히 동일하게 내보내지 않았다.

### 3. PM evaluation

- 스크립트: [scripts/test_v5_pm_dm.py](/home/billy/25-1kp/MoNaVLA/scripts/test_v5_pm_dm.py:1)
- checkpoint: 위 best ckpt 사용

결과:

- PM: `0.00%` (`0/100`)
- confusion:
  - `FORWARD -> FWD+R` `60/60`
  - `LEFT -> FWD+R` `18/18`
  - `RIGHT -> FWD+R` `22/22`

즉 dataset-level에선 사실상 **전부 `FWD+R` collapse**였다.

### 4. 현재 해석

`Exp21`은 다음을 동시에 보여준다.

1. attention probe 기준으로는 여전히 text `0.000%`
2. single-frame instruction swap에는 일정 반응이 있음
3. 하지만 dataset 전반 action matching은 `0%`

따라서 현재 가장 안전한 결론은 이렇다.

- `Pure HF`로 바꿨다고 해서 곧바로 practical policy가 되지는 않는다.
- 다만 `Exp11/15`처럼 "instruction을 완전히 동일 action으로만 내보내는 상태"와도 다르다.
- 즉 **collapse 양상이 하나가 아니다**:
  - `Google-Robot` 계열은 text-insensitive collapse
  - `Exp21`은 single-frame sensitivity는 있으나 sequence policy가 전역적으로 `FWD+R`로 무너지는 collapse

이 결과는 다음 실험 우선순위를 바꾼다.

- `Exp22/23`로 pure HF branch를 더 확인할 가치는 남아 있다.
- 하지만 동시에, root-cause를 backbone alone이 아니라
  - action objective
  - decoder routing
  - sequence policy stabilization
로 더 분리해야 한다.

### 5. Shared-split degradation breakdown (Exp11 vs Exp21)

- 스크립트: [scripts/analysis/evaluate_rollout_degradation_v5.py](/home/billy/25-1kp/MoNaVLA/scripts/analysis/evaluate_rollout_degradation_v5.py:1)
- 결과: [docs/v5/rollout_degradation/index.html](/home/billy/25-1kp/MoNaVLA/docs/v5/rollout_degradation/index.html:1),
  [docs/v5/rollout_degradation/degradation_summary.json](/home/billy/25-1kp/MoNaVLA/docs/v5/rollout_degradation/degradation_summary.json:1)

주의:

- 아래 `frame_acc`는 full validation PM이 아니라,
  **closed-loop와 동일한 episode split에서 계산한 frame-level accuracy**다.
- 목적은 절대 수치 비교보다, **같은 split에서 one-step → short rollout → full rollout이 어떻게 무너지는지** 보는 것이다.

| model | frame_acc | prefix@5 success | prefix@10 success | prefix@15 success | full success | full FPE |
|:---|---:|---:|---:|---:|---:|---:|
| Exp11 | 28.2% | 22.2% | 0.0% | 0.0% | 0.0% | 1.454 |
| Exp21 | 10.4% | 33.3% | 22.2% | 0.0% | 0.0% | 1.983 |

해석:

- `Exp11`은 frame-level accuracy가 더 높지만, `prefix@10`부터 바로 collapse한다.
- `Exp21`은 frame-level accuracy 자체는 더 낮지만, 아주 짧은 horizon에서는 오히려 더 오래 버틴다.
- 그러나 `prefix@15` 이후에는 둘 다 실패하고, full rollout에서는 `Exp21`이 더 크게 드리프트한다.

추가로 class transition을 보면, 두 모델의 attractor가 다르다.

- `Exp11` top predicted transitions:
  - `RIGHT -> RIGHT` `70`
  - `FORWARD -> FORWARD` `33`
- `Exp21` top predicted transitions:
  - `FWD+L -> FWD+L` `141`

즉:

- `Exp11`은 `RIGHT` 쪽으로 빨려 들어가는 sideways attractor
- `Exp21`은 거의 전 경로를 `FWD+L`로 처리하는 diagonal-left attractor

path-wise full 결과도 이 해석과 맞는다.

- `Exp11`은 `left_straight`, `right_straight`에서 frame accuracy가 상대적으로 높지만,
  `center_*`와 `left/right turn` 계열에서 일찍 무너진다.
- `Exp21`은 `right_left`, `center_left`처럼 `FWD+L`과 일부 정렬되는 경로에서만 부분 점수를 얻고,
  `left_right`, `right_right`, `left_straight`, `right_straight`에서 크게 깨진다.

즉 현재 evidence는 이렇게 정리된다.

- `Exp11`: one-step은 그럴듯하지만 rollout transition이 매우 약하다.
- `Exp21`: local instruction sensitivity는 있으나, dataset-wide action policy가 불안정해 긴 horizon에서 더 크게 무너진다.

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
