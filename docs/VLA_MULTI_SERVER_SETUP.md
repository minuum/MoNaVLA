# VLA 멀티 서버 환경 설정 가이드

## 📅 작성: 2025-12-17

## 🏗️ 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                    VLA System                            │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────┐         ┌──────────────────────┐ │
│  │  Jetson (fevers) │◄───────►│  Billy (A5000)       │ │
│  │  Robot Server    │Tailscale│  Model Server        │ │
│  ├──────────────────┤   VPN   ├──────────────────────┤ │
│  │                  │         │                      │ │
│  │ • 이미지 캡쳐     │         │ • VLA 모델 추론       │ │
│  │ • 로봇 주행       │         │ • API 서버           │ │
│  │ • ROS2 노드       │         │ • GPU 연산           │ │
│  │ • 데이터 수집     │         │                      │ │
│  │                  │         │                      │ │
│  │ Jetson Orin      │         │ NVIDIA RTX A5000     │ │
│  │ 100.85.118.58    │         │ 100.XXX.XXX.XXX      │ │
│  └──────────────────┘         └──────────────────────┘ │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## 🔧 서버 역할

### Jetson Server (fevers)
- **호스트명**: `fevers`
- **역할**: 로봇 제어 및 데이터 수집
- **Tailscale IP**: `100.85.118.58`
- **주요 작업**:
  - 카메라로 이미지 캡쳐
  - 로봇 주행 제어
  - ROS2 노드 실행
  - 데이터 수집
  - Billy 서버로 추론 요청

### Billy Server (A5000)
- **호스트명**: `billy`
- **역할**: VLA 모델 추론
- **Tailscale IP**: `100.XXX.XXX.XXX` (설정 필요)
- **주요 작업**:
  - VLA 모델 로딩
  - API 서버 실행
  - 추론 요청 처리
  - GPU 기반 연산

## 📦 설치 및 설정

### 🔹 공통 설정 (양쪽 서버 모두)

#### 1. 프로젝트 클론
```bash
cd ~
git clone <repository-url> vla
cd vla
```

#### 2. Aliases 설정
```bash
# .zshrc에 추가
echo 'source /home/soda/vla/.vla_aliases' >> ~/.zshrc
source ~/.zshrc
```

#### 3. Tailscale 설치 (미설치 시)
```bash
# Ubuntu/Debian
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# Tailscale IP 확인
tailscale ip -4
```

### 🤖 Jetson Server 전용 설정

#### 1. ROS2 Humble 설치 확인
```bash
source /opt/ros/humble/setup.bash
ros2 --version
```

#### 2. ROS2 Workspace 빌드
```bash
cd ~/vla/ROS_action
colcon build
source install/local_setup.bash
```

#### 3. 환경 변수 설정
```bash
# ~/.zshrc 또는 .vla_aliases에서 자동 설정되지만, 필요시 수동 설정:
export BILLY_TAILSCALE_IP="100.XXX.XXX.XXX"  # Billy 서버 IP
export VLA_API_KEY="billy-server-api-key"     # Billy 서버에서 생성된 API Key
```

### 🧠 Billy Server 전용 설정

#### 1. Python 환경 설정
```bash
cd ~/vla
pip3 install -r requirements.txt
```

#### 2. 모델 체크포인트 확인
```bash
ls -lh runs/mobile_vla_no_chunk_20251209/checkpoints/
ls -lh .vlms/kosmos-2-patch14-224/
```

#### 3. 환경 변수 설정
```bash
# .vla_aliases에서 자동 설정되지만, 필요시 override:
export VLA_API_SERVER="http://localhost:8000"
```

## 🚀 사용 방법

### 🤖 Jetson Server 사용

#### 1. 환경 설정
```bash
# Shell 재로드
source ~/.zshrc

# Jetson 환경 설정 (ROS2 포함)
vla-jetson-env
```

#### 2. Billy 서버 연결 확인
```bash
# 네트워크 연결 테스트
vla-network-check

# API 서버 Health check
vla-curl-health
```

#### 3. 로봇 작업 실행
```bash
# 데이터 수집
vla-collect

# 로봇 이동 제어
robot-move

# VLA 추론 시스템
vla-system
```

### 🧠 Billy Server 사용

#### 1. 환경 설정
```bash
# Shell 재로드
source ~/.zshrc

# Model 서버 환경 설정
vla-model-env
```

#### 2. API 서버 시작
```bash
# API 서버 시작
vla-start

# 상태 확인
vla-status

# 로그 확인
vla-logs
```

#### 3. API 테스트
```bash
# Health check
vla-health

# 전체 테스트
vla-test
```

## 🔑 API Key 설정

### Billy Server에서 API Key 생성

API 서버를 처음 실행하면 자동으로 API Key가 생성됩니다:

```bash
# Billy 서버에서
vla-start

# 로그에서 API Key 확인
vla-logs | grep "API Key"
# 출력 예시:
# 생성된 API Key: jFLQzbwEch8_S2lpioP6sC-S7-Jm9MCIXpgDebrp5Uc
```

### Jetson Server에 API Key 설정

생성된 API Key를 Jetson 서버에 설정:

```bash
# Jetson 서버에서
echo 'export VLA_API_KEY="jFLQzbwEch8_S2lpioP6sC-S7-Jm9MCIXpgDebrp5Uc"' >> ~/.zshrc
source ~/.zshrc

# 확인
vla-env
```

## 📊 주요 명령어

### 양쪽 서버 공통

| 명령어 | 설명 |
|--------|------|
| `vla-env` | 환경 변수 확인 |
| `vla-network-check` | 네트워크 연결 테스트 |
| `vla-help` | 도움말 |
| `vla-health` | API Health check |
| `vla-test` | API 전체 테스트 |
| `vla-curl-health` | 빠른 health check |
| `vla-ps` | 프로세스 확인 |
| `vla-cd` | 프로젝트로 이동 |
| `vla-gpu` | GPU 상태 |

