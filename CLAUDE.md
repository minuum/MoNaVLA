# MoNaVLA — Claude Code 행동 규칙

## 핵심 원칙

**계획을 사용자가 직접 검토하고 승인하기 전까지 코드를 절대 작성하지 마라.**

---

## 작업 워크플로우 (5단계)

### 1. 코드 리서치
새 작업 시작 전 반드시 관련 코드를 깊이 읽고 이해한다.

```
- 관련 파일 전부 읽기
- 동작 방식 파악
- 기존 레이어/패턴/컨벤션 확인
- 완료 후 research.md에 상세 보고서 작성
```

**리서치 없이 코딩하면 생기는 문제:**
- 기존 레이어를 무시하는 함수 생성
- ORM/프레임워크 관례 무시
- 중복 API 엔드포인트 생성

### 2. 계획 (plan.md 작성)
리서치 완료 후 `plan.md`를 작성한다. 코드는 아직 작성하지 않는다.

기본 형식은 `docs/plans/STANDARD_PLAN_TEMPLATE.md`를 따른다.

plan.md에 포함할 내용:
- 접근 방식 상세 설명
- 실제 변경사항을 보여주는 코드 스니펫
- 수정될 파일 경로
- 트레이드오프 고려사항

### 3. 주석 달기 (사용자 검토 → 반복)
사용자가 plan.md를 검토하고 메모를 추가한다.

```
사용자 메모 추가 → "모든 메모를 반영하고 문서를 업데이트해. 아직 구현하지 마." → 계획 재작성 → 반복
```

메모의 역할: 가정 수정, 접근 방식 거부, 제약조건 추가, 도메인 지식 전달

**승인 전까지 구현 금지.**

### 4. 기계적 구현
사용자가 승인하면 구현한다.

구현 시 규칙:
- 작업/단계 완료 시 plan.md에서 완료 표시
- 모든 작업이 완료될 때까지 멈추지 않음
- `any` / `unknown` 타입 사용 금지 (TypeScript)
- typecheck를 지속적으로 실행해 새 문제 방지

### 5. 피드백
구현 후 사용자 피드백을 받아 방향 조정.

방향이 잘못됐다면:
- `git reset` 또는 `git revert`로 되돌리고 다시 시작
- 잘못된 접근을 조금씩 고쳐나가는 것보다 revert가 거의 항상 더 좋다

---

## 행동 규칙 요약

| 상황 | 행동 |
|:---|:---|
| 새 작업 시작 | 코드 전에 리서치 먼저 |
| 계획 수립 후 | 사용자 승인 전까지 구현 금지 |
| 방향이 틀렸을 때 | revert 후 재시작 (점진적 수정 지양) |
| 기술/패키지 선택 | 사용자가 결정, Claude는 제안만 |
| 구현 중 | plan.md 완료 표시하며 진행 |

---

## 4단계 방어 체계

각 단계가 막아주는 것:

- **리서치** → 무지한 변경(기존 레이어 무시, ORM 관례 위반, 중복 엔드포인트)을 막는다
- **계획** → 잘못된 변경(방향 오류, 범위 초과)을 막는다
- **주석 달기** → 사용자의 판단과 도메인 지식을 주입한다
- **기계적 구현** → 방해 없이 승인된 계획만 실행한다

> "코드를 잘 쓰게 만드는 것"이 아니라 **"뭘 써야 하는지를 확실하게 만드는 것"**

---

## 방향 조정 패턴 (5단계 피드백)

- 좋은 건 취하고 나머진 버리기
- 과감하게 쳐내기
- 건드리면 안 되는 선 긋기
- **기술/패키지 선택은 사용자가 한다** — Claude는 옵션 제시만

방향이 완전히 틀렸을 때:
```
git reset 또는 git revert → 범위를 좁혀서 재시작
```
잘못된 접근을 조금씩 고치는 것보다 revert가 거의 항상 더 좋다.

---

## 에이전트 진입점

새 세션/에이전트 시작 시 읽기 순서: **`docs/AGENT_ENTRYPOINT.md`** 참조.

---

## GitHub Pages 공개 문서 규칙

