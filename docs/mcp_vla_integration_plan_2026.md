# 2026 VLA MCP (Model Context Protocol) Integration Plan

## 1. 개요 (Overview)
기존 REST API/ROS2 기반의 통신 방식을 넘어, **Model Context Protocol (MCP)**를 도입하여 VLA(Vision-Language-Action) 시스템의 유연성과 확장성을 극대화하는 2026년형 아키텍처 통합 계획입니다. 

**[UPDATE]** 로봇 서버(Jetson)에서 직접 VLA 모델 추론을 수행하며, 동시에 **MCP 서버** 역할을 합니다. GPU 학습 서버(inference-integration)는 **MCP 클라이언트**로서 로봇에 접속해 카메라 데이터를 받아 YOLO 분석 등 고연산 작업을 돕고, VLA의 판단을 보조하는 역할을 수행합니다.

---

## 2. 아키텍처 디자인 (Architecture Design)

### 2.1 로봇 서버 (Vla-driving / Jetson 16) - **VLA Inference & MCP Server**
로봇은 카메라 데이터, 로봇 상태를 제공함과 동시에 VLA 모델을 통한 자체 자율 주행 연산을 수행합니다.
- **주요 워크플로우**:
  1. 카메라 노드에서 이미지 프레임 수집.
  2. 로컬에 탑재된 **Mobile VLA (Kosmos-2 등)** 모델로 Action(linear_x, angular_z) 추론.
  3. 추론된 Action으로 모터 제어.
- **MCP Resources:**
  - `camera://front_rgb`: 로봇의 전면 카메라 실시간 프레임
  - `vla://status`: 현재 VLA 모델의 상태 및 최근 추론된 Action 값
- **MCP Tools:**
  - `get_camera_frame()`: 학습 서버의 객체 인식을 위한 최신 프레임 제공.
  - `override_velocity(linear_x, angular_z)`: 학습 서버(YOLO) 판단에 의한 긴급 회피 제어 권한 수용.

### 2.2 학습 서버 (inference-integration) - **YOLO + MCP Client**
고성능 GPU를 활용해 무거운 비전 디텍션(YOLO)을 담당하며, 로봇 서버를 모니터링 및 보조하는 에이전트 역할을 수행합니다.
- **주요 워크플로우**:
  1. Jetson(MCP Server)에 접속하여 `get_camera_frame()`을 주기적으로 호출 (또는 Resource 구독).
  2. **YOLO Module**: 받아온 이미지에서 사람, 동적 장애물, 목표 사물을 실시간 객체 탐지.
  3. **Decision Maker**: YOLO 결과를 바탕으로 위험 상황(충돌 임박 등) 판단.
  4. 위험 감지 시, 로봇(MCP Server)의 `override_velocity()` Tool을 호출하여 VLA의 원래 Action을 덮어쓰고 강제 정지/회피 명령 수행.

---

## 3. 구체적 구현 계획 (Implementation Details)

### Phase 1: 로봇 측 VLA 추론 및 MCP Server 구축 (Jetson)
- 기존 VLA API 서버 코드를 엣지 디바이스(Jetson) 추론용으로 최적화 및 ROS2 연동.
- Python 기반 `mcp` SDK를 사용하여 내부 포트(예: SSE 방식)로 MCP 서버 컨테이너 구동.
- `/image_raw` 토픽 제공 로직 및 외부 강제 제어를 위한 `override_velocity` 처리 로직 (우선순위 Mux) 구현.

### Phase 2: 학습 서버 측 MCP Client 및 YOLO 연동 구축
- Python `mcp` 클라이언트 구현 및 Tailscale IP를 통한 Jetson 접속.
- **YOLO 파이프라인 통합**: `ultralytics` 라이브러리로 YOLOv11 모델 구동 및 실시간 디텍션 파이프라인.
- Bounding Box 데이터를 기반으로 거리 및 위험도를 계산하는 모니터링 루프 구현.

### Phase 3: 상황 판단 로직 (Situation Awareness & Control)
- **Safety Overrides**: YOLO 인식 결과(사람, Box 등)가 특정 픽셀 크기(Proximity Threshold) 이상이면 `override_velocity(0, 0)` 등 정지 명령 전송.
- **명령권 중재 (Muxing)**: Jetson 내부에서 VLA 출력과 MCP Client(YOLO) 출력 간의 제어권 우선순위 룰(Rule) 설정.

---

## 4. 실험 설계 (Experimental Design)

### Experiment 1: 분산 추론 및 제어 Latency (Distributed Inference Latency)
- **목적**: Jetson에서의 VLA 추론 속도와, 학습 서버 경유 YOLO 디텍션 -> 제어 피드백 속도의 차이 및 동기화 확인.
- **측정 지표**: Jetson 카메라 캡처 ~ 학습 서버 YOLO 추론 ~ Jetson에 도착하는 Override 명령까지의 Total Latency.

### Experiment 2: 동적 장애물 회피 신뢰성 (Dynamic Obstacle Avoidance)
- **시나리오**: Jetson이 VLA를 이용해 자율 주행 중일 때, 갑작스러운 장애물(학습되지 않은 객체) 난입 상황.
- **측정 지표**: 학습 서버(YOLO+MCP Client) 개입으로 인한 충돌 회피 성공률.

### Experiment 3: Jetson 리소스 병목 분석 (Resource Bottleneck)
- **목적**: Jetson에서 VLA 추론 메인 루프와 실시간 비디오 스트리밍(MCP Server)이 동시에 구동될 때의 프레임 저하 확인.
- **대응책**: 해상도 조절 및 프레임 전송 주기(FPS) 최적화. 

---

## 5. 인프라 및 구축 요구사항 (Infrastructure Requirements)

- **Network**: **Tailscale VPN** 유지. Jetson과 학습 서버 간 **SSE (Server-Sent Events) 기반 통신**.
- **Hardware/Models**:
  - Jetson: **VLA Model** (Chunk10/Chunk5 등 量子化 모델), 카메라 하드웨어, ROS2 제어권.
  - Learning Server: **YOLO Model** (YOLOv11s 또는 YOLOv11m 등 GPU 연산 풀활용) 및 MCP Client 프로세스.
- **Software Dependencies**:
  - 양측 공통: Python `mcp` 라이브러리.

---

## 6. User Review Required

> [!IMPORTANT]  
> 1. **제어 우선순위**: 평상시 제어권은 Jetson 내부의 VLA 통과 모델에 있고, 상황 발생 시 학습 서버의 오버라이드가 개입하는 **Subsumption Architecture** 형태로 이해했습니다. 올바른지 확인 부탁드립니다.
> 2. **비디오 스트리밍 부하**: Jetson 구동 중 추가적인 영상 전송(MCP 경유)은 대역폭과 CPU 자원을 소모합니다. 이미지 해상도 다운샘플링 등 압축 전송 로직이 필수로 추가될 예정입니다.
