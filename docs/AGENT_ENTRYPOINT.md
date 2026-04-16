# MoNaVLA — Agent / Claude 진입점 가이드

새 에이전트나 Claude 세션이 이 프로젝트에 진입할 때 읽어야 할 파일 순서입니다.

---

## 필수 진입 순서 (항상 읽어야 함)

| 순서 | 파일 | 목적 |
|------|------|------|
| 1 | `CLAUDE.md` | 작업 규칙, 워크플로우, 프로젝트 컨텍스트 |
| 2 | `docs/BENCHMARK_PIPELINE_DESIGN.md` | 공식 평가 체계 설계 원칙 |
| 3 | `docs/v5/V5_EVALUATION_PROTOCOL.md` | V5 평가 프로토콜 상세 |
| 4 | `docs/v5/V5_EVALUATION_GAP_ANALYSIS.md` | 현재 평가 갭 분석 |
| 5 | `docs/v5/V5_CLOSED_LOOP_SIM_PLAN.md` | 클로즈드 루프 시뮬레이션 계획 |

---

## V5 실험 맥락까지 필요할 때 (이어서 읽기)

| 순서 | 파일 | 목적 |
|------|------|------|
| 6 | `docs/situation_analysis_20260411.md` | 현황 분석 및 TODO |
| 7 | `plan.md` | 현재 진행 중인 작업 계획 (Exp11) |
| 8 | `docs/v5/exp01_11_analysis.md` | Exp01~11 실험 전체 요약 |
| 9 | `docs/v5/exp09/report.md` | Exp09 (8-class) 상세 리포트 |
| 10 | `docs/v5/exp10/action_alignment.md` | Exp10 액션 정렬 분석 |

---

## 코드 진입점 (실행 기준)

| 역할 | 파일 |
|------|------|
| 학습 | `robovlm_nav/train.py` |
| 데이터셋 | `robovlm_nav/datasets/nav_h5_dataset_impl.py` |
| 추론 서버 | `robovlm_nav/serve/inference_server.py` |
| 오프라인 정책 평가 (PM/DM) | `scripts/test_v5_pm_dm.py` |
| BBox grounding 평가 | `scripts/test/eval_v5_exp10_bbox_grounding.py` |

---

## 다른 에이전트에게 전달할 프롬프트 (복사용)

### 전체 버전

```
먼저 CLAUDE.md를 읽고 작업 규칙을 파악해라.
그 다음 docs/BENCHMARK_PIPELINE_DESIGN.md와 docs/v5/V5_EVALUATION_PROTOCOL.md를 읽고
이 프로젝트의 공식 평가 체계를 이해해라.
그 다음 docs/situation_analysis_20260411.md, plan.md, docs/v5/exp01_11_analysis.md를 읽고
V5 실험의 현재 상태를 파악해라.
코드 확인은 robovlm_nav/train.py, robovlm_nav/datasets/nav_h5_dataset_impl.py,
robovlm_nav/serve/inference_server.py, scripts/test_v5_pm_dm.py 순서로 해라.
```

### 짧은 버전

```
- 규칙:        CLAUDE.md
- 공통 benchmark: docs/BENCHMARK_PIPELINE_DESIGN.md
- V5 평가:     docs/v5/V5_EVALUATION_PROTOCOL.md
- 현재 상태:   docs/situation_analysis_20260411.md, plan.md
- 실험 요약:   docs/v5/exp01_11_analysis.md
- 코드 진입:   train.py → nav_h5_dataset_impl.py → inference_server.py → test_v5_pm_dm.py
```

---

## CLAUDE.md와의 관계

`CLAUDE.md`는 Claude Code 작업 규칙(워크플로우, 금지사항, 프로젝트 컨텍스트)을 담습니다.
이 파일(`AGENT_ENTRYPOINT.md`)은 **읽기 순서 가이드**입니다 — 규칙이 아니라 네비게이션 지도입니다.
