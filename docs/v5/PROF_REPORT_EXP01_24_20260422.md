# 교수님 보고용 요약: Exp01~24 (2026-04-22)

## 10줄 버전

1. 초기 `Exp01~04`에서는 데이터 비율과 backbone을 바꾸면 end-to-end가 해결될 것이라고 봤습니다.
2. 그런데 `Exp04`가 val_loss는 크게 좋아졌지만 나중에 PM `0%` collapse를 보여서, loss와 실제 정책 성능이 다를 수 있다는 점이 확인됐습니다.
3. `Exp05~08`에서는 instruction 설계와 prompt를 바꿔 text conditioning을 살리려 했지만, 후속 분석상 policy가 text path 자체를 거의 쓰지 않는 문제가 더 컸습니다.
4. `Exp09~13`에서 end-to-end를 더 정교화했지만, `Exp10`은 perception은 강하고 policy transfer는 약했고, `Exp11`은 PM `58.6%`였지만 closed-loop `0%`였습니다.
5. `Exp13`에서 instruction embedding을 명시적으로 action head에 넣어도 left/right 구분이 살아나지 않아, 후단 주입만으로는 해결되지 않는다는 점이 드러났습니다.
6. 전환점은 `Exp14`였고, bbox history와 작은 image feature를 쓰는 decomposition policy가 PM `75.9%`, closed-loop `66.7%`로 현재 strongest practical baseline이 됐습니다.
7. 이후 `Exp15~18`에서 교수님 프로토콜과 end-to-end branch를 다시 검증했는데, `Exp17`은 PM `76.95%`에도 closed-loop `11.1%`, `Exp18`은 val_loss `1.325`에도 PM `27.62%`, closed-loop `11.1%`로 실패했습니다.
8. 이 결과로 현재는 `PM 상승만으로는 모델을 채택하지 않고`, closed-loop가 baseline을 넘는지가 mainline 승격 조건이 됐습니다.
9. `Exp19`는 Step2에 proxy feature를 더해 PM `76.58%`, closed-loop `55.6%`까지 올라 가장 유망한 후속 branch가 됐지만, 아직 baseline `66.7%`는 넘지 못했습니다.
10. 지금은 `Exp21~24`에서 pure HF backbone과 objective shaping을 분리해, text collapse뿐 아니라 action attractor collapse와 sequence stabilization 문제까지 근본 원인을 닫는 단계로 보고 있습니다.

---

## 현재 한 줄 결론

```text
현재 strongest practical path는 Exp14 Step2 계열이고,
root-cause 관점에서는 end-to-end failure를 backbone 문제와 objective 문제로 분리하는 단계입니다.
```

---

## 교수님께 바로 말할 문장

```text
초기에는 데이터 비율과 backbone을 바꾸면 end-to-end가 해결될 것이라고 봤지만,
실험이 진행될수록 loss와 실제 주행 성능이 다르고,
instruction conditioning 자체가 약하며,
실제론 decomposition policy가 더 안정적이라는 쪽으로 결론이 이동했습니다.

지금은 practical mainline은 Exp14 Step2를 유지하고,
동시에 pure-HF / objective 수정 실험으로
왜 policy가 특정 action attractor로 무너지는지 근본 원인을 분리하고 있습니다.
```
