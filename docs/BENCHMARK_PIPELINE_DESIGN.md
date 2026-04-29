# MoNaVLA 공통 벤치마크 파이프라인 설계
작성일: 2026-04-16

## 1. 목적

이 문서는 MoNaVLA의 모든 실험이 동일한 기준으로 비교되도록 하는 **고정 평가 파이프라인**과 **공통 벤치마크 설계**를 정의한다.

목표:
- 실험마다 평가 방식이 달라지는 문제 제거
- loss / PM / 정성 평가만으로 결론 내리는 문제 제거
- 실험, 데이터셋, 추론 경로, 실기 결과를 하나의 표준 리더보드로 통합

## 2. 왜 필요한가

현재 프로젝트는 다음 문제가 있다.

- 어떤 실험은 `val_loss`만 있다.
- 어떤 실험은 PM/DM만 있다.
- 어떤 실험은 HTML viewer와 정성 분석만 있다.
- 어떤 실험은 실제로 어떤 split에서 평가했는지 불명확하다.
- 학습 파이프라인과 추론 파이프라인 전체를 동일 기준으로 검증하지 못한다.

결과적으로:
- "좋아 보인다"와 "실제로 좋다"가 섞인다.
- 실험 간 비교가 재현되지 않는다.
- 교수님 보고나 논문용 표를 만들 때 해석이 흔들린다.

## 3. 설계 원칙

### 원칙 1. 평가 입력을 고정한다
- 학습 split
- validation split
- benchmark split
- real-world scenario set

실험마다 split이 달라지면 비교를 금지한다.

### 원칙 2. 평가 레이어를 고정한다
- Layer A: Data benchmark
- Layer B: Perception benchmark
- Layer C: Offline policy benchmark
- Layer D: Closed-loop simulation benchmark
- Layer E: Real robot benchmark

### 원칙 3. 산출물 형식을 고정한다
- `metrics.json`
- `leaderboard_row.json`
- `failure_summary.json`
- `episode_results.jsonl`
- 표준 HTML / plot 산출물

### 원칙 4. 사람 판단은 보조로만 쓴다
- 정성 시각화는 유지
- 최종 판정은 고정 metrics로만 결정

## 4. 벤치마크 대상 태스크 정의

현재 프로젝트의 공통 태스크는 아래처럼 정의한다.

### Primary Task
- `target-guided indoor navigation`
- 목표: 회색 바스켓을 향해 이동하고, 적절한 위치에서 정지

### Subtasks
- `center_left`
- `center_right`
- `center_straight`
- `left_left`
- `left_right`
- `left_straight`
- `right_left`
- `right_right`
- `right_straight`

### 핵심 행동 요구
- 좌/우 방향 결정
- 직진 유지
- 회전 보정
- 정지 타이밍
- trajectory consistency

## 5. 고정 데이터 분할

### 5.1 Split 종류

| Split | 목적 | 사용 시점 |
|------|------|----------|
| `train` | 학습 | training only |
| `val` | early stopping, ablation 비교 | training/eval |
| `bench_offline` | 공식 offline benchmark | 모델 비교 |
| `bench_rollout` | 공식 simulation benchmark | 정책 비교 |
| `bench_real` | 실기 benchmark 시나리오 | 최종 비교 |

### 5.2 고정 원칙
- `bench_offline`, `bench_rollout`, `bench_real`은 실험 간 공유한다.
- 실험 중간에 benchmark split을 다시 샘플링하지 않는다.
- path type 분포를 명시적으로 유지한다.

### 5.3 권장 분해
- path type stratified split
- difficulty tag 포함
- straight / turn / stop scenario 비율 고정

## 6. 벤치마크 레이어 설계

## Layer A. Data Benchmark

질문:
- 데이터셋이 실험 비교에 충분히 동일하고 균형 잡혀 있는가?

지표:
- episode count
- path type distribution
- action class distribution
- frame count distribution
- stop / rotation rarity
- instruction diversity

이 레이어에서 확인할 것:
- 어떤 실험이 데이터 이득인지 모델 이득인지 분리

## Layer B. Perception Benchmark

질문:
- 모델이 장면과 목표를 제대로 읽는가?

적용:
- grounding 계열 모델
- perception-aware policy

지표:
- BBox IoU
- center offset error
- target visibility recall
- left/right/center classification
- stop-needed signal quality

판정:
- perception이 약하면 policy 실패 원인을 모델이 아니라 perception으로 분류

## Layer C. Offline Policy Benchmark

질문:
- ground-truth sequence 위에서 적절한 action을 내는가?

지표:
- PM
- DM
- confusion matrix
- forward bias ratio
- stop precision / recall
- turn precision / recall
- path type별 성능

판정:
- 이 레이어는 "행동 결정 자체"를 본다.

## Layer D. Closed-Loop Simulation Benchmark

질문:
- 예측 action을 누적 적용하면 실제 목표에 도달하는가?

