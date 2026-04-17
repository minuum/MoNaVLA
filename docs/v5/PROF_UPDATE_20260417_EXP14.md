# 교수님 업데이트 메모
작성일: 2026-04-17

## 1. 이번에 한 일

이번에는 기존의 end-to-end policy 계열 실험들을 다시 정리하면서, `Exp14 bbox-navigation` 트랙을 별도로 검증했습니다.  
핵심 목적은 다음 질문을 확인하는 것이었습니다.

> 목표물의 위치를 읽는 능력(`grounding`)과  
> 그 위치 정보를 action으로 바꾸는 능력(`policy`)을  
> 분리해서 다루면 더 안정적인가?

기존 `Exp04`, `Exp09`, `Exp11`은 모두 이미지와 instruction을 받아서 곧바로 action class를 예측하는 **end-to-end policy** 구조였습니다.  
반면 이번 `Exp14`는 문제를 두 단계로 나눴습니다.

1. 먼저 VLM이 목표물의 위치를 읽는다.
2. 그 결과를 작은 action head가 받아 action으로 바꾼다.

즉, 이번 작업은 단순히 성능 숫자를 다시 재는 것이 아니라, **정책 학습 방식 자체를 decomposition 방식으로 바꿔 본 것**입니다.

---

## 2. 알고리즘 관점에서 본 핵심 해석

### 기존 end-to-end policy 계열의 문제

기존 정책형 실험들은 학습 loss는 좋아 보여도, 실제 inference에서는 shortcut learning이나 class collapse가 자주 발생했습니다.

- `Exp04`
  - 문서상으로는 `val_loss 0.776`
  - 하지만 재평가 결과 실제 `PM 0%`
  - 즉 loss는 좋아도 실제 제어는 무너진 사례

- `Exp11`
  - 현재 남아 있는 기존 학습형 baseline
  - `PM 58.6%`
  - 다만 left/right 계열 분리가 불안정하고 sanity에서 collapse 징후가 있음

이 결과는, **큰 action head를 end-to-end로 학습시키는 방식이 spatial grounding을 제대로 활용하지 못할 수 있다**는 점을 보여줍니다.

### Exp10에서 확인한 것

`Exp10`은 action policy 대신 목표물 위치 예측, 즉 grounding 자체를 학습한 실험입니다.

- teacher-forced 기준:
  - `val_loss 0.012`
  - `IoU 0.87`

즉 perception 자체는 강했습니다.  
하지만 이 출력을 free-form generation으로 뽑아 rule로 action에 연결해보면 실제 transfer는 `34.4%`밖에 나오지 않았습니다.

이 의미는 분명합니다.

> 모델 내부에 spatial information은 있지만,  
> 그것을 현재 generation interface로 바로 꺼내서 쓰는 방식은 불안정하다.

### Exp14 Step 1

그래서 `Exp14 Step 1`에서는 문제를 다시 단순화했습니다.

- 입력:
  - 최근 몇 프레임의 `bbox center x/y`
  - `bbox area`
  - `bbox 존재 여부`
- 모델:
  - 작은 `MLP`
- 목표:
  - 이 geometry/history feature만으로 action class 예측

결과는 `68.4%`였습니다.

즉, **VLM이 읽은 spatial cue를 직접 작은 decision head에 연결하는 방식**이 기존 학습형 baseline보다 더 잘 작동했습니다.

### Exp14 Step 2

`Step 1`의 한계는 bbox만으로는 애매한 장면을 충분히 구분하기 어렵다는 점이었습니다.  
특히 `center_left`, `center_right`처럼 경계가 애매한 경우에는 추가 시각 정보가 필요했습니다.

그래서 `Step 2`에서는 bbox history에 더해, 현재 프레임의 아주 작은 시각 feature를 추가했습니다.

- 추가 feature:
  - `16x16 grayscale image feature`

즉 feature level에서는:

`geometry (bbox history) + weak appearance (low-res image)`

구조가 된 것입니다.

기존 기록 기준 결과는 `75.9%`였습니다.

이건 알고리즘적으로 다음 의미를 가집니다.

> 거대한 end-to-end policy 전체를 다시 학습시키는 것보다,  
> spatial intermediate representation을 명시적으로 꺼내고  
> 그 위에 작은 head를 올리는 편이 더 잘 작동할 수 있다.

---

## 3. 현재 공식 비교

현재 Pages 기준으로 정리한 비교는 다음과 같습니다.

| 항목 | PM | 해석 |
|---|---:|---|
| Exp04 | 0% | loss 대비 inference collapse |
| Exp10 ckpt + rule | 34.4% | grounding score는 좋지만 transfer 실패 |
| Exp11 | 58.6% | 현재 기존 학습형 baseline |
| Exp14 Step 1 | 68.4% | bbox history만으로도 Exp11 초과 |
| Exp14 Step 2 | 75.9% | 현재 strongest practical baseline |

즉 현재 문서 기준 공식 해석은:

- `Exp11 = 기존 학습형 기준점`
- `Exp14 Step 2 = 현재 가장 강한 practical baseline`

입니다.

---

## 4. 주의점: 재현성은 아직 닫히지 않음

이번에 5분 안에 끝내는 quick smoke check로 `Step 2`를 새 split에서 다시 짧게 학습해봤습니다.

- 조건:
  - `seed0`
  - `8 epoch`
  - 빠른 재확인용
- 결과:
  - `11.3%`

이 값은 기존 `75.9%`를 바로 뒤집는 공식 결론은 아닙니다.  
하지만 중요한 신호는 줍니다.

> `Step 2`는 현재 매우 유망하지만,  
> split과 재학습 조건에 민감할 가능성이 있다.

따라서 지금 단계의 올바른 해석은:

- 알고리즘 방향 자체는 유망하다.
- 하지만 재현성 검증이 아직 충분하지 않다.

입니다.

---

## 5. 이번 업데이트의 한 줄 결론

이번에는 navigation을 end-to-end action prediction으로 보기보다,  
**grounding과 action mapping을 분리한 decomposition 알고리즘**으로 접근했습니다.

그 결과 기존 정책형 baseline(`Exp11 58.6%`)보다 높은 성능(`Step 2 75.9%`)이 관측됐습니다.  
다만 quick repro에서 민감도가 보여, 다음 단계는 **이 decomposition 구조의 재현성 확인**입니다.

---

## 6. 다음 단계 제안

1. `Step 2`를 여러 split/seed에서 다시 평가해 재현성 확인
2. `Exp11`과 `Step 2`를 가능한 한 같은 split에서 직접 비교
3. 어떤 feature가 성능을 만드는지 분석
   - bbox history만으로 되는지
   - low-res image가 실제로 추가 정보를 주는지
4. 가능하면 closed-loop 평가로 연결

---

## 7. 참고 문서

- [Exp14 Comparison](./bbox_nav_comparison.html)
- [Exp14 Step 2](./bbox_nav_step2/index.html)
- [Exp14 Step 2 Quick Repro](./bbox_nav_step2_repro/index.html)
- [V5 Dev Log](./devlog.html)
