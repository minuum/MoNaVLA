# Plan: MoNaVLA — 교수님 반박 대응 전략
작성일: 2026-05-24 / 업데이트: 2026-05-27

---

## 반박 라운드 현황

```
[R1] 5/15: "basket을 본다는 증거가 없다"         → ✅ 완료 (5-Track)
[R2] 5/22: "val_acc 불충분, 진짜 객체 인식 보여라" → ⚠️ 부분 해결
[R3] 예상:  "basket 단일 데이터 → 일반화 불가"    → ❌ 미해결
```

### R1 완료 — 5-Track 증거

| Track | 방법 | 결과 | 의미 |
|-------|------|------|------|
| 1 | Attention 분석 | 4.4× basket 집중 | basket 영역에 시선 고정 |
| 2 | Frozen CLIP probe | 96.6% | 학습 전부터 basket 인코딩 |
| 3 | Masking ablation | center 100% flip | basket이 행동의 직접 원인 |
| 4 | Kosmos-2 caption | basket 지칭 가능 | VLM 인식 확인 |
| 5 | Stage 1 v2 contrastive | 98.1% (frame-level) | 위치 정렬 강화 |

### R2 부분 해결 — 현황

| 서브 반박 | 상태 | 현재 수치 |
|---------|------|---------|
| R2-1: val set → test set | ✅ CL로 대응 가능 | CL 96.67% |
| R2-2: LoRA 기여도 불명 | ⚠️ 논리 보강 필요 | +1.5%p (CL 8.7× 파이프라인) |
| R2-3: 다른 물체 → 다른 행동 | ❌ FAIL | 90% 동일 (basket=red ball=nothing) |
| R2-4: 텍스트로 목표 변경 | ❌ 구조적 불가 | 93.3% 프롬프트 무관 |
| R2-5: pretrain 객체 유지 | ⚠️ 역효과 | Stage2 LoRA 92.6%→80.0% |

**R2-3/R2-4 근본 원인:** 학습 데이터 150 에피소드 = 100% basket 단일 → visual만으로 예측 가능 → 텍스트 사용 동기 없음.

---

## 전략: 2트랙 병행

### 트랙 A — 단기 (2~3주): 현재 시스템으로 설득 극대화

| 작업 | 목표 |
|------|------|
| A-1 | CL 추가 테스트: 다양한 시작 위치 → 96.67% 재현 |
| A-2 | LoRA 기여 논리 보강: 좌/중/우 균등 정렬 시각화 |
| A-3 | "basket GoalNav"로 재정의 + 설득 자료 |
| A-4 | research_story.html CH14: 전략 재정의 페이지 |

### 트랙 B — 중기 (4~8주): Goal-Conditioned 학습으로 근본 해결

| 단계 | 작업 |
|------|------|
| B-1 | 다양한 물체 에피소드 수집 (basket+ball+chair 각 30개씩) |
| B-2 | `train_goal_conditioned.py` 설계 (Option C 기반) |
| B-3 | 객체 대체 테스트 재실행 → 90% → 40% 미만 목표 |
| B-4 | Catastrophic Forgetting 재검증 |

---

## 다음 미팅 보고 시나리오

```
슬라이드 1: R1 완료 — 5가지 독립 증거
슬라이드 2: R2-1 완료 — CL 96.67% = 독립 test 환경
슬라이드 3: R2-2 보완 — LoRA: 좌/중/우 97~100% 균등 정렬 특화
슬라이드 4: R2-3/R2-4 솔직 진단 — 데이터 단일화가 원인, 해결 계획 있음
슬라이드 5: 트랙 B — Goal-Conditioned 학습 계획
```

---

## 즉시 실행 순서

```
1. A-1: CL 추가 테스트 (eval_exp54_stage2_v2_closedloop.py)
2. A-4: CH14 research_story.html 작성
3. B-1: 데이터 수집 계획 수립 (남은 9개 + 추가 물체)
4. B-2: train_goal_conditioned.py 설계
```

---

## 기존 테스트 스크립트 현황 (완료)

계층별 테스트 구조:
| 계층 | 질문 | 스크립트 |
|------|------|---------|
| L0 | Kosmos-2가 basket을 grounding하는가? | `test_grounding_baseline.py` ✅ |
| L1+L2 | bbox 반전/제거 시 action이 바뀌는가? | `test_action_counterfactual.py` ✅ |
| L2 | text 경로가 사망했음을 직접 증명 | `test_tracking_prompt.py` ✅ |
| L3 | LoRA 후 pretrain 객체 여전히 인식되는가? | `test_catastrophic_forgetting.py` ✅ |

