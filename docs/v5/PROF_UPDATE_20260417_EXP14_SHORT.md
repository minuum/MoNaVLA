# 교수님 보고용 짧은 버전

## 3문단 버전

이번에는 기존 V5 정책형 실험들을 다시 정리하면서, `Exp14 bbox-navigation` 트랙을 별도로 검증했습니다. 핵심 아이디어는 이미지를 바로 action으로 예측하는 end-to-end policy 대신, 먼저 목표물 위치를 읽는 `grounding`과 그 위치를 action으로 바꾸는 `action mapping`을 분리해서 다루는 것이었습니다. 즉, 큰 policy head 전체를 다시 학습시키기보다, spatial intermediate representation을 명시적으로 꺼내어 작은 head로 연결하는 구조를 시험했습니다.

이 관점에서 보면 기존 실험들은 한계가 분명했습니다. `Exp04`는 `val_loss 0.776`이었지만 재평가 결과 실제 `PM 0%`로 collapse였고, `Exp11`은 현재 남아 있는 기존 학습형 baseline으로 `PM 58.6%`입니다. 반면 `Exp10`은 teacher-forced 기준으로 `val_loss 0.012`, `IoU 0.87`로 perception은 강했지만, free-form generation을 바로 rule로 연결하면 실제 transfer는 `34.4%`에 그쳤습니다. 그래서 `Exp14 Step 1`에서는 bbox history만으로 작은 MLP를 학습시켰고 `68.4%`, `Step 2`에서는 여기에 `16x16 grayscale image feature`를 추가해 기존 기록 기준 `75.9%`까지 올라갔습니다.

현재 문서 기준 공식 비교는 `Exp11 58.6% vs Exp14 Step 2 75.9%`입니다. 다만 quick smoke check로 새 split에서 `seed0 / 8 epoch`만 다시 학습해보니 `11.3%`가 나와, 이 구조가 split과 학습 조건에 민감할 가능성도 확인했습니다. 따라서 현재 결론은, decomposition 방향 자체는 유망하고 실제로 기존 policy baseline보다 높은 수치를 보였지만, 다음 단계는 이 구조의 재현성을 더 엄밀하게 검증하는 것입니다.

---

## 메일체 버전

교수님,

이번에는 기존 V5 정책형 실험을 다시 정리하면서 `Exp14 bbox-navigation` 트랙을 별도로 검증했습니다. 핵심은 navigation을 end-to-end action prediction으로 보지 않고, 먼저 목표물 위치를 읽는 grounding과 그 결과를 action으로 바꾸는 mapping을 분리해서 다루는 방식이 실제로 더 안정적인지 확인하는 것이었습니다.

기존 정책형 계열을 다시 보면, `Exp04`는 loss는 좋아 보였지만 재평가 결과 실제 `PM 0%`로 collapse였고, 현재 남아 있는 기존 학습형 baseline은 `Exp11 PM 58.6%`입니다. 반면 `Exp10`은 teacher-forced 기준으로 `val_loss 0.012`, `IoU 0.87`까지 나와 perception 자체는 강했지만, free-form generation을 그대로 rule로 연결하면 실제 transfer는 `34.4%`에 그쳤습니다.

그래서 `Exp14 Step 1`에서는 bbox history만으로 작은 MLP를 학습시켜 `68.4%`, `Step 2`에서는 여기에 작은 image feature를 추가해 기존 기록 기준 `75.9%`까지 올라갔습니다. 현재 Pages 기준 공식 비교는 `Exp11 58.6% vs Exp14 Step 2 75.9%`로 정리했습니다.

다만 빠른 smoke check로 새 split에서 `seed0 / 8 epoch`만 다시 학습해보니 `11.3%`가 나와, 이 구조가 split과 재학습 조건에 민감할 가능성도 같이 확인했습니다. 따라서 지금 단계의 결론은, 알고리즘 방향은 유망하고 기존 policy baseline보다 높은 수치도 확보했지만, 다음 단계는 이 decomposition 구조의 재현성을 엄밀하게 확인하는 것입니다.

감사합니다.

---

## 1분 발표 버전

이번에는 navigation policy를 end-to-end action prediction으로 보지 않고, 목표물 위치를 읽는 grounding과 action mapping을 분리하는 방식으로 다시 봤습니다. 기존 `Exp04`는 loss는 좋았지만 재평가 결과 `PM 0%`였고, 현재 기존 학습형 baseline은 `Exp11 58.6%`입니다. `Exp10`은 perception은 강해서 `IoU 0.87`까지 나왔지만, 그 출력을 바로 action rule로 연결하면 실제 transfer는 `34.4%`에 그쳤습니다.

그래서 `Exp14`에서는 bbox history를 작은 MLP에 넣는 방식으로 바꿨고, `Step 1`이 `68.4%`, 여기에 작은 image feature를 더한 `Step 2`는 기존 기록 기준 `75.9%`까지 올라갔습니다. 즉 큰 action head를 end-to-end로 다시 학습시키는 것보다, spatial intermediate representation을 명시적으로 꺼내서 작은 head로 연결하는 방식이 더 잘 작동할 가능성을 봤습니다.

다만 빠른 재확인에서는 새 split, 짧은 학습 조건에서 `11.3%`가 나와 재현성 민감도도 같이 드러났습니다. 그래서 현재 결론은, 방향성은 맞고 성능도 유망하지만, 다음 단계는 이 구조가 정말 재현성 있게 유지되는지 검증하는 것입니다.
