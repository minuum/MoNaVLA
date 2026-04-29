# V5 평가 프로토콜
작성일: 2026-04-16

## 1. 목적

이 문서는 V5 실험을 `학습 loss`, `정성 시각화`, `오프라인 PM/DM`, `시뮬레이션 rollout`, `실기 테스트`까지 일관된 체계로 평가하기 위한 공식 프로토콜이다.

핵심 원칙:
- 정성 평가는 발견용이다.
- 정량 평가는 판정용이다.
- 실험은 **loss가 아니라 평가 단계 전체를 통과해야** 종료된 것으로 본다.

## 2. 현재 문제 정의

현재 V5 문서와 스크립트에는 다음이 존재한다.
- 분류형 정책 평가: `scripts/test_v5_pm_dm.py`, `scripts/test/eval_v5_exp08_pmdm.py`, `scripts/test/eval_v5_exp09_pmdm.py`
- grounding 평가: `scripts/test/eval_v5_exp10_bbox_grounding.py`
- 정성 시각화: `docs/v5/exp10/*`, viewer HTML

하지만 다음이 빠져 있다.
- perception -> action -> rollout -> real-world를 연결하는 공통 판정 체계
- episode-level success/failure를 측정하는 closed-loop simulation
- 실험별 동일 기준 leaderboard

## 3. 평가 레이어

### Layer 1. Static Perception Evaluation

질문:
- 모델이 프레임 하나에서 장면을 제대로 읽는가?

적용 대상:
- Exp10
- 향후 grounding-aware policy 실험

핵심 지표:
- BBox IoU
- Success Rate @ IoU 0.5
- target center offset error
- left/right/center direction classification accuracy
- stop-needed classification accuracy
- confidence calibration

산출물:
- frame-level CSV / JSON
- episode별 IoU 분포
- path type별 perception breakdown

통과 기준 예시:
- Mean IoU >= 0.70
- IoU@0.5 >= 80%
- center offset error가 실험 간 일관되게 감소

### Layer 2. Offline Policy Evaluation

질문:
- 모델이 ground-truth frame sequence 위에서 적절한 action을 내는가?

적용 대상:
- Exp01~09, Exp11

핵심 지표:
- PM (Perfect Match)
- DM (Directional Match)
- per-class accuracy
- confusion matrix
- forward bias ratio
- stop precision / stop recall
- turn onset lag
- path type별 성능

산출물:
- confusion matrix
- path type별 PM/DM 표
- stop/turn 실패 원인 분류

통과 기준 예시:
- PM >= baseline
- DM >= baseline
- Forward bias ratio 감소
- stop recall과 turn recall이 최소 기준 이상

### Layer 3. Closed-Loop Simulation Rollout

질문:
- 예측 action을 누적 적용했을 때 실제로 목표까지 도달하는가?

적용 대상:
- Exp04, Exp09, Exp11 우선

핵심 지표:
- episode success rate
- timeout rate
- collision proxy rate
- deviation from expert trajectory
- final target distance
- recovery success rate
- stop overshoot / undershoot

산출물:
- episode-level rollout log
- trajectory overlay plot
- failure taxonomy 요약

통과 기준 예시:
- success rate >= 70%
- timeout / oscillation / overshoot 감소
- expert trajectory 대비 terminal error 감소

### Layer 4. Real Robot Benchmark

질문:
- 시뮬레이션에서 통과한 정책이 실기에서도 재현되는가?

적용 대상:
- Layer 3를 통과한 checkpoint만

핵심 지표:
- fixed scenario success rate
- intervention count
- mean completion time
- stop accuracy
- unsafe action count

실험 규칙:
- checkpoint freeze 후 테스트
- scenario set 고정
- 실험 중 수동 튜닝 금지
- 영상 / action log / trajectory 동시 저장

## 4. 공식 판정 순서

1. Layer 1 통과 또는 면제 여부 확인
2. Layer 2 오프라인 정책 평가
3. Layer 3 closed-loop rollout
4. Layer 4 실기 테스트

주의:
- policy 실험은 Layer 2와 Layer 3를 모두 통과해야 한다.
- grounding 실험은 Layer 1에서 우선 판정하되, policy transfer 주장 시 Layer 3 연결 증거가 필요하다.

## 5. 실험 유형별 적용

| 실험 유형 | Layer 1 | Layer 2 | Layer 3 | Layer 4 |
|----------|---------|---------|---------|---------|
| Pure policy (Exp01~09, Exp11) | 선택 | 필수 | 필수 | 선택적 최종 |
| Grounding (Exp10) | 필수 | 보조 | transfer 주장 시 필수 | 필요 시 |
| Hybrid policy + grounding | 필수 | 필수 | 필수 | 최종 |

## 6. 공통 리더보드 포맷

모든 실험은 아래 표로 요약한다.

| Exp | Split | Perception | PM | DM | Forward Bias | Stop Recall | Sim Success | Real Success | Verdict |
|-----|-------|------------|----|----|--------------|-------------|-------------|--------------|---------|
| Exp04 | val | N/A | ? | ? | ? | ? | ? | ? | 미완료 |
| Exp09 | val | N/A | 85.7 | ? | 높음 | 낮음 추정 | ? | ? | bias 지속 |
| Exp10 | val | IoU 0.87 | 간접 | 간접 | N/A | stop discrepancy | 미연결 | ? | grounding 성공 |
| Exp11 | val | N/A | 미실행 | 미실행 | 미실행 | 미실행 | 미실행 | 미실행 | 계획 |

## 7. 실패 taxonomy

모든 평가는 아래 taxonomy로 실패를 라벨링한다.

- `forward_collapse`
- `false_stop`
- `missed_stop`
- `late_turn`
- `early_turn`
- `left_right_confusion`
- `rotation_missing`
- `oscillation`
- `overshoot`
- `perception_miss`
- `trajectory_divergence`

## 8. 저장 산출물 규격

실험마다 아래 파일을 남긴다.

- `metrics.json`
- `episode_rollout.jsonl`
- `failure_summary.json`
- `leaderboard_row.json`
- 시각화:
  - `confusion_matrix.png`
  - `trajectory_overlay.png`
  - `failure_examples.html`

## 9. 즉시 적용 우선순위

1. Exp04: Layer 2, Layer 3 보강
2. Exp09: Layer 3로 bias를 episode success 기준으로 재판정
3. Exp10: Layer 1 결과를 정식 metrics table로 고정
4. Exp11: 학습 전부터 동일 프로토콜 적용
