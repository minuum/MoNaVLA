# 📨 Message to Jetson Client (Soda)
**Status**: API Specification V1 Released & Push Completed

---

## 📢 중요 공지 (Important Notice)

Billy 서버(API Server)의 입출력 규격을 확정하여 Git에 Push했습니다 (`docs/API_INTERFACE_SPEC.md`).
**반드시 아래 규격을 준수하여 클라이언트를 실행해 주십시오.**

### 1. 변경 사항 (Changes)
- **API Specification**: `docs/API_INTERFACE_SPEC.md` 참조
- **API Key**: `qkGswLr0qTJQALrbYrrQ9rB-eVGrzD7IqLNTmswE0lU` (통일됨)
- **Instruction**: 학습 데이터 원문과 100% 일치시킴
  - `"Navigate around obstacles and reach the front of the beverage bottle on the left"`

### 2. 실행 가이드 (Action Items)
Jetson 터미널에서 다음 순서로 진행해주세요.

1. **Git Pull**:
   ```bash
   cd ~/vla
   git pull origin feature/inference-integration
   ```

2. **환경 변수 설정 (API Key 업데이트)**:
   ```bash
   export VLA_API_KEY="qkGswLr0qTJQALrbYrrQ9rB-eVGrzD7IqLNTmswE0lU"
   export BILLY_URL="http://100.86.152.29:8000"
   ```

3. **ROS2 클라이언트 확인**:
   - `docs/API_INTERFACE_SPEC.md`를 읽어보세요.
   - `ros2 run mobile_vla_package api_client_node --test`를 실행하여 Billy 서버와 통신이 잘 되는지 확인하세요.

---

**Billy Server는 현재 대기 중입니다.** (`vla-status`로 확인 가능)
성공적인 통합을 기원합니다! 🚀
