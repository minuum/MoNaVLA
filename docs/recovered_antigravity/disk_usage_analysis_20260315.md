# MoNaVLA 디스크 사용량 분석 및 정리 우선순위 리포트

Recovery source:
- `~/.gemini/antigravity/brain/2db62ac0-6d0d-4022-988d-516c1bd4fdac/disk_usage_analysis.md`

Recovery note:
- 이 문서는 Antigravity에서 보관된 분석 문서를 복구한 것입니다.
- 현재 저장소 기준으로는 참고 문서이며, 여기 적힌 삭제 후보를 자동 실행하지 않습니다.

현재 디스크 사용량이 **95% (사용 1.6T / 가용 102G)**로 매우 여유가 없는 상태입니다. 원활한 V4 학습 및 추론을 위해 정리가 시급합니다.

## 주요 용량 차지 항목

| 경로 | 용량 | 설명 |
| :--- | :--- | :--- |
| `third_party/RoboVLMs/runs` | **84G** | 과거 V2, V3 실험의 체크포인트 및 로그 |
| `runs/v4_nav` | **33G** | 현재 진행 중인 V4 학습 체크포인트 |
| `ROS_action` | **33G** | 데이터셋 (V2, V3, basket 등) |
| `checkpoints/backups` | **14G** | 과거 모델 백업 파일 |
| `git_recovery_backup` | **7.0G** | Git 복구용 백업 데이터 |

## 정리 우선순위

### 우선순위 1. 구버전 실험 결과

- `third_party/RoboVLMs/runs/v3_classification` (**63G**)
  - V3-Exp05, Exp06, Exp07 등 종료된 실험의 중간 체크포인트
  - 각 체크포인트가 약 **8.2GB**
  - best 또는 최종 결과만 남기고 나머지는 정리 후보
- `third_party/RoboVLMs/runs/exp_v2_series` (**15G**)
  - 오래된 V2 계열 실험 데이터

### 우선순위 2. 현재 학습 중인 V4 중간 결과

- `runs/v4_nav/kosmos/mobile_vla_v4_exp01/.../` (**33G**)
  - Epoch 02, 03, 04 체크포인트가 각각 약 **8.2GB**
  - 학습 안정화 이후 `last.ckpt`와 최적 체크포인트만 남기는 방향 검토

### 우선순위 3. 중복 및 백업 데이터

- `git_recovery_backup` (**7.0G**)
  - 현재 레포지토리 안정화 여부 확인 후 정리 판단
- `best_robovlms_mobile_model_epoch_1.pt` (**5.2G**)
  - 다른 백업 보유 여부 먼저 확인 필요

### 우선순위 4. 데이터셋 관리

- `ROS_action/` 하위 데이터셋
  - `basket_dataset_v2` (13G)
  - `mobile_vla_dataset` (17G)
  - 미사용 버전 또는 중복 데이터 검토 필요

## 향후 조치 제안

1. V3 정밀 정리
   - `last.ckpt`를 제외한 `epoch_*.ckpt` 정리 시 약 **40~50GB** 확보 가능
2. V4 자동 관리
   - trainer 설정에서 `save_top_k=1` 같은 방식으로 체크포인트 수 제한
3. 아카이빙
   - 중요한 결과는 외부 스토리지나 클라우드로 이동

> 주의
> 이 문서는 분석용입니다. 명확한 요청 전까지 어떠한 파일도 삭제하지 않습니다.

