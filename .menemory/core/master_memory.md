# Master Core Memory

이 파일은 Menemory 프롬프트에 항상 포함되는 핵심 메모리입니다.

**마지막 업데이트: 2026-05-01**

---

## 프로젝트 장기 목표

교수님 테스트 프로토콜 3단계 완전 통과:
- Step 1: 곡선만 학습 → 직선 이미지를 줘도 곡선으로 가는가? ✅ (Exp11, PM 58.6%)
- Step 2: 50/50 비율 → 동작하는가? ❌ (Exp16 완전 collapse, Exp25 55.6% CL로 우회)
- Step 3: 33/33/33 (left/straight/right) 전방향 자율 내비게이션 ⬜
- 최종: 실로봇에서 자율 경로 추종 (실패 시 TICVLA / MobilityVLA 대안 검토)

---

## 아키텍처 원칙

- Backbone: Kosmos-2 (frozen) + LoRA — `third_party/RoboVLMs/` 절대 수정 금지
- Google-robot pretrained backbone: `kosmos_ph_google-robot-post-train.pt`
- Pure HF Kosmos-2: `.vlms/kosmos-2-patch14-224` — text generation 정상, grounding 가능
- 액션 공간: V5 **8-class** discrete (STOP/FWD/LEFT/RIGHT/FWD+L/FWD+R/ROT_L/ROT_R)
- 데이터: `ROS_action/mobile_vla_dataset_v5/` — 150개 H5 에피소드
  - straight 3종 × 20 = 60개 / non-straight 6종 × 15 = 90개
- V4 `basket_dataset_v2/` (528 ep)는 현재 학습 미사용

---

## 현재 최선 모델 (2026-04-30 기준)

### End-to-end (practical baseline)
- **Exp25** — balanced objective, Pure HF Kosmos-2
  - closed-loop success: **55.6%**, PM: 52.38%, FPE: 0.382, TLD: 0.936
  - ckpt: `runs/v5_nav/kosmos/mobile_vla_v5_exp25/2026-04-22/v5-exp25-step3-balanced-objective/epoch_epoch=epoch=02-val_loss=val_loss=10.117.ckpt`
  - config: `configs/mobile_vla_v5_exp25_step3_balanced_objective.json`

### Decomposition (research baseline — 로봇 서버 미연결)
- **Exp14 Step 2 / Exp19** — BBox+Image MLP
  - PM: 75.9~76.6%, closed-loop: **66.7%**, FPE: 0.55m
  - 스크립트: `scripts/test_v5_bbox_nav_exp19_proxy.py`
  - bbox cache: `docs/v5/bbox_nav_step1/bbox_dataset.json`

### 진행 중 학습
- **Exp39** — Exp25 identical + last-4 LoRA (`lora_decoder_layers=4`)
  - config: `configs/mobile_vla_v5_exp39_exp25_last4_lora.json`
  - 목적: 과적합 방지 (전체 24층 LoRA → 끝 4층만, ~1/6 파라미터)
  - 로컬 GPU OOM으로 다른 서버에서 실행 예정
  - 학습 명령: `python3 robovlm_nav/train.py configs/mobile_vla_v5_exp39_exp25_last4_lora.json`
  - 비교 기준: Exp25 (CL 55.6%, PM 52.4%)

### 로봇 서버 현재 배포
- Primary end-to-end: **Exp17** (CL 11.1%)
- Fallback: **Exp18** (CL 11.1%)
- 서버: `soda@100.85.118.58 ~/MoNaVLA`
- API: `robovlm_nav/serve/inference_server.py`

---

## 핵심 발견 (확정된 사실)

1. **Text attention = 0%**: Google-robot post-training이 text 경로 완전 붕괴
   - Pure HF Kosmos-2: text 22.7% / image 77.3% (정상)
   - Google-robot 학습 후: text 0.000% / image 91.7% (붕괴)
   - LoRA/head-only 모두 복구 불가 — backbone 기인
   - 측정: `scripts/measure_attention.py`

2. **Image가 핵심, BBox는 보조**
   - bbox_only: 67.4%±9.8% / image_only: 75.6%±0.8% / bbox+image: 76.7%±1.3%
   - Pure Kosmos-2 grounding의 cx,cy,area < raw 16×16 image 정보량

3. **Shortcut collapse 미해결**
   - Exp37 (left_left 30ep overfit): train-PM 35%, 전 프레임을 LEFT로 예측
   - 데이터 제약/class weight만으로 해결 안 됨 — 구조적 문제

