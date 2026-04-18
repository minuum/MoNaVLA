# 교수님 업데이트 메모
작성일: 2026-04-17

## 1. 이번에 한 일

이번에는 기존의 end-to-end policy 계열 실험들을 다시 정리하면서, `Exp14 bbox-navigation` 트랙을 별도로 검증했습니다.  
핵심 목적은 다음 질문을 확인하는 것이었습니다.

> 목표물의 위치를 읽는 능력(`grounding`)과  
> 그 위치 정보를 action으로 바꾸는 능력(`policy`)을  
> 분리해서 다루면 더 안정적인가?

기존 `Exp04`, `Exp09`, `Exp11`은 모두 이미지와 instruction을 받아서 곧바로 action class를 예측하는 **end-to-end policy** 구조였습니다.  
반면 이번 `Exp14`는 문제를 두 단계로 나눴습니다.

1. 먼저 VLM이 목표물의 위치를 읽는다.
2. 그 결과를 작은 action head가 받아 action으로 바꾼다.

즉, 이번 작업은 단순히 성능 숫자를 다시 재는 것이 아니라, **정책 학습 방식 자체를 decomposition 방식으로 바꿔 본 것**입니다.

---

## 2. 알고리즘 관점에서 본 핵심 해석

### 기존 end-to-end policy 계열의 문제

기존 정책형 실험들은 학습 loss는 좋아 보여도, 실제 inference에서는 shortcut learning이나 class collapse가 자주 발생했습니다.

- `Exp04`
  - 문서상으로는 `val_loss 0.776`
  - 하지만 재평가 결과 실제 `PM 0%`
  - 즉 loss는 좋아도 실제 제어는 무너진 사례

- `Exp11`
  - 현재 남아 있는 기존 학습형 baseline
  - `PM 58.6%`
  - 다만 left/right 계열 분리가 불안정하고 sanity에서 collapse 징후가 있음

이 결과는, **큰 action head를 end-to-end로 학습시키는 방식이 spatial grounding을 제대로 활용하지 못할 수 있다**는 점을 보여줍니다.

### Exp10에서 확인한 것

`Exp10`은 action policy 대신 목표물 위치 예측, 즉 grounding 자체를 학습한 실험입니다.

- teacher-forced 기준:
  - `val_loss 0.012`
  - `IoU 0.87`

즉 perception 자체는 강했습니다.  
하지만 이 출력을 free-form generation으로 뽑아 rule로 action에 연결해보면 실제 transfer는 `34.4%`밖에 나오지 않았습니다.

이 의미는 분명합니다.

> 모델 내부에 spatial information은 있지만,  
> 그것을 현재 generation interface로 바로 꺼내서 쓰는 방식은 불안정하다.

### Exp14 Step 1

그래서 `Exp14 Step 1`에서는 문제를 다시 단순화했습니다.

- 입력:
  - 최근 몇 프레임의 `bbox center x/y`
  - `bbox area`
  - `bbox 존재 여부`
- 모델:
  - 작은 `MLP`
- 목표:
  - 이 geometry/history feature만으로 action class 예측

결과는 `68.4%`였습니다.

즉, **VLM이 읽은 spatial cue를 직접 작은 decision head에 연결하는 방식**이 기존 학습형 baseline보다 더 잘 작동했습니다.

### Exp14 Step 2

`Step 1`의 한계는 bbox만으로는 애매한 장면을 충분히 구분하기 어렵다는 점이었습니다.  
특히 `center_left`, `center_right`처럼 경계가 애매한 경우에는 추가 시각 정보가 필요했습니다.

그래서 `Step 2`에서는 bbox history에 더해, 현재 프레임의 아주 작은 시각 feature를 추가했습니다.

- 추가 feature:
  - `16x16 grayscale image feature`

즉 feature level에서는:

`geometry (bbox history) + weak appearance (low-res image)`

구조가 된 것입니다.

기존 기록 기준 결과는 `75.9%`였습니다.

이건 알고리즘적으로 다음 의미를 가집니다.

> 거대한 end-to-end policy 전체를 다시 학습시키는 것보다,  
> spatial intermediate representation을 명시적으로 꺼내고  
> 그 위에 작은 head를 올리는 편이 더 잘 작동할 수 있다.

---

## 3. 현재 공식 비교

현재 Pages 기준으로 정리한 비교는 다음과 같습니다.

| 항목 | PM | 해석 |
|---|---:|---|
| Exp04 | 0% | loss 대비 inference collapse |
| Exp10 ckpt + rule | 34.4% | grounding score는 좋지만 transfer 실패 |
| Exp11 | 58.6% | 현재 기존 학습형 baseline |
| Exp14 Step 1 | 68.4% | bbox history만으로도 Exp11 초과 |
| Exp14 Step 2 | 75.9% | 현재 strongest practical baseline |