---

## 스크립트 1: `scripts/test_grounding_baseline.py` (L0)

Pure Kosmos-2 + Stage1 LoRA (exp53) 비교로 VLM grounding 능력 측정.
- IoU ≥ 0.3 기준 hit rate
- path_type별 grounding 성공률
- base vs LoRA 비교

실행: `.venv/bin/python3 scripts/test_grounding_baseline.py [--model base|lora|both] [--n-episodes N]`

---

## 스크립트 2: `scripts/test_action_counterfactual.py` (L1+L2) ← 핵심

Stage 2 v2 모델에서 bbox/visual 독립 조작 → 인과성 측정.

| 조건 | 변경 | 기대 |
|------|------|------|
| A | baseline | gt acc ≈ 92.6% |
| B | bbox=zeros | 방향 정보 손실 |
| C | bbox cx 반전 (1-cx) | action flip ≥ 70% → basket 추적 증거 |
| D | 반대 방향 episode visual 교체 | action 변화 → visual도 기여 |

실행: `.venv/bin/python3 scripts/test_action_counterfactual.py [--n-episodes N]`

---

## 스크립트 3: `scripts/test_tracking_prompt.py` (L2)

Stage 2 v2의 text path 사망을 수치로 증명.
- 4가지 프롬프트 → 동일한 action (text 무시)
- Kosmos-2 VLM은 "tracking basket" grounding 가능 여부 확인

실행: `.venv/bin/python3 scripts/test_tracking_prompt.py [--skip-vlm] [--n-episodes N]`

---

## 스크립트 4: `scripts/test_catastrophic_forgetting.py` (L3)

Stage1 LoRA가 basket을 학습한 후 pretrain 객체 (RT-1: orange, blue bowl, etc.) 여전히 grounding 가능한지.

실행: `.venv/bin/python3 scripts/test_catastrophic_forgetting.py [--use-synthetic] [--image-dir PATH]`

---

## 체크리스트

- [x] `scripts/test_action_counterfactual.py` ✅
- [x] `scripts/test_grounding_baseline.py` ✅
- [x] `scripts/test_tracking_prompt.py` ✅
- [x] `scripts/test_catastrophic_forgetting.py` ✅

---

# Plan: Exp54 — 교수님 반박 3-Track 검증 플랜
작성일: 2026-05-22  
(기존 2-Stage 구현 플랜은 하단 Appendix 참조)

---

# Plan: Exp49+ SODA 서버 전송 + 평가 플랜
작성일: 2026-05-22

## 배경

Exp49 이후 학습된 MLP / CLIP-LoRA 모델들을 SODA 서버(`soda@100.85.118.58`)에 전송하고  
offline PM + closed-loop 평가를 수행해 현재 최선 모델을 확정한다.

현재 SODA 배포: **Exp17** (primary, CL 11.1%) / **Exp18** (fallback, CL 11.1%)  
목표: Exp49+ 중 CL > 11.1%인 후보를 찾아 서버 교체 준비

---

## 전송 대상 모델 목록

| 모델 | 파일 경로 | 크기 | 특이사항 |
|------|----------|------|---------|
| exp49 | `runs/v5_nav/mlp/exp49/exp49_mlp.pt` | ~2.7MB | vision_feat(1024) + bbox(32) |
| exp50 | `runs/v5_nav/mlp/exp50/exp50_mlp.pt` | ~4.8MB | vision_feat(1024) + bbox(32) |
| exp51 | `runs/v5_nav/mlp/exp51/exp51_mlp.pt` | ~2.8MB | vision_feat(1024) + bbox(32) |
| exp52 | `runs/v5_nav/mlp/exp52/exp52_mlp.pt` | ~4.9MB | lang_vis_feat(2048) + bbox(32) |
| exp53 | `runs/v5_nav/mlp/exp53/` (dir) | ~2.8MB | CLIP LoRA adapter + action head |
| exp54 stage1_v2 | `runs/v5_nav/mlp/exp54/stage1_v2/stage1_v2_projs.pt` | ~3MB | FrozenCLIP + image_proj |
| exp54 stage2 v1 | `runs/v5_nav/mlp/exp54/stage2/stage2_mlp.pt` | ~2.8MB | LoRA backbone 필요 |
| exp54 stage2 v2 | `runs/v5_nav/mlp/exp54/stage2_v2/stage2_v2_mlp.pt` | 학습 중 | stage1_v2 완료 후 전송 |

