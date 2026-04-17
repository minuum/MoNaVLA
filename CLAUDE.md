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

> **마지막 업데이트: 2026-04-12**

### 모델 현황

- **Backbone:** Kosmos-2 (frozen) + LoRA — `third_party/RoboVLMs/`는 수정하지 마라
- **현재 최선 모델:** V5 Exp04 — Google-robot pretrained 기반, 6-class discrete
  - 체크포인트: `runs/v5_nav/kosmos/mobile_vla_v5_exp04/2026-04-11/v5-exp04-google-robot/epoch_epoch=epoch=14-val_loss=val_loss=0.776.ckpt`
  - config: `configs/mobile_vla_v5_exp04_google_robot.json`
  - val_loss 0.776 (Exp01~03 대비 압도적, Google-robot 기반이 핵심)
- **이전 참고 모델:** V4 Weighted Huber Regression (`runs/v4_nav/kosmos/mobile_vla_v4_regression_v2`) — 현재는 Exp04 기반으로 대체됨

### 실험 이력 (V5)

| 실험 | config | val_loss | 특이사항 |
|------|--------|----------|---------|
| Exp01 | `mobile_vla_v5_exp01_discrete.json` | 2.270 | 전체 데이터, V4 기반, FORWARD 100% |
| Exp02 | `mobile_vla_v5_exp02_no_straight.json` | 2.210 | 직선 제거, stratified split |
| Exp03 | `mobile_vla_v5_exp02_clip_norm.json` | 1.784 | CLIP Norm Loss 추가 |
| **Exp04** | `mobile_vla_v5_exp04_google_robot.json` | **0.776** | **Google-robot 기반, 현재 최선** |

### 데이터

- **V5 (현재):** `ROS_action/mobile_vla_dataset_v5/` — 150개 H5 에피소드
  - 구성: straight 3종 × 20 = 60개, non-straight 6종 × 15 = 90개 (center/left/right × left/right path)
  - 포맷: `f['observations']['images']` (V4와 다름 — V4는 `f['images']`)
  - 액션: 6-class discrete (STOP/FORWARD/LEFT/RIGHT/FWD+L/FWD+R)
- **V4 (구):** `ROS_action/basket_dataset_v2/` (528 H5 에피소드) — 현재 학습에 미사용

### 액션 공간 (V5 6-class)

| Index | 이름 | 키 | 비고 |
|-------|------|-----|------|
| 0 | STOP | — | |
| 1 | FORWARD | W | 데이터 44~75% 차지, FORWARD bias 주원인 |
| 2 | LEFT | A (strafe) | |
| 3 | RIGHT | D (strafe) | |
| 4 | FWD+LEFT | — | 대각선 |
| 5 | FWD+RIGHT | — | 대각선 |

> ⚠️ 9-class 설정(inference_server.py)과 혼동 주의. V5 학습은 6-class. 서버의 2번(ROTATE_LEFT/T키), 8번(ROTATE_RIGHT/R키)은 별개.

### VLM 텍스트 생성 능력 (2026-04-11 검증)

- **Pure HF Kosmos-2** (`.vlms/kosmos-2-patch14-224`): 텍스트 생성 정상, BBox grounding 가능
- **Google-robot** (`.vlms/google_robot_pretrain/kosmos_ph_google-robot-post-train.pt`): `image_to_text_projection` 오염 → `generate()` 완전 망가짐 ("Tin Tin Tin Roof..." 반복)
- **V4 LoRA** (`runs/v4_nav/.../last.ckpt`): base_layer 추출 시 텍스트 생성 부분 유지, 내용 부정확

### 교수님 지시 테스트 프로토콜 (3/27 미팅)

```
Step 1: 곡선만 학습 → 직선 이미지를 줘도 곡선으로 가는가?  ← 현재 여기
Step 2: 50/50 비율 → 동작하는가?
Step 3: 33/33/33 (left/straight/right) → 완전 동작?
실패 시: TICVLA / MobilityVLA 대안 검토
```

**현재 상태:** Exp04가 Step 1 조건(곡선만, Google 기반)을 충족하나 PM/DM 오프라인 테스트 미실행.

### 핵심 파일

- **학습:** `robovlm_nav/train.py`, `robovlm_nav/trainer/nav_trainer.py`
- **데이터셋:** `robovlm_nav/datasets/nav_h5_dataset_impl.py` — V4/V5 포맷 자동 감지, stratified_split, exclude_path_types 지원
- **추론 서버:** `robovlm_nav/serve/inference_server.py` — 3DOF (lx, ly, az), 9-class 매핑 수정됨
- **설정:** `configs/mobile_vla_v5_exp*.json`
- **분석 스크립트:** `scripts/test_v5_pm_dm.py`, `scripts/test_three_vlm_text_gen.py`, `scripts/run_v5_grounding.py`
- **문서:** `docs/situation_analysis_20260411.md` — 현황 분석 + TODO, `docs/vlm_text_gen_comparison.html` — VLM 3종 비교
