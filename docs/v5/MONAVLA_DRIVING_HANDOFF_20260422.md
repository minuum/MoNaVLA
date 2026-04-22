# MoNaVLA Driving Handoff (2026-04-22)

이 문서는 `monavla-driving` 쪽에 전달할 현재 기준 배포 후보와,
`end-to-end` / `bbox-proxy` 두 경로의 차이를 한 번에 정리한 handoff 메모다.

## Main Robot Server

- Main deploy host: `soda@100.85.118.58`
- Main deploy directory: `~/MoNaVLA`

## Recommendation Summary

### A. End-to-end deploy candidate

- Primary: `exp17`
- Fallback: `exp18`

현재 end-to-end 중 로봇 서버에 바로 올릴 수 있는 건 이 두 개뿐이다.
둘 다 기존 API 서버(`robovlm_nav/serve/inference_server.py`)로 바로 배포 가능하다.

#### Primary: Exp17

- Checkpoint:
  - `runs/v5_nav/kosmos/mobile_vla_v5_exp17/2026-04-20/v5-exp17-step3-balanced/epoch_epoch=epoch=14-val_loss=val_loss=1.325.ckpt`
- Config:
  - `configs/mobile_vla_v5_exp17_step3_balanced.json`
- Reason:
  - closed-loop 기준 현재 end-to-end 1순위
  - `exp18`과 동률이지만 구조가 더 단순해서 서버 리스크가 낮음

#### Fallback: Exp18

- Checkpoint:
  - `runs/v5_nav/kosmos/mobile_vla_v5_exp18/2026-04-21/v5-exp18-vla-text-fusion/epoch_epoch=epoch=14-val_loss=val_loss=1.325.ckpt`
- Config:
  - `configs/mobile_vla_v5_exp18_vla_finetuned.json`
- Reason:
  - `exp17`과 같은 closed-loop (`11.1%`)
  - text embedding fusion이 있어 추론 경로는 더 복잡함

### B. BBox / Proxy deploy candidate

- Current best practical branch: `Exp19`
- Reference baseline: `Step2`

중요:
- 이 경로는 현재 **checkpoint 기반 API 모델이 아니다**
- `scripts/test_v5_bbox_nav_exp19_proxy.py`가 bbox cache를 읽고 작은 MLP를 학습/평가하는 구조다
- 즉 지금 상태로는 `inference_server.py`에 바로 꽂히지 않는다

#### Exp19 package

- Script:
  - `scripts/test_v5_bbox_nav_exp19_proxy.py`
- Required bbox cache:
  - `docs/v5/bbox_nav_step1/bbox_dataset.json`
- Reference summaries:
  - `docs/v5/bbox_nav_exp19_proxy/summary.json`
  - `docs/v5/bbox_nav_step2/summary.json`

#### Current performance note

- `Step2` PM ref: `75.95%`
- `Exp19` PM: `76.58%`
- Closed-loop note from internal docs:
  - `Step2`: `66.7%`
  - `Exp19`: `55.6%`

실전형 bbox/proxy로 보낼 자료는 `Exp19`가 맞지만,
지금은 **서버 API 추론기로 포장된 상태가 아니라 연구 스크립트 상태**다.

## Deployment Difference

### 1. End-to-end path

입력:
- RGB image
- instruction text

추론 구조:
- `image -> KosMos-2 VLM -> action head -> discrete/continuous action`

서버 진입점:
- `robovlm_nav/serve/inference_server.py`

필수 env:
- `VLA_CHECKPOINT_PATH`
- `VLA_CONFIG_PATH`
- `VLA_API_KEY`

상태 확인:
- `GET /health`

추론 호출:
- `POST /predict`

장점:
- 현재 서버 코드와 바로 연결됨
- ROS launch path가 이미 있음

단점:
- 현재 closed-loop 성능이 낮음
- bbox/proxy practical branch보다 실전성은 약함

### 2. BBox / Proxy path

입력:
- bbox history
- low-res image feature
- optional proxy features (`area`, `center_error_x`, `abs_delta_cx`, `recent_bbox_consistency`)

추론 구조:
- `bbox/proxy features -> small MLP -> action class`

현재 구현 위치:
- `scripts/test_v5_bbox_nav_step2.py`
- `scripts/test_v5_bbox_nav_exp19_proxy.py`
- `scripts/sim/evaluate_closed_loop_v5.py --model step2|exp19`

장점:
- practical closed-loop는 end-to-end보다 강함
- 병목 해석이 쉬움

단점:
- API 서버 통합이 아직 안 됨
- persistent checkpoint / service wrapper가 없음
- bbox producer와 runtime feature builder를 같이 설계해야 함

## What To Send To monavla-driving

### End-to-end package

- `runs/v5_nav/kosmos/mobile_vla_v5_exp17/2026-04-20/v5-exp17-step3-balanced/epoch_epoch=epoch=14-val_loss=val_loss=1.325.ckpt`
- `configs/mobile_vla_v5_exp17_step3_balanced.json`
- `runs/v5_nav/kosmos/mobile_vla_v5_exp18/2026-04-21/v5-exp18-vla-text-fusion/epoch_epoch=epoch=14-val_loss=val_loss=1.325.ckpt`
- `configs/mobile_vla_v5_exp18_vla_finetuned.json`
- `robovlm_nav/serve/inference_server.py`
- `ROS_action/start_mobile_vla.sh`
- `ROS_action/src/mobile_vla_package/launch/launch_mobile_vla.launch.py`

### BBox / Proxy package

- `scripts/test_v5_bbox_nav_step2.py`
- `scripts/test_v5_bbox_nav_exp19_proxy.py`
- `scripts/sim/evaluate_closed_loop_v5.py`
- `docs/v5/bbox_nav_step1/bbox_dataset.json`
- `docs/v5/bbox_nav_step2/summary.json`
- `docs/v5/bbox_nav_exp19_proxy/summary.json`

## Current Practical Guidance

- If the goal is **immediate robot deployment with existing API**:
  - send `exp17`
  - keep `exp18` as fallback

- If the goal is **best practical navigation research branch**:
  - send `Exp19` materials too
  - but mark them as `not yet server-integrated`

## Next Integration Task

If `monavla-driving` wants bbox/proxy runtime deployment,
the next missing piece is:

- a lightweight `proxy_inference_server.py`
  - loads bbox cache / runtime bbox extractor
  - rebuilds Exp19 proxy features online
  - serves the same `/predict` contract as the end-to-end server

Until that exists, `exp17/18` are deployable,
while `Exp19` is transferable as a research package, not a drop-in API model.
