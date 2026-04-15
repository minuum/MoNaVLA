# 📊 Trajectory 분석 및 파인튜닝 영향 평가

**Date:** 2025-11-14  
**분석 대상:** `1box_hori_left_core_medium`, `1box_hori_right_core_medium`

## 🔍 실제 Trajectory 분석 (데이터 수집 코드 기준)

### 데이터 수집 코드 매핑 (`mobile_vla_data_collector.py`)

```python
WASD_TO_CONTINUOUS = {
    'w': {"linear_x": 1.15, "linear_y": 0.0, "angular_z": 0.0},  # 전진
    'a': {"linear_x": 0.0, "linear_y": 1.15, "angular_z": 0.0},  # 좌
    'd': {"linear_x": 0.0, "linear_y": -1.15, "angular_z": 0.0},  # 우
    's': {"linear_x": -1.15, "linear_y": 0.0, "angular_z": 0.0}, # 후진
    'q': {"linear_x": 1.15, "linear_y": 1.15, "angular_z": 0.0}, # 전진+좌
    'e': {"linear_x": 1.15, "linear_y": -1.15, "angular_z": 0.0}, # 전진+우
    'z': {"linear_x": -1.15, "linear_y": 1.15, "angular_z": 0.0}, # 후진+좌
    'c': {"linear_x": -1.15, "linear_y": -1.15, "angular_z": 0.0}, # 후진+우
    ' ': {"linear_x": 0.0, "linear_y": 0.0, "angular_z": 0.0}     # 정지
}
```

### 실제 Trajectory 결과

#### 1. `1box_hori_left_core_medium`
- **가장 흔한 Trajectory:** `SWWWWAQQQQQQQWWWWE` (79회, 78.2%)
- **일관성:** 94.06% (낮을수록 일관적)
- **고유 trajectory:** 6개

**Trajectory 해석:**
- `S`: 정지 (episode_start, Frame 0)
- `W`: 전진 (Frame 1-4)
- `A`: 좌 (Frame 5)
- `Q`: 전진+좌 (Frame 6-11, 대각선 이동)
- `W`: 전진 (Frame 12-15)
- `E`: 전진+우 (Frame 17)

#### 2. `1box_hori_right_core_medium`
- **가장 흔한 Trajectory:** `SWWWWDEEEEEEEWWWWQ` (31회, 100.0%)
- **일관성:** 96.77% (낮을수록 일관적)
- **고유 trajectory:** 1개

**Trajectory 해석:**
- `S`: 정지 (episode_start, Frame 0)
- `W`: 전진 (Frame 1-4)
- `D`: 우 (Frame 5)
- `E`: 전진+우 (Frame 6-11, 대각선 이동)
- `W`: 전진 (Frame 12-15)
- `Q`: 전진+좌 (Frame 17)

## ⚠️ 파인튜닝 영향 분석

### 1. 액션 값 범위 문제

**현재 상황:**
- 데이터 수집: `linear_x`, `linear_y` = ±1.15
- 학습 코드 (`MobileVLAH5Dataset`): `torch.clamp(actions_tensor, -1.0, 1.0)`

**문제점:**
```python
# mobile_vla_h5_dataset.py:166
actions_tensor = torch.clamp(actions_tensor, -1.0, 1.0)
```

**영향:**
- ✅ **중요도: 낮음** - 실제로는 정규화가 필요할 수 있음
- 액션 값 1.15가 1.0으로 클램핑되지만, 이는 정규화 과정에서 일반적
- RoboVLMs는 정규화된 액션을 기대하므로 문제 없음

### 2. 대각선 액션 (Q, E) 사용

**현재 상황:**
- Trajectory에 대각선 액션 (`Q`, `E`)이 많이 포함됨
- `Q`: 전진+좌 (linear_x=1.15, linear_y=1.15)
- `E`: 전진+우 (linear_x=1.15, linear_y=-1.15)

**영향:**
- ✅ **문제 없음** - 실제 로봇 움직임을 정확히 반영
- 학습 코드는 `action[:2]`만 사용하므로 `linear_x`, `linear_y` 모두 정확히 전달됨
- 대각선 액션은 연속 액션 공간에서 자연스러운 움직임

### 3. Trajectory 일관성

**현재 상황:**
- `1box_hori_left_core_medium`: 78.2% 일관성 (6개 고유 trajectory)
- `1box_hori_right_core_medium`: 100% 일관성 (1개 고유 trajectory)

**영향:**
- ⚠️ **주의 필요** - 왼쪽 경로는 일관성이 낮음
- 6개의 다른 trajectory가 존재하지만, 주요 패턴이 78.2%로 충분히 높음
- 학습에는 문제 없지만, 데이터 다양성 확보 필요

### 4. 액션 차원 처리

**학습 코드 확인:**
```python
# mobile_vla_h5_dataset.py:148-152
action_2d = f['actions'][t][:2]  # linear_x, linear_y만 사용
action = np.zeros(7)
action[:2] = action_2d
action[6] = 0.0  # gripper는 항상 0 (열림)
```

**영향:**
- ✅ **정상 동작** - 2D 액션을 7D로 패딩하는 것은 RoboVLMs 표준
- `angular_z`는 사용하지 않지만, 이는 의도된 설계 (2D navigation)

## 📋 결론 및 권장사항

### ✅ 문제 없음
1. **액션 값 클램핑**: 정규화 과정에서 정상적
2. **대각선 액션**: 실제 움직임을 정확히 반영, 학습에 문제 없음
3. **액션 차원 처리**: RoboVLMs 표준에 맞게 정상 동작

### ⚠️ 개선 권장
1. **Trajectory 일관성 향상**: `1box_hori_left_core_medium`의 일관성 향상 필요
   - 현재 78.2%는 학습에는 충분하지만, 더 높은 일관성을 위해 가이드 정확도 향상
2. **데이터 다양성**: 6개의 고유 trajectory는 다양성을 제공하지만, 주요 패턴 비율 확인 필요

### 🎯 파인튜닝 진행 가능
- **현재 데이터셋으로 파인튜닝 진행 가능**
- Trajectory 분석 결과, 실제 로봇 움직임을 정확히 반영하고 있음
- 학습 코드와 데이터 형식이 호환됨
- 대각선 액션 사용은 자연스러운 움직임을 나타냄

## 📊 실제 Trajectory 예시

### `1box_hori_left_core_medium` (주요 패턴)
```
Frame 0:  S (정지)
Frame 1-4: W (전진)
Frame 5:   A (좌)
Frame 6-11: Q (전진+좌, 대각선)
Frame 12-15: W (전진)
Frame 17:  E (전진+우)
```

### `1box_hori_right_core_medium` (주요 패턴)
```
Frame 0:  S (정지)
Frame 1-4: W (전진)
Frame 5:   D (우)
Frame 6-11: E (전진+우, 대각선)
Frame 12-15: W (전진)
Frame 17:  Q (전진+좌)
```

## 🔧 참고사항

1. **액션 정규화**: 학습 시 `[-1, 1]` 범위로 클램핑되는 것은 정상
2. **대각선 액션**: `Q`, `E` 키는 실제 로봇의 대각선 이동을 나타냄
3. **일관성**: 78.2% 이상이면 학습에 충분하지만, 100%에 가까울수록 좋음

