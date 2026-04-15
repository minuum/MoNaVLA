# RoboVLMs 서브모듈 푸시 권한 설정 가이드

## 현재 상황
- 원격 저장소: `https://github.com/minuum/RoboVLMs.git`
- 로컬에 3개의 새로운 커밋이 있음
- 푸시 시 권한 오류 발생

## 해결 방법

### 방법 1: GitHub Personal Access Token 사용 (권장)

#### 1단계: Personal Access Token 생성
1. GitHub 웹사이트 접속: https://github.com
2. 우측 상단 프로필 클릭 → Settings
3. 좌측 메뉴에서 "Developer settings" 클릭
4. "Personal access tokens" → "Tokens (classic)" 선택
5. "Generate new token" → "Generate new token (classic)" 클릭
6. 설정:
   - Note: "RoboVLMs push access"
   - Expiration: 원하는 기간 선택 (또는 No expiration)
   - Scopes: `repo` 체크 (전체 저장소 권한)
7. "Generate token" 클릭
8. **토큰을 복사해 안전한 곳에 보관** (한 번만 표시됨)

#### 2단계: Git Credential 설정
```bash
cd /home/billy/25-1kp/vla/RoboVLMs_upstream

# 방법 A: URL에 토큰 포함 (임시)
git remote set-url origin https://<TOKEN>@github.com/minuum/RoboVLMs.git

# 방법 B: Git Credential Helper 사용 (권장)
git config credential.helper store
# push 시 토큰 입력하면 자동 저장됨
```

#### 3단계: 푸시 실행
```bash
git push origin main
# Username: minuum 입력
# Password: Personal Access Token 입력
```

---

### 방법 2: SSH 키 사용

#### 1단계: SSH 키 생성 (없는 경우)
```bash
ssh-keygen -t ed25519 -C "minwool0357@gmail.com" -f ~/.ssh/id_ed25519_minuum
```

#### 2단계: 공개 키를 GitHub에 등록
1. 공개 키 내용 확인:
```bash
cat ~/.ssh/id_ed25519_minuum.pub
```

2. GitHub 웹사이트:
   - Settings → SSH and GPG keys
   - "New SSH key" 클릭
   - Title: "RoboVLMs Server"
   - Key: 위에서 복사한 공개 키 붙여넣기
   - "Add SSH key" 클릭

#### 3단계: SSH 설정
```bash
# ~/.ssh/config에 추가
cat >> ~/.ssh/config << 'EOF'
Host github.com-minuum
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_minuum
    IdentitiesOnly yes
EOF
```

#### 4단계: 원격 URL 변경
```bash
cd /home/billy/25-1kp/vla/RoboVLMs_upstream
git remote set-url origin git@github.com-minuum:minuum/RoboVLMs.git
```

#### 5단계: 푸시 실행
```bash
git push origin main
```

---

### 방법 3: GitHub 저장소 권한 요청

minuum 계정의 저장소에 직접 접근 권한이 없는 경우:

1. 저장소 소유자(minuum)에게 Collaborator 권한 요청
2. 또는 Fork 후 Pull Request 생성

---

## 현재 저장소별 설정 확인

### vla 메인 저장소
```bash
cd /home/billy/25-1kp/vla
git config --local user.name
git config --local user.email
# 이미 minuum으로 설정됨
```

### RoboVLMs 서브모듈
```bash
cd /home/billy/25-1kp/vla/RoboVLMs_upstream
git config user.name
git config user.email
# 필요시 설정:
git config user.name "minuum"
git config user.email "minwool0357@gmail.com"
```

---

## 권장 순서

1. **Personal Access Token 방법**이 가장 간단하고 안전함
2. 토큰 생성 후 credential helper 사용
3. 한 번 인증하면 이후 자동으로 사용됨

---

## 주의사항

- Personal Access Token은 비밀번호처럼 취급
- 토큰을 코드나 공개 장소에 커밋하지 말 것
- 필요시 토큰을 회전(재생성)할 수 있음
- SSH 키 방법은 더 안전하지만 초기 설정이 복잡함

