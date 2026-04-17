# Exp14 연구 정리 표
작성일: 2026-04-17

## 핵심 결론

| 항목 | 내용 | 현재 해석 |
|---|---|---|
| 문제의식 | end-to-end policy가 spatial grounding을 제대로 쓰는가 | 기존 실험들은 loss와 실제 제어 성능이 자주 어긋남 |
| 이번 접근 | `grounding`과 `action mapping` 분리 | perception-to-action decomposition 실험 |
| 가장 중요한 결과 | `Exp11 58.6%` vs `Exp14 Step 2 75.9%` | 현재 문서 기준 strongest practical baseline은 Step 2 |
| 가장 중요한 정정 | `Exp10 ckpt + rule`은 `64.4%`가 아니라 `34.4%` | teacher-forced score와 free-form generation을 구분해야 함 |
| 가장 중요한 리스크 | quick repro에서 `11.3%` | split / 재학습 조건 민감도 존재 가능 |

---

## 실험별 요약

| 실험 | 알고리즘 관점 | 수치 | 해석 | 현재 위치 |
|---|---|---:|---|---|
| Exp04 | end-to-end policy, Google-Robot foundation | `val_loss 0.776`, `PM 0%` | 좋은 loss가 실제 inference를 보장하지 않는 반례 | baseline 아님 |
| Exp10 | grounding 자체를 next-token prediction으로 학습 | `val_loss 0.012`, `IoU 0.87`, `rule transfer 34.4%` | perception은 강하지만 generation interface가 불안정 | perception evidence |
| Exp11 | 기존 학습형 action baseline | `PM 58.6%` | 현재 남아 있는 정책형 기준점 | current policy baseline |
| Exp14 Step 1 | bbox history -> 작은 MLP | `68.4%` | spatial cue를 직접 작은 head에 연결하면 성능 상승 | Exp11 초과 |
| Exp14 Step 2 | bbox history + low-res image -> 작은 MLP | `75.9%` | geometry + weak appearance 결합이 가장 강함 | current strongest practical baseline |
| Exp14 Quick Repro | 새 split, `seed0 / 8 epoch` smoke check | `11.3%` | 재현성 민감도 경고 | 보조 검증 |

---

## 알고리즘 변화 정리

| 단계 | 입력 | 출력 | 핵심 아이디어 | 결과 |
|---|---|---|---|---|
| 기존 policy | image + instruction | action class | 모델이 perception과 control을 내부에서 한 번에 학습 | loss 대비 collapse 자주 발생 |
| Exp10 | image + prompt | bbox / grounding token | 목표물 위치를 읽는 능력 자체를 먼저 학습 | perception strong |
| Step 1 | bbox history | action class | 읽힌 spatial cue를 작은 head에 직접 연결 | `68.4%` |
| Step 2 | bbox history + low-res image | action class | geometry에 약한 appearance cue 추가 | `75.9%` |

---

## 이번에 실제로 확인한 것

| 확인한 주장 | 결과 | 의미 |
|---|---|---|
| end-to-end policy의 loss가 좋으면 실제 행동도 좋다 | 거짓 | Exp04가 반례 |
| grounding이 강하면 rule만으로도 policy가 된다 | 거짓 | Exp10 transfer는 `34.4%` |
| spatial intermediate representation을 명시적으로 꺼내면 더 낫다 | 부분적으로 참 | Step 1, Step 2가 Exp11 초과 |
| 작은 시각 feature를 bbox에 더하면 애매한 케이스가 좋아진다 | 유력 | Step 2가 Step 1보다 상승 |
| 현재 Step 2가 안정적으로 재현된다 | 아직 모름 | quick repro에서 민감도 노출 |

---

## 지금 교수님께 보고할 문장

| 구분 | 내용 |
|---|---|
| 한 줄 | navigation을 end-to-end policy로 두기보다, grounding과 action mapping을 분리한 decomposition 방식이 현재 더 강하게 보임 |
| 현재 공식 비교 | `Exp11 58.6%` vs `Exp14 Step 2 75.9%` |
| 가장 중요한 정정 | `Exp10`은 perception success이지 policy success가 아님 |
| 가장 중요한 리스크 | Step 2는 quick repro에서 성능 민감도가 드러나 재현성 검증이 필요 |

---

## 다음 단계

| 우선순위 | 해야 할 일 | 이유 |
|---|---|---|
| P0 | Step 2 재현성 검증 | 현재 strongest claim을 지키려면 필수 |
| P0 | Exp11 vs Step 2 같은 split 직접 비교 | apples-to-apples 비교 필요 |
| P1 | Step 2 ablation: bbox only vs bbox+image | image feature가 실제 기여하는지 확인 |
| P1 | failure case 분석 | 어떤 split에서 왜 무너지는지 파악 |
| P2 | closed-loop evaluation | offline PM을 실제 제어로 연결 |

---

## 참고 링크

| 문서 | 링크 |
|---|---|
| 상세 업데이트 | [PROF_UPDATE_20260417_EXP14.md](./PROF_UPDATE_20260417_EXP14.md) |
| 짧은 버전 | [PROF_UPDATE_20260417_EXP14_SHORT.md](./PROF_UPDATE_20260417_EXP14_SHORT.md) |
| 비교 페이지 | [bbox_nav_comparison.html](./bbox_nav_comparison.html) |
| Step 2 | [bbox_nav_step2/index.html](./bbox_nav_step2/index.html) |
| Quick Repro | [bbox_nav_step2_repro/index.html](./bbox_nav_step2_repro/index.html) |
