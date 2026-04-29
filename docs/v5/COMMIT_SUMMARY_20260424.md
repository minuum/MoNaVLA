# 2026-04-24 기준 커밋별 작업 요약

## 용도

- 교수님 미팅에서 "그동안 실제로 무엇을 했는지"를 커밋 단위로 설명하기 위한 문서
- 최근 핵심 흐름인 `2026-04-18 ~ 2026-04-23` 구간 위주 정리
- 기준 브랜치: `inference-integration`

## 한 줄 요약

- `4/18`: decomposition, attention, ablation, closed-loop 근거 정리
- `4/21`: pure-HF / exp18 / proxy branch / 결과 문서화
- `4/22`: evaluation workflow, resize ablation, bbox GT inspection, training strategy 정리
- `4/23`: `exp28` grounding-turnboost 실험과 교수님 미팅 브리프 추가

## 커밋별 요약

| 날짜 | 커밋 | 메시지 | 무엇을 했는가 | 미팅에서의 의미 | 바로 말할 멘트 |
| --- | --- | --- | --- | --- | --- |
| 2026-04-23 | `7c00d134` | `feat: add exp28 grounding training and meeting brief` | `exp28` config와 학습 경로를 실제 파이프라인에 연결하고, 미팅 브리프/슬라이드 초안을 추가 | `exp25` 이후 왜 `exp28`을 다음 실험으로 잡았는지 설명 가능 | "`exp25` 위에 grounding auxiliary와 turning boost를 붙인 실제 corrective run이 `exp28`입니다." |
| 2026-04-22 | `52ef45a6` | `feat: complete bbox GT inspection & add V5 training strategy` | `bbox_truth_mini` 72프레임 사람 검수 완료, YOLO-assisted labeling UI 추가, V5 학습 전략 문서화 | "GT 품질은 확인했다"는 근거 | "`bbox_truth_mini`는 72프레임 전수 검수까지 끝냈기 때문에, GT 품질 자체를 문제 삼기는 어렵습니다." |
| 2026-04-22 | `82a0b759` | `feat: add V5 evaluation and resize ablation workflows` | `exp25~27` config, bottleneck/bbox truth/rollout 평가 스크립트, resize ablation workflow 추가 | 최근 후보군을 공정하게 비교할 수 있는 평가 체계를 만든 커밋 | "`exp25`, `exp26`, `exp27` 비교는 같은 evaluation workflow 위에서 돌린 결과라서 직접 비교가 가능합니다." |
| 2026-04-21 | `ea5b66e2` | `feat: wire pure-hf models into analysis scripts` | pure-HF 모델을 attention/text-understanding 분석 스크립트에 연결 | backbone 원인 분석을 가능하게 한 연결 작업 | "이 시점부터 pure-HF와 Google-Robot을 같은 분석 코드에서 직접 비교할 수 있게 됐습니다." |
| 2026-04-21 | `2aeb94b0` | `feat: prepare pure-hf controlled ablation configs` | `exp21~23` pure-HF controlled ablation config와 연구 계획 문서 추가 | Google-Robot vs pure-HF 구분 실험의 출발점 | "text-ignore가 backbone 문제인지 확인하려고 pure-HF controlled ablation 축을 따로 열었습니다." |
| 2026-04-21 | `db40a787` | `docs: publish root-cause update for head-only collapse` | head-only collapse 원인에 대한 root-cause 문서와 pages 반영 | "왜 text가 안 먹는가"에 대한 설명 자료 | "head-only collapse 원인을 문서로 고정하면서, 이후 실험 해석 기준을 정리했습니다." |
| 2026-04-21 | `699b8e15` | `feat: add exp18 text-embedding infrastructure` | `exp18`용 text embedding 데이터셋/추론 인프라 추가 | text embedding 경로를 실제 실험축으로 확장 | "`exp18`은 text embedding 경로를 직접 실험축으로 올린 케이스였습니다." |
| 2026-04-21 | `47afc53c` | `feat: add proxy branch evaluation workflows` | proxy branch용 PM/closed-loop 평가 워크플로우 추가 | decomposition 파생 실험을 비교 가능한 형태로 만든 커밋 | "proxy branch도 PM과 closed-loop 기준으로 비교 가능하게 평가 체계를 붙였습니다." |
| 2026-04-21 | `a678cf98` | `docs: publish proxy branch results and current plan` | proxy branch 결과와 current plan 문서화 | 당시 어떤 실험을 이어갈지 의사결정 흔적 | "proxy branch 결과를 정리하면서 어떤 축을 버리고 어떤 축을 남길지 판단 근거를 만들었습니다." |
| 2026-04-21 | `429a8a8c` | `docs: publish exp18 evaluation and next-step plan` | `exp18` 평가 결과와 다음 계획 문서화 | exp18이 어디까지 갔고 왜 다음 단계로 넘어갔는지 설명 가능 | "`exp18`은 평가까지 끝낸 뒤 다음 실험으로 넘어갔고, 그 판단 근거를 이 커밋에서 문서화했습니다." |
| 2026-04-18 | `49a45c19` | `feat: closed-loop simulation eval (Phase 1) — Step2 66.7% vs Exp11 0%` | Step2 decomposition과 Exp11을 closed-loop 시뮬레이션에서 직접 비교 | "decomposition이 trajectory 안정성에서 더 낫다"는 가장 강한 근거 중 하나 | "offline 말고 closed-loop로 보면 decomposition Step2가 Exp11보다 훨씬 안정적이라는 걸 확인했습니다." |
| 2026-04-18 | `712c8d01` | `feat(exp15): head-only ablation — text collapse origin is Google-Robot backbone` | VLM frozen head-only ablation으로 text collapse 원인을 Google-Robot backbone으로 좁힘 | "LoRA가 text를 망쳤다"는 의심에 반박 가능 | "text collapse는 LoRA 때문이 아니라 Google-Robot backbone 단계에서 이미 생긴 문제로 보입니다." |
| 2026-04-18 | `833ac763` | `feat(ablation): Step 2 feature ablation — image vs bbox contribution` | bbox-only / image-only / bbox+image 비교로 Step2 성능의 주원인을 분리 | bbox만으로는 부족하고 image feature가 핵심이라는 근거 | "Step2 성능 상승의 주원인은 bbox가 아니라 image feature였고, bbox는 보조 신호에 가깝습니다." |
| 2026-04-18 | `b16b9480` | `feat(attention): causal text-ignore evidence via self-attention measurement` | self-attention 계측으로 trained model의 text attention collapse를 실측 | "instruction path가 실제로 죽어 있다"는 인과적 증거 | "instruction이 안 먹는다는 건 추측이 아니라, self-attention에서 text 비중이 0%로 떨어진 걸 실측한 결과입니다." |
| 2026-04-18 | `9840d4cc` | `feat(exp14): BBox navigation decomposition (Step 0-2) + reproducibility + same-split benchmark` | Step0~2, 5-seed repro, same-split benchmark까지 포함한 decomposition 실험 축 정리 | 현재까지 가장 강한 algorithmic baseline 정립 | "`Exp14 Step2`는 재현성과 비교 실험까지 붙어 있는, 현재 가장 강한 algorithmic baseline입니다." |

