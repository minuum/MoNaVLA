# V5 Closed-Loop Simulation 계획
작성일: 2026-04-16

## 1. 목표

Exp04, Exp09, Exp11 정책 실험과 Exp10 grounding proxy를 **episode-level closed-loop simulation**으로 평가한다.

핵심 질문:
- frame-wise prediction이 실제 trajectory로 이어지면 목표까지 도달하는가?

## 2. 왜 필요한가

현재 평가 체계의 한계:
- loss는 frame-level fitting만 보여준다.
- PM/DM는 현재 frame에 대한 label match만 보여준다.
- viewer는 사람이 눈으로 “그럴듯함”을 판단하게 만든다.

하지만 실제 navigation은 누적 오차 문제다.

예:
- turn이 2프레임 늦으면 trajectory 전체가 무너질 수 있다.
- stop이 1번만 늦어도 overshoot가 된다.
- frame-level accuracy가 높아도 episode success는 낮을 수 있다.

## 3. 시뮬레이션 입력

### 공통 입력
- H5 episode 이미지 시퀀스
- expert actions `[lx, ly, az]`
- language instruction
- 모델 체크포인트 또는 action proxy

### 실험별 입력 형태

| 실험 | 입력 형태 |
|------|-----------|
| Exp04 / Exp09 / Exp11 | policy model predicted discrete action |
| Exp10 | bbox center 기반 action proxy 또는 generated action text |

## 4. 시뮬레이션 상태 정의

시뮬레이터는 최소 상태를 유지한다.

- current pose `(x, y, theta)`
- current frame index
- predicted action
- accumulated trajectory
- target relative position proxy

초기 버전에서는 실제 물리엔진이 아니라 **dataset-driven kinematic simulation**으로 시작한다.

## 5. 첫 버전 단순화 가정

1. 각 frame은 일정한 시간 간격 `dt`를 가진다.
2. expert action과 predicted action은 동일한 control space를 사용한다.
3. pose update는 단순 differential / holonomic kinematics로 근사한다.
4. collision은 직접 측정 대신 proxy metric으로 평가한다.

## 6. pose update 예시

```python
x_next = x + lx * dt
y_next = y + ly * dt
theta_next = theta + az * dt
```

필요 시 body frame -> world frame 변환 추가:

```python
x_next = x + (lx * cos(theta) - ly * sin(theta)) * dt
y_next = y + (lx * sin(theta) + ly * cos(theta)) * dt
theta_next = theta + az * dt
```

## 7. 성공 / 실패 기준

### 성공
- final target distance <= threshold
- stop zone 안에서 정지
- timeout 없음
- trajectory divergence가 허용 범위 이내

### 실패
- timeout
- overshoot
- oscillation
- target miss
- excessive deviation
- stop failure

## 8. 측정 지표

### Episode-level
- success rate
- timeout rate
- overshoot rate
- final target distance
- trajectory length ratio
- mean lateral deviation
- mean heading error

### Event-level
- turn onset lag
- stop onset lag
- recovery success
- oscillation count

### Breakdown
- path type별 success
- action class별 실패 분포
- checkpoint별 비교

## 9. failure taxonomy

- `late_turn`
- `early_turn`
- `no_turn`
- `false_stop`
- `missed_stop`
- `forward_collapse`
- `oscillation`
- `terminal_offset_large`
- `trajectory_divergence`

## 10. 구현 단계

### Phase 1. Offline replay simulator
- H5 episode를 순회
- predicted action을 pose로 적분
- expert trajectory와 overlay 비교
- summary metrics 저장

### Phase 2. Exp10 action proxy simulator
- bbox center -> steering action 변환
- proxy rollout과 expert 비교
- grounding -> control 연결 검증

### Phase 3. Unified leaderboard
- Exp04 / Exp09 / Exp10-proxy / Exp11 결과를 동일 표로 기록

### Phase 4. Real robot handoff
- sim 통과 모델만 실기 대상에 올림

## 11. 출력 파일

- `rollout_metrics.json`
- `episode_rollouts.jsonl`
- `trajectory_overlay.html`
- `failure_examples.html`
- `leaderboard.csv`

## 12. 제안 스크립트 구조

```text
scripts/sim/
  evaluate_closed_loop_v5.py
  rollout_core.py
  metrics.py
  failure_taxonomy.py
  export_html.py
```

## 13. 우선 적용 대상

1. Exp04
   - baseline이라 가장 먼저 rollout 지표가 필요함
2. Exp09
   - PM/DM와 실제 행동의 괴리를 확인해야 함
3. Exp10 proxy
   - grounding이 navigation signal로 이어지는지 확인
4. Exp11
   - 학습 시작 전부터 동일 프로토콜로 비교

## 14. 검증 질문

closed-loop simulator가 만들어지면 아래 질문에 답할 수 있어야 한다.

- Exp04는 실제로 곡선 trajectory를 재현하는가?
- Exp09는 왜 PM/DM는 높지만 bias가 지속되는가?
- Exp10의 bbox tracking만으로도 navigation proxy가 성립하는가?
- Exp11은 Exp04/Exp09보다 terminal success가 나아지는가?

## 15. 결론

이 계획의 목표는 더 많은 실험을 만드는 것이 아니라, 기존 실험을 **episode success 기준으로 닫는 것**이다.

loss -> PM/DM -> rollout -> real-world 순서가 갖춰져야만 V5 실험이 판정 가능해진다.