즉 현재 문서 기준 공식 해석은:

- `Exp11 = 기존 학습형 기준점`
- `Exp14 Step 2 = 현재 가장 강한 practical baseline`

입니다.

---

## 4. 재현성 검증 업데이트 (정정)

이전 본문에 기록했던 "seed 0에서 `11.3%` 급락"은 실제 재측정 결과와 불일치하여 정정합니다.  
5개 split seed × 8 epoch 단기 재학습을 다시 수행한 결과는 다음과 같습니다.

| split_seed | Step 2 PM |
|:---:|:---:|
| 0 | 74.8% |
| 1 | 79.1% |
| 2 | 74.8% |
| 3 | 77.4% |
| 4 | 76.7% |

- **Mean ± std: `76.6% ± 1.6%`**
- 원본 `75.9%`는 이 범위의 정중앙에 위치합니다.
- 8 epoch 단기 재학습만으로도 동등한 성능이 재현되며, 220 epoch 풀 학습이 필수는 아닙니다.

따라서 "재현성 민감" 우려는 철회하며, 현재 해석은 다음과 같습니다.

- 알고리즘 방향 자체는 유망합니다.
- **decomposition 구조의 재현성은 5-seed 기준으로 확인**되었습니다.
- 남은 쟁점은 **Exp11과의 같은 split 직접 비교**와 **training seed 고정화**입니다.

재현성 데이터는 [bbox_nav_step2_repro/summary.json](./bbox_nav_step2_repro/summary.json)에서 확인할 수 있습니다.

---

## 5. Exp11 vs Step 2 Same-Split 직접 비교 (신규)

Step 2의 held-out 9 에피소드를 그대로 사용하고, `window_size=8`, `fwd_pred_next_n=5` 제약에서 Exp11이 예측 가능한 공통 프레임 subset 50개에서 두 모델을 직접 대조했습니다.

**1차 비교 (Step 2 20 epoch 단축)**

| 항목 | PM | 비고 |
|:---|---:|:---|
| Exp11 (기존 ckpt) | 50.0% (25/50) | epoch 14, val_loss 1.010 |
| Step 2 (20 epoch) | 34.0% (17/50) | 단축 학습 |
| Delta | -16.0%p | 이 subset에선 Step 2가 낮음 |

**2차 비교 (Step 2 220 epoch, 원본과 동일 조건)**

| 항목 | PM | 비고 |
|:---|---:|:---|
| Exp11 (기존 ckpt) | **50.0%** (25/50) | 동일 |
| **Step 2 (220 epoch)** | **50.0%** (25/50) | **동률** |
| Delta | **0.0%p** | 공정 비교 완료 |

세부 (path_type별 "correct / total", 220 epoch 기준):

| path_type | Exp11 | Step 2 (220 ep) |
|:---|:---:|:---:|
| center_straight | 0/2 | 0/2 |
| **center_left** | 0/6 | **3/6** |
| **center_right** | **6/6** | 2/6 |
| **left_straight** | **5/6** | 4/6 |
| left_left | 2/7 | 2/7 |
| **left_right** | 4/7 | **5/7** |
| **right_straight** | **5/6** | 4/6 |
| **right_left** | 1/6 | **3/6** |
| right_right | 2/4 | 2/4 |

**해석 (업데이트)**:

1. 1차 비교에서의 Step 2 약세(`-16%p`)는 **학습 epoch 부족이 주 원인**이었음을 확인했습니다. 220 epoch로 동일 조건을 맞추면 두 모델은 **동률(50% vs 50%)** 입니다.
2. Full test set 기준 `Step 2 75.9%` vs `Exp11 58.6%`의 우위는 **이 공통 subset에서는 발견되지 않습니다**. 즉 Step 2의 강점은 `window_size=8 / fwd_pred_next_n=5` 제약 밖 프레임(에피소드 중후반)에서 주로 나오는 것으로 추정됩니다.
3. Path type별 강점이 **상호 보완적**입니다.
   - Exp11: `center_right (6/6)`, `left_straight (5/6)`, `right_straight (5/6)`
   - Step 2: `center_left (3/6)`, `left_right (5/7)`, `right_left (3/6)`
4. 둘 다 `center_straight` 계열은 전혀 못 맞힙니다 (0/2). 직선 경로는 FORWARD 반복이라 첫 프레임만으로는 decision이 어려운 공통 약점.
5. **다음 단계는 두 모델의 per-path 강점을 결합하는 ensemble/mixture 설계** 또는 **공통 subset 밖 구간에서 Step 2의 진짜 우위 검증**입니다.

원본 데이터:
- [exp11_vs_step2_same_split/summary.json](./exp11_vs_step2_same_split/summary.json) (20 epoch)
- [exp11_vs_step2_same_split_fullep/summary.json](./exp11_vs_step2_same_split_fullep/summary.json) (220 epoch)

