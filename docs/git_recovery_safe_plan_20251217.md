# Git Repository 복구 안전 계획
**날짜**: 2025-12-17 21:52  
**작성자**: Antigravity AI

---

## 🔍 로컬 중요 자산 파악 완료

### 1. .gitignore된 중요 파일/디렉토리

#### 📦 **학습 체크포인트 및 결과 (48GB)**
```
runs/                                          48GB
├── mobile_vla_no_chunk_20251209/              (No chunk 학습 결과)
│   └── kosmos/mobile_vla_finetune/2025-12-17/
│       ├── mobile_vla_chunk5_20251217/        (오늘 학습)
│       └── mobile_vla_chunk10_20251217/       (오늘 학습)
├── vla_runs_temp/                             (이전 실험들)
│   ├── mobile_vla_no_chunk_aug_abs_20251210/
│   ├── mobile_vla_no_chunk_20251209/
│   └── mobile_vla_no_chunk_abs_20251210/
├── mobile_vla_lora_20251114/
└── cache/
```

**주의**: 이 디렉토리는 .gitignore에 있어서 **Git에 추적되지 않음**  
**중요도**: ⭐⭐⭐⭐⭐ (최고 - 연구의 핵심 결과물)

---

#### 🗄️ **데이터셋 (13GB)**
```
ROS_action/mobile_vla_dataset/                 13GB
├── episode_*.h5                               (500개 에피소드)
```

**상태**: Git LFS로 관리되지만 로컬에만 존재하는 파일 있을 수 있음  
**중요도**: ⭐⭐⭐⭐⭐ (최고 - Jetson에서 수집한 데이터)

---

#### 💾 **베이스 모델 체크포인트 (277MB)**
```
checkpoints/                                   277MB
├── RoboVLMs/
│   └── checkpoints/kosmos_ph_oxe-pretrain.pt  (36KB - 심볼릭 링크?)
└── cache/                                     277MB
    └── models--robovlms--RoboVLMs/           (HuggingFace 캐시)
```

**상태**: .gitignore에 있음, 재다운로드 가능  
**중요도**: ⭐⭐ (중간 - 재다운로드 가능)

---

### 2. Git 추적 중인 파일 (미커밋 상태)

#### 📄 **문서 (오늘 작성/수정)**
```
docs/
├── VLA_ALIASES_GUIDE.md                       (21:45 작성)
├── final_status_meeting_ready_20251217.md     (21:43)
├── api_server_debugging_20251217.md           (21:42)
├── dataset_validation_20251217.json           (21:18, 289KB)
├── dataset_validation_20251217.md             (21:18, 30KB)
├── progress_summary_20251217.md               (21:00)
├── git_cleanup_result_20251217.md             (20:46)
├── git_cleanup_analysis_20251217.md           (20:38)
├── server_performance_analysis_20251217.md    (20:34)
├── experiment_status_20251217.md              (19:34)
├── INFERENCE_API_GUIDE.md                     (13:32)
├── next_steps_progress_20251217.md            (13:30)
├── chunk10_final_report_20251217.md           (13:09)
├── chunk10_training_report_20251217.md        (12:58)
├── cleanup_result_20251217.md                 (11:22)
└── disk_cleanup_plan_20251217.md              (11:20)
```

**상태**: Untracked (아직 커밋되지 않음)  
**중요도**: ⭐⭐⭐⭐ (높음 - 오늘 하루 작업 결과)

---

#### 🔧 **스크립트 (오늘 작성/수정)**
```
scripts/
├── install_vla_aliases.sh                     (21:46)
├── test_chunk5_inference.py                   (21:41)
├── test_models_real_inference.py              (18:52)
├── test_inference_api.py                      (13:31)
├── test_models_simple.py                      (13:08)
├── test_all_models_inference.py               (13:07)
└── cleanup_checkpoints.py                     (11:23)
```

**상태**: Untracked (일부는 Git에 추적 중일 수 있음)  
**중요도**: ⭐⭐⭐⭐ (높음 - 실험 및 배포 스크립트)

---

#### ⚙️ **설정 파일**
```
Mobile_VLA/configs/
├── mobile_vla_chunk10_20251217.json           (오늘 생성)
├── mobile_vla_chunk5_20251217.json            (오늘 생성)
└── [기타 21개 설정 파일]                       (모두 Git 추적 중)
```

**상태**: Git 추적 중 (이미 커밋됨)  
**중요도**: ⭐⭐⭐ (중간 - Git에 이미 있음)

---

