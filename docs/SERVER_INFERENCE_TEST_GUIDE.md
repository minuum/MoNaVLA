# 🧪 Mobile VLA 서버 사이드 추론 테스트 가이드

**작성일**: 2026-02-12  
**대상**: Mobile VLA Navigation 모델 (EXP-01 ~ EXP-17)  
**목적**: 학습된 모델의 성능을 서버 환경에서 정량적/정성적으로 검증하기 위한 테스트 체계 정리

---

## 🚀 1. 테스트 방식 개요

서버 사이드 테스트는 크게 **API 기반 테스트**, **독립형(Standalone) 테스트**, **성능/양자화 테스트**의 세 가지 범주로 나뉩니다.

| 테스트 유형 | 주요 목적 | 위치 | 방식 |
|:---|:---|:---|:---|
| **API 기반** | 실제 로봇-서버 통신 환경 모사 | `scripts/test/api_*` | FastAPI 서버 호출 |
| **standalone** | 모델 자체의 추론 로직 및 가중치 확인 | `RoboVLMs/vla_test/` | 직접 모델 로드 |
| **정량 평가** | Dataset 기준 성공률(PM/DA) 측정 | `scripts/test/test_basket_batch_eval.py` | 배치 처리 및 통계 |
| **양자화** | INT8/FP16 성능 및 메모리 점유율 확인 | `scripts/test/test_*_int8.py` | BitsAndBytes 적용 |

---

## 📂 2. 주요 테스트 파일 및 소스 출처

### A. API 기반 테스트 (가장 권장되는 실전 모사 방식)
이 방식은 로봇이 이미지를 서버로 쏘고 액션을 받아가는 과정을 그대로 재현합니다.

- **`scripts/test/api_batch_test_basket.py`**
  - **출처**: `api_server.py`의 클라이언트 샘플 로직
  - **역할**: 데이터셋에서 랜덤 에피소드를 추출하여 API 서버에 연쇄 호출.
  - **특이사항**: `Snap-to-Grid` (액션 보정) 로직의 실효성 검증.
  
- **`scripts/test/test_robot_driving_18steps.py`**
  - **역할**: 실제 18프레임 주행 시나리오 시뮬레이션.
  - **로직**: 0.4초 주기로 18번 연속 호출하여 Latency(지연시간)와 GPU 메모리 유동성을 체크.

### B. 독립형(Standalone) 및 로컬 테스트
API 서버 없이 코드 레벨에서 모델의 `predict()`를 직접 호출합니다.

- **`RoboVLMs/vla_test/standalone_vla_test.py`**
  - **출처**: HuggingFace Transformers 공식 예제 기반 커스텀
  - **역할**: `PaliGemma` 또는 `Kosmos` 모델을 직접 로드하여 텍스트/이미지 입력 테스트.
  - **특징**: ROS2 의존성 없이 순수하게 모델 가중치만 테스트할 때 사용.

- **`scripts/test/test_basket_inference_windowed.py`**
  - **역할**: **Window size 8** (과거 히스토리 사용) 로직이 로컬에서 정확히 작동하는지 검증.
  - **로직**: `collections.deque`를 이용한 슬라이딩 윈도우 버퍼 구현 확인.

### C. 정량적 성능 평가
모델의 "실력"을 숫자로 나타내는 스크립트입니다.

- **`scripts/test/evaluate_direction_accuracy.py`**
  - **역할**: 모델이 방향(Left/Right/Straight)을 얼마나 정확하게 인지하는지(Direction Accuracy) 측정.
  - **출처**: `scripts/dataset/analyze_episode_frames.py`의 데이터 로더 계승.

---

## 🧠 3. 핵심 테스트 로직 분석

### 1) Windowed History (시계열 데이터 처리)
학습 데이터가 과거 8프레임을 사용하므로, 테스트 시에도 이 버퍼를 유지하는 것이 핵심입니다.

```python
# scripts/test/test_basket_inference_windowed.py 예시 로직
history = []
for frame in episode:
    history.append(frame)
    if len(history) > 8:
        history.pop(0) # 최신 8프레임 유지
    
    # 패딩 로직 (초기 프레임 부족 시 첫 프레임 복사)
    current_input = history.copy()
    while len(current_input) < 8:
        current_input.insert(0, history[0])
```

### 2) Instruction Prompting (프롬프트 일관성)
학습 시 사용된 특정 키워드(`<grounding>`)가 포함되어야 성능이 보장됩니다.

- **출처**: `api_server.py` 내 `predict()` 메서드
- **로직**: 
  - 단순 명령어(`"Navigate to the basket"`)를 입력받으면 
  - 내부적으로 `"<grounding>An image of a robot Navigate to the basket"`로 확장.

### 3) Action Post-processing (액션 후처리)
모델이 출력하는 `[-1, 1]` 사이의 Continuous 값을 로봇 제어값(`1.15`, `0.0`, `-1.15`)으로 변환합니다.

- **로직**: `_apply_snap_to_grid()` 함수 (Deadzone 처리 포함)
- **중요**: 이 후처리 로직이 `api_server.py`와 테스트 스크립트(`api_batch_test_basket.py`)에서 동일해야 함.

---

## 🛠️ 4. 테스트 실행 방법

### 1) API 서버 기반 테스트 수행 시
먼저 서버를 띄운 후 클라이언트를 실행합니다.

```bash
# Terminal 1: 서버 실행 (GPU 0번 사용)
export VLA_API_KEY="test_key_1234"
export VLA_MODEL_NAME="exp17_win8"
python3 api_server.py

# Terminal 2: 배치 테스트 실행
python3 scripts/test/api_batch_test_basket.py
```

### 2) 로컬 모델 검증 수행 시 (서버 미사용)
```bash
# 특정 체크포인트 직접 지정 테스트
python3 scripts/test/verify_current_basket_model.py \
    --checkpoint runs/unified_regression_win12/.../epoch=09.ckpt \
    --config Mobile_VLA/configs/mobile_vla_exp17_win8_k1.json
```

---

## 📋 5. 테스트 결과 리포트 경로
테스트 실행 후 생성되는 JSON 리포트들은 다음 위치에 저장됩니다.

- **`logs/archive/api_test_results.json`**: API 테스트 상세 로그
- **`RoboVLMs/vla_test/vla_test_results.json`**: 독립형 테스트 결과
- **`docs/EXPERIMENT_HISTORY_AND_INSIGHTS.md`**: 전반적인 실험 성공률 요약

---

## 💡 팁: 무엇을 확인해야 하는가?
1. **Perfect Match Rate**: 학습 데이터의 액션과 추론 액션이 얼마나 일치하는가?
2. **First Frame Issue**: 에피소드 첫 프레임에서 모델이 튀지 않고 정지(`[0,0]`)해 있는가?
3. **Latency Stability**: 지연 시간이 450ms 이내로 안정적인가? (600ms 이상 시 로봇 주행 불안정)

---
**최종 업데이트**: 2026-02-12  
**작성자**: Antigravity AI Assistant
    