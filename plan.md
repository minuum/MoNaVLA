# Plan: Exp11 — Option B (Google-Robot Backbone + 8-class)

> **방향 확정 (2026-04-16):** Exp04 백본 + Exp09 액션 공간 통합. 아직 아무도 안 해본 조합.

---

## 리서치 요약

### 8-class는 이미 지원됨 (버그 없음)

`nav_h5_dataset_impl.py:587-590`:
```python
if self.num_classes == 6:
    mapping = {0: 0, 1: 1, 2: 2, 4: 2, 3: 3, 5: 3, 6: 2, 7: 3}
    cls_labels = [mapping.get(int(l), 0) for l in cls_labels]
# num_classes == 8이면 이 블록 스킵 → 0~7 그대로 사용
```
→ **6-class 매핑 버그는 8-class 학습에 해당 없음.** `num_classes=8`만 설정하면 됨.

### 8-class 정의 (Exp09 기준)

| Index | 이름 | 설명 |
|-------|------|------|
| 0 | STOP | 정지 |
| 1 | FORWARD | 직진 (W) |
| 2 | LEFT | 좌 슬라이드 (A) |
| 3 | RIGHT | 우 슬라이드 (D) |
| 4 | FWD+LEFT | 대각선 좌전진 |
| 5 | FWD+RIGHT | 대각선 우전진 |
| 6 | ROT_LEFT | 제자리 좌회전 (CCW, az > 0.1) |
| 7 | ROT_RIGHT | 제자리 우회전 (CW, az < -0.1) |

6-class 대비 추가된 것: `ROT_LEFT(6)`, `ROT_RIGHT(7)` — inference_server.py의 9-class와 달리 여기서는 8번이 없음.

### 두 실험의 핵심 차이

| 항목 | Exp04 (Google-Robot) | Exp09 (8-class) | Exp11 (통합) |
|------|---------------------|----------------|-------------|
| 백본 | Google-Robot pretrain | V4 ckpt | **Google-Robot** |
| num_classes | 6 | 8 | **8** |
| window_size | 6 | 8 | **8** |
| data_dir | v5_data_bak (54ep) | mobile_vla_dataset_v5 (150ep) | **mobile_vla_dataset_v5** |
| exclude_straight | ✅ | ❌ | **결정 필요 ↓** |
| learning_rate | 1e-4 | 2e-5 | **5e-5 (중간값)** |
| max_epochs | 30 | 5 | **20** |

---

## 데이터 구조 확정 (실제 측정값)

### 에피소드 타입별 실제 분포

| 타입 | ep수 | 프레임 | 주요 액션 |
|------|------|--------|---------|
| center_straight | 20 | 280 | FWD 100% — **제외** |
| left_straight | 20 | 360 | ROT_R 1프레임 + FWD 나머지 |
| right_straight | 20 | 360 | ROT_L 1프레임 + FWD 나머지 |
| center_left | 15 | 270 | FWD+L/FWD+R 위주 |
| center_right | 15 | 270 | FWD+L/FWD+R 위주 |
| left_left | 15 | 277 | FWD+L/LEFT 위주 |
| left_right | 15 | 285 | FWD+R 위주 |
| right_left | 15 | 283 | FWD+L 위주 |
| right_right | 15 | 241 | FWD+R/RIGHT 위주 |

### ROT의 의미

```
left_straight  에피소드: [ROT_R, FWD, FWD, FWD, ...]  ← 첫 프레임만 ROT_R
right_straight 에피소드: [ROT_L, FWD, FWD, FWD, ...]  ← 첫 프레임만 ROT_L
center_straight 에피소드: [FWD, FWD, FWD, ...]
```

**ROT = "첫 장면에서 바스켓이 어느 쪽인지 보고 정렬 회전"**
- 에피소드당 정확히 1프레임
- left_straight → ROT_R (바스켓 왼쪽 → 오른쪽으로 회전해서 정렬)
- right_straight → ROT_L (바스켓 오른쪽 → 왼쪽으로 회전해서 정렬)

### 확정: exclude_path_types = ["center_straight"]

- center_straight 제외 (순수 FWD만, 유용한 정보 없음)
- left/right_straight 유지 → ROT_L 20프레임 + ROT_R 20프레임 확보
- **총 130ep 사용** (90 non-straight + 20 left_straight + 20 right_straight)