---

## 6. 이번 업데이트의 한 줄 결론

이번에는 navigation을 end-to-end action prediction으로 보기보다,  
**grounding과 action mapping을 분리한 decomposition 알고리즘**으로 접근했습니다.

정책형 baseline(`Exp11 58.6% full, 50.0% same-subset`)과 decomposition(`Step 2 75.9% full, 76.6 ± 1.6% repro, 220-ep same-subset 50.0%`)의 직접 비교에서, **full split에서는 decomposition이 우세하고, 공통 subset에서는 양 모델이 동률**입니다.  
두 모델은 **path type별 강점이 상호 보완적**이며, 다음 단계는 **full set에서 Exp11 역방향 평가** 및 **상호 보완 구조의 통합 실험**입니다.

---

## 7-1. Attention Weight 실측 (Causal Evidence, 2026-04-18)

"텍스트가 action에 전달되지 않는다"는 주장을 self-attention weight 실측으로 뒷받침했습니다. `third_party/RoboVLMs/`를 수정하지 않고 `register_forward_hook` 방식으로 `output_attentions=True`를 주입해 capture했습니다.

**Transformer input layout** (확정): `seq=257 = image_embeds(0:64) + text_embeds(64:256) + action_token(256)`

**Exp11 (last layer, 3 instruction)**

| Region | left | right | forward |
|:---|:---:|:---:|:---:|
| Image (0:64) | **91.7%** | **91.7%** | **92.0%** |
| Text (64:76, 실제 instruction 12 tokens) | **0.000%** | **0.000%** | **0.000%** |
| Pad (76:256) | ~0% | ~0% | ~0% |
| Self (action, pos 256) | 8.3% | 8.3% | 8.0% |

Top-5 attention position은 `(7, 0.2407), (8, 0.1774), (2, 0.1565), (6, 0.1316), (256, 0.083)`로 **left/right에서 소수점 4자리까지 bit-level 동일**. 즉 instruction을 바꿔도 어느 image patch에 attend할지가 전혀 달라지지 않습니다.

**Exp13** (`instr_proj`로 instruction embedding을 action head에 명시 주입한 실험)

| Region | left | right | forward |
|:---|:---:|:---:|:---:|
| Image (0:64) | 85.8% | 85.8% | 84.3% |
| Text (64:76) | **0.000%** | **0.000%** | **0.000%** |

instruction embedding을 후단에 추가해도 **LM 단계에서 이미 text가 무시**되고 있어 실효가 없음.

**Cross-attention 없음**: `output.cross_attentions` is `None` (Kosmos decoder-only). Self-attention이 유일한 통로이며, 그 통로가 instruction을 버립니다.

**Pure Kosmos-2 (학습 전 foundation) 대조** — before/after 증거

| 모델 | Image ratio | Text ratio |
|:---|:---:|:---:|
| Pure Kosmos-2 (LoRA/FT 없음) | 77.3% | **22.7%** |
| Exp11 (학습 후) | 91.7% | **0.000%** |
| Exp13 (학습 후) | 85.8% | **0.000%** |

Pure Kosmos-2는 instruction text에 **정상적으로 22% attend**하나, 우리의 학습 절차를 거친 후에는 **0%로 완전히 소멸**합니다.

**Exp15 (Head-only ablation, 2026-04-18 추가) — 인과 수정**

| 모델 | Image ratio | Text ratio | PM |
|:---|:---:|:---:|:---:|
| Pure HF Kosmos-2 (학습 전) | 77.3% | **22.7%** | — |
| Exp15 (head-only, VLM frozen) | 94.4% | **0.000%** | **37.5%** |
| Exp11 (LoRA 학습 후) | 91.7% | **0.000%** | **58.6%** |
| Exp13 (LoRA + instr_proj) | 85.8% | **0.000%** | 15% |

Exp15는 VLM(Kosmos 전체)이 완전히 frozen된 상태 — LoRA 없음, mm_projector 없음, text_embedding 없음 — 에서 action head만 학습한 실험입니다. 결과는 text=0.000%.

이는 **text attention collapse가 우리의 LoRA/projector 학습이 아니라 Google-Robot post-training 단계에서 이미 발생했음**을 의미합니다. VLM 가중치를 일절 건드리지 않아도 Google-Robot backbone은 이미 text=0%입니다.

수정된 해석:
- Pure HF Kosmos-2 → 22.7% text attention (건강한 foundation)
- Google-Robot post-training → text 0% (post-training이 text path 붕괴, 우리 탓 아님)
- 우리의 LoRA → PM 37.5%(head-only) → 58.6%(LoRA) 향상, 그러나 text attention 복구 불가
- **"텍스트 무시"는 Google-Robot post-training에서 상속된 특성이며, 우리 fine-tuning이 만든 것이 아닙니다**

