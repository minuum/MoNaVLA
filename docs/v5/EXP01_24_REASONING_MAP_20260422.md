# Exp01~24 Reasoning Map (2026-04-22)

## 목적

이 문서는 `Exp01~24`를 단순 실험 목록이 아니라, **어떤 가설이 생겼고 왜 반박되었고 현재 어떤 중간 결론에 도달했는지**의 흐름으로 재구성한 내부용 정리다.

핵심 전제는 다음과 같다.

- 초기에는 `데이터 비율 / backbone / prompt`를 조정하면 end-to-end가 해결될 것이라고 봤다.
- 중간에는 `instruction text path collapse`가 핵심 병목이라고 봤다.
- 현재는 거기에 더해 `PM과 closed-loop 괴리`, `STOP supervision 부재`, `sequence-level action attractor collapse`까지 포함한 구조 문제로 본다.

---

## 한 줄 요약

```text
Exp01~13은 end-to-end를 살리려는 과정이었고,
Exp14가 decomposition의 practical superiority를 보여줬으며,
Exp15~24는 "왜 end-to-end가 무너지는가"를 분리해내는 과정이다.
```

---

## Phase 1 — Exp01~04

### 당시 가설

```text
문제는 데이터 비율과 출발 backbone일 가능성이 크다.
직선 비율을 줄이고 더 좋은 backbone을 쓰면 해결될 수 있다.
```

### 실험 해석

- `Exp01`
  - 전체 데이터 baseline
  - FORWARD shortcut이 강하게 보임
  - 의미: 문제의 출발점
  - 유망도: 낮음

- `Exp02`
  - 직선 제거
  - 일부 개선은 보였지만 근본 해결은 아님
  - 의미: 단순 class ratio 조절만으로는 부족
  - 유망도: 낮음

- `Exp03`
  - alignment / norm 계열 loss 보강
  - val_loss는 좋아졌지만 행동 개선은 확정 못 함
  - 의미: optimization gain과 policy gain은 다를 수 있음
  - 유망도: 보통 이하

- `Exp04`
  - Google-Robot backbone으로 교체
  - 당시에는 가장 유망해 보였음
  - 그러나 나중에 PM `0%` collapse
  - 의미: `낮은 val_loss = 실제 정책 향상` 가설이 처음으로 크게 무너짐
  - 유망도: 당시 높음, 최종 낮음

### 이 단계의 결론

```text
"데이터 비율과 backbone만 바꾸면 된다"는 생각은 부분적으로만 맞았다.
특히 Exp04는 val_loss 착시를 강하게 보여준 첫 사례였다.
```

---

## Phase 2 — Exp05~08

### 당시 가설

```text
문제는 텍스트 표현 방식일 수 있다.
instruction을 더 잘 쓰게 만들면 행동도 바뀔 수 있다.
```

### 실험 해석

- `Exp05`
  - action-aware instruction
  - temporal consistency를 높이려는 시도
  - 유망도: 보통

- `Exp06`
  - pure HF alignment / tokenizer 정렬
  - grounding token 호환성 개선
  - 유망도: 보통

- `Exp07`
  - path-type grounding
  - path ambiguity를 줄이려는 시도
  - 유망도: 당시 보통, 최종 낮음

- `Exp08`
  - center-goal awareness
  - prompt 기반 stop/goal awareness 시도
  - 유망도: 당시 보통 이상

### 나중에 어떻게 재해석됐나

`Exp07/11/13`의 text-ignore 분석 이후, 이 구간은 이렇게 다시 읽게 됐다.

```text
prompt를 잘 설계하는 것과
policy가 실제로 text path를 사용하는 것은 별개다.
policy가 text를 안 읽으면 prompt engineering만으로는 해결 안 된다.
```

---

## Phase 3 — Exp09~13

### 당시 가설

```text
end-to-end policy를 더 잘 다듬으면 된다.
텍스트나 grounding을 더 직접적으로 얹으면 행동도 개선될 수 있다.
```

### 실험 해석

- `Exp09`
  - 정리된 end-to-end 축
  - 한동안 메인 축처럼 보였음
  - 의미: 중간 이정표
  - 유망도: 당시 중간 이상

- `Exp10`
  - grounding 자체를 학습
  - perception은 강했지만 policy 전이는 약함
  - 의미: `볼 수는 있는데 움직이지는 못한다`
  - 유망도: perception용으로 높음, policy용으로 낮음

- `Exp11`
  - end-to-end 학습형 baseline
  - PM `58.6%`, closed-loop `0.0%`
  - 의미: offline PM과 실제 주행은 다르다
  - 유망도: 당시 높음, 최종 제한적

- `Exp12`
  - oracle 성격 검증
  - 구조적 문제 의심 강화
  - 유망도: 분석용

- `Exp13`
  - instruction embedding을 action head에 명시 주입
  - 기대는 컸지만 left/right 구분 실패
  - 의미: 후단 주입만으로는 conditioning이 안 살아난다
  - 유망도: 당시 높음, 최종 낮음

### 이 단계의 결론

```text
grounding이 된다고 policy가 되는 것도 아니고,
instruction embedding을 뒤에 붙인다고 text-conditioned action이 되는 것도 아니었다.
```

---

## Phase 4 — Exp14

### 사고 전환

```text
문제를 end-to-end 한 번에 풀지 말고,
지각과 제어를 분해하면 오히려 더 잘 될 수 있다.
```

### 실험 해석

- `Exp14 Step1`
  - bbox history만으로 PM `68.4%`
  - Exp11 `58.6%`를 넘김
  - 유망도: 높음

