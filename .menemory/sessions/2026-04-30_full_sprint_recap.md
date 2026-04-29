# MoNaVLA Full Sprint Recap — 2026-04-30

이 문서는 2026-04-16 ~ 2026-04-30 기간의 전체 실험/분석/배포 진행 상황을 담은
단일 진입 파일이다. 다른 서버/에이전트가 git pull 후 이 파일 하나만 읽으면
현재까지의 모든 맥락을 복구할 수 있도록 설계되었다.

---

## 1. 현재 브랜치 및 최신 커밋

```
브랜치: inference-integration (main에 merge 완료)
최신 커밋: 1e540390 docs+data: Apr28 sprint recap
주요 코드 변경: main 브랜치까지 push 완료 (2026-04-30)
```

---

## 2. 실험 전체 타임라인

### Phase A: End-to-end Google-robot baseline (Apr16~18)

**Exp11** — Google-robot + 8-class, 현재 end-to-end 역대 최선
- val_loss=1.010, PM=58.6%, closed-loop=**0%** (FPE 1.45m)
- `exclude_path_types: ["center_straight"]` → 130 ep 학습
- eval 버그 3개 수정 (t=-1/t=0 불일치, window_size 하드코딩, GT parse 오류)

**Exp12** — per-frame instruction 정렬 시도 → Oracle test에서 GT instruction 줘도 LEFT=0% → 폐기

**Exp13** — action head에 instruction embedding additive conditioning
- word embedding mean pool → Linear(2048→2048) → LSTM input에 additive
- PM=15%, FWD+L collapse → word embedding mean으로는 instruction 구별 불가 → 폐기

**Exp14 (Step 2)** — BBox + Image MLP decomposition
- Pure HF Kosmos-2 grounding → bbox(cx,cy,w,h) + 16×16 grayscale image → MLP → action
- PM=75.9% (5 seeds: 76.6±1.6%), closed-loop=**66.7%** (FPE 0.55m)
- Step 2가 Exp11 closed-loop 대비 압도적 (66.7% vs 0%)

**Exp15** — head-only ablation (VLM fully frozen)
- PM=37.5%, text attention=**0.000%** 재확인 → LoRA 탓이 아님, Google-robot backbone 기인 확정

**Feature ablation (Exp14 후속)**
- bbox_only: 67.4%±9.8% / image_only: 75.6%±0.8% / bbox+image: 76.7%±1.3%
- image가 핵심, bbox는 +1.1%p (노이즈 수준)

**Closed-loop sim (Phase 1)**
- FPE: Step2 0.55m vs Exp11 1.45m, TLD ≈ 1.03 (동일)
- 방향 오류 누적으로 Exp11 완전 실패, Step2 6/9 성공

---

### Phase B: Text attention 분석 (Apr17~18)

- monkey-patch로 output_attentions=True 주입 (RoboVLMs 수정 0)
- 토큰 레이아웃: image(0:64) + text(64:256) + action(256), seq=257
- **Pure HF Kosmos-2**: image 77.3% / text **22.7%** — 정상
- **Exp11 (학습 후)**: image 91.7% / text **0.000%** — 붕괴
- **Exp13 (학습 후)**: image 85.8% / text **0.000%** — 구조 수정도 무효
- **Exp15 (head-only)**: image 94.4% / text **0.000%** — LoRA 탓 아님 확정
- 결론: Google-robot post-training이 text attention 경로 붕괴시킴

---

### Phase C: Exp16~19 (교수 프로토콜 Step2 시도, BBox proxy) (Apr18~22)

**Exp16** — center_straight 포함 전체 150ep
- FORWARD weight=0.4 적용
- 결과: PM=0% — FWD+L/FWD+R collapse. center_straight 추가가 직접 원인

**Exp17** — step3 balanced (현재 로봇 서버 primary)
- closed-loop 11.1%, 로봇 서버 배포 중 (`soda@100.85.118.58`)

**Exp18** — VLA text fusion (로봇 서버 fallback)
- closed-loop 11.1%, Exp17과 동률

**Exp19** — BBox proxy (Exp14 Step2 기반 + 추가 튜닝)
- PM 76.6%, closed-loop 55.6%
- 연구 스크립트 상태 (`scripts/test_v5_bbox_nav_exp19_proxy.py`)
- inference_server.py API **미연결** — 다음 작업 필요

---

### Phase D: Pure HF ablation + objective 실험 (Apr21~24)

**Exp21~24** — Pure HF Kosmos-2 head-only / objective 변형
- val_loss 수준: 2~10 범위, 평가 대부분 미완

**Exp25** — balanced objective, **현재 practical baseline**
- closed-loop **55.6%**, PM 52.38%, FPE 0.382, TLD 0.936
- ckpt: `runs/.../mobile_vla_v5_exp25/2026-04-22/v5-exp25-step3-balanced-objective/epoch=02-val_loss=10.117.ckpt`
- config: `configs/mobile_vla_v5_exp25_step3_balanced_objective.json`

**Exp26** — direct224 전처리
- PM=70.2% (offline 최강), closed-loop=0.0% → rollout 반례

**Exp27** — letterbox224 전처리
- PM=15.5%, closed-loop=33.3% → Exp25 대비 전반 열세

**Exp28** — grounding aux loss + turn-family oversampling
- PM=38.1%, closed-loop=0.0% — aux 연결 됐지만 practical improvement 없음

**Exp29~31** — 5ep short ablation
- Exp29 (coarse-only): PM 21.4%, bbox IoU 0.000
- Exp30 (bbox+coarse): PM 14.3%, bbox IoU 0.000
- Exp31 (learned loss mixing): **학습 완료, PM/rollout 평가 미완**
  - ckpt: `runs/.../mobile_vla_v5_exp31/2026-04-24/.../last.ckpt`

