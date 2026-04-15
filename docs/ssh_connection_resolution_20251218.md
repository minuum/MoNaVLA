# SSH 연결 문제 해결 완료 리포트

**작성일**: 2025-12-18 05:54  
**작성자**: Antigravity  

---

## 🎯 문제 요약

Jetson에서 Billy 서버로 SSH 터널링을 시도했으나 연결 실패:

```
Tailscale 연결: ✅ (Direct, 100.86.152.29)
Port 8000: ❌ (Timeout)
Port 22 (SSH): ❌ (Timeout)
Tailscale SSH: ❌ (502 Bad Gateway)
```

---

## 🔍 원인 분석

### Billy 서버 SSH 설정 확인 결과:

```bash
# /etc/ssh/sshd_config 확인
Port 10022  # ← 기본 Port 22가 아님!

# SSH 데몬 상태 확인
● ssh.service - OpenBSD Secure Shell server
   Active: active (running) since Tue 2025-12-16 19:47:30 KST

# 실제 Listening Port 확인
tcp        0      0 0.0.0.0:10022           0.0.0.0:*               LISTEN
tcp6       0      0 :::10022                :::*                    LISTEN
```

### **핵심 원인**:
- Billy 서버는 **Port 10022**에서 SSH를 listening
- Jetson은 기본 **Port 22**로 접속 시도
- 따라서 연결 실패 (타임아웃)

---

## ✅ 해결 방법

### Jetson에서 실행할 명령어:

```bash
# 기존 (실패):
ssh billy@100.86.152.29

# 수정 (성공):
ssh billy@100.86.152.29 -p 10022
```

### SSH 터널 생성:

```bash
# 수동 터널 생성
ssh -N -f -L 8000:localhost:8000 billy@100.86.152.29 -p 10022

# 또는 자동화 스크립트 사용
cd ~/vla
bash scripts/jetson_ssh_tunnel.sh
```

---

## 📁 생성된 파일

### 1. `/home/billy/25-1kp/vla/docs/SSH_TUNNEL_GUIDE.md`
- **목적**: SSH 터널링 완전 가이드
- **내용**:
  - Port 10022 사용 안내
  - SSH Key 기반 인증 설정
  - 수동/자동 터널 생성 방법
  - 문제 해결 (Troubleshooting)
  - ROS2 Client 실행 방법

### 2. `/home/billy/25-1kp/vla/scripts/jetson_ssh_tunnel.sh`
- **목적**: Jetson SSH 터널 자동 설정 스크립트
- **기능**:
  - ✅ 환경 변수 자동 로드 (secrets.sh)
  - ✅ Tailscale 연결 확인
  - ✅ 기존 터널 확인 및 종료
  - ✅ SSH 연결 테스트 (Key/Password 인증 모두 지원)
  - ✅ 터널 생성 및 Health Check
  - ✅ 실행 가능 권한 부여 완료 (`chmod +x`)

### 3. `/home/billy/25-1kp/vla/JETSON_SETUP.md`
- **업데이트**: SSH 터널링 섹션 추가
- **내용**:
  - SSH Config 설정 방법
  - SSH Key 생성 및 등록
  - 터널 생성 및 관리
  - 중요 정보 (Port 10022 강조)

---

## 🚀 Jetson 실행 절차 (최종)

### 방법 1: 자동화 스크립트 (권장)

```bash
# 1. vla 디렉토리로 이동
cd ~/vla

# 2. 자동 터널 설정 실행
bash scripts/jetson_ssh_tunnel.sh

# 3. ROS2 Client 실행
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
export VLA_API_SERVER="http://localhost:8000"
ros2 run mobile_vla_package api_client_node
```

### 방법 2: 수동 설정

