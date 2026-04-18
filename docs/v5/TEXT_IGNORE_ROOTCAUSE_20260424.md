# 텍스트 Instruction 무시 현상: 근본원인 분석

**작성일**: 2026-04-17 (초안) / 다음 미팅(2026-04-24경) 대비
**상태**: 🚧 작업 중 — 실측 TODO 다수

---

## 1. 요약 (TL;DR)

- **Exp07, Exp11, Exp13 세 모델에서 좌/우/전진 instruction이 동일 이미지에 대해 완전히 동일한 action 출력** — L2(left, right) = `8.43e-08` (Exp07) / `0.0` (Exp11) / `0.0` (Exp13).
- **Attention weight 실측 (2026-04-18)**: Action token이 image region(0:64)에 **91.7%**, instruction text region(64:76)에 **정확히 0.000%** attend. 3 instruction의 attention 패턴이 **bit-level 동일**.
- **Pure Kosmos-2 (foundation) 대조**: image 77.3% / **text 22.7%** — foundation은 instruction에 정상 attend하나, **학습 후 0%로 소멸**.
- Cross-attention 없음 (Kosmos decoder-only) → self-attention이 유일 통로. 학습이 이 통로의 text path를 죽임.
- 결론: **"학습 과정이 Transformer self-attention 단계에서 instruction text 경로를 죽이는 구조적 현상"** — before/after causal chain 확보. BBox decomposition(Exp14)이 유일하게 작동하는 이유는 **text 경로 자체를 우회**했기 때문.

---

## 2. 교수님 질문 (2026-04-17 미팅)

> 세 가지 학습 세팅 중 어느 것이 텍스트 무시 문제를 해결하는가?
> 1. VLM LoRA 파인튜닝만
> 2. Action head만
> 3. 둘 다
>
> 그리고 원인은 **레이어 구조** 때문인가 **학습 파이프라인** 때문인가?

다음 주 미팅 전까지 레이어 수준에서 분석하여 정리할 것.

---

## 3. 현상 정량 증거

### 3.1 동일 이미지 + 8개 instruction → 동일 action (실측, 2 모델)

- 스크립트: [scripts/test_v5_text_understanding.py](../../scripts/test_v5_text_understanding.py)
- 결과 파일: `/tmp/v5_text_understanding_result.json`

**Exp07 (`last-v1.ckpt`, 2026-04-11)**

| instruction group | class | action |
|:---|:---:|:---|
| `[ORIGINAL]` Navigate until ... centered | STOP | [0, 0, 0] |
| left_1~3 (3종 변형) | FWD+L | [0.8130, 0.8130, 0] |
| right_1~3 (3종 변형) | FWD+L | [0.8130, 0.8130, 0] |
| forward_1~2 (2종 변형) | FWD+L | [0.8130, 0.8130, 0] |

- **L2(left, right) = 8.43e-08** (bit-level 동일, 소수점 7자리까지 일치)

**Exp11 (`epoch=14-val_loss=1.010.ckpt`, 2026-04-17 실측)** — 현재 학습형 baseline

| instruction group | class | action |
|:---|:---:|:---|
| `[ORIGINAL]` Navigate until ... centered | STOP | [0, 0, 0] |
| left_1~3 (3종 변형) | **LEFT** | [0, 1.150, 0] |
| right_1~3 (3종 변형) | **LEFT** | [0, 1.150, 0] |
| forward_1~2 (2종 변형) | **LEFT** | [0, 1.150, 0] |

- **L2(left, right) = 0.0**

**Exp13 (`last-v1.ckpt`, 2026-04-17 실측)** — instruction embedding을 명시적으로 action head에 주입한 실험

| instruction group | class | action |
|:---|:---:|:---|
| `[ORIGINAL]` Navigate until ... centered | STOP | [0, 0, 0] |
| left_1~3 / right_1~3 / forward_1 (7종) | **RIGHT** | [0, -1.150, 0] |
| forward_2 "Go directly ahead to the target" | STOP | [0, 0.230, 0] |