지표:
- success rate
- timeout rate
- overshoot rate
- terminal distance
- trajectory deviation
- recovery rate
- oscillation count

판정:
- frame-wise accuracy가 episode success로 이어지는지 검증

## Layer E. Real Robot Benchmark

질문:
- 시뮬레이션 통과 모델이 실기에서도 재현되는가?

지표:
- scenario success rate
- intervention count
- completion time
- safety event count
- stop accuracy

판정:
- 실기 benchmark는 마지막 승인 단계다.

## 7. 공통 리더보드 설계

모든 실험은 아래 표 한 줄로 요약한다.

| Exp | Train Split | Offline Split | Perception | PM | DM | Stop Recall | Turn Recall | Sim Success | Real Success | Verdict |
|-----|-------------|---------------|------------|----|----|-------------|-------------|-------------|--------------|---------|

### Verdict 규칙
- `Rejected`: baseline 미만
- `Needs Analysis`: 일부 개선, rollout 미완료
- `Candidate`: offline + simulation 통과
- `Accepted`: real benchmark 통과

## 8. 추론 파이프라인 벤치마크

학습 모델만이 아니라 **추론 경로 전체**도 benchmark 대상이다.

### 8.1 추론 경로 정의
- config load
- tokenizer / processor load
- checkpoint load
- preprocessing
- model forward / generate
- action mapping
- post-processing
- robot command output

### 8.2 추론 benchmark 지표
- load success rate
- config reproducibility
- inference latency
- VRAM / RAM usage
- output validity rate
- action mapping correctness
- stop safety fallback correctness

### 8.3 고정 테스트 세트
- 대표 frame set
- 대표 episode set
- malformed input set
- edge-case stop/turn set

## 9. 실패 taxonomy 표준화

모든 benchmark는 아래 taxonomy를 사용한다.

- `data_imbalance`
- `forward_collapse`
- `left_right_confusion`
- `rotation_missing`
- `false_stop`
- `missed_stop`
- `late_turn`
- `overshoot`
- `oscillation`
- `perception_miss`
- `pipeline_load_failure`
- `latency_exceeded`
- `unsafe_output`

## 10. 표준 실행 순서

새 실험은 항상 아래 순서로 평가한다.

1. Data benchmark
2. Training complete + checkpoint freeze
3. Offline policy / perception benchmark
4. Closed-loop simulation benchmark
5. Inference pipeline benchmark
6. Real robot benchmark
7. Leaderboard 반영

## 11. 저장 구조 제안

```text
benchmarks/
  definitions/
    benchmark_manifest.yaml
    offline_split.json
    rollout_split.json
    real_scenarios.yaml
  results/
    exp04/
      metrics.json
      leaderboard_row.json
      failure_summary.json
    exp09/
    exp10/
    exp11/
```

## 12. benchmark manifest 필드

```yaml
benchmark_name: monavla_v1
task: target_guided_indoor_navigation
dataset: mobile_vla_dataset_v5
offline_split: benchmarks/definitions/offline_split.json
rollout_split: benchmarks/definitions/rollout_split.json
real_scenarios: benchmarks/definitions/real_scenarios.yaml
metrics:
  - pm
  - dm
  - stop_recall
  - turn_recall
  - sim_success
  - real_success
failure_taxonomy:
  - forward_collapse
  - false_stop
  - overshoot
```

## 13. 버전 정책

- benchmark는 버전 관리한다.
- split 또는 metric 정의가 바뀌면 `monavla_v1` -> `monavla_v2`로 올린다.
- 서로 다른 benchmark version 결과는 같은 표에서 직접 비교하지 않는다.

## 14. 지금 당장 필요한 산출물

### P0
- benchmark manifest
- offline split 고정
- rollout split 고정
- leaderboard 템플릿

### P1
- inference pipeline benchmark script
- closed-loop rollout benchmark script
- failure taxonomy export

### P2
- real robot scenario sheet
- benchmark summary dashboard

## 15. 현재 프로젝트에 적용한 해석

이 설계 기준으로 보면:
- Exp04는 baseline이지만 benchmark가 닫히지 않았다.
- Exp09는 offline benchmark 일부만 통과했고 rollout benchmark는 없다.
- Exp10은 perception benchmark는 강하지만 policy benchmark로 전이되지 않았다.
- Exp11은 benchmark 적용 전 상태다.

## 16. 결론

MoNaVLA에 필요한 것은 더 많은 단발 실험이 아니라, **고정된 benchmark pipeline 위에서 실험을 반복하는 구조**다.

앞으로는 "새 실험"보다 먼저 아래 질문에 답할 수 있어야 한다.

- 같은 split에서 비교했는가?
- 같은 benchmark version을 썼는가?
- offline, simulation, inference, real-world를 모두 통과했는가?

이 세 가지가 없으면 결과는 참고자료일 뿐, 공식 결론이 아니다.