공개용 문서나 주요 진행 로그를 새로 만들면, **`docs/index.html` 첫 화면 Hero 버튼 영역**에도 반드시 진입 링크를 추가한다.

기본 위치:
- [docs/index.html](/home/billy/25-1kp/MoNaVLA/docs/index.html:137)

의도:
- GitHub Pages 첫 화면에서 바로 찾을 수 있어야 함
- 새 문서가 `docs/` 아래에만 묻히지 않도록 함
- 앞으로 공개 문서 추가는 “문서 생성 + 메인 Hero 링크 추가”를 한 세트로 취급

---

## Menemory 연동

세션 시작 시 `.menemory/core/master_memory.md`를 반드시 읽어라. 이 파일이 프로젝트의 장기 핵심 메모리다.

```bash
# 상태 확인
menemory status

# 장기 메모리 조회
menemory show
```

**규칙:**
- `.menemory/core/master_memory.md`에 기록할 내용이 생기면 사용자에게 제안한다 (직접 쓰지 않는다)
- Claude auto-memory (`~/.claude/projects/.../memory/`)와 menemory는 별개 시스템이다 — 중복 저장하지 마라
  - Claude memory: 사용자 프로필, 피드백, 작업 방식 선호도
  - Menemory core: 프로젝트 장기 목표, 아키텍처 원칙, 금지 규칙

---

## 프로젝트 컨텍스트

> **마지막 업데이트: 2026-04-18**

### 모델 현황

- **Backbone:** Kosmos-2 (frozen) + LoRA — `third_party/RoboVLMs/`는 수정하지 마라
- **현재 최선 end-to-end 모델:** V5 Exp11 — Google-robot pretrained + 8-class
  - 체크포인트: `runs/v5_nav/kosmos/mobile_vla_v5_exp11/2026-04-16/v5-exp11-google-robot-8cls/epoch_epoch=epoch=14-val_loss=val_loss=1.010.ckpt`
  - config: `configs/mobile_vla_v5_exp11_google_robot_8cls.json`
  - PM 58.6%, val_loss 1.010. closed-loop: **0% success** (FPE 1.45m 누적 오류)
- **현재 최선 decomposition 모델:** Exp14 Step 2 — BBox+Image MLP
  - PM 75.9% (5 seeds 76.6±1.6%). closed-loop: **66.7% success** (FPE 0.55m)
  - bbox_dataset.json: `docs/v5/bbox_nav_step1/bbox_dataset.json` (45 ep, 794 frames)
- **진행 중:** Exp16 — 전체 150 ep (center_straight 포함) 8-class 학습 중

### 실험 이력 (V5)

| 실험 | config | val_loss | PM | 특이사항 |
|------|--------|----------|----|---------|
| Exp01~03 | `exp01~03` | 1.784~2.270 | — | V4 기반, FORWARD collapse |
| Exp04 | `exp04_google_robot` | 0.776 | 0% | Google-robot backbone 첫 도입. val_loss 좋지만 PM 0% collapse |
| Exp09 | `exp09` | — | — | 8-class 시도, bias 잔존 |
| Exp10 | `exp10` | 0.012 | — | BBox grounding 학습 (IoU 0.87), free-gen transfer 34.4% |
| **Exp11** | `exp11_google_robot_8cls` | **1.010** | **58.6%** | **현재 end-to-end baseline. 8-class, Google-robot** |
| Exp12 | `exp12_action_instr` | — | — | instruction conditioning 시도, 폐기 (text 완전 무시 확인) |
| Exp13 | `exp13_instr_cond` | — | — | 설계 후 폐기 |
| Exp14 Step2 | MLP (bbox+image) | — | **75.9%** | **현재 best. decomposition 접근** |
| Exp15 | `exp15_head_only` | 1.553 | 37.5% | VLM 완전 frozen, head만 학습. text attention 0% 재확인 |
| Exp16 | `exp16_all_paths` | 학습 중 | — | 교수 프로토콜 Step 2 — center_straight 포함 150 ep |

### 핵심 발견 (2026-04-18 기준)