#### 📂 **학습 스크립트**
```
scripts/train_active/
├── train_chunk10.sh                           (최근 수정)
├── train_chunk5.sh
├── train_aug_abs.sh
├── train_openvla.sh
├── run_all_experiments.sh
├── train_no_chunk.sh
├── train_case3_fixed.sh
├── train_frozen_vlm.sh
└── train_abs_action.sh
```

**상태**: Git 추적 중 또는 Untracked  
**중요도**: ⭐⭐⭐ (중간)

---

## ⚠️ Git Repository 재구축 시 주의사항

### 🚨 **절대 손실되어서는 안 되는 것들**

1. **`runs/` 디렉토리 전체 (48GB)**
   - Chunk5, Chunk10 학습 결과 (오늘 완료)
   - No chunk 학습 결과
   - 모든 이전 실험 체크포인트

2. **`ROS_action/mobile_vla_dataset/` (13GB)**
   - 500개 에피소드 데이터
   - Jetson에서 수집한 원본 데이터

3. **오늘 작성한 문서들 (16개)**
   - 특히 dataset_validation, chunk10 리포트, API 가이드

4. **오늘 작성한 스크립트들 (7개)**
   - test_chunk5_inference.py, install_vla_aliases.sh 등

---

### ✅ **재다운로드/재생성 가능한 것들**

1. **`checkpoints/cache/` (277MB)**
   - HuggingFace에서 재다운로드 가능

2. **Git 추적 중인 기존 설정 파일들**
   - 리모트에서 pull하면 복구됨

---

## 📋 안전한 복구 절차 (수정안)

### Phase 1: 완전 백업 (필수)

```bash
# 1. 전체 프로젝트 백업 (안전을 위해)
cd /home/billy/25-1kp
sudo rsync -av --info=progress2 vla/ vla_backup_full_20251217/

# 2. 중요 자산만 별도 백업
mkdir -p /tmp/vla_critical_backup_20251217
cd /home/billy/25-1kp/vla

# 학습 결과 (48GB - 시간 소요)
echo "학습 결과 백업 중... (48GB)"
rsync -av --info=progress2 runs/ /tmp/vla_critical_backup_20251217/runs/

# 데이터셋 심볼릭 링크 또는 경로 저장 (Jetson에 원본 있으므로 선택사항)
# rsync -av --info=progress2 ROS_action/mobile_vla_dataset/ /tmp/vla_critical_backup_20251217/dataset/

# 오늘 작성 문서
rsync -av docs/*_20251217*.* /tmp/vla_critical_backup_20251217/docs/
cp docs/INFERENCE_API_GUIDE.md /tmp/vla_critical_backup_20251217/docs/
cp docs/VLA_ALIASES_GUIDE.md /tmp/vla_critical_backup_20251217/docs/

# 오늘 작성 스크립트
cp scripts/install_vla_aliases.sh /tmp/vla_critical_backup_20251217/scripts/
cp scripts/test_chunk5_inference.py /tmp/vla_critical_backup_20251217/scripts/
cp scripts/test_models_real_inference.py /tmp/vla_critical_backup_20251217/scripts/
cp scripts/test_all_models_inference.py /tmp/vla_critical_backup_20251217/scripts/
cp scripts/test_models_simple.py /tmp/vla_critical_backup_20251217/scripts/
cp scripts/cleanup_checkpoints.py /tmp/vla_critical_backup_20251217/scripts/

# 백업 확인
du -sh /tmp/vla_critical_backup_20251217/
ls -lh /tmp/vla_critical_backup_20251217/runs/
```

**예상 시간**: 15-30분 (48GB 전송)  
**필수 여부**: ✅ **절대 필수**

---

### Phase 2: Git Repository 재구축

```bash
# 3. 현재 디렉토리 이름 변경
cd /home/billy/25-1kp
mv vla vla_corrupted_20251217

# 4. 깨끗하게 clone
git clone git@github.com-vla:minuum/vla.git vla
cd vla

# 5. Jetson의 최신 커밋이 있는 브랜치로 이동
git checkout feature/inference-integration

# 6. 현재 리모트 상태 확인
git log --oneline -10
# 예상: b989865e (origin/feature/inference-integration) 최신 커밋
```

**예상 시간**: 5분  
**결과**: Jetson의 6개 최신 커밋 자동 반영

---

### Phase 3: 중요 자산 복원

