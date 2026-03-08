# 2026 VLA MCP (Model Context Protocol) Integration Plan

## 1. 개요 (Overview)
기존 REST API/ROS2 기반의 통신 방식을 넘어, **Model Context Protocol (MCP)**를 도입하여 VLA(Vision-Language-Action) 시스템의 유연성과 확장성을 극대화하는 2026년형 아키텍처 통합 계획입니다. 

로봇은 데이터와 제어 인터페이스를 제공하는 **MCP 서버**가 되고, GPU 인퍼런스 서버는 이를 활용하여 상황을 인식하고 행동을 결정하는 **MCP 클라이언트** 역할을 수행합니다. 이를 통해 단순히 Action 값을 반환하는 것을 넘어, YOLO 기반의 동적 장애물 회피 및 복합적인 상황 판단이 가능해집니다.

---

## 2. 아키텍처 디자인 (Architecture Design)

### 2.1 로봇 서버 (Vla-driving / Jetson) - **MCP Server**
로봇은 자신의 센서 데이터와 액추에이터 제어 기능을 MCP 표준에 맞게 노출합니다.
- **MCP Resources:**
  - `camera://front_rgb`: 로봇의 전면 카메라 실시간 프레임
  - `sensor://status`: 현재 로봇의 속도, 배터리, 상태 정보
- **MCP Tools:**
  - `get_camera_frame()`: 최신 이미지 프레임 요청
  - `set_velocity(linear_x, angular_z)`: 로봇의 이동 명령 하달
  - `emergency_stop()`: 긴급 정지 메커니즘

### 2.2 학습 서버 (inference-integration) - **MCP Client**
단순 API 엔드포인트에서 벗어나 능동적인 에이전트(Agent) 또는 컨트롤러 모듈로 동작합니다.
- **주요 워크플로우**:
  1. 로봇(MCP Server)에 연결하여 `get_camera_frame()` Tool을 호출하거나 Resource를 구독하여 이미지를 가져옵니다.
  2. **YOLO Module**: 받아온 이미지에서 사람, 동적 장애물, 특정 사물을 실시간 객체 탐지(Object Detection).
  3. **VLA Module (Kosmos-2 등)**: 목적지 네비게이션을 위한 Action(linear_x, angular_z) 추론.
  4. **Decision Maker**: YOLO 분석 결과(장애물 근접 등)와 VLA 추론 결과를 종합 판단. (예: 정면 장애물 디텍션 시 VLA 명령 무시하고 정지 혹은 회피 명령 생성).
  5. 로봇(MCP Server)의 `set_velocity()` Tool을 호출하여 로봇 구동.

---

## 3. 구체적 구현 계획 (Implementation Details)

### Phase 1: 로봇 측 MCP Server 구축 (Jetson)
- Python 기반 `mcp` SDK (`mcp-server-standard` 또는 커스텀 서버)를 사용하여 ROS2 노드를 래핑(Wrapping)하는 코드 작성.
- ROS2의 `/image_raw` 토픽을 캡처하여 Base64로 인코딩 후 반환하는 Tool 구현.
- `/cmd_vel` 토픽으로 Twist 메시지를 퍼블리시하는 Tool 구현.

### Phase 2: 인퍼런스 서버 측 MCP Client 구축 (학습 서버)
- Python `mcp` 클라이언트 라이브러리를 사용하여 Jetson MCP Server와 통신(Stdio 또는 SSE 방식 통신, Tailscale IP 활용).
- **YOLO 파이프라인 통합**: `ultralytics` 라이브러리를 통해 YOLOv8/v11 모델 로드, 프레임 디텍션 수행 로직 추가.
- 기존 VLA API 서버 로직을 MCP 클라이언트 컨트롤 룹(Control Loop) 안에 편입: `while True:` 루프 안에서 센서 리딩 -> 추론 -> 모터 제어 사이클 형태로 변환.

### Phase 3: 상황 판단 로직 (Situation Awareness & Control)
- **Safety Overrides**: YOLO에서 Bounding Box의 크기가 일정 임계값(Threshold) 이상일 경우(충돌 임박), VLA의 `linear_x`가 양수이더라도 `linear_x = 0` 및 회피 경로 재생성(Turn Bias 적용).
- **목표물 인식 강화**: "주행 중 사물 판단"을 위해 YOLO가 타겟 오브젝트를 디텍션하면 VLA의 텍스트 프롬프트를 동적으로 변경하여 추론 정확도 향상.

---

## 4. 실험 설계 (Experimental Design)

### Experiment 1: 통신 지연시간 및 오버헤드 분석 (Latency)
- **목적**: 기존 REST / ROS2 브릿지 연결 대비 MCP 프로토콜 스택 추가로 인한 네트워크 레이턴시 측정.
- **측정 지표**: `get_camera_frame()` 요청부터 `set_velocity()` 도달까지의 End-to-End Latency. (목표: < 150ms).

### Experiment 2: 동적 장애물 회피 성공률 (Dynamic Obstacle Avoidance)
- **시나리오**: 로봇이 목표물을 향해 VLA 주행 중 (ex: "Navigate to the desk"), 갑자기 사람이나 상자가 경로에 뛰어듬.
- **측정 지표**: YOLO+MCP 기반 Safety Override 동작 성공 횟수 / 총 시도 횟수. (충돌 회피율).

### Experiment 3: 시스템 안정성 및 메모리 분석
- **목적**: Jetson에서 MCP Server 가동 시의 리소스 점유율(CPU, RAM) 분석 및 학습 서버에서 YOLO + VLA 동시 로드 시의 VRAM 사용량(OOM 방지) 모니터링.

---

## 5. 인프라 및 구축 요구사항 (Infrastructure Requirements)

- **Network**: 현재 사용중인 **Tailscale VPN**을 그대로 유지. SSE (Server-Sent Events) 전송 계층을 통해 MCP 통신 (HTTP 기반).
- **Software Dependencies**:
  - Jetson: `mcp` (Python SDK), `ros2-humble`-python-bridge 패키지.
  - Learning Server: `ultralytics` (YOLO), `mcp` (Python SDK), 기존 `Mobile_VLA` 환경 유지.
- **Models**:
  - VLA: 기존 검증된 `Chunk10 Epoch 8` 또는 `Chunk5 Epoch 6` 체크포인트 재사용.
  - YOLO: 실시간 성을 고려하여 가벼운 `YOLOv11n` (Nano) 또는 `YOLOv11s` (Small) 모델 사용 추천.