---

## 의존 데이터 파일 (함께 전송)

| 파일/디렉토리 | 크기 | 용도 |
|-------------|------|------|
| `docs/v5/bbox_nav_exp46/vision_features.npz` | ~6.7MB | exp49/50/51 CL 평가용 pre-extracted feature |
| `docs/v5/bbox_nav_exp46/bbox_dataset_full.json` | 포함 | frame metadata |
| `docs/v5/bbox_nav_exp52/lang_vis_features.npz` | ~13MB | exp52 전용 |
| `docs/v5/bbox_nav_exp52/lang_vis_features_index.json` | 포함 | |
| `scripts/eval_exp54_stage2.py` | — | exp54 stage2 v1 PM eval |
| `scripts/eval_exp54_stage2_v2.py` | — | exp54 stage2 v2 PM eval |
| `scripts/eval_exp54_stage2_v2_closedloop.py` | — | exp54 stage2 v2 CL eval |

> ⚠️ `.vlms/kosmos-2-patch14-224` 은 SODA에 이미 있다고 가정.  
> 없으면 `soda:~/.vlms/kosmos-2-patch14-224` 경로 확인 후 별도 전송 필요.

---

## Step 1: 사전 확인 (minum 머신에서)

```bash
# stage2_v2 학습 완료 여부 확인
cat logs/exp54_stage2_v2.log | tail -20
ls -la runs/v5_nav/mlp/exp54/stage2_v2/

# SODA 서버 접속 확인
ssh soda@100.85.118.58 "ls ~/MoNaVLA/runs/v5_nav/mlp/ 2>/dev/null || echo 'mlp dir not found'"
ssh soda@100.85.118.58 "ls ~/MoNaVLA/.vlms/ 2>/dev/null"
```

---

## Step 2: 모델 전송

```bash
# 1) MLP 모델 가중치 전송 (exp49~54)
rsync -avz --progress \
  runs/v5_nav/mlp/exp49/ \
  runs/v5_nav/mlp/exp50/ \
  runs/v5_nav/mlp/exp51/ \
  runs/v5_nav/mlp/exp52/ \
  runs/v5_nav/mlp/exp53/ \
  runs/v5_nav/mlp/exp54/ \
  soda@100.85.118.58:~/MoNaVLA/runs/v5_nav/mlp/

# 2) 의존 feature 파일 전송
rsync -avz --progress \
  docs/v5/bbox_nav_exp46/vision_features.npz \
  docs/v5/bbox_nav_exp46/bbox_dataset_full.json \
  soda@100.85.118.58:~/MoNaVLA/docs/v5/bbox_nav_exp46/

rsync -avz --progress \
  docs/v5/bbox_nav_exp52/lang_vis_features.npz \
  docs/v5/bbox_nav_exp52/lang_vis_features_index.json \
  soda@100.85.118.58:~/MoNaVLA/docs/v5/bbox_nav_exp52/

# 3) 평가 스크립트 전송 (diff만)
rsync -avz --progress \
  scripts/eval_exp54_stage2.py \
  scripts/eval_exp54_stage2_v2.py \
  scripts/eval_exp54_stage2_v2_closedloop.py \
  scripts/sim/evaluate_closed_loop_v5.py \
  soda@100.85.118.58:~/MoNaVLA/scripts/
```

---

## Step 3: SODA에서 평가 실행

### 3-A. exp49/50/51/52 closed-loop (기존 eval 스크립트 지원)

```bash
ssh soda@100.85.118.58
cd ~/MoNaVLA

# exp49
python3 scripts/sim/evaluate_closed_loop_v5.py --model exp49

# exp50
python3 scripts/sim/evaluate_closed_loop_v5.py --model exp50

# exp51
python3 scripts/sim/evaluate_closed_loop_v5.py --model exp51

# exp52
python3 scripts/sim/evaluate_closed_loop_v5.py --model exp52
```

### 3-B. exp54 stage2 v2 PM 평가

```bash
.venv/bin/python3 scripts/eval_exp54_stage2_v2.py
```

### 3-C. exp54 stage2 v2 closed-loop 평가

