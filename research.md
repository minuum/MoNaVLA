# MoNaVLA V5 서버 사이드 리서치 (2026-04-08)

---

## ⚠️ 미팅록 기반 확정 전략 (Ground Truth)

### 1. Fixed Path Strategy (에피소드 단순화)
- **9개 Canonical Paths** 집중 (좌/중/우 × 3)
- 출발 지점 고정, 초기 Heading 고정 → 변수 최소화
- **목표:** 에피소드 150개 수준에서 "몸체 회전 + 중앙 정렬" 완벽 구현 증명

### 2. Visual Grounding 검증 (BBox-Centric)
- **핵심 지표:** 바스켓이 중앙으로 이동 → BBox도 함께 중앙으로 이동해야 함
- `gradio_offline_h5_analyzer.py`로 전수 조사
- BBox가 흔들리면 Action 학습도 실패로 간주

### 3. 프롬프트 확정
```
"Navigate toward the gray basket until it gets closer"
```
모든 스크립트에서 이 프롬프트로 통일.

### 4. Discrete 6-Class Action (V5 방향)
- V4 continuous regression → V5는 **6-class discrete**로 복귀
- Forward / Left / Right / Stop 등 6가지 키 입력 매핑
- 수집 시 "정답 동작" 위주 수집으로 데이터 Quality 보장

### 5. 즉시 Action Items (서버 관련)

| 구분 | 작업 | 상태 |
|:---|:---|:---|
| **수집** | 좌/중/우 각 20개, 총 150개 V5 데이터 확보 | 진행 중 |
| **프롬프트** | 모든 스크립트 프롬프트 `"Navigate until closer"`로 업데이트 | **대기** |
| **시각화** | BBox 중앙 수렴 GIF/HTML 생성 (교수님 데모용, 월/화) | 대기 |
| **자원** | H100 지원 요청 근거 준비 (학습 소요 시간, 병목 지점) | 대기 |

---


## 1. V5의 핵심 전환점

| 항목 | V4 | V5 (Phase 2) |
|------|-----|--------------|
| **학습 데이터** | 다양한 환경 (151+ 에피소드) | 고정된 9개 경로 반복 (45~225 에피소드) |
| **목표** | 일반화 능력 | Gray Basket 정밀 제어 (95% 성공률) |
| **액션 스타일** | Forward/Curved/Diagonal 혼합 | Centering + Body Rotation + STOP 특화 |
| **피드백** | 이미지만으로 판단 | 거리/각도 센서 기반 정밀 제어 |
| **서버 역할** | 순수 추론 엔진 | 추론 + 수집 + 검증 + 학습 지원 통합 플랫폼 |

**V5 목표:** 9개 고정 경로(좌/중/우 각 3개) × 5회 반복 × 조명 변화 = 45+ 에피소드로 95% 정밀도 달성

---

## 2. 현재 inference_server.py 한계

**현재 구조 (`robovlm_nav/serve/inference_server.py`, 1083줄):**
- `POST /predict`: image + instruction → [linear_x, angular_z]
- `POST /health`, `POST /reset` (버퍼 초기화)
- ActionBuffer: 10개 액션 미리 예측 (Chunk Reuse)
- 스레드 안전 액션 저장소

**V5를 위해 없는 것:**

| 부족한 점 | 설명 |
|---------|------|
| 센서 피드백 입력 | distance, imu_yaw, position 입력 처리 없음 |
| 에피소드 상태 추적 | 각 호출이 독립적, 누적 상태 없음 |
| 데이터 로깅 | 추론 입출력 저장 없음 |
| 조건부 정지 | 센서 기반 STOP 강제 로직 없음 |
| 수집 모드 | 온라인 데이터 수집 엔드포인트 없음 |
| 데이터 검증 | 수집된 HDF5 검증 기능 없음 |

---

## 3. 서버에서 새로 구현해야 할 기능

### 🔴 MUST-HAVE (V5 최소 구현)

#### 3.1 `/collect` 엔드포인트
추론 + 센서 데이터를 함께 받아 HDF5에 저장하는 핵심 엔드포인트.

```python
POST /collect
Input: {
    image: str,            # base64
    instruction: str,
    robot_id: str,         # "fevers"
    episode_id: str,       # "episode_20260408_120000"
    frame_index: int,
    sensor_data: {
        distance_mm: float,
        imu_yaw: float,
        position: [float, float],
        timestamp: float
    },
    ground_truth_action?: [float, float]  # 수동 라벨링 시
}
Output: {
    status: "saved" | "error",
    file_path: str,
    server_latency_ms: float
}
```

#### 3.2 `/episode/start` & `/episode/end`
에피소드 라이프사이클 관리.

```python
POST /episode/start
Input: {
    robot_id: str,
    episode_id: str,
    start_position: [float, float],
    target_object: str,   # "gray_basket"
    environment: str,
    lighting: str
}
Output: { episode_uuid: str }

POST /episode/end
Input: {
    episode_uuid: str,
    success: bool,
    final_distance_mm: float,
    total_frames: int,
    completion_reason: str  # "reached" | "timeout" | "collision"
}
Output: { status: "closed", hdf5_path: str, validation_errors: [...] }
```

#### 3.3 센서 데이터 포함 HDF5 확장 포맷

**V4 형식:**
```
episode.h5
├── images    [N, 224, 224, 3]
├── actions   [N, 2]
└── metadata  { instruction: str }
```

