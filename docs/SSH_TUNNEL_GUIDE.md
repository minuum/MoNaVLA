# 🔒 SSH 터널링 가이드 (Jetson ↔ Billy)

## ⚠️ **중요 발견사항**

Billy 서버는 **Port 10022**에서 SSH를 listening하고 있습니다 (Port 22가 아님!).

```bash
# Billy 서버 SSH 설정 확인 결과
Port 10022
```

---

## 📊 현재 상황

| 항목 | 상태 | 비고 |
|------|------|------|
| Tailscale 연결 | ✅ | Direct (100.86.152.29) |
| SSH 데몬 (Billy) | ✅ | Port 10022 listening |
| Port 8000 (API) | ❌ | 외부 노출 안됨 (정상) |
| Jetson 접속 시도 | ❌ | Port 22로 시도했으나 실패 |

---

## 🚀 Jetson에서 실행할 명령어

### 방법 1: 직접 SSH 터널 생성 (Port 10022 사용)

```bash
# 1. 환경 변수 로드
source /path/to/secrets.sh  # BILLY_IP, VLA_API_KEY 포함

# 2. SSH 터널 생성 (비밀 연결, Port 10022 사용!)
ssh -N -f -L 8000:localhost:8000 billy@${BILLY_IP} -p 10022
# 비밀번호 또는 SSH Key 입력

# 3. API 서버 테스트
export VLA_API_SERVER="http://localhost:8000"
curl -H "X-API-Key: ${VLA_API_KEY}" http://localhost:8000/health

# 출력 예상:
# {"status":"healthy","model":"loaded","device":"cuda"}
```

### 방법 2: SSH Config 파일 사용 (권장)

```bash
# 1. SSH Config 설정 (한 번만 실행)
mkdir -p ~/.ssh
cat >> ~/.ssh/config << 'EOF'

Host billy-server
  HostName 100.86.152.29
  User billy
  Port 10022
  # SSH Key 사용 시 (권장):
  # IdentityFile ~/.ssh/id_rsa_billy
EOF

chmod 600 ~/.ssh/config

# 2. SSH 터널 생성 (간단한 명령어로!)
ssh -N -f -L 8000:localhost:8000 billy-server

# 3. API 테스트
source /path/to/secrets.sh
export VLA_API_SERVER="http://localhost:8000"
curl -H "X-API-Key: ${VLA_API_KEY}" http://localhost:8000/health
```

---

## 🤖 ROS2 Client 실행

```bash
# 1. SSH 터널이 실행 중인지 확인
ps aux | grep "ssh -N"
# 출력에 "ssh -N -f -L 8000:localhost:8000" 확인

# 2. ROS2 환경 설정
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash

# 3. 환경 변수 설정
export VLA_API_SERVER="http://localhost:8000"
export VLA_API_KEY="your-secret-key-here"

# 4. ROS2 Client Node 실행
ros2 run mobile_vla_package api_client_node
```

---

## 🔐 SSH Key 기반 인증 설정 (비밀번호 없이 접속)

### Jetson에서 실행:

```bash
# 1. SSH Key 생성 (없는 경우)
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa_billy -N ""

# 2. Public Key를 Billy 서버로 복사
ssh-copy-id -p 10022 billy@100.86.152.29
# 비밀번호 입력 (마지막으로!)

# 3. 테스트 (비밀번호 없이 접속되어야 함)
ssh -p 10022 billy@100.86.152.29 "echo 'SSH Key 인증 성공!'"
```

---

## 🛠️ 문제 해결 (Troubleshooting)

### 1. "Connection refused" 에러
```bash
# Billy 서버에서 SSH 데몬 확인
systemctl status ssh

# SSH가 Port 10022에서 listening 중인지 확인
ss -tlnp | grep 10022
```

### 2. "Permission denied" 에러
```bash
# SSH Key 파일 권한 확인
chmod 600 ~/.ssh/id_rsa_billy
chmod 644 ~/.ssh/id_rsa_billy.pub
chmod 700 ~/.ssh
```

### 3. SSH 터널 종료하기
```bash
# SSH 터널 프로세스 찾기
ps aux | grep "ssh -N"

# 프로세스 종료 (PID 확인 후)
kill <PID>
```

### 4. Billy 서버 SSH Port를 22로 변경하려면
```bash
# Billy 서버에서 실행 (주의: 현재 SSH 세션 유지 필요)
sudo sed -i 's/^Port 10022/Port 22/' /etc/ssh/sshd_config
sudo systemctl restart ssh

# 새 터미널에서 Port 22로 접속 테스트 후, 기존 세션 종료
```

---

## ✨ SSH 터널링의 장점

| 장점 | 설명 |
|------|------|
| 🔒 **암호화** | 모든 통신이 SSH로 암호화됨 |
| 🚫 **포트 보호** | 8000번 포트를 외부 노출 불필요 |
| ✅ **방화벽 우회** | Tailscale + SSH만 열면 됨 |
| 🎯 **단순성** | 복잡한 방화벽 설정 불필요 |

---

## 📝 요약

1. **Billy 서버**: SSH Port 10022 사용 중
2. **Jetson → Billy**: `-p 10022` 옵션으로 SSH 터널 생성
3. **API 접속**: `localhost:8000`으로 안전하게 접속
4. **보안**: SSH Key 기반 인증 권장

**이제 Jetson에서 위 명령어를 실행하면 안전하게 API 서버에 접속할 수 있습니다!** 🚀
