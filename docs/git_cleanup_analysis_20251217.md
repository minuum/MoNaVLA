# Git 히스토리 정리 상세 분석
**작성일**: 2025-12-17 20:37  
**목적**: Git 저장소 크기 축소 및 성능 개선

---

## 1. 현황 분석

### 1.1 Git 저장소 상태
```
.git/ 크기: 90GB
Pack 파일: 60GB (47GB + 13GB)
총 커밋: 612개
히스토리의 고유 파일: 52,604개
Uncommitted 파일: 519개
```

### 1.2 워크스페이스 대용량 디렉토리 (.gitignore 처리됨)
```
RoboVLMs_upstream/  : 128GB (runs 103GB + .vlms 25GB)
runs/               : 48GB (학습 체크포인트)
.vlms/              : 25GB (Kosmos-2 모델)
Robo+/              : 3.4GB (ONNX 모델 포함)
checkpoints/        : 277MB
```

**✅ 이 디렉토리들은 이미 .gitignore에 포함되어 있어 현재 워크스페이스에는 유지됨**

### 1.3 현재 워크스페이스의 중요 파일
```
best_robovlms_mobile_model_epoch_1.pt: 5.2GB (Git 미추적)
현재 활성 학습 체크포인트들 (runs/ 디렉토리)
VLM 모델 (.vlms/ 디렉토리)
```

---

## 2. Git 히스토리에 포함된 대용량 파일들

### 2.1 확인된 대용량 Blob (상위 항목)
```
515MB: checkpoints/cache/.../blobs/b66d3fb4... (incomplete 파일)
44MB:  Robo+/Mobile_VLA/quantized_models_cpu/mae0222_model_cpu.onnx
40MB:  docs/references/2412.14058v3.pdf
14MB:  ROS_action/src/yolov5s.pt
10MB:  docs/references/2405.05941v1.pdf
~2.7MB: ROS_action/mobile_vla_dataset/*.png (다수)
```

### 2.2 가장 많이 변경된 파일 (커밋 빈도)
```
611회: (빈 라인)
48회:  ROS_action/mobile_vla_dataset/scenario_progress.json
46회:  .gitignore
44회:  mobile_vla_data_collector.py
40회:  ROS_action/mobile_vla_dataset/time_period_stats.json
```

---

## 3. 정리 전략

### 3.1 제거 대상 (Git 히스토리에서만 제거, 워크스페이스 유지)

#### A. 대용량 모델 파일 (10MB 이상)
- ✅ `*.pt` (PyTorch 모델)
- ✅ `*.ckpt` (체크포인트)
- ✅ `*.onnx` (ONNX 모델)
- ✅ `*.pth` (PyTorch 가중치)
- ✅ `*.bin` (바이너리 모델)
- ✅ `*.safetensors` (모델 텐서)

**근거**: 이미 .gitignore에 포함되어 있으며, 현재 필요한 파일은 워크스페이스에 별도 보관

#### B. 이미지 데이터셋
- ✅ `ROS_action/mobile_vla_dataset/*.png`
- ✅ `ROS_action/mobile_vla_dataset/*.jpg`

**근거**: 데이터셋은 별도 저장소나 LFS로 관리해야 함

#### C. 불완전/임시 파일
- ✅ `*.incomplete`
- ✅ `checkpoints/cache/models--robovlms--RoboVLMs/blobs/*`

**근거**: 캐시 파일은 재생성 가능

#### D. 대용량 PDF (선택적)
- ⚠️ `docs/references/*.pdf` (10MB 이상만)

**근거**: 참고 논문은 필요하지만, 외부 링크로 대체 가능한 경우 제거

### 3.2 보존 대상 (히스토리 유지)
- ✅ 모든 소스 코드 (`.py`, `.sh`, `.md` 등)
- ✅ 설정 파일 (`.json`, `.yaml`, `.toml` 등)
- ✅ 문서 (`.md`, 소형 PDF)
- ✅ Git 설정 (`.gitignore`, `.gitattributes` 등)

---

## 4. 안전성 검증

### 4.1 현재 워크스페이스 파일 안전성
```bash
# .gitignore에 명시된 대용량 디렉토리 확인
runs/                   ✅ .gitignore에 있음 → 정리 후에도 유지됨
checkpoints/            ✅ .gitignore에 있음 → 정리 후에도 유지됨
.vlms/                  ✅ .gitignore에 있음 → 정리 후에도 유지됨
RoboVLMs_upstream/      ✅ 히스토리에 없음 (submodule?) → 안전
Robo+/                  ✅ .gitignore에 있음 → 정리 후에도 유지됨
*.pt, *.ckpt, *.onnx    ✅ .gitignore에 있음 → 정리 후에도 유지됨
```

**결론**: ✅ **현재 워크스페이스의 모든 중요 파일은 .gitignore로 보호되어 있어, Git 히스토리 정리 후에도 손실 없음**

### 4.2 Uncommitted 변경사항
```
519개 파일이 uncommitted 상태
```

**조치**: Git 히스토리 정리 전에 현재 상태 확인 필요
- 중요한 변경사항이면 커밋 또는 stash
- 불필요한 파일이면 정리

---

## 5. 정리 실행 계획

### Phase 1: 백업 (필수)
```bash
# 1. 전체 미러 백업
git clone --mirror /home/billy/25-1kp/vla ~/vla-git-backup-20251217.git

# 2. 워크스페이스 백업 (중요 파일만)
tar -czf ~/vla-workspace-backup-20251217.tar.gz \
  best_robovlms_mobile_model_epoch_1.pt \
  Mobile_VLA/ \
  ROS_action/src/ \
  scripts/ \
  docs/

# 3. runs/ 디렉토리 중 최신 체크포인트 백업
find runs/ -name "*.ckpt" -mtime -7 -exec cp -v {} ~/ckpt-backup-20251217/ \;
```

