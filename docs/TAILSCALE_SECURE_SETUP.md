# 🔒 Billy-Jetson 보안 접속 가이드

## 📋 파일 구조 요약

### Billy 서버 (이 저장소)
```
vla/
├── secrets.sh                    # ⛔ Git 무시됨 (API Key 저장)
├── setup_security.sh              # ✅ Git에 올림 (방화벽 설정 스크립트)
├── billy_connection_info.sh       # ✅ Git에 올림 (안내 문서, 비밀 없음)
├── jetson_setup_template.sh       # ✅ Git에 올림 (Jetson용 템플릿)
└── api_server.py                  # ✅ Git에 올림 (API 서버)
```

### Jetson (로봇 쪽)
```
jetson_workspace/
├── secrets.sh                    # ⛔ 직접 생성 (Billy IP + API Key 저장)
└── vla_api_client.py             # API 클라이언트 (저장소에서 받음)
```

---

## 🚀 Billy 서버 설정 (이 문서를 보는 당신)

### 1️⃣ 비밀 정보 설정
- ✅ 이미 완료: `secrets.sh` 생성됨
- 내용:
  ```bash
  export VLA_API_KEY="qkGswLr0qTJQALrbYrrQ9rB-eVGrzD7IqLNTmswE0lU"
  ```

### 2️⃣ 방화벽 설정 (처음 한 번만)
```bash
sudo ./setup_security.sh
```
**효과**: Tailscale VPN을 통한 접속만 허용, 일반 인터넷에서의 접속 차단

### 3️⃣ 서버 실행
```bash
source secrets.sh && python3 api_server.py
```

---

## 🤖 Jetson 설정 (로봇 담당자용)

### 1️⃣ Tailscale 설치 및 실행
```bash
# Jetson에 Tailscale 설치 (한 번만)
curl -fsSL https://tailscale.com/install.sh | sh

# Tailscale 실행 (재부팅 후에도 자동 실행됨)
sudo tailscale up
```

### 2️⃣ 비밀 정보 설정
```bash
# Jetson에서 secrets.sh 생성
nano secrets.sh
```

**내용**:
```bash
export BILLY_IP="100.86.152.29"
export BILLY_URL="http://100.86.152.29:8000"
export VLA_API_KEY="qkGswLr0qTJQALrbYrrQ9rB-eVGrzD7IqLNTmswE0lU"
```

### 3️⃣ 접속 테스트
```bash
source secrets.sh
curl -H "X-API-Key: $VLA_API_KEY" $BILLY_URL/health
```

**성공 시 출력**:
```json
{"status": "healthy", "model_loaded": false, "device": "cuda"}
```

---

## 🛡️ 보안 체크리스트

| 항목 | 상태 | 설명 |
|:---|:---:|:---|
| `secrets.sh` Git 무시 | ✅ | `.gitignore`에 추가됨 |
| API Key 암호화 | ✅ | Tailscale VPN으로 전송 암호화 |
| 방화벽 설정 | ⏳ | `sudo ./setup_security.sh` 실행 필요 |
| SSH 포트 허용 | ✅ | 22번 포트 허용 (잠김 방지) |
| 외부 접속 차단 | ⏳ | 방화벽 설정 후 완료 |

---

## 🔑 비밀 정보 관리 원칙

### ✅ Git에 올려도 되는 것
- 포트 번호 (8000)
- 스크립트 코드
- 문서
- 모델 이름

### ⛔ Git에 절대 올리면 안 되는 것
- API Key
- Tailscale IP (권장)
- SSH 포트 번호 (권장)

---

## 📞 문제 해결

### Q: Jetson에서 "Connection refused" 에러
**A**: Tailscale이 켜져 있는지 확인하세요.
```bash
tailscale status
```

### Q: "Unauthorized" 에러
**A**: API Key가 정확한지 확인하세요.
```bash
echo $VLA_API_KEY  # Billy와 동일한 값이어야 함
```

### Q: SSH 접속이 끊겼어요
**A**: 방화벽 설정 전에 SSH 포트 허용 명령이 실행되었는지 확인하세요.
- 복구: 물리적으로 서버에 접속하여 `sudo ufw disable` 실행

---

**작성일**: 2025-12-18  
**관리자**: Billy  
**버전**: 1.0