**결론 (수정)**: text collapse는 backbone 선택(Google-Robot)에서 기인하며, Pure HF Kosmos-2 기반이었다면 text attention이 보존됐을 가능성이 있습니다. LoRA는 PM을 높이는 역할을 하지만 text path를 죽이는 역할은 하지 않습니다.

데이터: [attention_analysis/summary.json](./attention_analysis/summary.json)

**Per-layer × per-head collapse 분석 (2026-04-18)**

24 layer × 32 head 전체를 비교한 결과:

- **전역 동시 붕괴**: Pure Kosmos는 layer별로 text ratio 22~72%의 분포(layer 2에서 peak 72%). Exp11/13/15는 **layer 0 ~ 23 전체에서 text = 0.0%** — 특정 layer만의 국소 문제가 아니라 전 stack이 동시에 무너짐.
- **100% head mortality**: Pure Kosmos의 32 head 중 21~32개가 "text head"(text region 합계 > 0.05)였으나, Google-Robot 기반 모델은 **모든 layer에서 0 heads**.
- **Peak text layer 2 현상**: Foundation은 shallow layer(특히 layer 2)에서 instruction grounding 형성. Google-Robot post-training 후 이 shallow grounding이 제거됨.
- **Exp15(frozen) ≈ Exp11(LoRA)**: attention distribution이 거의 동일(94.4% vs 91.7%) — LoRA가 attention을 추가로 변형하는 효과는 작음.

데이터: [attention_analysis/mechanism.json](./attention_analysis/mechanism.json) / [mechanism.html](./attention_analysis/mechanism.html)

---

## 7. 다음 단계 제안

1. ~~`Step 2`를 여러 split/seed에서 다시 평가해 재현성 확인~~ → **완료 (76.6 ± 1.6%, 5 seeds)**
2. ~~`Exp11`과 `Step 2`를 가능한 한 같은 split에서 직접 비교~~ → **완료**
   - 1차 (Step 2 20 epoch): Step 2 34% / Exp11 50% (Step 2 열세)
   - 2차 (Step 2 220 epoch, 공정 조건): Step 2 50% / Exp11 50% (**동률**)
   - 결론: subset에서는 동률, full에서는 Step 2 75.9% > Exp11 58.6%
   - 차기: full set에서 Exp11 역방향 평가 + path별 상호보완 검증
3. ~~어떤 feature가 성능을 만드는지 분석~~ → **완료 (2026-04-18, feature ablation)**

   | Feature | PM mean | PM std |
   |---|---:|---:|
   | BBox-only | 67.4% | ±9.8% |
   | **Image-only** | **75.6%** | **±0.8%** |
   | BBox+Image | 76.7% | ±1.3% |

   - **Image feature가 핵심 driver.** BBox grounding 결과(cx,cy,area)는 raw 16×16 image 대비 정보량이 낮음.
   - bbox 추가 기여는 +1.1%p — 노이즈 수준.
   - 기존 Step 1(68.4%)의 step 1 vs step 2 비교는 feature 차이뿐 아니라 MLP 용량 차이도 섞인 것이었음 → 이제 분리 완료.
   - 참고: [Feature Ablation 결과](./bbox_nav_feature_ablation/index.html)

4. ~~텍스트 instruction이 모델 예측에 실제로 기여하는지에 대한 **causal evidence 확보**~~
   - Exp11/Exp13 재실행으로 instruction 변경 시 logit/attention 차이 측정
   - Oracle test 정량 재현 (Exp12 LEFT% 수치)
5. ~~가능하면 closed-loop 평가로 연결~~ → **완료 (2026-04-18, Phase 1 offline replay)**

   | 모델 | 성공률 (9 ep) | mean FPE | mean TLD |
   |---|---:|---:|---:|
   | **Step 2 (BBox+Image MLP)** | **66.7%** (6/9) | 0.55m | 1.03 |
   | Exp11 (end-to-end policy) | 0.0% (0/9) | 1.45m | 1.03 |

   - Step 2가 closed-loop에서 Exp11을 압도. TLD는 둘 다 1.03으로 이동 거리는 유사하지만, Exp11은 방향 오류 누적으로 FPE가 2.6배 높음.
   - Phase 1 설계: FPE < 0.5m AND TLD ∈ [0.7, 1.5] 성공 기준. offline replay (원본 H5 이미지 기반).
   - 참고: [Closed-Loop 평가 결과](./closed_loop_eval/index.html)

---

## 7. 참고 문서

- [Exp14 Comparison](./bbox_nav_comparison.html)
- [Exp14 Step 2](./bbox_nav_step2/index.html)
- [Exp14 Step 2 Quick Repro](./bbox_nav_step2_repro/index.html)
- [V5 Dev Log](./devlog.html)