```bash
.venv/bin/python3 scripts/eval_exp54_stage2_v2_closedloop.py
```

---

## Step 4: 결과 수집 + 비교

목표 비교 테이블:

| 모델 | PM | CL success | FPE | 비고 |
|------|-----|-----------|-----|------|
| Exp17 (현재 배포) | — | 11.1% | — | baseline |
| Exp25 (best 기록) | 52.4% | 55.6% | 0.382 | minum 기준 |
| **exp49** | TBD | TBD | TBD | |
| **exp50** | TBD | TBD | TBD | |
| **exp51** | TBD | TBD | TBD | |
| **exp52** | TBD | TBD | TBD | |
| **exp54 s2v2** | TBD | TBD | TBD | stage2_v2 완료 후 |

**배포 교체 기준**: CL success ≥ 33% (Exp17 대비 3배 이상)

---

## 체크리스트

- [ ] stage2_v2 학습 완료 확인
- [ ] SODA ssh 접속 및 환경 확인 (.vlms 경로, .venv 환경)
- [ ] rsync — 모델 가중치 전송
- [ ] rsync — feature 파일 전송
- [ ] rsync — 평가 스크립트 전송
- [ ] exp49 CL 평가
- [ ] exp50 CL 평가
- [ ] exp51 CL 평가
- [ ] exp52 CL 평가
- [ ] exp54 stage2 v2 PM 평가
- [ ] exp54 stage2 v2 CL 평가
- [ ] 결과 테이블 작성 + 배포 교체 후보 결정

---

---

## 핵심 질문

> "모델이 basket을 보는 건가, 복도 패턴을 외운 건가?"

현재 상태: Stage 1 v2 98.1%, 실험 A/B v2 완료.  
남은 약점: right 방향 0%p 격차, left/right 어텐션 측정 불가, 전체 3.5%p 격차.

**이 플랜의 목표**: 약점을 보완하는 3개 추가 실험으로 교수님 반박 논리를 완성한다.

---

## Track 1: Kosmos-2 텍스트 생성 실험 ← 지금 할 것

**목적**: "CLIP 인코더가 basket을 물리적으로 인식하는가?" 직접 확인  
**방법**:  
- `bbox_dataset_frame_level.json`의 consistent=True 프레임에서 방향별 샘플 추출  
- Pure HF Kosmos-2 (`<grounding>` 모드 + caption 모드)로 텍스트 생성  
- basket 관련 키워드(basket/box/container/bin) 언급 여부 측정  
- 방향(left/center/right) × 구간(early/mid/late) 9조합 분석

**파일**: `scripts/exp54_kosmos_caption_probe.py`  
**출력**:
```
[left/early]  caption: "a hallway with a gray container on the left"  → ✅ basket keyword
[left/mid  ]  caption: "a corridor"                                    → ❌ no keyword
[center/late] caption: "a gray basket in the center of the hallway"   → ✅ basket keyword
...
---
keyword hit율: left=X/3  center=X/3  right=X/3
```

**결과 해석**:
- keyword hit 50%↑ → "CLIP이 이미 basket을 텍스트로 인식한다" ✅
- keyword hit 낮음 → "CLIP의 텍스트 생성은 믿을 수 없지만, CLIP feature는 별개" (Option 2로)

**프롬프트 전략** (2가지 동시 실행):
```python
PROMPTS = {
    "grounding": "<grounding>An image of a gray basket",   # bbox + entity 추출
    "caption":   "An image of",                            # 자유 caption
}
```

**코드 스니펫**:
```python
# grounding 모드 (기존 test_grounding_comparison.py 방식 재사용)
PROMPT_GROUNDING = "<grounding>An image of a gray basket"
gen = model.generate(pixel_values=pv, input_ids=inputs["input_ids"], ...)
caption, entities = processor.post_process_generation(raw)

# caption 모드
PROMPT_CAPTION = "An image of"
# 동일하게 generate, 자유 텍스트 출력
```

**수정 파일**: 신규 생성 (`scripts/exp54_kosmos_caption_probe.py`)

---

## Track 2: Zero-shot Linear Probe ← Track 1 결과 보고 결정

**목적**: Stage 1 학습 전 frozen Kosmos-2 CLIP feature가 이미 basket 위치를 인코딩하는가  
**방법**:
- frozen Kosmos-2 비전 인코더 (LoRA 없음, 학습 없음)
- `bbox_dataset_frame_level.json` consistent 프레임 feature 추출
- logistic regression (sklearn) → left/center/right 분류
- 5-fold CV