- `Exp14 Step2`
  - bbox + low-res image feature
  - PM `75.9%`
  - closed-loop `66.7%`
  - 유망도: 매우 높음
  - 의미: 현재 strongest practical baseline

### 이 단계의 결론

```text
실전 기준으로는 decomposition이 end-to-end보다 낫다.
이 시점부터 baseline은 Exp11이 아니라 Exp14 Step2가 됐다.
```

---

## Phase 5 — Exp15~18

### 질문

```text
end-to-end가 왜 무너지는가?
교수님 프로토콜은 실제로 문제를 해결하는가?
```

### 실험 해석

- `Exp15`
  - Google-Robot head-only control
  - text attention `0.000%`
  - 의미: LoRA는 collapse의 필요조건이 아니다
  - 유망도: 분석용으로 매우 중요

- `Exp16`
  - 교수님 Step2 계열
  - PM `0%` collapse 문맥
  - 의미: 단순 비율 교정은 오히려 diagonal collapse를 만들 수 있다
  - 유망도: 낮음

- `Exp17`
  - balanced end-to-end
  - PM `76.95%`
  - closed-loop `11.1%`
  - 의미: `PM 상승 != 실제 주행 향상`
  - 유망도: 당시 높음, 최종 제한적

- `Exp18`
  - text embedding fusion
  - best val_loss `1.325`
  - PM `27.62%`
  - closed-loop `11.1%`
  - 의미: 낮은 val_loss와 text fusion도 gate를 넘지 못함
  - 유망도: 당시 아이디어는 높음, 결과는 낮음

### 이 단계의 결론

```text
교수님 프로토콜은 PM 신호를 일부 개선할 수는 있어도,
현재 backbone/policy 구조에서는 closed-loop 해법이 아니다.
```

---

## Phase 6 — Exp19~20

### 질문

```text
Exp14 Step2를 유지하면서
도착 근접 상태(proxy)를 더 주면 baseline을 넘어설 수 있는가?
```

### 실험 해석

- `Exp19`
  - Step2 + proxy features
  - PM `76.58%`
  - closed-loop `55.6%`
  - 의미: end-to-end보다 훨씬 낫고, proxy branch 중 가장 유망
  - 하지만 baseline `66.7%`는 못 넘음
  - 유망도: 높음

- `Exp20`
  - goal_near auxiliary head
  - PM `75.32%`
  - auxiliary 자체는 잘 배웠지만 main action은 개선 안 됨
  - 의미: `상태를 안다`와 `정책이 좋아진다`는 다르다
  - 유망도: 보통 이하

### 이 단계의 결론

```text
V5는 STOP supervision이 없는 접근 trajectory dataset에 가깝다.
그래서 stop/goal-near는 direct label이 아니라 proxy state estimation 문제로 다뤄야 한다.
```

---

## Phase 7 — Exp21~24

### 질문

```text
문제는 Google-Robot backbone 자체인가?
아니면 현재 action objective / sequence policy 학습이 attractor collapse를 유도하는가?
```

### 실험 해석

- `Exp21`
  - pure HF + head-only
  - best val_loss `2.009`
  - attention probe상 text `0.000%`
  - single-frame instruction sensitivity는 존재
  - PM `0.00%`
  - 전역 `FWD+R` collapse
  - 의미: backbone만 바꾸면 끝나는 문제는 아님
  - 유망도: 성능용 낮음, 분석용 높음

- `Exp22`
  - pure HF + LoRA
  - 준비됨
  - 의미: LoRA가 pure HF 위에서 어떤 역할을 하는지 분리용
  - 유망도: 분석용 잠재력 높음

- `Exp23`
  - pure HF + both
  - 준비됨
  - 의미: fully trainable pure HF path 분리용
  - 유망도: 분석용 잠재력 높음

- `Exp24`
  - objective 수정 branch
  - anti-attractor class weights
  - label smoothing
  - prior regularization
  - 의미: backbone보다 objective가 특정 attractor를 만드는지 직접 보는 실험
  - 유망도: 현재 꽤 높음

### 이 단계의 결론

```text
현재 병목은 "텍스트를 읽냐/안 읽냐" 하나가 아니다.
local sensitivity, objective shaping, sequence stabilization을 따로 봐야 한다.
```

---

## 현재까지의 최종 중간 결론

1. `Exp14 Step2`가 여전히 strongest practical baseline이다.
2. `Exp19`는 가장 유망한 후속 branch이지만 baseline 승격은 아니다.
3. end-to-end branch는 아직 closed-loop gate를 못 넘었다.
4. 문제는 단일 원인이 아니라 아래 네 축의 결합이다.
   - text path collapse
   - PM / closed-loop gap
   - STOP supervision 부재
   - action attractor collapse

---

## 현재 유망도 정리

### A급

- `Exp14 Step2`
- `Exp19`
- `Exp24` 방향성

### B급

- `Exp10`
- `Exp15`
- `Exp21`
- `Exp22/23` 기획

### 당시엔 유망했지만 최종 탈락

- `Exp04`
- `Exp13`
- `Exp17`
- `Exp18`
- `Exp20`

### 초기 탐색 / 방향 수정용

- `Exp01`
- `Exp02`
- `Exp03`
- `Exp05`
- `Exp06`
- `Exp07`
- `Exp08`
- `Exp09`
- `Exp12`
- `Exp16`

---

## 실무적 의미

```text
practical mainline:
  Exp14 Step2 -> Exp19 refinement

fundamental line:
  Exp21~24 root-cause separation
```

현재는 점수만 더 올리는 단계보다, **왜 특정 branch가 특정 action attractor로 무너지는지**를 분리하는 단계로 보는 것이 맞다.