### 실제 클래스 분포 (130ep 기준)

| 클래스 | 프레임 | 비율 | weight |
|--------|--------|------|--------|
| 0 STOP | 0 | 0% | 1.0 |
| 1 FORWARD | ~1,620 | ~65% | 0.5 |
| 2 LEFT | 60 | ~2.4% | 10.0 |
| 3 RIGHT | 46 | ~1.9% | 10.0 |
| 4 FWD+L | 255 | ~10.2% | 4.0 |
| 5 FWD+R | 270 | ~10.8% | 4.0 |
| 6 ROT_L | 20 | ~0.8% | **50.0** |
| 7 ROT_R | 20 | ~0.8% | **50.0** |

ROT_L/R는 1프레임/에피소드로 극히 희귀 → weight 50.0으로 강하게 보정.

---

## 변경 파일

### 1. `configs/mobile_vla_v5_exp11_google_robot_8cls.json` (신규)

```json
{
    "parent": "configs/mobile_vla_v5_exp04_google_robot.json",
    "exp_name": "v5-exp11-google-robot-8cls",
    "task_name": "mobile_vla_v5_exp11",

    "num_classes": 8,
    "window_size": 8,

    "learning_rate": 5e-5,
    "max_epochs": 20,

    "act_head": {
        "num_classes": 8,
        "action_dim": 8,
        "class_weights": [1.0, 0.5, 10.0, 10.0, 4.0, 4.0, 50.0, 50.0]
    },

    "train_dataset": {
        "data_dir": "/home/billy/25-1kp/MoNaVLA/ROS_action/mobile_vla_dataset_v5",
        "num_classes": 8,
        "window_size": 8,
        "exclude_path_types": ["center_straight"]
    },
    "val_dataset": {
        "data_dir": "/home/billy/25-1kp/MoNaVLA/ROS_action/mobile_vla_dataset_v5",
        "num_classes": 8,
        "window_size": 8,
        "exclude_path_types": ["center_straight"]
    }
}
```

Exp04 parent에서 오버라이드:
- `num_classes`: 6 → 8
- `window_size`: 6 → 8
- `class_weights`: 6개 → 8개 (ROT_L/R는 50.0으로 강하게 보정)
- `data_dir`: v5_data_bak → mobile_vla_dataset_v5
- `exclude_path_types`: ["straight"] → **["center_straight"]** (left/right_straight 유지)
- `learning_rate`, `max_epochs`: 조정
- (나머지 동일: pretrained_vlm_path, load_vlm_only=true, stratified_split)

### 2. 코드 수정 없음

8-class 지원 코드는 이미 `nav_h5_dataset_impl.py`에 있음. Config만 추가하면 됨.

---

## 리스크

| 리스크 | 원인 | 대응 |
|--------|------|------|
| ROT_L/ROT_R 학습 안 됨 | 데이터 분포 확인 전 | 학습 전 `python -c "..."` 로 클래스 분포 출력 |
| window_size=8 → 메모리 OOM | 시퀀스 길이 증가 | batch_size 줄이기 또는 window_size=6 유지 |
| val_loss가 Exp04(0.776)보다 나빠짐 | 8-class가 6-class보다 어려운 문제 | 20 epoch 이상 학습 또는 lr 조정 |
| FORWARD 과다 출력 | class_weight 부족 | FORWARD weight를 0.3으로 낮추기 |

---

## 기대 결과

| 지표 | Exp04 | Exp09 | Exp11 예상 |
|------|-------|-------|-----------|
| 백본 | Google-Robot | V4 ckpt | Google-Robot |
| val_loss | 0.776 | 1.203 | **0.5~0.9** (목표) |
| PM (Partial Match) | 18.89% | 85.7%(Forward bias 의심) | **40%+** |
| ROT_L/ROT_R | 미지원 | 있으나 미평가 | 유의미하게 등장 |

---

## 완료 체크리스트

- [x] 데이터셋 클래스 분포 사전 확인 — 130ep, ROT_L/R 각 20프레임(0.9%) 확인
- [x] `configs/mobile_vla_v5_exp11_google_robot_8cls.json` 생성 — 데이터 로딩 843 sequences 검증 완료
- [ ] 학습 실행
- [ ] PM/DM 검증 (Exp04, Exp09 대비 비교)