**파일**: `scripts/exp54_zeroshot_linear_probe.py`  
**기대값**: 70%↑이면 "CLIP은 이미 basket 위치를 안다"

**결과 해석**:
- 80%↑ → "Stage 1은 새 능력을 만드는 게 아니라 기존 능력을 꺼내는 것" (강한 주장)
- 60~80% → "부분적으로 인코딩됨, Stage 1이 강화하는 구조"
- 60%↓ → "Stage 1이 실제로 능력을 만들어줌" (이것도 의미 있는 결과)

---

## Track 3: Basket Masking Ablation ← Track 1, 2 결과 보고 결정

**목적**: basket 영역을 지웠을 때 Stage 1 v2 예측이 바뀌는가? (인과적 증거)  
**방법**:
- cx_det, cy_det, area_det로 basket 위치 특정
- 해당 영역을 gray (128,128,128)로 masking
- Stage 1 v2에 원본 vs 마스킹 이미지 입력
- confidence 변화량 측정

**파일**: `scripts/exp54_basket_mask_ablation.py`  
**기대값**: confidence 30%↓ → "basket을 보고 있었다"

---

## 실행 순서

```
[완료] Stage 1 v2 학습 (val_acc 98.1%)
[완료] 실험 A v2 (early→late +3.5%p)
[완료] 실험 B v2 (center 어텐션 4.4×)
[완료] Track 1: Kosmos-2 caption — "trash can"/"air conditioner" (basket vocab 불일치)
[완료] Track 2: Zero-shot linear probe — 96.6% ✅
[완료] Track 3: Masking ablation — center 100% flip ✅
[완료] 시각화 이미지 + before/after 갤러리
[진행 중] Stage 2 v2 재학습 (PID 1333599, logs/exp54_stage2_v2.log)
[대기] closed-loop 평가 (Stage 2 v2 완료 후)
[대기] 신규 21개 트라젝토리 수집 (로봇 서버 팀)
```

---

## 완성 시 교수님 보고 구조

```
1. "CLIP이 basket을 텍스트로 인식한다"    ← Track 1
2. "Frozen feature에서도 위치 정보 있다"  ← Track 2
3. "Basket 가리면 예측이 흔들린다"        ← Track 3
4. "Late 프레임에서 정확도 더 높다"       ← 실험 A v2
5. "Basket 근접 시 어텐션 집중도 증가"    ← 실험 B v2 (center)
```

5개 증거가 모두 같은 방향을 가리키면 → "basket을 본다"를 방어할 수 있음.

---

## Appendix: 기존 2-Stage 구현 플랜 (2026-05-19)


---

## 1. 배경 및 동기

### Exp53의 실패 원인 (진단 완료)

```
grounding 탐지율:    0/6 (0%)  — Kosmos-2가 gray basket을 못 찾음
bbox_dataset 탐지:  99.1%     — 실제로는 쓰레기통/에어컨 bbox를 대리 사용
any_entity 비율:    4/6       — 엉뚱한 객체 bbox가 basket 위치 추정값으로 쓰임
entity_match(진짜): 1/6 (17%) — "gray box"로 1번만 실제 인식
```

**근본 문제:** CLIP LoRA가 basket을 인식하도록 학습된 적이 없다.  
Exp53은 액션 분류(8-class)를 end-to-end로 학습했기 때문에  
"basket이 어디 있나"를 이미지에서 직접 보는 능력이 생기지 않았다.

---

## 2. 핵심 과학적 질문 (교수님)

> **"박스를 본 건가, 텍스트를 외운 건가?"**

이를 답하려면:
- Stage 1에서 **텍스트-이미지 정렬**로 CLIP이 basket을 인식하도록 명시적 학습
- Stage 1만 단독으로 테스트 → "gray basket on the left" 텍스트가 left 이미지와 정렬되는가?
- 그게 된 다음에야 Stage 2 액션 학습 의미 있음

---

## 3. 아키텍처

### Stage 1: Vision-Language Alignment (Contrastive)

```
이미지 → CLIP LoRA(layers 16-23) → vis_feat(1024) → proj(256)
텍스트 → Kosmos-2 LM(frozen)   → text_feat(2048) → proj(256)
                                       ↓
                               InfoNCE Contrastive Loss
```