### Jetson Server 전용

| 명령어 | 설명 |
|--------|------|
| `vla-jetson-env` | Jetson 환경 설정 (ROS2) |
| `vla-collect` | 데이터 수집 시작 |
| `robot-move` | 로봇 이동 제어 |
| `vla-system` | VLA 시스템 시작 |

### Billy Server 전용

| 명령어 | 설명 |
|--------|------|
| `vla-model-env` | Model 서버 환경 설정 |
| `vla-start` | API 서버 시작 |
| `vla-stop` | API 서버 중지 |
| `vla-restart` | API 서버 재시작 |
| `vla-status` | API 서버 상태 |
| `vla-logs` | API 서버 로그 |

## 🔍 트러블슈팅

### Jetson Server

#### 네트워크 연결 실패
```bash
# Tailscale 상태 확인
tailscale status

# Billy 서버 Ping 테스트
ping $BILLY_TAILSCALE_IP

# 방화벽 확인 (Billy 서버에서)
sudo ufw status
sudo ufw allow 8000/tcp
```

#### ROS2 환경 문제
```bash
# ROS2 환경 재설정
cd ~/vla/ROS_action
colcon build --symlink-install
source install/local_setup.bash

# 또는
vla-jetson-env
```

#### API 호출 실패
```bash
# API Key 확인
vla-env

# API 서버 상태 확인 (Billy에서)
vla-status

# 네트워크 테스트
vla-network-check
```

### Billy Server

#### API 서버 시작 실패
```bash
# 로그 확인
vla-logs

# 포트 충돌 확인
lsof -i :8000

# 기존 프로세스 종료
vla-stop
# 또는
pkill -f api_server.py

# 재시작
vla-start
```

#### 모델 로딩 실패
```bash
# 체크포인트 확인
ls -lh runs/mobile_vla_no_chunk_20251209/checkpoints/

# robovlms 모듈 확인
python3 -c "import robovlms"

# 필요시 재설치
pip3 install -e RoboVLMs/
```

#### GPU 메모리 부족
```bash
# GPU 상태 확인
nvidia-smi

# 다른 프로세스 확인 및 종료
```

## 📡 통신 흐름

### 일반적인 추론 요청 흐름

```
1. Jetson: 카메라 이미지 캡쳐
   ↓
2. Jetson: 이미지를 base64로 인코딩
   ↓
3. Jetson → Billy: POST /predict 요청
   {
     "image": "base64_encoded_image",
     "instruction": "Navigate to the left box"
   }
   ↓
4. Billy: VLA 모델 추론
   ↓
5. Billy → Jetson: 응답
   {
     "action": [linear_x, linear_y],
     "latency_ms": 123.45
   }
   ↓
6. Jetson: 로봇 제어 명령 실행
```

## 🔄 동기화 및 배포

### 코드 동기화

#### Jetson → Billy
```bash
# Jetson에서
cd ~/vla
git add .
git commit -m "Update from Jetson"
git push

# Billy에서
cd ~/vla
git pull
```

#### 파일 직접 동기화 (rsync)
```bash
# Jetson → Billy
rsync -avz --exclude '.git' ~/vla/ billy@$BILLY_TAILSCALE_IP:~/vla/

# Billy → Jetson  
rsync -avz --exclude '.git' ~/vla/ soda@$JETSON_TAILSCALE_IP:~/vla/
```

## 📝 환경 변수 정리

### Jetson Server
```bash
VLA_SERVER_ROLE=jetson
VLA_SERVER_NAME="Jetson Robot Server"
VLA_PROJECT_DIR=/home/soda/vla
JETSON_TAILSCALE_IP=100.85.118.58
BILLY_TAILSCALE_IP=100.XXX.XXX.XXX  # 설정 필요
VLA_API_SERVER=http://${BILLY_TAILSCALE_IP}:8000
VLA_API_KEY=<billy-server-api-key>
ROS_DOMAIN_ID=42
```

### Billy Server
```bash
VLA_SERVER_ROLE=model
VLA_SERVER_NAME="Billy Model Server"
VLA_PROJECT_DIR=/home/billy/vla  # 또는 /home/soda/vla
JETSON_TAILSCALE_IP=100.85.118.58
BILLY_TAILSCALE_IP=100.XXX.XXX.XXX  # 자신의 IP
VLA_API_SERVER=http://localhost:8000
VLA_API_KEY=<auto-generated-on-first-run>
```

## ✅ 체크리스트

### Jetson Server 설정
- [ ] Git repository 클론
- [ ] `.vla_aliases` 소싱
- [ ] Tailscale 설치 및 연결
- [ ] ROS2 Humble 설치 확인
- [ ] ROS2 Workspace 빌드
- [ ] Billy 서버 Tailscale IP 설정
- [ ] Billy 서버 API Key 설정
- [ ] `vla-network-check`로 연결 확인
- [ ] `vla-jetson-env` 테스트

### Billy Server 설정
- [ ] Git repository 클론
- [ ] `.vla_aliases` 소싱
- [ ] Tailscale 설치 및 연결
- [ ] Python 패키지 설치
- [ ] 모델 체크포인트 확인
- [ ] 방화벽 포트 8000 개방
- [ ] `vla-start`로 API 서버 시작
- [ ] API Key 확인 및 Jetson에 공유
- [ ] `vla-test`로 API 테스트

---

**문서 버전**: 1.0  
**최종 수정**: 2025-12-17  
**작성자**: VLA Team  
**유지보수**: 양쪽 서버 모두에서 이 문서를 동기화