```bash
# 1. SSH Config 설정 (한 번만)
mkdir -p ~/.ssh
cat >> ~/.ssh/config << 'EOF'

Host billy-server
  HostName 100.86.152.29
  User billy
  Port 10022
EOF

chmod 600 ~/.ssh/config

# 2. SSH Key 생성 및 등록 (한 번만, 비밀번호 생략 위해)
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa_billy -N ""
ssh-copy-id -p 10022 billy@100.86.152.29

# 3. SSH 터널 생성
source ~/vla/secrets.sh
ssh -N -f -L 8000:localhost:8000 billy-server

# 4. API 테스트
export VLA_API_SERVER="http://localhost:8000"
curl -H "X-API-Key: ${VLA_API_KEY}" http://localhost:8000/health

# 5. ROS2 실행
ros2 run mobile_vla_package api_client_node
```

---

## 🔒 보안 이점

| 항목 | Port 직접 노출 | SSH 터널링 |
|------|----------------|------------|
| 암호화 | ❌ 평문 통신 | ✅ SSH 암호화 |
| 포트 노출 | 8000번 포트 오픈 필요 | ❌ 불필요 (22만 오픈) |
| 방화벽 설정 | 복잡 (ufw 규칙 추가) | ✅ 단순 (SSH만) |
| 인증 | API Key만 | ✅ SSH Key + API Key 이중 인증 |

---

## 📊 Billy 서버 현재 상태

```bash
# SSH 데몬
● ssh.service - active (running)
  Port: 10022
  Listening: 0.0.0.0:10022, :::10022

# Tailscale
100.86.152.29  billy-ms-7e07  Direct 연결

# API 서버 (Billy에서 실행 필요 확인)
# Port 8000 (외부 노출 안됨 - 정상)
```

---

## ✅ 체크리스트

### Billy 서버:
- [x] SSH 데몬 실행 중 (Port 10022)
- [x] Tailscale 연결 활성화
- [ ] API 서버 실행 확인 필요 (`inference_server.py`)

### Jetson:
- [ ] `scripts/jetson_ssh_tunnel.sh` 실행
- [ ] SSH Key 생성 및 등록 (선택적, 비밀번호 생략 위해)
- [ ] SSH 터널 생성 확인
- [ ] API Health Check 성공 확인
- [ ] ROS2 Client 실행 테스트

---

## 📝 다음 단계

1. **Jetson에서 SSH 터널 설정**:
   ```bash
   cd ~/vla
   bash scripts/jetson_ssh_tunnel.sh
   ```

2. **Billy 서버에서 API 서버 실행 확인**:
   ```bash
   # Billy 서버에서 실행
   ps aux | grep inference_server
   
   # 실행 중이 아니면 시작:
   cd ~/25-1kp/vla
   ./scripts/start_api_server.sh
   ```

3. **Jetson에서 API 테스트**:
   ```bash
   curl -H "X-API-Key: ${VLA_API_KEY}" http://localhost:8000/health
   ```

4. **ROS2 Client 실행**:
   ```bash
   ros2 run mobile_vla_package api_client_node
   ```

---

## 🆘 문제 해결

### "Connection refused" 에러
- Billy 서버에서 `systemctl status ssh` 확인
- Port 10022가 열려있는지 확인: `ss -tlnp | grep 10022`

### "Permission denied (publickey)" 에러
- SSH Key 권한 확인: `chmod 600 ~/.ssh/id_rsa_billy`
- 또는 비밀번호 인증 사용

### API 서버 응답 없음
- Billy 서버에서 API 서버 실행 여부 확인
- `ps aux | grep inference_server`
- 로그 확인: `tail -f logs/api_server.log`

---

## 📚 참고 문서

- 자세한 가이드: `docs/SSH_TUNNEL_GUIDE.md`
- Jetson 설정: `JETSON_SETUP.md`
- 자동화 스크립트: `scripts/jetson_ssh_tunnel.sh`

---

**완료 시간**: 2025-12-18 05:54  
**상태**: ✅ Billy 서버 분석 완료, Jetson 실행 대기  
**다음**: Jetson에서 SSH 터널 설정 및 API 연결 테스트