- **학습**: CLIP LoRA만 업데이트 (LM frozen)
- **목표**: vis_proj("basket_left_image") ≈ text_proj("gray basket on the left")
- **검증**: val set에서 image→text retrieval 정확도 (3-class: left/center/right)

### Stage 2: Navigation Action Head

```
Stage1 CLIP LoRA (frozen) → vis_feat(1024)
                                  +
bbox_history(8×4=32)              +
                                  ↓
                              MLP (Exp49 구조) → 8-class action
```

- **학습**: MLP만 업데이트 (CLIP LoRA frozen)
- **d_in**: 32 + 1024 = 1056 (goal 3-dim 제거 — Stage 1에서 이미 학습됨)

---

## 4. 데이터

### Stage 1 텍스트 레이블 생성

기존 H5 150 에피소드에서 자동 생성:

```python
PATH_TO_TEXT = {
    "left_straight":  "The gray basket is on the left side of the image",
    "left_left":      "The gray basket is on the left side of the image",
    "left_right":     "The gray basket is on the left side of the image",
    "center_straight":"The gray basket is in the center of the image",
    "center_left":    "The gray basket is in the center of the image",
    "center_right":   "The gray basket is in the center of the image",
    "right_straight": "The gray basket is on the right side of the image",
    "right_left":     "The gray basket is on the right side of the image",
    "right_right":    "The gray basket is on the right side of the image",
}
```

- 총 ~2626 프레임 → (image, text) 쌍
- Train/Val: 120/30 에피소드 (random_state=42, Exp53과 동일)

**한계 인지:**  
`path_type`은 에피소드 전체 방향이지 프레임별 basket 위치가 아니다.  
초반 프레임은 basket이 멀리 있어 레이블 노이즈 있음.  
→ 에피소드 후반 70% 프레임만 사용하는 옵션 추가 (후순위)

---

## 5. 단계별 실행 계획

### Phase 1: Stage 1 학습 스크립트 작성 ✅ (2026-05-19 완료)
- [x] `scripts/train_exp54_stage1_contrastive.py`
  - `model.text_model` last token (output_hidden_states=True → hidden_states[-1][:, -1, :])
  - image_proj: Linear(1024, 256), text_proj: Linear(2048, 256)
  - 3개 고정 텍스트 앵커 + anchor 기반 3-class CE loss (temperature=0.07)
  - 저장: `runs/v5_nav/mlp/exp54/stage1/`
- [x] `configs/exp54_stage1_contrastive.json`

### Phase 2: Stage 1 학습 실행 + 검증 ✅ (스크립트 작성 완료)
- [ ] 학습 실행: `python3 scripts/train_exp54_stage1_contrastive.py`
- [x] 검증 스크립트: `scripts/test_exp54_stage1_retrieval.py`
  - val 이미지 → 3개 앵커 cosine sim 비교, 3-class retrieval accuracy
  - 혼동 행렬 출력
  - **기준: 80% 이상이면 basket 인식 성공으로 판정**

### Phase 3: Stage 2 학습 스크립트 작성 ✅ (2026-05-19 완료)
- [x] `scripts/train_exp54_stage2_action.py`
  - Stage 1 LoRA 로드 (완전 frozen)
  - MLP: d_in=1056 (bbox_32 + vis_1024, goal 제거)
  - 저장: `runs/v5_nav/mlp/exp54/stage2/stage2_mlp.pt`
- [x] `configs/exp54_stage2_action.json`

### Phase 4: Stage 2 학습 실행 + PM 평가
- [ ] 학습 실행 (epochs: 300)
- [ ] PM 평가 (`scripts/test_v5_pm_dm.py` 또는 내부 val_acc)
- [ ] 비교 기준: Exp53 94.7%, Exp49 96.4%

### Phase 5: 교수님 보고 자료
- [ ] Stage 1 retrieval 결과 표
- [ ] Stage 2 PM / 방향별 정확도 표
- [ ] "박스를 본다" 근거: Stage 1 통과 여부

---

## 6. 코드 변경 범위

| 파일 | 내용 |
|------|------|
| `scripts/train_exp54_stage1_contrastive.py` | 신규 — Stage 1 contrastive 학습 |
| `scripts/test_exp54_stage1_retrieval.py` | 신규 — Stage 1 검증 (retrieval accuracy) |
| `scripts/train_exp54_stage2_action.py` | 신규 — Stage 2 action head 학습 |
| `configs/exp54_stage1_contrastive.json` | 신규 |
| `configs/exp54_stage2_action.json` | 신규 |

