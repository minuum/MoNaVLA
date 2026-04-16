# Plan: Exp11 - Option B (Google-Robot Backbone + 8-class)
작성일: 2026-04-16

## 1. 목표
- 해결하려는 문제: Exp04의 Google-Robot 백본 성능을 유지하면서 8-class 액션 공간(ROT_L/ROT_R 포함)으로 확장한다.
- 기대 결과: 8-class 학습 설정을 안정적으로 구성하고, PM/DM 기준에서 Exp04와 Exp09 대비 의미 있는 비교가 가능해진다.
- 이번 문서 단계:
  - [x] 리서치만 완료
  - [x] 구현 전 승인 대기
  - [ ] 승인 후 구현 예정

> 방향 확정 (2026-04-16): Exp04 백본 + Exp09 액션 공간 통합. 아직 아무도 안 해본 조합.

## 2. 배경 / 현재 상태
- 현재 동작: Exp04는 6-class Google-Robot 기반으로 가장 낮은 `val_loss=0.776`을 기록했다.
- 문제 증상: 현재 최선 모델은 6-class라서 `ROT_LEFT`, `ROT_RIGHT`를 직접 학습하지 못한다.
- 관련 실험/이전 작업:
  - Exp04: Google-Robot pretrain, 6-class, 현재 최선
  - Exp09: 8-class 액션 공간 실험
  - Exp11: Exp04 백본과 Exp09 액션 공간의 통합 시도
- 참고 문서 / 커밋 / 이슈:
  - `configs/mobile_vla_v5_exp04_google_robot.json`
  - `docs/v5/exp09/report.md`
  - `configs/mobile_vla_v5_exp11_google_robot_8cls.json`

## 3. 리서치 요약
### 3.1 확인한 코드 / 데이터 / 문서
- 파일:
  - `robovlm_nav/datasets/nav_h5_dataset_impl.py`
  - `configs/mobile_vla_v5_exp04_google_robot.json`
  - `configs/mobile_vla_v5_exp11_google_robot_8cls.json`
  - `robovlm_nav/serve/inference_server.py`
- 확인한 핵심 동작:
  - `num_classes == 6`일 때만 6-class 병합 매핑이 적용된다.
  - `num_classes == 8`이면 기존 0~7 레이블이 그대로 유지된다.
  - V5 데이터셋에는 `center_straight`, `left_straight`, `right_straight` 및 곡선 경로 타입이 섞여 있다.
- 기존 패턴 / 제약:
  - Exp04는 Google-Robot 백본을 그대로 유지해야 한다.
  - `center_straight`는 정보량이 낮고 FORWARD bias를 심화시킨다.
  - ROT_L/R는 희귀 클래스라 class weight 보정이 필요하다.

### 3.2 핵심 근거
- 근거 1: 8-class는 코드 수정 없이 데이터셋 레이어에서 이미 지원된다.
- 근거 2: `left_straight`, `right_straight`에는 각 에피소드 첫 프레임의 ROT 신호가 포함되어 있다.
- 근거 3: `center_straight`만 제외하면 130개 에피소드에서 ROT_L/R 각 20프레임을 확보할 수 있다.

```python
if self.num_classes == 6:
    mapping = {0: 0, 1: 1, 2: 2, 4: 2, 3: 3, 5: 3, 6: 2, 7: 3}
    cls_labels = [mapping.get(int(l), 0) for l in cls_labels]
# num_classes == 8이면 이 블록 스킵 -> 0~7 그대로 사용
```

### 3.3 데이터 구조 확정
#### 에피소드 타입별 실제 분포

| 타입 | ep수 | 프레임 | 주요 액션 |
|------|------|--------|---------|
| center_straight | 20 | 280 | FWD 100% - 제외 |
| left_straight | 20 | 360 | ROT_R 1프레임 + FWD 나머지 |
| right_straight | 20 | 360 | ROT_L 1프레임 + FWD 나머지 |
| center_left | 15 | 270 | FWD+L/FWD+R 위주 |
| center_right | 15 | 270 | FWD+L/FWD+R 위주 |
| left_left | 15 | 277 | FWD+L/LEFT 위주 |
| left_right | 15 | 285 | FWD+R 위주 |
| right_left | 15 | 283 | FWD+L 위주 |
| right_right | 15 | 241 | FWD+R/RIGHT 위주 |

#### ROT의 의미

```text
left_straight  에피소드: [ROT_R, FWD, FWD, FWD, ...]
right_straight 에피소드: [ROT_L, FWD, FWD, FWD, ...]
center_straight 에피소드: [FWD, FWD, FWD, ...]
```

- ROT = 첫 장면에서 바스켓 위치를 보고 정렬 회전하는 신호
- 에피소드당 정확히 1프레임만 등장
- `exclude_path_types = ["center_straight"]`로 확정
- 총 130ep 사용: 90 non-straight + 20 left_straight + 20 right_straight

#### 실제 클래스 분포 (130ep 기준)

