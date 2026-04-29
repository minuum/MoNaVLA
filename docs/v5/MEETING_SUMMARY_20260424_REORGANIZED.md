# 2026-04-24 미팅 정리 및 이전 진행사항 요약

## 1. 교수님 질문 및 의문점에 대한 반박

### Q1. 왜 지금도 `exp25`를 baseline으로 잡는가

- 현재 기준은 offline accuracy가 아니라 실제 `closed-loop / ETE` 성능이다.
- 그 기준에서 `exp25`가 최근 후보 중 가장 실전성이 높다.
  - closed-loop success: `55.6%`
  - mean FPE: `0.382`
  - mean TLD: `0.936`
  - PM/DM: `52.38%`
- 특히 `center_left`, `center_right`, `center_straight`, `left_straight`, `right_straight`는 closed-loop `100%`다.
- 즉 "전체가 안 된다"가 아니라, 이미 되는 slice와 아직 무너지는 slice가 분리되어 있다.

### Q2. 왜 `exp26`처럼 offline 수치가 더 좋은 모델을 안 쓰는가

- `exp26`의 PM/DM는 `70.24%`로 최근 후보 중 가장 높다.
- 그러나 closed-loop success는 `0.0%`, mean FPE는 `1.189`다.
- 즉 현재 병목은 단순 분류 정확도 부족이 아니라, rollout 중 `turning commitment`가 유지되지 않는 문제다.
- 따라서 이번 미팅에서는 "offline이 좋아도 rollout이 보장되지 않는다"는 반례로 `exp26`을 설명하는 것이 맞다.

### Q3. `exp27`의 letterbox 가설이 더 나은 방향 아닌가

- 현재 데이터상으로는 아니다.
- `exp27`은 closed-loop success `33.3%`, mean FPE `0.932`, PM/DM `15.48%`다.
- 즉 `exp25`보다 rollout도 낮고, offline도 불안정하다.
- 따라서 letterbox는 현재 시점에서는 "유망한 개선안"이 아니라 "비교용 ablation"으로 두는 것이 맞다.

### Q4. 사람이 검수한 bbox GT를 붙이면 바로 해결되는 것 아닌가

- 현재 5-epoch short ablation 결과는 그 가설을 지지하지 않는다.
- `exp29`(coarse-only):
  - mean IoU `0.000`
  - IoU@0.3 `0.0%`
  - PM/DM `21.43%`
- `exp30`(bbox+coarse):
  - mean IoU `0.000`
  - IoU@0.3 `0.0%`
  - PM/DM `14.29%`
- 둘 다 `FORWARD`, `LEFT`, `RIGHT`를 회복하지 못했다.
- 따라서 현재 맞는 해석은 "GT가 틀렸다"가 아니라, **현재 head/loss 설계로는 GT를 줘도 usable bbox와 left/right policy가 살아나지 않는다**이다.

### Q5. 그러면 문제는 GT 품질이 아니라 무엇인가

- 현재 evidence는 GT 품질 문제보다 `loss competition`과 `shared feature` 설계 문제를 더 강하게 가리킨다.
- `exp28~30`은 이름상 grounding auxiliary가 들어가 있지만, 실제 final validation loss 기준으로는 base action loss가 약 `99.6%`를 차지한다.
  - `exp28`: base share `99.57%`
  - `exp29`: base share `99.64%`
  - `exp30`: base share `99.65%`
- 즉 bbox/coarse supervision이 config에는 존재해도 실제 학습에서는 너무 약하게 작동한다.
- 그 결과 bbox head는 tiny center box로 collapse하고, coarse는 center bias만 강화되며, left/right policy 회복으로 이어지지 않았다.

### Q6. 그렇다면 현재 병목은 정확히 무엇인가

- 가장 직접적인 병목은 `turning commitment collapse`다.
- `exp25`는 직진/센터 정렬 계열은 통과하지만, `left_left`, `left_right`, `right_left`, `right_right`는 closed-loop `0%`다.
- 즉 초반 몇 프레임 안에 "언제, 어느 방향으로 돌기 시작할지"를 안정적으로 결심하지 못한다.
- 이번 미팅에서는 문제를 "모델 전체 실패"가 아니라, **특정 turning family failure slice가 남아 있는 상태**로 설명하는 것이 정확하다.

### Q7. 그렇다면 왜 다음 실험이 `exp28` 또는 그 후속(`exp31`)인가

- `exp28`은 현재 best rollout baseline인 `exp25`를 유지한 채, weakest slice만 직접 보강하는 설계다.
- 추가된 요소는 다음과 같다.
  - `bbox_truth_mini` 72프레임 human-reviewed grounding supervision
  - bbox regression head + coarse position classification head
  - turning family oversampling
  - stronger turn/side class weighting
- `exp29`, `exp30`은 이 구조의 short ablation이고, 2026-04-24에는 `exp31`에서 action/bbox/coarse 비율을 고정 lambda가 아니라 learned mixing으로 바꾸는 follow-up이 시작되었다.
- 즉 다음 단계는 "GT를 더 넣는다"가 아니라, **GT가 실제로 경쟁력 있게 학습되도록 loss 구조를 바꾸는 것**이다.

## 2. 이전 진행사항 요약

### 지금까지 무엇을 확인했는가

1. V5에서는 문제를 `9개 고정 경로`와 `discrete action`으로 단순화했다.
2. 기존 end-to-end policy 계열은 학습 loss가 좋아도 rollout collapse가 반복되었다.
3. `Exp10`에서 perception 자체는 강하다는 점을 확인했다.
   - BBox grounding: `val_loss 0.012`, `IoU 0.87`
4. `Exp14 Step2`에서 grounding과 policy를 분리한 decomposition이 강한 baseline임을 확인했다.
   - PM `75.9%`
   - 5-seed repro `76.6 +- 1.6%`
   - closed-loop `66.7%`