---

### Phase E: Pure HF last-4 LoRA + overfit 실험 (Apr24~28)

**Exp32~36** — Pure HF Kosmos-2, last-4 decoder + LoRA, left-family 50ep
- val_loss: 6.5~7.5 (높음)
- arm_action shape: [4, **10**] → num_classes 불일치 의심 (8이어야 함)
- Trainer.fit stopped 미완료 — 학습 중단 또는 early 종료
- **PM 평가 전혀 없음**

> ⚠️ Exp32~36은 val_loss 스케일이 Exp25~31과 다름 (6~10 vs 1~2).
> `num_classes=10` 가능성 있음. 실행 전 config parent chain 재확인 필요.

**Exp37** — left_left 에피소드만 30ep overfit
- best ckpt: epoch=24, val_loss=1.080
- PM eval (train set): **35%**, 전 프레임 LEFT 예측 (collapse)
- confusion: FORWARD(43)→LEFT, LEFT(36)→LEFT, FWD+L(24)→LEFT
- 의미: 데이터 제약 없어도 구조적 collapse → shortcut 근본 미해결

**Exp38** — all-path head-only 20ep sanity check
- Pure HF Kosmos-2, no class weights, fwd_pred_next_n=1
- best ckpt: epoch=14, val_loss=1.438
- **PM 평가 미완**

---

## 3. 인식 능력 검증 (2026-04-28)

`scripts/analysis/inspect_vlm_grounding_initial18.py`로 9 path × 2 초기 프레임(18 frames) 평가

- seed_coarse_agreement = 1.0 — basket 방향 위치는 대략 맞음
- seed_detection_agreement = 0.333 — 실제 basket으로 인식은 33%
- 모델이 감지한 객체: "trash can", "air conditioner", "wall", "window"
- basket을 "basket"으로 부른 경우: **0/18**

결론: "위치는 보고 있지만 이름을 모른다" — prompted grounding(Exp10 IoU 0.87)과 대조됨

---

## 4. 로봇 서버 배포 현황

```
서버: soda@100.85.118.58 ~/MoNaVLA
sync 스크립트: scripts/sync/push_v5_top3_candidates_to_robot_server.sh
```

| 모델 | 역할 | 상태 |
|------|------|------|
| Exp17 | end-to-end primary | 배포 중 |
| Exp18 | end-to-end fallback | 배포 대기 |
| Exp19 (BBox proxy) | 연구 스크립트 | inference_server.py 미연결 |

로봇 서버 top3 문서: `docs/v5/robot_server_top3_candidates_20260423.md`

---

## 5. 다음에 해야 할 것 (우선순위 순)

1. **Exp38 PM 평가** — val_loss 1.438, sanity check 결과 확인
   ```bash
   python3 scripts/test_v5_pm_dm.py \
     --config configs/mobile_vla_v5_exp38_allpath_head_only_20ep.json \
     --ckpt runs/v5_nav/kosmos/mobile_vla_v5_exp38/2026-04-28/v5-exp38-allpath-head-only-20ep/epoch_epoch=epoch=14-val_loss=val_loss=1.438.ckpt
   ```

2. **Exp31 PM/rollout 평가** — learned loss mixing 5ep
   ```bash
   python3 scripts/test_v5_pm_dm.py \
     --config configs/mobile_vla_v5_exp31_step3_grounding_turnboost_learnedmix_5ep.json \
     --ckpt runs/v5_nav/kosmos/mobile_vla_v5_exp31/2026-04-24/.../last.ckpt
   ```

3. **Exp32~36 num_classes 점검** — arm_action [4,10] 원인 파악 후 재실험 여부 결정

4. **Basket prompted grounding 재실행** — "gray basket" 명시 프롬프트로 Exp10 ckpt와 비교

5. **BBox proxy → inference_server.py 연결** — Exp19 서버 API 포장

---

## 6. 핵심 파일 경로 치트시트

```bash
# 학습
python3 robovlm_nav/train.py configs/mobile_vla_v5_expNN_xxx.json

# PM 평가
python3 scripts/test_v5_pm_dm.py --config configs/... --ckpt runs/...

# Closed-loop 평가
python3 scripts/sim/evaluate_closed_loop_v5.py --model exp25 --config ...

# Text attention 측정
python3 scripts/measure_attention.py --config ... --ckpt ...

# BBox proxy 평가
python3 scripts/test_v5_bbox_nav_exp19_proxy.py
```

---

## 7. 참조 문서

| 문서 | 내용 |
|------|------|
| `docs/AGENT_ENTRYPOINT.md` | 에이전트 진입 순서 |
| `docs/MEMORY_SYNC_MAP.md` | 메모리 시스템 위치/정책 |
| `docs/v5/MONAVLA_DRIVING_HANDOFF_20260422.md` | 로봇 서버 배포 핸드오프 |
| `docs/v5/RECOGNITION_PROOF_RESULT_20260428.md` | basket 인식 능력 검증 |
| `docs/v5/EXP_STATUS_20260424.md` | Exp25~31 상태 상세 |
| `docs/v5/PURE_KOSMOS_LAST4_LORA_STATUS_20260427.md` | Exp32~36 설계 배경 |
| `docs/v5/PROF_UPDATE_20260417_EXP14.md` | 교수님 업데이트 전체 이력 |
| `plan.md` | 실험별 상세 계획 + 결과 |
| `CLAUDE.md` | 행동 규칙 + 프로젝트 컨텍스트 |
