# VLA Aliases 사용 가이드

**작성일:** 2025-12-17

---

## 🚀 설치 방법

### 1. `.bashrc`에 추가 (권장)

```bash
# ~/.bashrc 파일 끝에 다음 줄을 추가
echo '' >> ~/.bashrc
echo '# VLA Project Aliases' >> ~/.bashrc
echo 'source ~/25-1kp/vla/.vla_aliases' >> ~/.bashrc

# 적용
source ~/.bashrc
```

### 2. 수동 로드 (임시 사용)

```bash
source ~/25-1kp/vla/.vla_aliases
```

---

## 📋 주요 Alias 목록

### 학습 관찰 📊

| Alias | 설명 |
|-------|------|
| `vla-tb` | Tensorboard 시작 (포트 6006) |
| `vla-log` | 최근 학습 로그 실시간 확인 |
| `vla-log-chunk5` | Chunk5 학습 로그 |
| `vla-log-chunk10` | Chunk10 학습 로그 |
| `vla-train-status` | 학습 프로세스 상태 확인 |
| `vla-ckpt` | 최근 체크포인트 확인 |
| `vla-ckpt-chunk5` | Chunk5 체크포인트 Top 5 |
| `vla-ckpt-chunk10` | Chunk10 체크포인트 Top 5 |

### 추론 서버 🚀

| Alias | 설명 |
|-------|------|
| `vla-server-start` | 서버 시작 (중복 체크 포함) |
| `vla-server-stop` | 서버 종료 |
| `vla-server-restart` | 서버 재시작 |
| `vla-server-status` | 서버 실행 상태 확인 |
| `vla-server-log` | 서버 로그 실시간 확인 |
| `vla-server-health` | API 헬스 체크 (JSON) |
| `vla-api-test` | API 전체 테스트 실행 |

### GPU & 시스템 💻

| Alias | 설명 |
|-------|------|
| `vla-gpu` | GPU 상태 실시간 모니터링 (watch) |
| `vla-gpu-quick` | GPU 상태 한 번만 확인 |
| `vla-gpu-mem` | GPU 메모리만 간단히 |
| `vla-status` | 전체 시스템 상태 (GPU + 프로세스 + 디스크) |
| `vla-disk` | 디스크 사용량 Top 20 |
| `vla-disk-runs` | runs 디렉토리 사용량 |

### 데이터셋 📦

| Alias | 설명 |
|-------|------|
| `vla-data-count` | 데이터셋 에피소드 개수 |
| `vla-data-validate` | 데이터셋 검증 실행 |
| `vla-data-recent` | 최근 수집된 데이터 20개 |

### 학습 시작 🎓

| Alias | 설명 |
|-------|------|
| `vla-train-chunk5` | Chunk5 학습 시작 |
| `vla-train-chunk10` | Chunk10 학습 시작 |
| `vla-train-stop` | 학습 프로세스 종료 |

### 프로젝트 관리 🛠️

| Alias | 설명 |
|-------|------|
| `vla` | VLA 프로젝트 디렉토리로 이동 |
| `vla-git` | Git 상태 확인 |
| `vla-git-log` | Git 로그 (최근 10개) |
| `vla-log-clean` | 7일 이상 된 로그 삭제 |
| `vla-overview` | 전체 상황 한눈에 보기 ⭐ |
| `vla-meeting-ready` | 미팅 준비 체크리스트 |
| `vla-help` | 전체 alias 도움말 |

### 긴급 ⚠️

| Alias | 설명 |
|-------|------|
| `vla-kill-all` | 모든 VLA 프로세스 강제 종료 |

---

## 💡 사용 예시

### 일반적인 작업 흐름

```bash
# 1. 프로젝트 디렉토리로 이동
vla

# 2. 전체 상황 확인
vla-overview

# 3. GPU 상태 확인
vla-gpu-quick

# 4. 추론 서버 시작
vla-server-start

# 5. 서버 상태 확인
vla-server-status
vla-server-health

# 6. Tensorboard 시작 (별도 터미널)
vla-tb
```

### 학습 모니터링

```bash
# 터미널 1: 학습 로그 확인
vla-log-chunk5

# 터미널 2: GPU 상태 실시간
vla-gpu

# 터미널 3: Tensorboard
vla-tb
```

### 미팅 준비

```bash
# 전체 체크
vla-meeting-ready

# 최근 체크포인트 확인
vla-ckpt-chunk5
vla-ckpt-chunk10

# 데이터 개수 확인
vla-data-count
```

### 문제 해결

```bash
# 서버가 응답 안 할 때
vla-server-status
vla-server-log

# 서버 재시작
vla-server-restart

# 모든 프로세스 확인
vla-status

# 긴급 종료
vla-kill-all
```

---

## 🎯 즐겨 사용할 Alias Top 10

1. **`vla-overview`** - 전체 상황 한눈에
2. **`vla-server-start`** - 서버 시작
3. **`vla-server-status`** - 서버 상태 확인
4. **`vla-gpu-quick`** - GPU 빠르게 확인
5. **`vla-log`** - 학습 로그 확인
6. **`vla-ckpt`** - 최근 체크포인트
7. **`vla-tb`** - Tensorboard
8. **`vla-data-count`** - 데이터 개수
9. **`vla-meeting-ready`** - 미팅 준비
10. **`vla-help`** - 도움말

---

## ⚙️ 커스터마이징

`.vla_aliases` 파일을 직접 수정하여 자신만의 alias를 추가할 수 있습니다:

```bash
# 파일 편집
nano ~/25-1kp/vla/.vla_aliases

# 수정 후 다시 로드
source ~/25-1kp/vla/.vla_aliases
```

---

## 📝 팁

### 1. Tab 자동완성
대부분의 터미널에서 `vla-`까지 입력 후 Tab을 누르면 사용 가능한 모든 alias를 보여줍니다.

### 2. 체이닝
여러 명령을 연결할 수 있습니다:
```bash
vla && vla-overview && vla-server-status
```

### 3. 백그라운드 실행
서버나 Tensorboard는 자동으로 백그라운드에서 실행됩니다.

### 4. 로그 확인
모든 로그는 `logs/` 디렉토리에 타임스탬프와 함께 저장됩니다.

---

## 🆘 문제 해결

### Alias가 작동하지 않을 때

```bash
# 1. .bashrc에 제대로 추가되었는지 확인
grep vla_aliases ~/.bashrc

# 2. 수동으로 다시 로드
source ~/25-1kp/vla/.vla_aliases

# 3. 새 터미널 열기
```

### 서버 시작이 안 될 때

```bash
# 1. 기존 프로세스 확인
vla-server-status

# 2. 강제 종료 후 재시작
vla-server-stop
sleep 2
vla-server-start

# 3. 로그 확인
vla-server-log
```

---

## 🎉 즐거운 연구 되세요!

문제가 있거나 새로운 alias가 필요하면 `.vla_aliases` 파일을 자유롭게 수정하세요!
