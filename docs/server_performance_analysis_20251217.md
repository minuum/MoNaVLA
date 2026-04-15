# 안티그래비티 서버 성능 분석 리포트
**작성일**: 2025-12-17 20:32  
**분석 대상**: Billy A5000 서버  
**문제**: 안티그래비티 서버 진입 시 지연 발생

---

## Executive Summary

안티그래비티 서버 진입 속도 저하의 **근본 원인은 Git 저장소의 비정상적인 비대화**입니다. `.git/` 디렉토리가 **90GB**를 차지하고 있으며, 이로 인해 파일 시스템 I/O 성능이 저하되고 있습니다.

### 핵심 발견사항
- ✅ **CPU/메모리**: 정상 (사용률 낮음)
- ✅ **GPU**: 정상 (유휴 상태)
- ✅ **디스크 여유 공간**: 충분 (75% 사용, 449GB 가용)
- ❌ **Git 저장소 크기**: **심각한 문제** (90GB)
- ⚠️ **임시 파일**: 주의 필요 (7GB in /tmp)

---

## 1. 시스템 리소스 상태

### 1.1 CPU & 메모리
```
Load Average: 1.10, 1.05, 1.01 (1 day uptime)
메모리: 125GB 총량, 120GB 가용, 3.5GB 사용 (정상)
CPU 사용률: ~2% (idle 98.3%)
```
**평가**: ✅ 정상 - 리소스 여유 충분

### 1.2 디스크 사용량
```
/dev/nvme0n1p2: 1.8TB 총량, 1.3TB 사용, 449GB 가용 (75%)
```
**평가**: ✅ 정상 - 여유 공간 충분

### 1.3 GPU 상태
```
NVIDIA RTX A5000: 17°C, 7W/230W
VRAM: 678MB/24564MB (3%)
GPU Util: 0%
```
**평가**: ✅ 정상 - 유휴 상태

### 1.4 네트워크 포트
```
활성 서비스:
- Port 8000: Python inference server (PID 356829)
- Port 80: HTTP 서버
- Port 10022: SSH
- Port 43467, 36179, 38389: 안티그래비티 language server
```
**평가**: ✅ 정상

---

## 2. Git 저장소 심층 분석

### 2.1 문제의 심각성
```bash
.git/ 디렉토리 크기: 90GB
.git/objects/pack/ 크기: 59GB
  - pack-03b0d1675caebff6110bd612e14173fd633f7ca8.pack: 47GB
  - pack-954945d0da4148e8a0bbf712a43ef450b1896971.pack: 13GB

총 커밋 수: 612개
In-pack 오브젝트: 18,349개
```

### 2.2 대용량 파일 분석
Git 히스토리에 포함된 대용량 파일 (상위 5개):
1. `checkpoints/cache/.../blobs/b66d3fb4...`: **515MB** (incomplete)
2. `Robo+/Mobile_VLA/quantized_models_cpu/mae0222_model_cpu.onnx`: **44MB**
3. `docs/references/2412.14058v3.pdf`: **40MB**
4. `ROS_action/src/yolov5s.pt`: **14MB**
5. `docs/references/2405.05941v1.pdf`: **10MB**

### 2.3 현재 워크스페이스 대용량 파일
- `best_robovlms_mobile_model_epoch_1.pt`: **5.6GB** (현재 파일, Git 미추적)
- `/tmp/best_robovlms_mobile_model_epoch_1.pt`: **5.2GB** (임시 파일)

### 2.4 문제 원인 추정
1. **대용량 모델 체크포인트 파일이 Git 히스토리에 추가되었다가 삭제됨**
   - 삭제된 파일도 `.git/objects/pack/`에 영구 보존됨
   - Pack 파일 2개가 총 60GB를 차지

2. **이미지 데이터셋 파일이 커밋됨**
   - `ROS_action/mobile_vla_dataset/` 디렉토리의 PNG 이미지들
   - 각 이미지 약 2.7MB, 수백~수천 장이 히스토리에 보존

3. **PDF 논문, ONNX 모델 등 바이너리 파일 누적**

---

## 3. 안티그래비티 프로세스 분석

