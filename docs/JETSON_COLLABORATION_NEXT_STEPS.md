# 🚀 Jetson & Billy 협업 Next Steps
**작성일**: 2025-12-18  
**상태**: 준비 완료 (Ready for Integration)

---

## ✅ 현재 상황 요약 (Status Update)

1.  **Git & Code**: Jetson 측 코드를 Pull 완료했습니다. 
    - `api_client_node.py`: 로봇 제어 로직 확인됨 (Mecanum style move). 수정 불필요.
    - `docs/JETSON_BILLY_COLLABORATION.md`: Jetson 측 가이드 확인 완료.

2.  **API 서버 (Billy)**:
    - **API Key 통일 완료**: `qkGswLr0...` (Jetson 문서 기준)
    - **모델 로딩 완료**: `chunk5_epoch6` (Best Model)
    - **서버 재시작 완료**: 현재 접속 가능 상태

---

## 📋 To-Do List (Action Items)

### 1. Jetson 측 실행 요청 (Priority: High)
Billy 서버는 준비되었습니다. Jetson(Soda) 터미널에서 다음을 실행해주세요:

1.  `secrets.sh` 파일 생성 (또는 확인):
    ```bash
    export VLA_API_KEY="qkGswLr0qTJQALrbYrrQ9rB-eVGrzD7IqLNTmswE0lU"
    export BILLY_URL="http://100.86.152.29:8000"
    ```
2.  **SSH 터널링** (필요시):
    ```bash
    ssh -N -f -L 8000:localhost:8000 billy@100.86.152.29 -p 10022
    ```
3.  **ROS2 클라이언트 실행**:
    ```bash
    ros2 run mobile_vla_package api_client_node
    ```
4.  **테스트 키 입력**: `T` 키를 눌러 시스템 연결 테스트를 진행해주세요.

### 2. 주행 테스트 (Lab Test)
- **시나리오**: "Navigate around obstacles and reach the front of the beverage bottle on the left"
- **기대 동작**: 로봇이 전진하면서 왼쪽(`y > 0`)으로 이동하는 벡터로 움직여야 함.
- **모니터링**: Billy 서버에서 `vla-logs`로 요청이 들어오는지 확인.

### 3. Latency 최적화 (Optional)
- 현재 약 380ms 소요됨.
- 로봇 움직임이 너무 끊기면 `api_client_node.py`의 `inference_timer` 주기(현재 100ms)를 400ms 정도로 늘려서 동기화하거나, 비동기 처리를 강화해야 함.

---

## 🛠️ 설정 값 (Configuration)

| 항목 | 값 | 비고 |
|------|----|------|
| **Billy IP** | `100.86.152.29` | Tailscale |
| **API Port** | `8000` | |
| **API Key** | `qkGswLr0...` | 보안 주의 |
| **Action Space** | `[linear_x, linear_y]` | `angular_z = 0` |
| **Instruction** | "Navigate around... left" | 통일됨 |

---

이제 **Jetson 터미널**에서 작업을 시작하시면 됩니다! 🚀
