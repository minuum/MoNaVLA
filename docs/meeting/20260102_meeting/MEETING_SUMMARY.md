# Mobile VLA 프로젝트 교수님 미팅 보고서 (2026.01.02)

본 문서는 최근 이틀간 진행된 Mobile VLA 프로젝트의 개발 성과, 기술적 이슈 해결, 그리고 실험 결과를 종합한 미팅 자료입니다. 논문 작성 및 로봇 실증 테스트를 위한 기반이 마련되었습니다.

## 1. 핵심 개발 성과 (Key Achievements)

### 1) Edge Device 최적화 (Jetson Orin Nano 타겟)
기존 RoboVLMs(7B) 모델을 경량화하여 엣지 디바이스 구동을 실현했습니다.
*   **모델 경량화**: Kosmos-2 (1.6B) Backbone 채택.
*   **양자화(Quantization)**: BitsAndBytes INT8 적용.
*   **성과 지표**:
    *   **GPU 메모리**: 14GB → **1.8GB** (INT8 적용 시, Billy 서버 A5000 기준 측정)
    *   **추론 속도**: **495ms (약 2.0Hz)** (Billy 서버 A5000 기준 측정)
    *   *Note: Jetson Orin Nano(16GB)에서도 충분히 구동 가능한 리소스 범위임을 확인.*

### 2) 성능 최적화 (Action Chunking)
이동 로봇(Mobile Navigation)에 적합한 제어 파라미터를 실험적으로 검증했습니다.
*   **비교 실험**: Chunk Size 5 vs 10
*   **결과**: **Chunk 5**가 Chunk 10 대비 월등한 성능 기록.
    *   Val Loss: **0.067** (Chunk 5) vs 0.284 (Chunk 10) - **76% 개선**
    *   RMSE: **0.259** (Chunk 5) vs 0.533 (Chunk 10) - **51% 개선**
*   **결론**: 모바일 로봇의 민첩한 제어에는 짧은 Horizon(Chunk 5)이 유리함.

## 2. 주요 기술적 이슈 및 해결 (Troubleshooting)

### 1) 데이터 스케일링(Clipping) 문제 발견 및 해결
*   **현상**: 학습 데이터(최대 속도 1.15)가 학습 설정 상의 범위(`-1.0 ~ 1.0`)로 인해 **Clipping(잘림)**되어 학습됨. 이로 인해 모델이 최대 1.0까지만 출력하는 문제 발생.
*   **데이터 특성 파악**: 실제 데이터가 `0`과 `1.15`로 이루어진 **Bang-Bang Control** 형태임을 확인. 중간값(0.5 등)이 거의 없음.
*   **해결책**: 재학습 대신 **추론(Inference) 단계 보정** 적용.
    *   API 서버 및 파이프라인에 `Gain 1.15` 적용 및 `[-1.15, 1.15]` 범위로 역변환(De-normalization) 로직 추가.
    *   결과적으로 원본 데이터의 물리적 속도(1.15 m/s)를 완벽하게 복원함.

### 2) Window Size 설정 (History Length)
*   **설정**: **Window Size = 2**
*   **근거**: Mobile Navigation은 현재 상황(장애물 유무)에 대한 즉각적 반응이 중요함(Markov Property).
    *   최신 연구(OpenVLA, ACT 등) 트렌드인 **"Short Input(1~2), Long Output(Chunking)"** 전략과 일치함.
    *   불필요한 과거 정보를 배제하여 연산 효율성 극대화 (Jetson 구동 핵심 요인).

### 3) 추론 파이프라인 검증 (Billy Server A5000)
*   일시: 2026.01.02
*   검증 내용: `scripts/verify_inference_fact.py` 실행 결과
*   **결과**:
    *   **모델 로딩**: Kosmos-2 (1.6B) FP16 모델 정상 로드 완료.
    *   **Gain Correction 동작 확인**:
        *   Chunk 5 (5 steps) 추론 결과가 `1.15` (최대 속도) 근처 값으로 정확히 복원됨을 확인.
        *   Sample Output: `[1.141, -1.124]`, `[1.149, 0.244]` 등
        *   -> 데이터셋의 물리적 속도(1.15m/s)를 추론 단계에서 완벽히 복원 성공.
    *   **Action Shape**: `(5, 2)` 형태의 Action Chunking 정상 출력 확인.

## 3. 시스템 구축 현황

### 1) API 서버 구축 (For Robot Integration)
*   **FastAPI 기반 추론 서버**: Jetson(Robot)과 Billy(Server) 간 통신 담당.
*   **기능**:
    *   Base64 이미지 수신 및 전처리.
    *   **INT8 Quantization** 적용 (Billy 서버 테스트 완료).
    *   **Gain Correction(1.15) 로직** 탑재 (검증 완료).
    *   Action Buffer 관리 (Receding Horizon Control 지원).

### 2) 논문 작성 준비
*   **초안 작성 완료**:
    *   `PAPER_DRAFT_FULL_20251231.md`: 서론, 방법론(Method), 실험(Experiments), 결론 포함.
*   **시각화 자료 완비**:
    *   학습 곡선(Training Curves): Chunk 5의 안정적 수렴 확인.
    *   리소스 비교(Resource Chart): FP32 vs INT8 효율성 비교.

## 4. 향후 계획 (Next Steps)

1.  **로봇 실증 테스트 (Sim2Real / Real World)**
    *   보정된 API 서버를 통해 실제 로봇 주행 테스트 수행.
    *   `1.15` 속도 복원 및 조향 성능 검증.
2.  **데이터셋 확장 (Optional)**
    *   현재 500개 에피소드(Left/Right 균형)로 충분한 성능을 보이나, 복잡한 장애물 회피를 위해 추가 데이터 확보 고려.
3.  **학습 파이프라인 고도화**
    *   추후 재학습 시에는 Config의 `norm_min/max`를 `-1.2 ~ 1.2`로 수정하여 Clipping 문제 원천 차단.

---
**첨부 자료**:
*   `docs/dataset_statistics.json`: 데이터셋 통계 (Left/Right 250)
*   `docs/figures/`: 시각화 그래프
*   `docs/PAPER_DRAFT_FULL_20251231.md`: 논문 초안
