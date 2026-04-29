# 2026-04-24 기준 학습 현황 및 `exp` 상태

## 한 줄 요약

- 현재 배포/실전 기준 baseline은 `exp25`
- 최근 비교군은 `exp25~31`
- `exp29`, `exp30`, `exp31` short 5-epoch run은 학습 종료
- `exp31`은 오늘(2026-04-24) 완료된 최신 follow-up이며, 아직 PM/rollout 평가는 안 끝남

## 최근 핵심 실험 상태표

| 실험 | 목적 | 학습 상태 | 현재 해석 | 다음 액션 |
| --- | --- | --- | --- | --- |
| `exp25` | balanced objective baseline | 완료 | 현재 best practical baseline | baseline 유지 |
| `exp26` | direct224 preprocessing ablation | 완료 | offline strong, rollout fail | 반례로 사용 |
| `exp27` | letterbox224 ablation | 완료 | `exp25`보다 약함 | reference로만 유지 |
| `exp28` | grounding aux + turn-family boost | 학습/평가 artifact 확보 | rollout 개선 미확인, 승격 실패 | 후속 구조 실험으로 이관 |
| `exp29` | coarse-only 5ep ablation | 학습 종료 | bbox 없이 coarse만 봐도 recovery 실패 | replacement 후보 아님 |
| `exp30` | bbox+coarse 5ep ablation | 학습 종료 | bbox까지 넣었지만 더 악화 | replacement 후보 아님 |
| `exp31` | learned loss mixing 5ep | 학습 종료 | 최신 corrective follow-up, 평가 대기 | PM/rollout 평가 필요 |

## 모델별 상세 상태

### `exp25`

- 역할: current practical baseline
- checkpoint:
  - `runs/v5_nav/kosmos/mobile_vla_v5_exp25/2026-04-22/v5-exp25-step3-balanced-objective/epoch_epoch=epoch=02-val_loss=val_loss=10.117.ckpt`
- 상태:
  - 학습 완료
  - rollout / PM 평가 완료
- 핵심 수치:
  - closed-loop success `55.6%`
  - mean FPE `0.382`
  - mean TLD `0.936`
  - PM/DM `52.38%`
- 판단:
  - 아직 대체 후보가 없으므로 baseline 유지가 맞다.

### `exp26`

- 역할: offline-strong reference
- checkpoint:
  - `runs/v5_nav/kosmos/mobile_vla_v5_exp26/2026-04-22/v5-exp26-step3-objective-direct224/epoch_epoch=epoch=14-val_loss=val_loss=7.036.ckpt`
- 상태:
  - 학습 완료
  - rollout / PM 평가 완료
- 핵심 수치:
  - PM/DM `70.24%`
  - closed-loop `0.0%`
  - mean FPE `1.189`
- 판단:
  - rollout 반례로는 중요하지만, practical candidate로는 탈락.

### `exp27`

- 역할: letterbox ablation reference
- checkpoint:
  - `runs/v5_nav/kosmos/mobile_vla_v5_exp27/2026-04-23/v5-exp27-step3-objective-letterbox224/epoch_epoch=epoch=08-val_loss=val_loss=7.932.ckpt`
- 상태:
  - 학습 완료
  - rollout / PM 평가 완료
- 핵심 수치:
  - PM/DM `15.48%`
  - closed-loop `33.3%`
  - mean FPE `0.932`
- 판단:
  - `exp25`보다 전반적으로 약해서 승격 이유가 없음.

### `exp28`

- 역할: grounding aux + turning-family oversampling 첫 실전형 보강
- checkpoint:
  - `runs/v5_nav/kosmos/mobile_vla_v5_exp28/2026-04-23/v5-exp28-step3-objective-grounding-turnboost/epoch_epoch=epoch=13-val_loss=val_loss=8.708.ckpt`
- 상태:
  - 장기 run artifact 확보
  - rollout / PM 평가 완료
- 핵심 수치:
  - PM/DM `38.10%`
  - closed-loop `0.0%`
- 판단:
  - aux 연결 자체는 됐지만 practical improvement로는 이어지지 못함.
  - 그래서 `exp29~31` 후속 구조 실험으로 넘어간 상태.

### `exp29`

- 역할: coarse-only short ablation
- artifact:
  - `runs/v5_nav/kosmos/mobile_vla_v5_exp29/2026-04-23/v5-exp29-step3-grounding-turnboost-coarseonly-5ep/last.ckpt`
- 상태:
  - `last.ckpt` 존재
  - 2026-04-23 23:55 KST 기준 저장
  - short 5-epoch 학습 종료로 해석 가능
- 핵심 수치:
  - PM/DM `21.43%`
  - bbox mean IoU `0.000`
  - IoU@0.3 `0.0%`
- 판단:
  - coarse-only가 bbox+coarse보다 덜 나쁘긴 했지만, replacement 후보는 아님.

### `exp30`

- 역할: bbox+coarse short ablation
- artifact:
  - `runs/v5_nav/kosmos/mobile_vla_v5_exp30/2026-04-24/v5-exp30-step3-grounding-turnboost-bboxcoarse-5ep/last.ckpt`
- 상태:
  - `last.ckpt` 존재
  - 2026-04-24 02:55 KST 기준 저장
  - short 5-epoch 학습 종료로 해석 가능
- 핵심 수치:
  - PM/DM `14.29%`
  - bbox mean IoU `0.000`
  - IoU@0.3 `0.0%`
- 판단:
  - bbox를 같이 넣는다고 빠르게 좋아지지 않았고, 오히려 더 악화.

### `exp31`

- 역할: learned loss mixing follow-up
- config:
  - `configs/mobile_vla_v5_exp31_step3_grounding_turnboost_learnedmix_5ep.json`
- artifact:
  - `runs/v5_nav/kosmos/mobile_vla_v5_exp31/2026-04-24/v5-exp31-step3-grounding-turnboost-learnedmix-5ep/last.ckpt`
  - best visible ckpt:
    - `epoch 00`: `val_loss 0.889`
    - `epoch 01`: `val_loss 0.951`
    - `epoch 02`: `val_loss 0.942`
- 로그 관찰:
  - train log 마지막에 `Trainer.fit stopped: max_epochs=5 reached`
  - final visible epoch4 val_loss 약 `1.030`
  - 2026-04-24 09:35 KST 기준 `last.ckpt` 저장
- 판단:
  - 오늘 기준 가장 최신 corrective run
  - 학습은 끝났고, 아직 PM/rollout 평가가 남아 있다.
  - 즉 현재 상태는 `completed training, pending evaluation`.

## 지금 바로 보고할 추천 문장

1. 현재 실전 기준 baseline은 `exp25`입니다.
2. `exp26`, `exp27`은 모두 비교는 끝났지만 baseline 교체 근거는 없습니다.
3. `exp28`은 aux를 실전에 연결한 첫 보강 실험이었지만, rollout 개선은 확인되지 않았습니다.
4. `exp29`, `exp30`은 5-epoch short ablation으로 종료됐고, GT를 붙여도 바로 해결되지는 않았습니다.
5. 오늘 가장 최신 상태는 `exp31` short run 완료이며, 지금 필요한 것은 추가 학습보다 평가입니다.