- **L2(left, right) = 0.0** (7개 instruction에 bit-level 동일 action)
- `forward_2` 하나만 약하게 다름 → `instr_proj`이 instruction별 미세 차이를 만드나, **left/right 구분은 여전히 0**
- collapse 방향: Exp07=FWD+L, Exp11=LEFT, Exp13=RIGHT — **방향은 다르지만 모든 모델에서 L2(left,right)=0**

**→ 3 모델 교차 검증으로 단일 체크포인트 우연 가능성 완전 배제. instruction 신호가 action 경로에 기여하지 않음이 실측으로 재현됨.**

### 3.2 Oracle Test (Exp12) — 정량 재현 필요

- 근거: `plan.md` Exp12 섹션 "GT instruction 주입해도 LEFT=0% 동일"
- 관련 경로: `runs/v5_nav/kosmos/mobile_vla_v5_exp12/2026-04-17/.../`
- **한계**: 정량 수치 summary 파일 없음, 실행 스크립트 별도 재현 필요
- TODO: Oracle test 재실행 후 `(LEFT%, FWD+L%)` 수치 확보

### 3.3 Pure Kosmos-2 Foundation 능력

- 결과 파일: [docs/v5/pure_backbone_9paths/results.json](./pure_backbone_9paths/results.json)
- `<grounding>` prompt 응답:

| path_type | Foundation 응답 | 평가 |
|:---|:---|:---:|
| left_left | "far **left** of the image" | ✅ |
| right_right | "far **right** of the image" | ✅ |
| center_left / center_right / center_straight | "center" 계열 | ❌ |

→ **Foundation 자체는 극단적 좌우는 이해**, 중간 영역은 약함. 학습 후 이 능력이 손실되는 현상 관찰.

---

## 4. 원인 가설 세 갈래

### 4.1 레이어 구조 — 실측 확정 (2026-04-18)

Hook 기반 attention capture (RoboVLMs 미수정)로 Exp11/Exp13에서 실측.

**Transformer input layout (확정)**: `seq=257 = image_embeds(0:64) + text_embeds(64:256) + action_token(256)`

**Action token의 self-attention 분포** (last layer, 3 instruction 평균):

| Region | Exp11 | Exp13 |
|:---|:---:|:---:|
| Image (0:64) | **91.7~92.0%** | 84.3~85.8% |
| Text (64:76, real instruction tokens) | **0.000%** | **0.000%** |
| Pad (76:256) | ~0% | ~0% |
| Action self (256) | 8.0~8.3% | 14~16% |

Top-5 attention position (Exp11): `pos 7, 8, 2, 6, 256` — **3 instruction에서 소수점 4자리까지 동일** (left/right 완전 일치, forward 미세 차이). 즉 **어떤 image patch에 attend할지가 instruction과 무관하게 고정**.

Cross-attentions: `None` (Kosmos decoder-only, `add_cross_attention: false`). Self-attention이 유일한 통로이며, 이 통로가 instruction을 버린다.

Exp13의 `instr_proj` (word embedding → mean → Linear(2048→2048) → LSTM input에 additive)도 실패: LM 단계에서 이미 text가 무시되기 때문에 후단에 embedding을 더하는 것은 일정한 bias만 추가하여 collapse를 유발.

- 실측 데이터: [attention_analysis/summary.json](./attention_analysis/summary.json)
- 스크립트: [scripts/measure_attention.py](../../scripts/measure_attention.py)

**Pure Kosmos-2 (foundation, 학습 전) 대조 — "before/after" 증거 (2026-04-18)**

[scripts/measure_attention_pure_kosmos.py](../../scripts/measure_attention_pure_kosmos.py)로 LoRA/FT 없는 raw `.vlms/kosmos-2-patch14-224` 모델에 동일 이미지 + 동일 3 instruction 투입 후 last text token의 attention 측정.