**V5 형식:**
```
episode.h5
├── images              [N, 224, 224, 3]
├── actions             [N, 2]
├── distance            [N]        # 거리센서 (mm), INT16 압축
├── imu_yaw             [N]        # 각도 (rad)
├── positions           [N, 2]     # 로봇 위치 (x, y)
├── sensor_timestamps   [N]        # 센서 타임스탬프
└── metadata            {
    ├── instruction: str
    ├── robot_id: str
    ├── environment: str
    ├── lighting_condition: str
    ├── target_object: str
    ├── success: bool
    └── completion_reason: str
}
```

#### 3.4 `/validate/episode`
수집 데이터 자동 검증.

```python
POST /validate/episode
Input: { hdf5_path: str }
Output: {
    is_valid: bool,
    checks: {
        frame_count:        { expected, actual, pass },
        sensor_sync:        { expected, actual, pass },
        action_range:       { min, max, pass },
        distance_monotonic: { pass, reason? },
        outliers:           { count, indices }
    },
    warnings: [str],
    errors: [str]
}
```

**핵심 검증 로직:**
- 거리가 단조 감소하는가? (충돌 없음 확인)
- 액션이 정상 범위 내인가? (linear_x: [0,1], angular_z: [-1,1])
- 센서와 이미지 타임스탬프 동기화 확인
- 이상치(outlier) 프레임 탐지

### 🟡 SHOULD-HAVE (1주일 내 추가)

#### 3.5 `/dataset/stats`
```python
POST /dataset/stats
Input: { hdf5_path: str }
Output: {
    episode_count: int,
    total_frames: int,
    action_distribution: {
        "stop":    { count, percentage },
        "forward": { count, percentage },
        ...
    },
    distance_statistics: { min, max, mean, std },
    imbalance_warnings: [str]
}
```

#### 3.6 센서 기반 조건부 정지

```python
CLOSE_THRESHOLD_MM = 250  # 25cm

def should_stop(model_output, sensor_data):
    # 센서가 근접 감지하면 모델 무시하고 STOP 강제
    if sensor_data.distance_mm < CLOSE_THRESHOLD_MM:
        return True
    return False
```

#### 3.7 로깅 시스템
매 추론 호출의 입출력, 센서, 지연시간 기록.

### 🟢 NICE-TO-HAVE (향후 고도화)

- **다중 전략 관리**: Receding Horizon vs Chunk Reuse 자동 전환
- **세션 상태 기반 추론**: 에피소드 진행 상황에 따른 동적 전략 변경
- **실시간 모니터링**: 대시보드 메트릭 제공

---

## 4. 아키텍처 변화

### V4 (현재)
```
fevers (Jetson)
  └── vla_api_client.py → POST /predict → Billy A5000
                                              └── 추론만
```

### V5 (목표)
```
fevers (Jetson)
  ├── /camera/image_raw  ─┐
  ├── /distance_sensor    ├─→ vla_collection_client.py → Billy A5000
  ├── /imu/data           │                                ├── POST /collect
  └── /odom             ──┘                                ├── POST /episode/start
                                                           ├── POST /episode/end
                                                           ├── POST /validate/episode
                                                           └── POST /dataset/stats

Billy A5000
  ├── 추론 (기존 /predict)
  ├── 데이터 수집 (/collect)
  ├── 에피소드 관리 (/episode/*)
  └── 검증/통계 (/validate/*, /dataset/*)
         ↓
    HDF5 저장소 (V5 확장 포맷)
         ↓
    학습 파이프라인 (nav_h5_dataset_impl.py 수정 필요)
```

---

## 5. 코드 구조 개선 방향

**현재:** `MobileVLAInference` 클래스가 너무 많은 책임

**개선:** 책임 분리

```python
class ModelInference:
    """모델 추론만"""
    def predict(self, images, instruction) -> actions

class SensorIntegration:
    """센서 데이터 처리 + 조건부 정지"""
    def validate(self, sensor_data) -> bool
    def condition_stop(self, model_action, sensor_data) -> action

class EpisodeManager:
    """에피소드 라이프사이클"""
    def start_episode(self, metadata) -> uuid
    def add_frame(self, image, sensors, action)
    def end_episode(self, success, reason) -> hdf5_path

class DataCollector:
    """데이터 수집 & 저장"""
    def save_to_hdf5(self, episode_state)
    def validate(self, hdf5_path) -> ValidationResult
```

---

## 6. 의존성 (구현 전 확인 필요)

서버 구현 전에 확정되어야 할 것들:
1. **로봇 센서 ROS2 토픽명** — `/distance_sensor`, `/imu/data`, `/odom` 형식 확인
2. **네트워크 구조** — fevers ↔ Billy 간 통신 (현재 100.86.152.29:8000)
3. **HDF5 저장 위치** — Billy 서버의 저장 경로 결정
4. **`nav_h5_dataset_impl.py`** — 학습 코드가 V5 포맷(센서 데이터 포함) 읽도록 수정 필요
5. **`vla_api_client.py`** — 로봇 클라이언트를 수집 모드로 확장 필요

---

## 7. 구현 우선순위 요약

```
Week 1: 수집 파이프라인
  - 데이터 모델 정의 (SensorData, CollectRequest 등)
  - /collect 엔드포인트
  - /episode/start, /episode/end
  - HDF5 V5 포맷 저장

Week 2: 검증 & 분석
  - /validate/episode (단조 감소, 범위, 동기화)
  - /dataset/stats
  - 센서 기반 조건부 정지 로직
  - 로깅 시스템

Week 3: 고도화
  - 다중 전략 (Receding Horizon / Chunk Reuse)
  - 실시간 모니터링
  - nav_h5_dataset_impl.py V5 포맷 지원
```