1. **Text attention = 0%**: Google-robot post-training이 이미 text 경로 붕괴시킴. 우리 LoRA 학습과 무관.
   - Exp15 head-only에서도 text=0% 재확인 → 모델 구조 기인
   - 측정 스크립트: `scripts/measure_attention.py`

2. **Image가 핵심, BBox는 보조**: feature ablation 결과
   - bbox_only: 67.4%±9.8% / image_only: 75.6%±0.8% / bbox+image: 76.7%±1.3%
   - BBox grounding(Pure Kosmos-2)의 cx,cy,area는 16×16 image 대비 정보량 낮음

3. **Closed-loop에서 decomposition 압도**: Step 2 66.7% vs Exp11 0%
   - TLD는 동일(1.03)이지만 Exp11은 방향 오류 누적 → FPE 2.6배
   - 스크립트: `scripts/sim/evaluate_closed_loop_v5.py`

### 데이터

- **V5 (현재):** `ROS_action/mobile_vla_dataset_v5/` — 150개 H5 에피소드
  - 구성: straight 3종 × 20 = 60개, non-straight 6종 × 15 = 90개
  - 포맷: `f['observations']['images']` (V4와 다름 — V4는 `f['images']`)
  - 액션 분포 (8-class 기준): FORWARD 71.4% (center_straight 제외시), 74.4% (전체)
- **V4 (구):** `ROS_action/basket_dataset_v2/` (528 H5 에피소드) — 현재 학습 미사용

### 액션 공간 (V5 8-class, Exp11+)

| Index | 이름 | 비고 |
|-------|------|------|
| 0 | STOP | 데이터 없음 — 에피소드 끝 프레임에 합성 |
| 1 | FORWARD | 71~74% 차지, FORWARD bias 주원인 |
| 2 | LEFT | strafe |
| 3 | RIGHT | strafe |
| 4 | FWD+LEFT | 대각선 |
| 5 | FWD+RIGHT | 대각선 |
| 6 | ROT_L | 제자리 회전 좌, ~0.8% |
| 7 | ROT_R | 제자리 회전 우, ~0.8% |

> ⚠️ 9-class 설정(inference_server.py)과 혼동 주의. V5 학습은 8-class. 서버의 class 매핑은 별개.
> ⚠️ Google-robot backbone으로 `generate()` 절대 호출 금지 — "Tin Tin Tin Roof..." 무한 반복.

### 교수님 지시 테스트 프로토콜 (3/27 미팅)

```
Step 1: 곡선만 학습 → 직선 이미지를 줘도 곡선으로 가는가?  ← Exp11 완료 (PM 58.6%)
Step 2: 50/50 비율 → 동작하는가?                           ← Exp16 학습 중
Step 3: 33/33/33 (left/straight/right) → 완전 동작?
실패 시: TICVLA / MobilityVLA 대안 검토
```

### VLM 텍스트 생성 능력

- **Pure HF Kosmos-2** (`.vlms/kosmos-2-patch14-224`): 텍스트 생성 정상, BBox grounding 가능
- **Google-robot** (`.vlms/google_robot_pretrain/kosmos_ph_google-robot-post-train.pt`): `generate()` 완전 망가짐 — 사용 금지
- Exp11/Exp15 모두 text attention = 0.000% (per-layer 측정 완료)

### 핵심 파일

- **학습:** `robovlm_nav/train.py` (positional arg: `python3 robovlm_nav/train.py configs/xxx.json`)
- **데이터셋:** `robovlm_nav/datasets/nav_h5_dataset_impl.py`
- **추론 서버:** `robovlm_nav/serve/inference_server.py`
- **PM 평가:** `scripts/test_v5_pm_dm.py`
- **Closed-loop 평가:** `scripts/sim/evaluate_closed_loop_v5.py` (--model exp11|step2)
- **Attention 분석:** `scripts/measure_attention.py`
- **Feature ablation:** `scripts/ablate_bbox_image_features.py`
- **문서:** `docs/v5/PROF_UPDATE_20260417_EXP14.md` — 교수님 업데이트 (전체 이력)
- **Pages:** `docs/index.html` — GitHub Pages 진입점 (Hero 버튼 있음)
