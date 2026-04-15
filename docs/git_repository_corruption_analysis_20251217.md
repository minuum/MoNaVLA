# Git Repository Corruption 분석 보고서
**날짜**: 2025-12-17  
**분석 대상**: `/home/billy/25-1kp/vla`

---

## 1. 현재 상황 요약

### 문제 증상
- **Push 불가**: 로컬과 리모트 간 sync가 깨진 상태
- **Git corruption**: 다수의 커밋 객체를 읽을 수 없음
- **Fetch 실패**: `fatal: fetch-pack: invalid index-pack output`

### 핵심 발견 사항

#### 1.1 로컬과 리모트의 분기 (Divergence)
```bash
# 로컬 HEAD (feature/inference-integration)
4ea5d752 - fix: Improve .gitignore and update chunk configs

# 리모트 HEAD (origin/feature/inference-integration)
b989865e - docs: Billy 서버 담당자를 위한 알림 메시지 추가
```

**결론**: 로컬 브랜치가 리모트보다 **6 커밋 뒤처져 있음**

#### 1.2 Git 객체 Corruption
`git fsck --full` 결과: **229개 이상의 커밋 객체를 읽을 수 없음**

예시:
- `error: Could not read 295481239b2532d918659b8c63416ad77659392e`
- `error: Could not read ecc8daaf7cbae660927fbe45c20fd7932509c058`
- (총 229+ 객체 손상)

#### 1.3 작업 디렉토리 상태
```
Untracked files: 276개
주요 카테고리:
- 데이터셋 파일 (.h5): 69개
- 문서 파일: 12개
- 스크립트 파일: 5개
```

---

## 2. 왜 Push가 안 되는가?

### 근본 원인

1. **로컬 브랜치가 outdated**
   - 로컬: `4ea5d752` (12월 중순)
   - 리모트: `b989865e` (더 최신)
   - Jetson에서 push한 커밋들을 pull 하지 않음

2. **Git repository corruption**
   - `.git/objects/` 디렉토리의 객체 파일 손상
   - Commit graph 불일치
   - 원인 추정:
     - 디스크 용량 부족 중 git 작업
     - 하드 리부트 또는 강제 종료
     - 파일 시스템 오류

3. **Fetch 불가**
   - Corrupted 객체로 인해 fetch가 실패
   - Delta 해석 실패: `fatal: 묶음에 알아내지 못한 델타 2개가 있습니다`

---

## 3. Jetson 서버 커밋 분석

### Jetson이 push한 커밋들 (리모트에만 존재)
```
b989865e - docs: Billy 서버 담당자를 위한 알림 메시지 추가
90ca4532 - feat: VLA 멀티 서버 환경 구조 재구성 (Jetson-Billy 분리)
0f0c231a - docs: Complete dataset verification final report
55c1f554 - feat: Complete full dataset color scan - confirmed single anomaly
c01e6b71 - feat: Complete color analysis - identified cause of desaturated appearance
777dec7c - feat: Complete dataset error frame analysis with evidence-based detection
```

**내용**:
- VLA 멀티 서버 환경 재구성
- 데이터셋 검증 최종 보고서
- 색상 분석 및 이상 프레임 분석

**필요성**: 이 커밋들은 Jetson의 최신 작업이므로 **반드시 받아들여야 함**

---

## 4. 해결 전략

### 전략 A: Repository 재구축 (권장) ✅

**장점**:
- 완전한 corruption 해결
- 깨끗한 시작점
- 향후 문제 방지

**단점**:
- 로컬 작업 백업 필요

**절차**:
```bash
# 1. 현재 작업 백업
cd /home/billy/25-1kp
mv vla vla_backup_20251217

# 2. 깨끗하게 clone
git clone git@github.com-vla:minuum/vla.git vla

# 3. 작업 브랜치로 이동
cd vla
git checkout feature/inference-integration

# 4. 필요한 작업 파일만 복사 (주의: 대용량 파일 제외)
# - docs/ 디렉토리의 새 문서들
# - scripts/ 디렉토리의 신규 스크립트
# - 설정 파일 변경사항

# 5. 선택적 commit & push
git add <필요한 파일들>
git commit -m "fix: Restore work after repository corruption"
git push origin feature/inference-integration
```