기존 파일 수정 없음. Exp53 코드 재사용 (CLIPLoRABackbone 클래스).

---

## 7. Exp53과의 차이

| 항목 | Exp53 | Exp54 (이 플랜) |
|------|-------|----------------|
| 학습 구조 | End-to-end (1 stage) | 2 stage 분리 |
| basket 인식 | 학습 안 됨 | Stage 1에서 명시적 학습 |
| 텍스트 역할 | 없음 | Stage 1 contrastive 정렬에 직접 사용 |
| 검증 가능성 | "박스를 보나?" 불가 | Stage 1 단독 검증으로 답 가능 |
| goal 벡터 | fake bbox (cx,cy,area) | 제거 — Stage 1 feat으로 대체 |

---

## 8. 완료 기준

- [ ] Stage 1 retrieval accuracy ≥ 80% (val, 3-class)
- [ ] Stage 2 PM ≥ Exp53 수준 (94%+)
- [ ] "방향어 없이도 성공" 테스트에서 Stage 1 기반 근거 제시 가능

---

## 결정 사항

**text_feat 추출: 옵션 A 결정 (2026-05-19)**
- Kosmos-2 LM (`model.model.text_model`) last token hidden state 사용
- 3개 고정 text anchor 사전 계산 후 frozen
- image_proj(1024→256) + text_proj(LM_dim→256) 학습
- loss: anchor 기반 3-class cosine similarity classification (temperature=0.07)

**Stage 1 레이블 노이즈:**  
path_type 기반 레이블이 프레임 단위로 정확하지 않음.  
→ 에피소드 중반-후반 프레임만 사용하는 옵션은 Phase 2 결과 보고 결정.

---

## Option C: Pure Kosmos-2 End-to-End VLA (2026-05-26 추가)

### 배경 — 왜 Option C인가?

| 비교 | Exp11 (Google-robot) | Exp54 (분해 MLP) | **Option C (Pure Kosmos-2)** |
|------|---------------------|-----------------|------------------------------|
| 백본 | Kosmos-2 + Google-robot 가중치 | frozen CLIP + MLP head | Pure HF Kosmos-2 (손상 없음) |
| text 경로 | 구조적 사망 (attn=0%) | 포트 없음 (D_IN=288) | **살아있음** |
| grounding | 불가 (generate 망가짐) | 외부 color thresh | **native 토큰** |
| action 출력 | MLP logit → argmax | MLP logit → argmax | **generate() → 텍스트 토큰** |
| 교수님 요청 | "다른 물체 이상한 행동" 불가 | "다른 물체 이상한 행동" 불가 | **prompt로 목표 바꾸면 행동 바뀜** |

**핵심 차이**: text 경로가 살아있으므로 프롬프트로 목표 객체를 바꾸면 모델 행동이 달라진다.
→ 교수님 핵심 요구사항("다른 걸 집어넣으면 이상한 행동") 실제 증명 가능.

---

### 다른 VLA와의 비교

| VLA | 모델 크기 | 액션 포맷 | 학습 데이터 | 차이점 vs Option C |
|-----|--------|---------|-----------|------------------|
| **RT-2** (Google, 2023) | PaLM-E 55B | 256 bins/axis (연속) | RT-1 130K ep | 55배 크고, 조작용 (7-DOF 팔) |
| **OpenVLA** (Stanford, 2024) | LLaMA-7B | 256 bins/axis | OXE 970K ep | 4배 크고, 범용 로봇 조작 |
| **RoboVLMs** (우리 Exp11) | Kosmos-2 1.6B | 8-class text | oxe+rt1 | Google-robot weights로 text 사망 |
| **Option C** | Kosmos-2 1.6B | 8-class text | 우리 150 ep | text 살아있음, 복도 내비게이션 |

**RT-2/OpenVLA가 generate()를 쓰는 이유**: 연속 액션 공간(팔 관절 각도)을 토큰으로 양자화해야 해서.  
**우리가 더 단순한 이유**: 8개 이산 클래스라 텍스트 이름("FORWARD" 등)을 그대로 쓸 수 있음.

---

### 아키텍처 설계