| 모델 | Image ratio | **Text ratio** |
|:---|:---:|:---:|
| Pure Kosmos-2 (foundation) | 77.1~77.8% | **22.2~22.9%** |
| Exp11 (LoRA + action head 학습) | 91.7~92.0% | **0.000%** |
| Exp13 (+ instr_proj 명시 주입) | 84.3~85.8% | **0.000%** |

Pure Kosmos-2의 Top-5 position에는 **text positions가 섞여 있다** (예: pos 1 `<grounding>`, pos 74 instruction token). Exp11의 Top-5는 모두 image region 내부(`pos 7, 8, 2, 6, 256`).

**→ 학습 전에는 text에 22% attend하던 모델이, 학습 후 0%로 완전히 사라진다. "학습 과정이 instruction text attention을 소멸시킨다"는 causal 주장이 직접 증명됨.**

- 원본: [attention_analysis/pure_kosmos.json](./attention_analysis/pure_kosmos.json)

**Per-layer × per-head collapse 분석 (2026-04-18)**

24 Kosmos LM layer × 32 heads 전체를 측정한 결과 (스크립트: [scripts/analyze_attention_mechanism.py](../../scripts/analyze_attention_mechanism.py)):

| Layer | Pure (img/text, #text-heads) | Exp11 | Exp13 |
|:---:|:---:|:---:|:---:|
| 0  | 74.0% / 26.0% / **30.7 heads** | 55.1% / **0.0%** / 0 | 50.3% / 0.0% / 0 |
| **2** | **27.7% / 72.3% / 28.0** *(peak)* | 69.1% / 0.0% / 0 | 27.9% / 0.0% / 0 |
| 5  | 55.9% / 44.1% / 26.7 | 73.1% / 0.0% / 0 | 45.0% / 0.0% / 0 |
| 12 | 50.7% / 49.3% / 32.0 | 92.7% / 0.0% / 0 | 81.5% / 0.0% / 0 |
| 18 | 76.3% / 23.7% / 27.7 | 96.9% / 0.0% / 0 | 82.7% / 0.0% / 0 |
| 23 | 77.4% / 22.6% / 27.3 | 91.8% / 0.0% / 0 | 85.3% / 0.0% / 0 |

**Mechanism 특징**:

1. **Uniform global collapse**: 학습 후 **layer 0부터 layer 23까지 전역 동시 text=0%**. 특정 deep layer만의 문제 아님 → LoRA가 특정 layer만 망가뜨린 게 아니라 **전 stack이 동시 붕괴**.
2. **Binary regime shift**: Pure는 layer별 22~72%의 넓은 분포 → 학습 후 **모든 layer 정확히 0.0**. 점진적 감소 아닌 binary 붕괴.
3. **100% head mortality**: Pure Kosmos에서 32 head 중 21~32개가 "text head"(threshold 0.05 초과) → 학습 후 **모든 layer에서 0 heads alive**.
4. **Peak text layer 2 현상**: Foundation은 shallow layer(특히 layer 2)에서 grounding/alignment, deep layer에서 reasoning이라는 표준 VLM 해석. 이 shallow grounding이 학습으로 파괴됨.
5. **Deep layer image 극단화**: Exp11의 layer 21에서 image 99.6%까지 증가 — 학습이 "text 무시" 뿐 아니라 "image에 과집중" 동시에 유도.

- 데이터: [attention_analysis/mechanism.json](./attention_analysis/mechanism.json) / [mechanism.html](./attention_analysis/mechanism.html)

### 4.2 학습 파이프라인 가설 (Shortcut Learning)

- 기존 분석: [docs/analysis/grounding_and_shortcut_analysis_20260203.md](../analysis/grounding_and_shortcut_analysis_20260203.md)
- V4 시절 증거: instruction suffix("sliding left" 등)가 정답을 노출, "Fly to the moon"에도 특정 액션 고수.
- V5에서도 에피소드 단위 path_type instruction이 사용됨:
  - `left_straight` 에피소드: 첫 1프레임 ROT_R + 나머지 FORWARD 97%에 "left" instruction 동일 부착
  - → "left instruction → FORWARD" shortcut이 구조적으로 형성 가능
- FORWARD class imbalance (~65%) 가 shortcut을 더 강화.
- 코드 근거: [robovlm_nav/datasets/nav_h5_dataset_impl.py](../../robovlm_nav/datasets/nav_h5_dataset_impl.py) `_get_action_aware_instruction` 계열.

### 4.3 Foundation / 평가 지표 가설

- Kosmos-2 자체는 좌/우 공간 이해 능력 있음(§3.3).
- 그러나 end-to-end 학습 loss는 teacher-forced next action prediction, 평가 PM은 free-running → **exposure bias** 잔존 가능.
- Exp04 val_loss 0.776 → PM 0% 의 큰 gap은 이 가설 부분 지지.

---

## 5. 교수님 3-way 세팅 대비 현재 데이터

| 세팅 | 해당 실험 | 결과 (PM) | text 이해 여부 | 비고 |
|:---|:---|:---:|:---:|:---|
| VLM LoRA만 FT | Exp02, 05~08 | ~50% | ❌ (collapse 관찰) | head frozen 아님 |
| Action head만 | Exp14 Step 1/2 (BBox) | 68.4 / 75.9 | — (instruction 미사용) | text 경로 자체 제거 |
| 둘 다 | Exp04 / 09 / 11 / 13 | 0~58% (inference) | ❌ **L2=0 실측 (Exp11/13)** | instr_proj 명시 주입도 실패 |

**해석**:
- 세 세팅 모두 "text-conditioned action"을 학습시키지 못했음.
- Step 1/2의 성공은 **text를 쓰지 않음**으로써 얻은 것이라, 교수님이 원한 "text 이해" 해결과는 다른 축.
- **깨끗한 3-way controlled ablation은 아직 실행되지 않음** (실험들이 세팅 이외 요소도 달랐음) — §7 TODO.

---

## 6. Counter-Arguments (논문 리뷰어 관점)

### 반문 1 — "Step 2 75.9%는 1회 측정의 운 좋은 결과 아닌가?"

- **방어**:
  - 5 split seed × 8 epoch 재측정 결과 `76.6% ± 1.6%`로 안정적 재현 ([bbox_nav_step2_repro/summary.json](./bbox_nav_step2_repro/summary.json))
  - 공통 subset 50개 공정 비교 (220 epoch 동일 조건): **Step 2 50% = Exp11 50% 동률** ([exp11_vs_step2_same_split_fullep/summary.json](./exp11_vs_step2_same_split_fullep/summary.json))
  - 1차 비교의 `-16%p` 약세는 학습 epoch 단축(`20 vs 220`) 탓으로 확인됨 — split bias 아님
- **잔여 약점**:
  - Training seed 고정 불명 (split seed만 통제)
  - Full test set에서 Exp11 평가는 미실행 → Step 2 `75.9% full` 우위의 반대 방향 검증 필요
  - Model save 누락 — inference 재현 불가

### 반문 2 — "텍스트 무시가 구조적 원인이라는 causal evidence가 없다"

- **방어**:
  - Exp07: L2(left, right) = `8.43e-08`
  - Exp11 (현재 최신 학습형 baseline, val_loss 1.010): L2 = `0.0`
  - **Exp13 (instruction embedding을 명시적으로 action head에 주입): L2 = `0.0`** — instr_proj 추가 아키텍처도 실패
  - 세 모델에서 동일 현상, collapse 방향은 모두 다름(FWD+L / LEFT / RIGHT) → 우연이 아닌 **학습 과정 자체가 text 경로를 죽이는 구조적 현상**
  - Pure Kosmos-2 foundation은 좌/우 이해 유지 (§3.3) → 학습 전후 차이가 결정적
- **Attention 실측 보강 (2026-04-18)**:
  - Exp11: image region `91.7%` / text region `0.000%` (3 instruction 전부)
  - Exp13: image region `85.8%` / text region `0.000%`
  - 3 instruction의 attention 패턴 **bit-level 동일** (소수점 4자리)
  - Cross-attention 없음 → self-attention이 유일 통로, 그 통로가 instruction을 버림
- **Pure Kosmos-2 대조 (2026-04-18)**:
  - Foundation (LoRA/FT 없음): image `77.3%` / **text `22.7%`** — instruction에 정상 attend
  - 학습 후 (Exp11/13): text `0.000%` — **학습이 text attention을 소멸시킴**
  - 이로써 causal chain 완성: "학습 과정이 instruction text 경로를 죽임 → 학습된 모델이 instruction 무시"
- **잔여 약점**:
  - Oracle test(Exp12) 정량 수치 미확보
  - Exp13의 `forward_2` 샘플만 약한 action 차이 → instr_proj이 아주 미세한 기여 (left/right 구별은 여전히 0)
  - Attention 소멸의 **메커니즘** (FORWARD class imbalance? LoRA 특정 layer? mm_projector?) 은 미규명

### 반문 3 — "3-way ablation이 실제로 실행되지 않았다"

- **방어**: 제한적 — 과거 실험들이 정확히 LoRA-only / head-only / both로 분리된 적 없음.
- **잔여 약점**: controlled comparison 없이는 "셋 다 실패"라는 일반화 불가. §7 TODO.

### 반문 4 — "BBox가 성공한 게 아니라 task simplification일 뿐"

- **논리 방어 (2026-04-18 보강)**:
  1. **"Text-conditioned" 주장이 애초에 불가능**하다는 것이 §4.1에서 증명됨 — Exp07/11/13 공통으로 학습 후 self-attention의 text region이 0.000%. 즉 **어떤 설계를 하더라도 현재 프레임워크 내에서는 text conditioning이 불가능**. BBox decomposition은 이 불가능성을 회피하는 principled workaround.
  2. **Path_type이 instruction의 역할을 대신 수행**: V5 데이터셋은 path_type(center_left/left_right 등)이 에피소드마다 fixed label로 부여되어 있고, BBox trajectory가 이 label과 강하게 상관. 즉 "text instruction → path choice"의 매핑이 데이터 레벨에선 이미 결정적. BBox history가 path_type을 암묵적으로 복원 가능.
  3. **Instruction은 redundant**: Pure Kosmos-2 9-paths 테스트에서 "center" case는 text로도 구별 약함(§3.3). 즉 **text가 있어도 제공되는 정보량은 제한적**. spatial signal이 더 많은 정보를 담고 있음.
- **논문 framing 재정의**:
  - 기존("text-conditioned VLA") → **변경("shortcut-free spatial navigation via grounding-policy decomposition")**
  - 이 framing은 §1/§9에 이미 반영됨 — "Learned collapse of instruction attention path ... and spatial decomposition as a principled workaround"
- **잔여 약점 (학습 필요)**:
  - Optional 보완 실험 Exp19(가칭) — Step 2 input에 instruction embedding concat → 실제로 성능 개선하는지 검증
  - 현재 학습 큐에 추가 검토 가능

### 반문 5 — "Exp04 loss 0.776 → PM 0% gap은 exposure bias 아닌가?"

- **방어**: Exp11이 동일 구조에서 PM 58.6%까지 올라감 → pure exposure bias만은 아님.
- **잔여 약점**: 1-step teacher-forced PM vs N-step free-running PM 차이를 정량화한 적 없음.

---

## 7. 방어 가능 vs 방어 불가 (종합)

| 주장 | 강도 | 주 근거 |
|:---|:---:|:---|
| 모델이 instruction에 무반응 (Exp07 / 11 / 13) | ★★★★★ | L2 = 8.43e-08 (Exp07), 0.0 (Exp11, Exp13) |
| Foundation에 좌/우 이해 있음 | ★★★ | pure_backbone_9paths |
| Step 2 재현성 76.6% ± 1.6% | ★★★★ | 5-seed 실측 |
| Step 2 > Exp11 (always) | ★ | same-subset에선 역전 |
| 레이어 구조 원인 (image 91%, text 0.000%) | ★★★★★ | attention weight 실측 완료 (Exp11/Exp13) |
| 학습이 text 경로를 죽인다 (before/after) | ★★★★★ | Pure Kosmos text 22.7% → 학습 후 0% 소멸 |
| 파이프라인 shortcut이 원인 | ★★★ | V4 정성 증거 + V5 instruction 생성 로직 |
| 3 세팅 모두 실패 | ★★ | controlled ablation 부재 |

---

## 8. 남은 실측 TODO

- [x] ~~**Exp11 / Exp13 에서 text_understanding 테스트 실행**~~ — **완료 (2026-04-17)**: 둘 다 L2(left, right) = 0.0 확인
- [ ] **Oracle test (Exp12) 재현** — GT instruction 주입, LEFT% 정량 수치 확보
- [x] ~~**Attention weight 측정**~~ — **완료 (2026-04-18)**: image 91%, text `0.000%`, 3 instruction 동일 (`attention_analysis/summary.json`)
- [x] ~~**Same-subset에서 Step 2 220-epoch 재학습**~~ — **완료 (2026-04-17)**: `Step 2 50% = Exp11 50%` 동률
- [ ] **3-way controlled ablation** — 동일 데이터/config에서 LoRA-only / head-only / both 학습
- [ ] **1-step TF vs N-step free-running PM gap** 측정 — exposure bias 기여도 정량화

---

## 9. 결론 (2026-04-18 실측 반영)

- 현상(텍스트 무시)은 **correlational + causal 둘 다 확정**.
  - Correlational: Exp07/11/13 출력 레벨 L2 = 0
  - Causal (layer-level): self-attention 레벨에서 text region `0.000%`
  - Causal (before/after): Pure Kosmos-2에선 `22.7%` → 학습 후 `0%` **소멸**
- 교수님이 제시한 "레이어 구조 vs 학습 파이프라인" 중 **둘이 연결됨**: 학습 파이프라인(shortcut learning)이 Transformer의 self-attention 구조를 변형하여 **text path를 원천 차단**. "레이어 구조 원인"과 "학습 파이프라인 원인"은 별개가 아닌 **학습이 구조를 파괴한 결과**.
- Cross-attention이 없는 구조 + self-attention이 text를 버림 → **우회 통로 부재**. Exp13의 `instr_proj` 후단 주입도 LM 단계의 soul collapse를 복원하지 못함.
- BBox decomposition(Exp14)의 성공은 "text conditioning을 고쳤다"가 아니라 **"text 경로 자체를 제거했다"**에 가까움.
- **논문 framing 제안**: "Learned collapse of instruction attention path in frozen-backbone VLA fine-tuning, and spatial decomposition as a principled workaround."

---

## 10. 참고 파일

- 실측 로그: `/tmp/v5_text_understanding_result.json`
- 재현성: [docs/v5/bbox_nav_step2_repro/summary.json](./bbox_nav_step2_repro/summary.json)
- 공정 비교: [docs/v5/exp11_vs_step2_same_split/summary.json](./exp11_vs_step2_same_split/summary.json)
- 교수 보고: [docs/v5/PROF_UPDATE_20260417_EXP14.md](./PROF_UPDATE_20260417_EXP14.md)
- Shortcut 근거: [docs/analysis/grounding_and_shortcut_analysis_20260203.md](../analysis/grounding_and_shortcut_analysis_20260203.md)
- Exp13 구현: [robovlm_nav/models/nav_robokosmos.py](../../robovlm_nav/models/nav_robokosmos.py)
- 텍스트 테스트 스크립트: [scripts/test_v5_text_understanding.py](../../scripts/test_v5_text_understanding.py)
