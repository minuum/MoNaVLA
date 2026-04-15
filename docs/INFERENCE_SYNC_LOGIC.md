# Mobile VLA 추론-수집 동기화 로직 (Synchronization Logic)

## 1. 배경 (Background)
RoboVLMs 기반의 Mobile VLA 시스템에서 **"데이터 수집(Data Collection)"**과 **"실시간 추론(Real-time Inference)"** 간의 시간적 불일치가 발생할 수 있습니다. 이를 해결하기 위해 두 시스템의 주기를 일치시키는 작업을 수행했습니다.

## 2. 불일치 분석 (Mismatch Analysis)

| 시스템 | 기존 설정 | 동작 방식 |
| :--- | :--- | :--- |
| **데이터 수집 (Collector)** | **0.3초** | 키 입력 시 0.3초 동안 이동 후 정지 (Burst Mode) |
| **모델 정책 (Policy)** | **0.4초** | 학습된 모델은 0.4초 동안의 속도 제어를 의도함 |
| **실시간 추론 (Inference)** | **0.5초** | 0.5초 주기로 추론 루프 실행 |

* **문제점:** 수집된 데이터는 0.3초 단위의 움직임으로 구성되어 있는데, 추론이 0.5초마다 이루어지면 로봇의 제어 주기가 느려지고 반응성이 떨어지며, 학습된 분포(0.3초 움직임)와 추론 환경(0.5초 지속) 간의 괴리가 발생합니다.

## 3. 결정 사항 (Decision)
**"추론 주기를 수집 데이터에 맞춘다."**

* **변경 전:** Inference Interval = 0.5s
* **변경 후:** Inference Interval = **0.3s**

### 논리적 근거
1. **데이터 우선 원칙:** 학습된 모델은 수집된 데이터(0.3초 Burst)의 물리적 특성을 학습했습니다. 추론 시에도 이와 동일한 호흡(0.3초)으로 명령을 내려야 모델이 의도한 대로 움직입니다.
2. **반응성 향상:** 0.5초에서 0.3초로 주기를 단축함으로써 로봇의 반응 속도가 향상됩니다.
3. **구현 일치:** `mobile_vla_data_collector.py`의 `move_duration` (0.3s)과 `vla_inference_node.py`의 `inference_interval` (0.3s)을 일치시켜 **[수집-학습-추론]** 파이프라인의 시간적 정합성을 확보했습니다.

## 4. 적용 코드
* **파일:** `ROS_action/src/vla_inference/vla_inference/vla_inference_node.py`
* **변경 내용:**
  ```python
  # self.inference_interval = 0.5  # 기존
  self.inference_interval = 0.3  # 변경: 데이터 수집 burst 시간과 동기화
  ```