### 3.1 주요 프로세스
```
PID 362321: language_server (CPU: 4.0%, MEM: 0.4%, Uptime: 5분 14초)
PID 361828: extensionHost (CPU: 6.8%, MEM: 0.1%)
PID 361490: server-main (CPU: 0.5%, MEM: 0.1%)
PID 356829: Python inference_server (CPU: 0.2%, MEM: 0.2%, Port 8000)
```

### 3.2 성능 이슈 연관성
- Language server가 Git 저장소를 스캔하면서 90GB의 `.git/` 디렉토리를 읽음
- 대용량 pack 파일(47GB + 13GB) 처리로 인한 I/O 지연
- 파일 워처(fileWatcher) 프로세스가 대량의 Git 오브젝트를 모니터링

---

## 4. 최근 활동 로그 분석

### 4.1 최근 50개 명령어 요약
주요 활동:
1. **모델 학습 및 체크포인트 관리**
   - Chunk5, Chunk10 모델 학습
   - 체크포인트 파일 탐색 및 관리

2. **API 서버 배포 및 테스트**
   - `inference_api_server.py` 실행 (PID 96062 → 355121 → 356829)
   - 테스트 스크립트 실행

3. **모델 파일 관리**
   - 대용량 .ckpt 파일 조회
   - 실험 결과 로그 확인

### 4.2 시스템 로그 (journalctl)
```
12월 17 19:39:19: sudo pam_unix 인증 실패 (경미)
```
**평가**: 심각한 시스템 에러 없음

---

## 5. 영향 분석

### 5.1 안티그래비티 진입 속도 저하 원인
1. **Git 오브젝트 스캔 지연**
   - 90GB `.git/` 디렉토리 초기 로딩
   - 18,349개 Git 오브젝트 인덱싱

2. **파일 워처 초기화 지연**
   - 대용량 pack 파일 메타데이터 읽기
   - 워크스페이스 파일 트리 구성 시 I/O 부하

3. **Language Server Protocol (LSP) 초기화 지연**
   - Git 히스토리 기반 코드 분석 준비
   - Blame, history 등의 기능을 위한 사전 로딩

### 5.2 기타 부작용
- Git 명령어 실행 속도 저하 (`git status`, `git log` 등)
- 디스크 공간 낭비 (90GB)
- 백업/동기화 시간 증가

---

## 6. 권장 조치사항

### 🔴 긴급 (Critical)

#### 조치 1: Git 히스토리 정리 (BFG Repo-Cleaner 사용)
```bash
# 1. 백업 생성
git clone --mirror /home/billy/25-1kp/vla /home/billy/vla-backup.git

# 2. BFG 설치 및 실행
wget https://repo1.maven.org/maven2/com/madgag/bfg/1.14.0/bfg-1.14.0.jar
java -jar bfg-1.14.0.jar --strip-blobs-bigger-than 10M /home/billy/25-1kp/vla

# 3. Git garbage collection
cd /home/billy/25-1kp/vla
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# 4. 결과 확인
git count-objects -vH
du -sh .git/
```

**예상 효과**: 
- `.git/` 크기 감소: 90GB → **예상 5~10GB**
- 진입 속도 개선: **현재 대비 5~10배 빠름**
- 디스크 공간 회수: **~80GB**

#### 조치 2: Git LFS 설정 강화
```bash
# .gitattributes 업데이트
*.pt filter=lfs diff=lfs merge=lfs -text
*.ckpt filter=lfs diff=lfs merge=lfs -text
*.onnx filter=lfs diff=lfs merge=lfs -text
*.pdf filter=lfs diff=lfs merge=lfs -text
*.png filter=lfs diff=lfs merge=lfs -text
*.jpg filter=lfs diff=lfs merge=lfs -text

# 기존 대용량 파일을 Git LFS로 마이그레이션
git lfs migrate import --include="*.pt,*.ckpt,*.onnx,*.pdf" --everything
```

### 🟡 중요 (High Priority)

#### 조치 3: .gitignore 강화
```bash
# 추가 권장 항목
checkpoints/cache/
*.pt
*.ckpt
*.pth
runs/
logs/*.log
__pycache__/
.vlms/
tensorrt_best_model/
```