| 클래스 | 프레임 | 비율 | weight |
|--------|--------|------|--------|
| 0 STOP | 0 | 0% | 1.0 |
| 1 FORWARD | ~1,620 | ~65% | 0.5 |
| 2 LEFT | 60 | ~2.4% | 10.0 |
| 3 RIGHT | 46 | ~1.9% | 10.0 |
| 4 FWD+L | 255 | ~10.2% | 4.0 |
| 5 FWD+R | 270 | ~10.8% | 4.0 |
| 6 ROT_L | 20 | ~0.8% | 50.0 |
| 7 ROT_R | 20 | ~0.8% | 50.0 |

## 4. 제안 변경 사항
### 4.1 변경 개요
- 무엇을 바꾸는가:
  - Exp04 parent를 기반으로 하는 Exp11 8-class config를 사용한다.
  - `window_size`, `num_classes`, `class_weights`, `exclude_path_types`를 재설정한다.
- 무엇은 바꾸지 않는가:
  - `nav_h5_dataset_impl.py`의 8-class 지원 로직은 수정하지 않는다.
  - Google-Robot pretrained backbone 자체는 바꾸지 않는다.

### 4.2 변경 파일
1. `configs/mobile_vla_v5_exp11_google_robot_8cls.json`
   - `num_classes: 8`
   - `window_size: 8`
   - `learning_rate: 5e-5`
   - `max_epochs: 20`
   - `class_weights: [1.0, 0.5, 10.0, 10.0, 4.0, 4.0, 50.0, 50.0]`
   - `exclude_path_types: ["center_straight"]`
2. 코드 수정 없음
   - 8-class 지원 코드는 이미 존재하므로 config만 추가한다.

### 4.3 구현 방식
1. Exp04 parent config를 기준으로 Exp11 전용 override 작성
2. 데이터셋 로딩이 8-class로 정상 동작하는지 확인
3. 학습 후 PM/DM 기준으로 Exp04, Exp09와 비교

```json
{
  "parent": "configs/mobile_vla_v5_exp04_google_robot.json",
  "exp_name": "v5-exp11-google-robot-8cls",
  "task_name": "mobile_vla_v5_exp11",
  "num_classes": 8,
  "window_size": 8,
  "learning_rate": 5e-5,
  "max_epochs": 20
}
```

### 4.4 핵심 비교

| 항목 | Exp04 | Exp09 | Exp11 |
|------|-------|-------|-------|
| 백본 | Google-Robot pretrain | V4 ckpt | Google-Robot |
| num_classes | 6 | 8 | 8 |
| window_size | 6 | 8 | 8 |
| data_dir | v5_data_bak (54ep) | mobile_vla_dataset_v5 (150ep) | mobile_vla_dataset_v5 |
| exclude_straight | 전체 straight 제외 | 미적용 | center_straight만 제외 |
| learning_rate | 1e-4 | 2e-5 | 5e-5 |
| max_epochs | 30 | 5 | 20 |

## 5. 검증 계획
- 검증 명령:
  - 데이터셋 클래스 분포 출력
  - Exp11 config 로딩 확인
  - 학습 후 PM/DM 평가 스크립트 실행
- 성공 기준:
  - 8-class 데이터 로딩이 정상 동작할 것
  - ROT_L/R가 학습 대상에 포함될 것
  - Exp04 대비 심각한 성능 붕괴 없이 비교 가능한 결과가 나올 것
- 수동 확인 항목:
  - 학습 로그에서 클래스 편향 확인
  - PM/DM 결과에서 FORWARD bias 지속 여부 확인
  - ROT_L/R 예측이 실제로 등장하는지 확인

## 6. 리스크 / 트레이드오프
| 리스크 | 원인 | 대응 |
|--------|------|------|
| ROT_L/ROT_R 학습 안 됨 | 희귀 클래스 분포 | 학습 전 클래스 분포 재확인, weight 유지 |
| window_size=8 OOM | 시퀀스 길이 증가 | batch_size 축소 또는 window_size=6 재검토 |
| val_loss 악화 | 8-class가 더 어려운 문제 | epoch 증가 또는 lr 조정 |
| FORWARD 과다 출력 | class_weight 부족 | FORWARD weight를 추가 조정 |

## 7. 롤백 / 대안
- 롤백 방법:
  - Exp11이 실패하면 Exp04 설정으로 복귀해 baseline 유지
- 대안 A:
  - window_size를 6으로 낮춰 메모리 안정성을 우선 확보
- 대안 B:
  - FORWARD weight를 더 낮추고 ROT_L/R weight를 추가 상향

## 8. 작업 순서 가이드 (DO NOT EXECUTE YET)
1. 데이터셋 클래스 분포 재확인
2. `configs/mobile_vla_v5_exp11_google_robot_8cls.json` 검토
3. 학습 실행
4. PM/DM 검증 및 Exp04, Exp09와 비교

## 9. 완료 체크리스트
- [x] 리서치 완료
- [x] 사용자 피드백 반영
- [x] 구현 승인 획득
- [x] 구현 완료
- [ ] 검증 완료
- [ ] 결과 문서화

## 10. 기대 결과

| 지표 | Exp04 | Exp09 | Exp11 예상 |
|------|-------|-------|-----------|
| val_loss | 0.776 | 1.203 | 0.5~0.9 |
| PM (Partial Match) | 18.89% | 85.7% (Forward bias 의심) | 40%+ |
| ROT_L/ROT_R | 미지원 | 있으나 미평가 | 유의미하게 등장 |