### Phase 2: BFG Repo-Cleaner 실행
```bash
# 1. BFG 다운로드
cd /home/billy/25-1kp/vla
wget https://repo1.maven.org/maven2/com/madgag/bfg/1.14.0/bfg-1.14.0.jar

# 2. 대용량 파일 제거 (10MB 이상)
java -jar bfg-1.14.0.jar --strip-blobs-bigger-than 10M .git

# 3. Git Garbage Collection
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# 4. 결과 확인
du -sh .git/
git count-objects -vH
```

### Phase 3: 정리된 히스토리 적용
```bash
# 1. 현재 브랜치 상태 확인
git status

# 2. 필요시 .gitignore 강화 (이미 충분히 설정되어 있음)
# 추가 항목 없음

# 3. 커밋 및 푸시 (원격 저장소가 있는 경우)
# git push --force origin --all
# git push --force origin --tags
```

### Phase 4: 검증
```bash
# 1. 워크스페이스 파일 확인
ls -lh best_robovlms_mobile_model_epoch_1.pt
ls -lh runs/ checkpoints/ .vlms/

# 2. Git 상태 확인
git status
git log --oneline -20

# 3. 주요 기능 테스트
python3 scripts/test_models_real_inference.py
```

---

## 6. 예상 결과

### 6.1 디스크 공간
```
개선 전:
- .git/: 90GB
- 총 사용: ~300GB

개선 후 (예상):
- .git/: 5~10GB (85~95% 감소)
- 총 사용: ~220GB
- 회수 공간: ~80GB
```

### 6.2 성능
```
안티그래비티 진입:
- 개선 전: 15~30초
- 개선 후: 3~5초

Git 명령어:
- git status: 5~10초 → <1초
- git log: 3~5초 → <1초
```

### 6.3 워크스페이스 파일
```
✅ 모든 현재 파일 유지
✅ runs/, checkpoints/, .vlms/ 등 대용량 디렉토리 보존
✅ 활성 학습 체크포인트 보존
✅ 소스 코드 및 설정 파일 유지
```

---

## 7. 위험 및 완화 방안

### 7.1 위험 요소
1. ⚠️ **Git 히스토리 재작성으로 인한 협업 충돌**
   - 완화: 개인 프로젝트인 경우 문제 없음
   - 완화: 팀 프로젝트인 경우 사전 공지 필수

2. ⚠️ **과거 특정 커밋으로 복구 불가능**
   - 완화: 미러 백업 유지
   - 완화: 중요 커밋 별도 보관

3. ⚠️ **원격 저장소 동기화 이슈**
   - 완화: Force push 필요성 인지
   - 완화: 백업 후 진행

### 7.2 안전장치
```bash
# 1. 백업 검증
ls -lh ~/vla-git-backup-20251217.git
tar -tzf ~/vla-workspace-backup-20251217.tar.gz | head -20

# 2. 복구 절차 준비
# 문제 발생 시:
# rm -rf .git
# git clone ~/vla-git-backup-20251217.git .git
# git reset --hard HEAD
```

---

## 8. 실행 체크리스트

### 사전 준비
- [ ] 현재 작업 중인 코드 커밋 또는 stash
- [ ] Uncommitted 파일 519개 확인 및 정리
- [ ] 중요 파일 목록 확인

### 백업
- [ ] Git 미러 백업 생성
- [ ] 워크스페이스 중요 파일 백업
- [ ] 최신 체크포인트 별도 보관

### 실행
- [ ] BFG 다운로드
- [ ] BFG 실행 (10MB 이상 파일 제거)
- [ ] Git GC 실행

### 검증
- [ ] .git/ 크기 확인 (목표: 10GB 이하)
- [ ] 워크스페이스 파일 무결성 확인
- [ ] Git 명령어 성능 테스트
- [ ] 학습 스크립트 동작 확인

---

## 9. 실행 명령어 요약

```bash
# ====== Step 1: 백업 ======
git clone --mirror /home/billy/25-1kp/vla ~/vla-git-backup-20251217.git
tar -czf ~/vla-workspace-backup-20251217.tar.gz \
  best_robovlms_mobile_model_epoch_1.pt \
  Mobile_VLA/ ROS_action/src/ scripts/ docs/

# ====== Step 2: BFG 정리 ======
cd /home/billy/25-1kp/vla
wget -q https://repo1.maven.org/maven2/com/madgag/bfg/1.14.0/bfg-1.14.0.jar
java -jar bfg-1.14.0.jar --strip-blobs-bigger-than 10M .git
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# ====== Step 3: 검증 ======
du -sh .git/
git count-objects -vH
ls -lh best_robovlms_mobile_model_epoch_1.pt runs/ .vlms/
git status
```

---

## 10. 결론

✅ **안전성**: 현재 워크스페이스의 모든 중요 파일은 .gitignore로 보호되어 있어 안전  
✅ **효과**: .git/ 크기 90GB → 5~10GB 예상 (85~95% 감소)  
✅ **성능**: 안티그래비티 진입 속도 5~10배 개선 예상  
⚠️ **주의**: 백업 필수, Git 히스토리 재작성은 되돌릴 수 없음  

**권장사항**: 백업 생성 후 즉시 실행 가능