---

### 전략 B: 강제 동기화 (빠르지만 위험) ⚠️

**주의**: 로컬의 미커밋 작업이 **영구히 손실**될 수 있음

```bash
# 1. 리모트 상태를 강제로 가져오기
cd /home/billy/25-1kp/vla
git fetch --all
git reset --hard origin/feature/inference-integration

# 2. 작업 디렉토리 정리
git clean -fd
```

---

### 전략 C: Git 복구 시도 (시간 소요, 성공 불확실)

```bash
# 1. 커밋 그래프 재생성
rm -f .git/objects/info/commit-graph
git commit-graph write --reachable

# 2. 객체 재구성 시도
git remote prune origin
git gc --aggressive --prune=now

# 3. 다시 fetch 시도
git fetch origin feature/inference-integration
```

---

## 5. 권장 조치 순서

### 즉시 조치 (15분)

1. **현재 미커밋 작업 식별**
   ```bash
   # 새 문서들 확인
   ls -lht docs/ | head -20
   
   # 새 스크립트 확인
   ls -lht scripts/ | head -20
   ```

2. **중요 파일 백업**
   ```bash
   mkdir -p /tmp/vla_work_backup_20251217
   cp docs/*_20251217*.md /tmp/vla_work_backup_20251217/
   cp scripts/test_*.py /tmp/vla_work_backup_20251217/
   ```

3. **전략 A 실행** (repository 재구축)

---

### 후속 조치 (30분)

1. **작업 파일 복원 및 커밋**
   - 백업한 파일들 중 필요한 것만 선택
   - .gitignore 확인 후 add
   - 의미 있는 커밋 메시지로 commit

2. **대용량 파일 처리**
   - .h5 파일들은 .gitignore 확인
   - 필요시 Git LFS 설정

3. **동기화 검증**
   ```bash
   git status
   git log --oneline --graph origin/feature/inference-integration..HEAD
   git push origin feature/inference-integration
   ```

---

## 6. 예방 조치

### 향후 권장사항

1. **정기적 백업**
   ```bash
   # cron job 설정
   0 2 * * * cd /home/billy/25-1kp/vla && git push origin --all
   ```

2. **대용량 파일 관리**
   - .gitignore 철저히 관리
   - Git LFS 활용
   - 50MB 이상 파일은 rsync 사용

3. **디스크 용량 모니터링**
   ```bash
   # 주간 디스크 체크
   df -h /home
   du -sh /home/billy/25-1kp/vla/.git
   ```

4. **작업 흐름 개선**
   - 하루 단위로 commit & push
   - Feature branch 단위 작업
   - Pull 먼저, push 나중에

---

## 7. 즉시 실행 가능한 명령어

### Option 1: 안전한 재구축 (추천)
```bash
# 백업
cd /home/billy/25-1kp
cp -r vla vla_backup_$(date +%Y%m%d_%H%M%S)

# 재 clone
rm -rf vla
git clone git@github.com-vla:minuum/vla.git vla
cd vla
git checkout feature/inference-integration

# 필요한 작업 파일 복원 (수동)
```

### Option 2: 빠른 강제 동기화 (주의!)
```bash
cd /home/billy/25-1kp/vla
git fetch --all
git reset --hard origin/feature/inference-integration
git clean -fd
```

---

## 8. 다음 단계 결정 필요

**질문**:
1. 로컬에 **미커밋된 중요 작업**이 있습니까?
2. 시간적 여유는 어느 정도입니까? (15분 vs 1시간)
3. Jetson의 최신 커밋을 **즉시** 받아야 합니까?

**선택지에 따른 권장**:
- 중요 작업 있음 + 시간 있음 → **전략 A** (재구축)
- 중요 작업 없음 + 빠르게 → **전략 B** (강제 동기화)
- 시간 많음 + 실험적 → **전략 C** (복구 시도)

---

## 부록: 손상된 객체 목록

총 229개 이상의 커밋 객체 손상 확인.
주요 패턴: 모든 SHA-1 해시 범위에 걸쳐 분산됨 (0~f)
→ 시스템적 문제 (디스크, 파일시스템) 가능성 높음
