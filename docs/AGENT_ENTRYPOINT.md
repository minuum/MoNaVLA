# Agent Entrypoint
작성일: 2026-04-16

## 1. 목적

이 문서는 새로 들어온 에이전트가 MoNaVLA 프로젝트를 빠르게 파악할 수 있도록, **어떤 파일을 어떤 순서로 읽어야 하는지**를 정의한다.

대상:
- Claude
- Codex
- Antigravity
- 기타 에이전트/서브에이전트

## 2. 가장 먼저 읽을 문서

### Step 1. 작업 규칙
- [CLAUDE.md](/home/billy/25-1kp/MoNaVLA/CLAUDE.md:1)

확인할 것:
- 계획 승인 전 구현 금지
- `plan.md` 작성 규칙
- menemory 관련 규칙
- 현재 프로젝트 컨텍스트

### Step 2. 공통 benchmark 체계
- [docs/BENCHMARK_PIPELINE_DESIGN.md](/home/billy/25-1kp/MoNaVLA/docs/BENCHMARK_PIPELINE_DESIGN.md:1)

확인할 것:
- 프로젝트 공통 benchmark layer
- 고정 split 개념
- leaderboard 구조
- 추론 파이프라인까지 평가 대상이라는 점

### Step 3. V5 평가 체계
- [docs/v5/V5_EVALUATION_PROTOCOL.md](/home/billy/25-1kp/MoNaVLA/docs/v5/V5_EVALUATION_PROTOCOL.md:1)
- [docs/v5/V5_EVALUATION_GAP_ANALYSIS.md](/home/billy/25-1kp/MoNaVLA/docs/v5/V5_EVALUATION_GAP_ANALYSIS.md:1)
- [docs/v5/V5_CLOSED_LOOP_SIM_PLAN.md](/home/billy/25-1kp/MoNaVLA/docs/v5/V5_CLOSED_LOOP_SIM_PLAN.md:1)

확인할 것:
- 지금 프로젝트에서 어떤 평가가 비어 있는지
- 왜 closed-loop simulation이 필요한지
- 어떤 실험이 공식적으로 닫히지 않았는지

## 3. 현재 상태를 파악하는 핵심 문서

아래 문서를 순서대로 읽으면 현재 V5 흐름을 파악할 수 있다.

1. [docs/situation_analysis_20260411.md](/home/billy/25-1kp/MoNaVLA/docs/situation_analysis_20260411.md:1)
2. [plan.md](/home/billy/25-1kp/MoNaVLA/plan.md:1)
3. [docs/v5/exp01_11_analysis.md](/home/billy/25-1kp/MoNaVLA/docs/v5/exp01_11_analysis.md:1)
4. [docs/v5/exp09/report.md](/home/billy/25-1kp/MoNaVLA/docs/v5/exp09/report.md:1)
5. [docs/v5/exp10/action_alignment.md](/home/billy/25-1kp/MoNaVLA/docs/v5/exp10/action_alignment.md:1)

요약:
- 현재 정책 baseline은 Exp04
- Exp09는 8-class 통합이지만 bias가 남음
- Exp10은 grounding 쪽 최근 성과
- Exp11은 다음 정책 후보

## 4. 코드 진입 순서

### 학습 파이프라인
1. [robovlm_nav/train.py](/home/billy/25-1kp/MoNaVLA/robovlm_nav/train.py:1)
2. [robovlm_nav/trainer/nav_trainer.py](/home/billy/25-1kp/MoNaVLA/robovlm_nav/trainer/nav_trainer.py:1)
3. [robovlm_nav/datasets/nav_h5_dataset_impl.py](/home/billy/25-1kp/MoNaVLA/robovlm_nav/datasets/nav_h5_dataset_impl.py:1)

### 추론 파이프라인
1. [robovlm_nav/serve/inference_server.py](/home/billy/25-1kp/MoNaVLA/robovlm_nav/serve/inference_server.py:1)
2. [scripts/gradio_inference_dashboard.py](/home/billy/25-1kp/MoNaVLA/scripts/gradio_inference_dashboard.py:1)

### 평가 파이프라인
1. [scripts/test_v5_pm_dm.py](/home/billy/25-1kp/MoNaVLA/scripts/test_v5_pm_dm.py:1)
2. [scripts/test/eval_v5_exp09_pmdm.py](/home/billy/25-1kp/MoNaVLA/scripts/test/eval_v5_exp09_pmdm.py:1)
3. [scripts/test/eval_v5_exp10_bbox_grounding.py](/home/billy/25-1kp/MoNaVLA/scripts/test/eval_v5_exp10_bbox_grounding.py:1)

## 5. 문서 신뢰도 가이드

### 우선 신뢰할 문서
- `CLAUDE.md`
- `docs/BENCHMARK_PIPELINE_DESIGN.md`
- `docs/v5/V5_EVALUATION_PROTOCOL.md`
- `docs/situation_analysis_20260411.md`
- `plan.md`
- `docs/v5/exp01_11_analysis.md`

### 주의해서 읽을 문서
- [docs/v5/index.md](/home/billy/25-1kp/MoNaVLA/docs/v5/index.md:1)
  - 일부 실험 상태와 수치가 최신 문서를 완전히 반영하지 못할 수 있다.
- [docs/v5/exp10/report.md](/home/billy/25-1kp/MoNaVLA/docs/v5/exp10/report.md:1)
  - 초기 계획 문서라 실제 진행도보다 뒤처져 있다.
- [docs/EXP09_10_11_TRAINING_REPORT.md](/home/billy/25-1kp/MoNaVLA/docs/EXP09_10_11_TRAINING_REPORT.md:1)
  - 2026-02의 예전 세대 실험이라 현재 V5 naming과 혼동하면 안 된다.

## 6. 다른 에이전트에게 줄 짧은 지시문

```text
먼저 CLAUDE.md를 읽고 작업 규칙을 파악해라.
그 다음 docs/BENCHMARK_PIPELINE_DESIGN.md와 docs/v5/V5_EVALUATION_PROTOCOL.md를 읽고
이 프로젝트의 공식 평가 체계를 이해해라.
그 다음 docs/situation_analysis_20260411.md, plan.md, docs/v5/exp01_11_analysis.md를 읽고
V5 실험의 현재 상태를 파악해라.
코드는 robovlm_nav/train.py -> robovlm_nav/datasets/nav_h5_dataset_impl.py
-> robovlm_nav/serve/inference_server.py -> scripts/test_v5_pm_dm.py 순서로 확인해라.
```

## 7. 현재 프로젝트의 공식 해석

- 정책 baseline: Exp04
- 정책 실패 사례: Exp09
- 최근 시각적 성과: Exp10
- 다음 정책 후보: Exp11

## 8. 주의사항

- `third_party/RoboVLMs/`는 upstream 성격이 강하므로 수정 전에 반드시 근거를 확인한다.
- `menemory`는 별도 저장소/서브모듈이므로 본 저장소 변경과 분리해서 본다.
- untracked 문서/스크립트가 있을 수 있으므로 `git status`를 먼저 확인한다.
