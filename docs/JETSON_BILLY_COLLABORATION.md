# 🤝 Jetson(Soda) - Billy 서버 협업 및 통합 가이드

이 문서는 Jetson 로봇(Client)과 Billy 서버(Inference Server) 간의 연동을 위한 **순차적 실행 가이드**와 **필수 설정**을 공유합니다.

## 📡 시스템 구조
- **Jetson (Soda)**: 로봇 제어, 카메라 촬영, 추론 요청 (Client)
- **Billy Server**: VLA 모델 추론, API 서버 호스팅 (Server)
- **통신**: SSH Tunneling (Jetson `:8000` -> Billy `:8000`)

---

## 🚀 실행 순서 (Step-by-Step)

### Step 1. Billy 서버: API 서버 시작 (필수!)
**담당자**: Billy 서버 관리자
**목표**: 모델을 메모리에 로드하고 API 요청 대기

1. Billy 서버 접속
   ```bash
   ssh billy@100.86.152.29 -p 10022
   ```
2. API 서버 시작 (모델 로드 포함)
   ```bash
   cd ~/vla
   source .vla_aliases
   vla-start  # tmux 세션에서 서버 시작됨
   ```
3. 확인
   ```bash
   curl localhost:8000/health
   # 응답에 "model_loaded": true 가 있어야 함!
   ```

---

### Step 2. Jetson: SSH 터널링 연결
**담당자**: Soda (Jetson)
**목표**: 로컬 포트 8000을 Billy 서버로 포워딩

```bash
# Jetson 터미널
ssh -N -f -L 8000:localhost:8000 billy@100.86.152.29 -p 10022
```

---

### Step 3. Jetson: 카메라 서버 시작
**담당자**: Soda (Jetson)
**목표**: GStreamer 카메라 스트림을 ROS 서비스로 제공

```bash
# Jetson 터미널 1
run_camera_server
# "✅ get_image_service 서비스 서버 준비 완료!" 메시지 확인
```
> **주의**: `RTPS_READER_HISTORY Error`는 무시해도 됩니다. (ROS2 내부 로그)

---

### Step 4. Jetson: API 클라이언트 시작
**담당자**: Soda (Jetson)
**목표**: 키보드/추론 제어 시작

```bash
# Jetson 터미널 2
run_vla_client
```

---

## 🔑 중요 설정 및 파일

### 1. Jetson (`~/vla/secrets.sh`)
이 파일은 Git에 없으므로 직접 생성해야 합니다.
```bash
export VLA_API_SERVER="http://localhost:8000"
export VLA_API_KEY="qkGswLr0qTJQALrbYrrQ9rB-eVGrzD7IqLNTmswE0lU"
export BILLY_SERVER_IP="100.86.152.29"
```

### 2. Billy (`~/vla/.vla_aliases`)
API 서버 실행을 돕는 Alias입니다.
```bash
alias vla-start="python3 api_server.py --config configs/inference_config.yaml"
```

---

## 🛠️ 트러블슈팅 (Troubleshooting)

### Q1. "API 서버: 연결됨, 모델 미로드" 라고 떠요.
- **원인**: Billy 서버에서 `api_server.py`가 실행되었지만, 모델 가중치가 로드되지 않았거나 로딩 중입니다.
- **해결**: Billy 서버 로그를 확인하여 모델 로딩 완료 메시지를 기다리세요.

### Q2. "이미지 획득 실패" 또는 타임아웃
- **원인**: 카메라 서비스가 죽었거나, 2개 이상 실행 중입니다.
- **해결**:
  ```bash
  # 모든 관련 프로세스 정리
  pkill -f camera_service
  pkill -f api_client
  # 다시 시작
  run_camera_server
  ```

### Q3. RTPS Error가 계속 떠요.
- **내용**: `[RTPS_READER_HISTORY Error] Change payload size...`
- **해결**: ROS2 DDS 설 정 문제이나, **현재 기능에는 영향이 없으므로 무시**하세요.

---

## 📝 개발 가이드 (RoboVLMs 스타일)

### 추론 로직 (api_client_node.py)
1. **입력**: 224x224 RGB 이미지 + 텍스트 명령어
2. **출력**: `[linear_x, linear_y]` (2DOF Action)
3. **제어**: `angular_z`는 0으로 고정 (학습 데이터 특성 반영)
4. **주기**: 10Hz (100ms)

### 테스트 방법
- **I 키**: 자동 주행 (추론 모드)
- **R 키**: 단일 추론 테스트 (디버깅용 상세 로그)
- **T 키**: 시스템 상태 점검 (카메라, API, 모델 연결)