## 날짜별 흐름 설명

### 2026-04-18: decomposition과 원인 분석의 핵심 근거 확보

- `9840d4cc`
  - `Exp14 Step0~2`를 정리하고, 재현성과 same-split 비교까지 붙였다.
  - 이 시점부터 "grounding과 action mapping을 분리하면 더 안정적일 수 있다"는 축이 명확해졌다.
- `b16b9480`
  - self-attention 계측으로 trained model의 text path collapse를 실측했다.
  - 이후 교수님 질문에 대해 "text가 실제로 안 들어간다"는 근거를 제시할 수 있게 됐다.
- `833ac763`
  - Step2의 성능 상승이 bbox 때문인지 image 때문인지 분리했다.
  - 결과적으로 image feature가 주원인이고 bbox는 보조라는 해석이 가능해졌다.
- `712c8d01`
  - text collapse가 LoRA 때문이 아니라 Google-Robot backbone 단계에서 이미 발생했다는 점을 확인했다.
- `49a45c19`
  - decomposition vs end-to-end를 closed-loop에서 직접 비교해 trajectory 안정성 차이를 보여줬다.

### 2026-04-21: pure-HF, exp18, proxy branch로 원인 분리와 확장

- `2aeb94b0`, `ea5b66e2`
  - pure-HF controlled ablation을 실제로 분석 가능한 형태로 준비했다.
- `699b8e15`
  - `exp18` text-embedding 인프라를 붙여, text 경로를 다시 실험축으로 확장했다.
