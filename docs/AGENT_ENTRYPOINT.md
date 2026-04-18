# Agent Entrypoint
작성일: 2026-04-16 / 마지막 업데이트: 2026-04-18

## 1. 목적

새로 들어온 에이전트가 MoNaVLA 프로젝트를 빠르게 파악할 수 있도록 **읽기 순서**를 정의한다.

## 2. 가장 먼저 읽을 문서

### Step 1. 작업 규칙 + 현재 상태 (필수)
- [CLAUDE.md](/home/billy/25-1kp/MoNaVLA/CLAUDE.md:1) — 행동 규칙 + **프로젝트 컨텍스트** (최신 실험 이력 포함)

확인할 것:
- 계획 승인 전 구현 금지
- `plan.md` 작성 규칙
- 현재 최선 모델 / 실험 이력 / 교수 프로토콜 현황

### Step 2. 장기 메모리
- `.menemory/core/master_memory.md` — 장기 목표, 아키텍처 원칙, 금지 규칙

### Step 3. 현재 진행 계획
- [plan.md](/home/billy/25-1kp/MoNaVLA/plan.md:1) — 진행 중/완료 실험의 상세 계획

## 3. 현재 상태 한 줄 요약 (2026-04-18)

| 항목 | 내용 |
|---|---|
| 현재 best PM | Exp14 Step 2 (BBox+Image MLP) **75.9%** |
| 현재 best closed-loop | Exp14 Step 2 **66.7%** success vs Exp11 0% |
| 텍스트 attention | 모든 학습 모델 **0%** (Google-robot pretrain 기인) |
| 진행 중 학습 | **Exp16** — 교수 프로토콜 Step 2 (전체 150 ep, center_straight 포함) |
| 교수 프로토콜 | Step 1 ✅ (Exp11) / Step 2 🔄 (Exp16 학습 중) / Step 3 ⬜ |

## 4. 핵심 스크립트 진입점

### 학습
```bash
python3 robovlm_nav/train.py configs/mobile_vla_v5_expNN_xxx.json
```

### PM 평가 (end-to-end policy)
```bash
python3 scripts/test_v5_pm_dm.py --config configs/... --ckpt runs/...
```

### Closed-loop 평가
```bash
python3 scripts/sim/evaluate_closed_loop_v5.py --model exp11|step2 [--config ...] [--ckpt ...]
```

### Attention 분석
```bash
python3 scripts/measure_attention.py --config configs/... --ckpt runs/...
```

### Feature ablation (BBox vs Image)
```bash
python3 scripts/ablate_bbox_image_features.py
```

## 5. 코드 진입 순서

### 학습 파이프라인
1. [robovlm_nav/train.py](/home/billy/25-1kp/MoNaVLA/robovlm_nav/train.py:1)
2. [robovlm_nav/trainer/nav_trainer.py](/home/billy/25-1kp/MoNaVLA/robovlm_nav/trainer/nav_trainer.py:1)
3. [robovlm_nav/datasets/nav_h5_dataset_impl.py](/home/billy/25-1kp/MoNaVLA/robovlm_nav/datasets/nav_h5_dataset_impl.py:1)

### 평가 파이프라인
1. [scripts/test_v5_pm_dm.py](/home/billy/25-1kp/MoNaVLA/scripts/test_v5_pm_dm.py:1) — PM/DM
2. [scripts/sim/evaluate_closed_loop_v5.py](/home/billy/25-1kp/MoNaVLA/scripts/sim/evaluate_closed_loop_v5.py:1) — closed-loop
3. [scripts/sim/rollout_core.py](/home/billy/25-1kp/MoNaVLA/scripts/sim/rollout_core.py:1) — kinematic simulation core

### 분석 파이프라인
1. [scripts/measure_attention.py](/home/billy/25-1kp/MoNaVLA/scripts/measure_attention.py:1)
2. [scripts/ablate_bbox_image_features.py](/home/billy/25-1kp/MoNaVLA/scripts/ablate_bbox_image_features.py:1)

## 6. 문서 신뢰도 가이드

### 최신 (우선 신뢰)
- `CLAUDE.md` — 프로젝트 컨텍스트 포함, 2026-04-18 업데이트
- `plan.md` — 각 실험의 상세 계획 및 결과
- `docs/v5/PROF_UPDATE_20260417_EXP14.md` — 교수님 업데이트 전체 이력

### 참고용 (내용 검증 후 사용)
- `docs/situation_analysis_20260411.md` — 2026-04-11 스냅샷, 이후 Exp11~16 반영 안 됨
- `docs/v5/exp01_11_analysis.md` — Exp11 분석, 이후 추가 분석 있음

### 구버전 (읽지 말 것)
- `docs/EXP09_10_11_TRAINING_REPORT.md` — 2026-02 세대, V5 naming과 다름

## 7. 현재 프로젝트 공식 해석

- **end-to-end policy baseline**: Exp11 (PM 58.6%, closed-loop 0%)
- **decomposition baseline**: Exp14 Step 2 (PM 75.9%, closed-loop 66.7%)
- **text attention**: 0% — Google-robot post-training 기인 (우리 학습 무관)
- **image가 핵심**: feature ablation에서 bbox grounding < raw image
- **진행 중**: Exp16 (교수 프로토콜 Step 2)

## 8. 주의사항

- `third_party/RoboVLMs/` 절대 수정 금지
- Google-robot backbone으로 `generate()` 호출 금지 ("Tin Tin..." 무한 반복)
- `menemory`는 별도 시스템 — `.menemory/core/master_memory.md` 읽기만
- `git status` 먼저 확인 (untracked 파일 많을 수 있음)