4. **Pure HF grounding 오인식**
   - gray basket을 "trash can", "air conditioner" 등으로 잘못 명명
   - coarse 방향은 맞음 (seed_coarse_agreement=1.0), 명시 인식은 33%
   - 증거: `docs/v5/RECOGNITION_PROOF_RESULT_20260428.md`

5. **Offline PM vs Closed-loop 괴리**
   - Exp26: PM 70.2%, CL 0% (offline 강함 ≠ rollout 강함)
   - PM 높아도 누적 방향 오류 → rollout 실패 가능

---

## 실험 이력 요약 (V5 전체)

| 실험 | 특이사항 | PM | CL |
|------|---------|----|----|
| Exp01~03 | V4 기반, FORWARD collapse | — | — |
| Exp04 | Google-robot 첫 도입, val 0.776 | 0% | — |
| Exp10 | BBox grounding (IoU 0.87) | — | — |
| Exp11 | Google-robot 8-class baseline | 58.6% | 0% |
| Exp12~13 | instruction cond 시도, 폐기 | — | — |
| Exp14 Step2 | BBox+Image MLP decomposition | 75.9% | 66.7% |
| Exp15 | head-only ablation | 37.5% | — |
| Exp16 | all-path 150ep, center_straight 포함 | 0% | — |
| Exp17 | step3 balanced (로봇 서버 primary) | — | 11.1% |
| Exp18 | VLA text fusion (로봇 서버 fallback) | — | 11.1% |
| Exp19 | BBox proxy MLP, Exp14 기반 | 76.6% | 55.6% |
| Exp21~24 | Pure HF controlled ablation | — | — |
| **Exp25** | **현재 practical baseline** | **52.4%** | **55.6%** |
| Exp26 | direct224, offline 강/rollout 약 | 70.2% | 0% |
| Exp27 | letterbox224 ablation | 15.5% | 33.3% |
| Exp28 | grounding aux + turn boost | 38.1% | 0% |
| Exp29~31 | 5ep short ablation (loss mixing) | 14~21% | — |
| Exp32~36 | Pure HF last-4 LoRA, left-family | val 6.5~7.5 | 미평가 |
| Exp37 | left_left 30ep overfit | 35%(collapse) | — |
| Exp38 | all-path head-only 20ep sanity | 미평가 | — |
| **Exp39** | **Exp25 + last-4 LoRA** | **학습 예정** | — |

---

## 미해결 / 다음 단계

1. **Exp31, Exp35, Exp36, Exp38 PM/rollout 평가 미완**
2. **Exp32~36 val_loss=6.5~7.5 — 버그 아님 (2026-05-01 확인)**
   - arm_action [4,10]은 raw sequence (window_size+fwd_next-1), get_labels()가 정상 chunking
   - 고손실 원인: class_weights 스케일(ROT_L/R=50배) + 5ep 미수렴
3. **Exp39 학습 대기** — 로컬 GPU OOM, 다른 서버에서 실행 필요
4. Shortcut collapse 근본 해결책 미확보
4. Gray basket prompted grounding 재실행 필요 (현재 free-gen은 오인식)
5. BBox proxy (Exp19)를 inference_server.py에 연결하는 작업 미완

---

## 금지 규칙

- `third_party/RoboVLMs/` 수정 금지
- inference_server.py의 9-class 공간과 학습의 8-class 공간 혼용 금지
- Google-robot backbone으로 `generate()` 호출 금지 (텍스트 생성 망가짐 — "Tin Tin..." 반복)
- `master_memory.md`는 Claude가 사용자 요청 없이 직접 수정하지 않음

---

## 메모리 시스템 통합 조회

**참조**:
- `.menemory/core/memory_systems_integration.md`
- `docs/MEMORY_SYNC_MAP.md`
- `.agent/skills/memory-sync-hub/SKILL.md`

세 개의 메모리 시스템 (Claude Code, Codex IDE, AntiGravity-Server)을 통합 관리하는 맵.
- Claude memory: 프로젝트 격리, MEMORY.md 인덱스
- Codex memory: 로컬 IDE, SQLite 로그, history
- AntiGravity: 시스템 런타임, 서버 로그

세션 시작 시 `docs/AGENT_ENTRYPOINT.md` → `docs/MEMORY_SYNC_MAP.md` →
`MEMORY.md` → `memory_systems_integration.md` 순으로 읽는다.

주의:
- Antigravity 복구 원문은 `~/.gemini/antigravity/brain/<uuid>/` 에 있다.
- `conversations/*.pb` 는 인덱스일 뿐이다.