- `47afc53c`
  - proxy branch 평가 워크플로우를 추가해 decomposition 파생 실험도 비교 가능하게 만들었다.
- `429a8a8c`, `a678cf98`, `db40a787`
  - exp18 결과, proxy branch 결과, text-ignore root cause를 문서화해 당시 판단 근거를 고정했다.

### 2026-04-22: 최근 practical track 평가 체계 구축

- `82a0b759`
  - `exp25`, `exp26`, `exp27`을 같은 틀에서 비교할 수 있는 evaluation workflow를 구축했다.
  - resize ablation, rollout degradation, bbox truth, bottleneck split까지 묶어서 볼 수 있게 했다.
- `52ef45a6`
  - `bbox_truth_mini` 72프레임 human-reviewed GT를 최종 점검했다.
  - 동시에 labeling 도구와 V5 training strategy를 정리해, aux grounding 실험의 기반을 만들었다.

### 2026-04-23: `exp28` 실험과 미팅 준비

- `7c00d134`
  - `exp25` 기반에 grounding auxiliary + turn-family boost를 넣은 `exp28`을 실제 학습 파이프라인에 연결했다.
  - 동시에 교수님 미팅 브리프와 슬라이드 초안을 추가해, 실험과 보고를 한 묶음으로 정리했다.

## 미팅에서 바로 쓸 수 있는 커밋 중심 설명

### 버전 1. 짧게

`4월 18일에는 decomposition이 실제로 더 안정적이라는 근거와 text-ignore 원인 분석을 끝냈고, 4월 21일에는 pure-HF와 exp18 쪽 원인 분리 실험을 확장했습니다. 4월 22일에는 exp25~27 비교를 위한 evaluation workflow와 bbox GT 검수를 마쳤고, 4월 23일에는 그 위에서 exp28 grounding-turnboost 실험과 미팅 자료를 연결했습니다.`

### 버전 2. 더 기술적으로

`핵심 흐름은 세 단계였습니다. 첫째, 4월 18일에 Exp14 decomposition, attention measurement, feature ablation, closed-loop eval로 알고리즘 근거를 확보했습니다. 둘째, 4월 21일에는 pure-HF controlled ablation과 exp18 text embedding, proxy branch evaluation으로 원인 분리 실험을 확장했습니다. 셋째, 4월 22~23일에는 exp25~27 practical track 평가 체계를 만들고 bbox GT를 정리한 뒤, exp28 grounding-turnboost를 실제 학습 실험으로 연결했습니다.`

## 빠른 발표 멘트 묶음

### baseline 관련

- "`exp25`는 현재 practical baseline이고, 이건 evaluation workflow를 붙여 최근 후보군과 직접 비교한 결과입니다."
- "`exp26`은 offline이 좋아도 rollout이 0이었기 때문에 accuracy 숫자만으로 후보를 고를 수 없다는 반례입니다."

### GT / grounding 관련

- "`bbox_truth_mini`는 사람 검수를 끝낸 GT라서, 지금 문제는 GT 품질보다 그 GT를 실제 학습에 전달하는 구조 쪽에 가깝습니다."
- "`exp28` 이후 실험은 GT를 더 넣는 실험이 아니라, GT가 실제로 경쟁력 있게 작동하도록 만들려는 실험입니다."

### root-cause 관련

- "instruction path collapse는 추측이 아니라 attention 실측으로 확인한 현상입니다."
- "그리고 그 collapse는 LoRA보다 Google-Robot backbone 단계의 영향이 더 직접적이라고 보고 있습니다."

## 이번 미팅과 직접 연결되는 핵심 커밋 5개

1. `9840d4cc`
   - decomposition baseline을 정리한 커밋
2. `b16b9480`
   - text-ignore 현상을 실측으로 보인 커밋
3. `49a45c19`
   - closed-loop에서 decomposition 우위를 보인 커밋
4. `82a0b759`
   - 최근 후보군 평가 체계를 만든 커밋
5. `7c00d134`
   - `exp28`과 미팅 자료를 연결한 최신 실험 커밋

## 참고

- 최신 미팅 정리: `docs/v5/MEETING_SUMMARY_20260424_REORGANIZED.md`
- 발표용 1페이지: `docs/v5/MEETING_ONEPAGE_20260424.md`
- 발표 스크립트: `docs/v5/MEETING_SCRIPT_20260424.md`
- 현재 exp 상태: `docs/v5/EXP_STATUS_20260424.md`