```
입력:
  image (224×224)  +  text prompt
    ↓                     ↓
  vision encoder      text tokenizer
    ↓                     ↓
  ┌─────────────────────────────┐
  │   Kosmos-2 Transformer      │  ← LoRA on layers 16-23
  │   (cross-attention 포함)    │
  └─────────────────────────────┘
              ↓
         generate()
              ↓
    "FORWARD" / "LEFT" / "RIGHT" / ...
              ↓
       class index → robot action
```

**LoRA 대상:**
- vision encoder layers 16-23 (upper half, domain adaptation)
- text decoder layers 16-23 (action token generation)
- 전체 파라미터: ~1.6B → LoRA trainable: ~8M (0.5%)

---

### 프롬프트 전략 (3가지 비교 실험)

**P1 — Blind (basket만 언급):**
```
<image> The robot must follow the gray basket in the corridor.
Navigation action (FORWARD/LEFT/RIGHT/FWD+L/FWD+R/ROT_L/ROT_R/STOP):
```

**P2 — BBox-assisted (색상 감지 결과 주입):**
```
<image> Gray basket detected at position ({cx:.2f}, {cy:.2f}), area {area:.3f}.
Navigation action (FORWARD/LEFT/RIGHT/FWD+L/FWD+R/ROT_L/ROT_R/STOP):
```

**P3 — Grounding-augmented (VLM 자체 그라운딩 후 액션):**
```
Step 1: <grounding><phrase>gray basket</phrase>  → bbox 추출
Step 2: "Basket is at ({cx}, {cy}). Navigate:"  → action 예측
(두 단계 sequential inference)
```

**추천:** P2로 시작 (가장 직접적, 기존 bbox 파이프라인 재활용 가능)

---

### 학습 파이프라인

```python
# 데이터 포맷
{
  "image": PIL.Image,                    # H5에서 로드
  "prompt": "... Navigation action:",    # P1/P2/P3 중 택1
  "target": "FORWARD",                  # gt_class → CLASS_NAMES[gt_class]
}

# 손실 함수
# target 토큰에만 cross-entropy (prompt는 마스킹)
loss = CE(logits[:, prompt_len:, :], target_ids)

# 추론
out = model.generate(prompt, max_new_tokens=5)
pred_text = out.strip().split()[0]       # "FORWARD" 추출
pred_class = CLASS_NAMES.index(pred_text)
```

---

### 구현 파일 계획

| 파일 | 역할 | 상태 |
|------|------|------|
| `scripts/test_kosmos2_raw.py` | Pure Kosmos-2 다양한 테스트 모음 | [ ] 구현 예정 |
| `scripts/train_optionC_lora.py` | Pure Kosmos-2 LoRA fine-tuning | [ ] 구현 예정 |
| `scripts/eval_optionC.py` | generate() 기반 평가 | [ ] 구현 예정 |
| `configs/exp_optionC_p2.json` | P2 프롬프트 설정 | [ ] 구현 예정 |

---

### 검증 계획 (승인 후 순서)

1. **Sanity** (학습 전): `test_kosmos2_raw.py --mode zeroshot` → zero-shot acc 측정
2. **학습**: `train_optionC_lora.py --prompt p2 --epochs 100`
3. **기본 평가**: `eval_optionC.py` → val acc (vs Exp54 92.6%)
4. **핵심 테스트**: 
   - "basket" → 정상 액션
   - "red ball" → 다른 행동 or confused output
   - 빈 프롬프트 → 랜덤 or 멈춤
5. **CL 평가**: `eval_exp54_stage2_v2_closedloop.py` 포맷 재사용

---

### 예상 리스크

| 리스크 | 가능성 | 대응 |
|--------|--------|------|
| 150 ep로 학습 부족 | 중간 | data augment (flip, crop) |
| generate()가 액션 외 텍스트 출력 | 높음 | temperature=0, max_new_tokens=3 |
| grounding LoRA와 충돌 | 낮음 | 레이어 분리 |
| 학습 속도 (Jetson GB10) | 중간 | gradient checkpointing |

---

**승인 대기 항목:**
- [ ] 프롬프트 전략 선택 (P1/P2/P3 중 어떤 걸로 시작?)
- [ ] LoRA rank 설정 (r=8? r=16?)
- [ ] 학습 에폭 (100? 200?)
- [ ] 기존 Stage1 image_proj 재사용 여부 (재사용 시 수렴 빠름)