#### 조치 4: /tmp 정리
```bash
# 임시 파일 정리
rm -f /tmp/best_robovlms_mobile_model_epoch_1.pt  # 5.2GB
find /tmp -name "*.npy" -mtime +7 -delete
find /tmp -name "*.log" -mtime +7 -delete
```

### 🟢 권장 (Medium Priority)

#### 조치 5: Python 캐시 정리
```bash
find /home/billy/25-1kp/vla -type d -name "__pycache__" -exec rm -rf {} +
find /home/billy/25-1kp/vla -name "*.pyc" -delete
```

#### 조치 6: 안티그래비티 로그 정리
```bash
# 7일 이상 된 로그 정리
find ~/.antigravity-server/data/logs/ -type d -mtime +7 -exec rm -rf {} +
```

---

## 7. 실행 계획

### Phase 1: 즉시 실행 (오늘)
1. ✅ 현 상태 백업
   ```bash
   git clone --mirror /home/billy/25-1kp/vla ~/vla-backup-$(date +%Y%m%d).git
   ```

2. ✅ Git 히스토리 정리 (BFG)
   - 10MB 이상 blob 제거
   - Garbage collection 실행

3. ✅ 효과 측정
   ```bash
   du -sh .git/
   time git status
   ```

### Phase 2: 후속 조치 (1주일 내)
1. Git LFS 마이그레이션
2. .gitignore 업데이트 및 커밋
3. /tmp 및 캐시 정리 스크립트 작성
4. 정기 정리 cron job 등록

### Phase 3: 모니터링 (지속)
1. 주간 디스크 사용량 체크
2. Git 저장소 크기 모니터링
3. 안티그래비티 진입 속도 측정

---

## 8. 예상 성과

### 개선 전
- `.git/` 크기: **90GB**
- 안티그래비티 진입 시간: **추정 15~30초**
- `git status` 실행 시간: **추정 5~10초**

### 개선 후 (예상)
- `.git/` 크기: **5~10GB** (90% 감소)
- 안티그래비티 진입 시간: **3~5초** (80~90% 개선)
- `git status` 실행 시간: **1초 이하** (90% 개선)
- 회수된 디스크 공간: **~80GB**

---

## 9. 위험 관리

### 위험 요소
1. **히스토리 재작성으로 인한 협업 충돌**
   - 완화: 백업 생성, 팀원 사전 공지

2. **중요 파일 손실 가능성**
   - 완화: Full mirror 백업 유지

3. **원격 저장소 동기화 문제**
   - 완화: Force push 필요성 사전 확인

### 백업 전략
```bash
# 1. 완전 백업
tar -czf ~/vla-full-backup-20251217.tar.gz /home/billy/25-1kp/vla

# 2. Git mirror 백업
git clone --mirror /home/billy/25-1kp/vla ~/vla-git-backup-20251217.git

# 3. 중요 파일 별도 보관
cp best_robovlms_mobile_model_epoch_1.pt ~/models-backup/
```

---

## 10. 결론

안티그래비티 서버 진입 지연의 **근본 원인은 Git 저장소 비대화**이며, **시스템 리소스 자체에는 문제가 없습니다**. 

**BFG Repo-Cleaner를 사용한 Git 히스토리 정리**를 통해 문제를 해결할 수 있으며, 이는 **안티그래비티 진입 속도를 5~10배 개선**할 것으로 예상됩니다.

**즉시 조치 필요**: Git 히스토리 정리가 시급하며, 정리 후 Git LFS 및 .gitignore 강화를 통해 재발을 방지해야 합니다.

---

## 부록: 참고 명령어

### Git 저장소 분석
```bash
# Pack 파일 분석
git verify-pack -v .git/objects/pack/*.idx | sort -k 3 -n | tail -20

# 대용량 파일 추적
git rev-list --objects --all | \
  git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | \
  awk '/^blob/ {print substr($0,6)}' | sort -n -k 2 | tail -20

# 삭제된 대용량 파일 찾기
git log --all --pretty=format: --name-only --diff-filter=D | \
  sort -u | grep -E '\.(pt|ckpt|pth|onnx)$'
```

### 실시간 모니터링
```bash
# 디스크 I/O 모니터링
sudo apt install sysstat
iostat -x 2

# Git 작업 벤치마크
time git status
time git log --oneline -100
```