```bash
# 7. .gitignore된 중요 디렉토리 복원
cd /home/billy/25-1kp/vla

# runs 디렉토리 복원 (48GB)
echo "학습 결과 복원 중..."
rsync -av --info=progress2 /tmp/vla_critical_backup_20251217/runs/ ./runs/

# 또는 기존 corrupted 버전에서 직접 이동 (더 빠름)
mv ../vla_corrupted_20251217/runs ./runs

# 데이터셋 복원 (Jetson에서 sync 예정이면 skip 가능)
# rsync -av /tmp/vla_critical_backup_20251217/dataset/ ./ROS_action/mobile_vla_dataset/

# 8. 오늘 작성 문서 복원
cp /tmp/vla_critical_backup_20251217/docs/*.md ./docs/
cp /tmp/vla_critical_backup_20251217/docs/*.json ./docs/

# 9. 오늘 작성 스크립트 복원
cp /tmp/vla_critical_backup_20251217/scripts/*.py ./scripts/
cp /tmp/vla_critical_backup_20251217/scripts/*.sh ./scripts/

# 10. 복원 확인
ls -lh runs/
ls -lh docs/*_20251217*
ls -lh scripts/test_*.py
```

**예상 시간**: 15-30분 (48GB 전송 또는 mv)

---

### Phase 4: 새 작업 커밋

```bash
# 11. 오늘 작업물 Git에 추가
git status

# 문서 추가
git add docs/*_20251217*.md
git add docs/*_20251217*.json
git add docs/INFERENCE_API_GUIDE.md
git add docs/VLA_ALIASES_GUIDE.md

# 스크립트 추가
git add scripts/test_chunk5_inference.py
git add scripts/install_vla_aliases.sh
git add scripts/test_all_models_inference.py
git add scripts/test_models_simple.py
git add scripts/test_models_real_inference.py
git add scripts/cleanup_checkpoints.py

# 커밋
git commit -m "docs: Add 20251217 experiment reports and API guides

- Add chunk10 training and final reports
- Add dataset validation results
- Add inference API and VLA aliases guides
- Add test scripts for chunk5 and multi-model inference
- Add server debugging and cleanup documentation
"

# 12. Push
git push origin feature/inference-integration
```

---

### Phase 5: 검증

```bash
# 13. 최종 상태 확인
git status
git log --oneline --graph -10

# 14. 중요 파일 존재 확인
ls -lh runs/mobile_vla_no_chunk_20251209/kosmos/mobile_vla_finetune/2025-12-17/
ls -lh docs/*_20251217*
ls -lh scripts/test_*.py

# 15. 디스크 사용량 확인
du -sh runs/
du -sh ROS_action/mobile_vla_dataset/
```

---

## 🔄 대안: 더 빠르고 안전한 방법

### Option B: 기존 디렉토리 유지하고 Git만 초기화

```bash
# 1. Git 디렉토리만 백업
cd /home/billy/25-1kp/vla
mv .git .git_corrupted_20251217

# 2. 새로운 clone을 다른 곳에 만들기
cd /tmp
git clone git@github.com-vla:minuum/vla.git vla_clean
cd vla_clean
git checkout feature/inference-integration

# 3. .git 디렉토리만 가져오기
cp -r .git /home/billy/25-1kp/vla/

# 4. 원래 위치로 돌아가서 상태 확인
cd /home/billy/25-1kp/vla
git status
# 예상: 오늘 작성한 파일들만 untracked로 표시됨

# 5. 오늘 작업물 커밋
git add docs/*_20251217*.md docs/*.json scripts/test_*.py scripts/*.sh
git commit -m "docs: Add 20251217 work"
git push origin feature/inference-integration
```

**장점**:
- `runs/`, `ROS_action/mobile_vla_dataset/` 그대로 유지
- 복사/이동 시간 절약 (30분 → 5분)
- 실수 가능성 최소화

**단점**:
- Git 디렉토리 corruption이 완전히 해결되지 않을 가능성 (낮음)

---

## 💡 최종 권장사항

### 추천: **Option B** (더 빠르고 안전)

**이유**:
1. **시간 효율**: 5분 vs 60분
2. **안전성**: 기존 파일 그대로, Git만 교체
3. **단순성**: 복잡한 rsync 불필요

**조건**:
- `runs/` 48GB를 옮기기 부담스러움
- Jetson 커밋만 받으면 됨
- 로컬 작업물 보존이 최우선

---

### 실행 확인 필요사항

진행하기 전에 확인해주세요:

1. **데이터셋이 Jetson에도 있나요?**
   - ✅ Yes → `ROS_action/mobile_vla_dataset/` 백업 선택사항
   - ❌ No → 반드시 백업 필요

2. **`runs/` 디렉토리 백업할 공간이 있나요?**
   ```bash
   df -h /tmp
   df -h /home/billy
   ```

3. **어떤 방법을 선호하시나요?**
   - Option A: 완전 재구축 (안전하지만 느림, 60분)
   - Option B: .git만 교체 (빠르고 안전함, 5분) ← **추천**

어떤 방법으로 진행할까요?