5. 최근 4/22~4/24 구간에서는 실전형 end-to-end 후보군 `exp25~31`을 집중적으로 비교했다.

### 현재까지 정리된 실험 규모

- V5 config 기준 명명된 실험 ID: `27개`
  - 확인된 config: `exp01, 02, 04~13, 15~18, 21~31`
- V5 run directory 기준 최근 실행 흔적이 남아 있는 실험: `10개`
  - `exp03, exp12, exp17, exp25~31`
- 이번 미팅에서 직접 비교해야 하는 핵심 최근 후보군: `6개`
  - `exp25`, `exp26`, `exp27`, `exp28`, `exp29`, `exp30`
- 2026-04-24 당일 follow-up:
  - `exp31` started, learned loss mixing 적용, 아직 rollout 평가는 없음

### 실험 접근법 분류

| 접근 축 | 대표 실험 | 목적 | 현재 해석 |
| --- | --- | --- | --- |
| 초기 end-to-end policy | `exp01~09` | discrete action baseline 구축 | collapse와 bias 반복 |
| grounding-only / perception | `exp10` | 목표물 위치 인식 성능 확인 | perception은 강함 |
| decomposition | `exp14 Step1/2` | grounding과 policy 분리 | strongest algorithmic evidence |
| protocol expansion / all-path | `exp16~18` | 교수님 프로토콜 대응, all-path 확장 | end-to-end practical line 형성 |
| pure-HF / objective shaping | `exp21~24` | backbone/학습 목표 원인 분리 | `exp25`로 이어지는 준비 단계 |
| recent practical rollout track | `exp25~31` | 실전형 end-to-end 개선 | `exp25` baseline, `exp28~31` 보강 축 |

## 3. 현재 최근 실험군(`exp25~31`) 해석

| 실험 | 핵심 변화 | PM/DM | Closed-loop | 해석 |
| --- | --- | ---: | ---: | --- |
| `exp25` | balanced objective baseline | `52.38%` | `55.6%` | 현재 best practical baseline |
| `exp26` | direct 224 resize | `70.24%` | `0.0%` | offline strong, rollout fail |
| `exp27` | letterbox 224 | `15.48%` | `33.3%` | letterbox 가설 악화 |
| `exp28` | + grounding aux + turn boost | `38.10%` | `0.0%` | aux 연결은 됐지만 실전 개선 미확인 |
| `exp29` | coarse-only, 5 epochs | `21.43%` | 미승격 | bbox 없이 coarse만 본 short ablation |
| `exp30` | bbox+coarse, 5 epochs | `14.29%` | 미승격 | bbox까지 넣었지만 더 악화 |
| `exp31` | learned loss mixing, 5 epochs | 미평가 | 미평가 | 2026-04-24 follow-up 진행 중 |

## 4. 관계도 및 플로우

### 실험 계보 관계도

```text
V5 fixed-path / discrete-action setup
    |
    +-- [초기 end-to-end] exp01~09
    |       -> collapse / bias 반복
    |
    +-- [grounding-only] exp10
    |       -> perception strong 확인 (IoU 0.87)
    |
    +-- [decomposition] exp14 Step1/2
    |       -> grounding + policy 분리
    |       -> strong baseline 확보
    |
    +-- [protocol / all-path] exp16~18
    |       -> 교수님 프로토콜 대응
    |
    +-- [pure-HF / objective diagnosis] exp21~24
    |       -> backbone / objective 원인 분리
    |
    +-- [practical rollout track] exp25
            |
            +-- exp26: direct224 ablation
            +-- exp27: letterbox224 ablation
            +-- exp28: grounding aux + turn-family boost
                    |
                    +-- exp29: coarse-only short ablation
                    +-- exp30: bbox+coarse short ablation
                    +-- exp31: learned loss mixing follow-up
```

### 현재 의사결정 플로우

```text
문제 정의
-> 전체 failure가 아니라 turning family failure slice가 남아 있음
-> baseline 선택은 offline이 아니라 rollout 기준
-> 그래서 exp25를 baseline으로 고정
-> exp26/27은 반례 및 ablation으로 정리
-> exp28~30으로 grounding aux + turn boost 검증
-> short ablation 결과: GT만 추가해도 바로 해결되지는 않음
-> 따라서 다음 단계는 GT 추가보다 loss balance 재설계
-> exp31에서 learned mixing 검증 중
```

## 5. 미팅에서 바로 말할 핵심 결론

1. 현재 제일 솔직하고 강한 메시지는 "`exp25`가 practical baseline이고, 남은 병목은 turning commitment"이다.
2. "`exp26`은 offline이 좋아도 rollout이 0"이므로 accuracy 숫자만으로 후보를 고르면 안 된다.
3. "human-reviewed bbox GT를 붙이면 바로 해결된다"는 가설은 `exp29/30` short ablation으로 지지되지 않았다.
4. 현재 문제는 GT 품질보다 **aux loss가 실제 학습 경쟁에서 너무 약한 구조**에 가깝다.
5. 그래서 오늘 보고는 `exp25 baseline + exp28~31 active fix in progress` 구조로 정리하는 것이 가장 정확하다.

## 6. 근거 문서

- `docs/v5/PROF_MEETING_BRIEF_20260424.md`
- `docs/v5/PROF_REBUTTAL_TALK_TRACK_20260424.md`
- `docs/v5/EXP25_30_FACTOR_BREAKDOWN_20260424.md`
- `docs/v5/GROUNDING_AUX_ABLATION_20260424.md`
- `docs/v5/PROF_UPDATE_20260417_EXP14.md`
- `docs/v5/robot_server_top3_candidates_20260423.md`
