# 디스크 용량 분석 및 삭제 계획
**분석일:** 2025-12-17  
**작성자:** Antigravity AI Assistant

## 📊 현재 상태 요약

### 전체 디스크 사용량
```
파일시스템: /dev/nvme0n1p2
전체 용량: 1.8TB
사용 중: 1.7TB
남은 용량: 35GB
사용률: 99% ⚠️ **위험 수준**
```

### 주요 디렉토리 용량 분석

#### 1. `/home/billy/25-1kp/vla` (622GB)
| 디렉토리 | 용량 | 설명 |
|---------|------|------|
| `RoboVLMs_upstream` | 311GB | 업스트림 RoboVLMs 코드 및 실험 |
| `runs` | 163GB | 최근 실험 체크포인트 |
| `.git` | 90GB | Git 히스토리 (대용량 pack 파일 포함) |
| `.vlms` | 25GB | VLM 모델 캐시 |
| `ROS_action` | 13GB | ROS 액션 데이터 |
| `git_recovery_backup` | 7.0GB | Git 복구 백업 (2025-12-17) |
| `result` | 5.6GB | 실험 결과 |
| `Robo+` | 3.4GB | Robo+ 관련 |

#### 2. 홈 디렉토리 기타 프로젝트 (1.4TB 전체)
| 디렉토리 | 용량 | 프로젝트 상태 추정 |
|---------|------|----------------|
| `/home/billy/.cache` | 203GB | 캐시 파일 |
| `/home/billy/.cache/huggingface` | 118GB | Hugging Face 모델 캐시 |
| `/home/billy/다운로드` | 102GB | 다운로드 폴더 |
| `/home/billy/koalpaca` | 99GB | KoAlpaca 프로젝트 |
| `/home/billy/anaconda3` | 85GB | Anaconda 환경 |
| `/home/billy/.cache/pypoetry` | 49GB | Poetry 가상환경 |
| `/home/billy/yong` | 41GB | Yong 프로젝트 |
| `/home/billy/WIR` | 39GB | WIR 프로젝트 |
| `/home/billy/llama` | 31GB | LLaMA 프로젝트 |
| `/home/billy/capstone_` | 24GB | 캡스톤 프로젝트 |
| `/home/billy/rd` | 23GB | RD 프로젝트 |
| `/home/billy/Gemma` | 13GB | Gemma 프로젝트 |

---

## 🎯 삭제 계획

### **우선순위 1: 즉시 삭제 가능 (안전)** - 약 **350-400GB** 확보 가능

#### 1.1 Git Pack 파일 최적화 (약 40-50GB 확보)
- **위치:** `/home/billy/25-1kp/vla/.git/objects/pack/`
- **현재 용량:** 90GB (47GB + 13GB의 거대 pack 파일)
- **문제:** 
  - `pack-03b0d1675caebff6110bd612e14173fd633f7ca8.pack`: **47GB**
  - `pack-954945d0da4148e8a0bbf712a43ef450b1896971.pack`: **13GB**
  - Git 히스토리에 대용량 모델 체크포인트가 실수로 커밋되었을 가능성

**삭제 명령:**
```bash
# 1. Git 히스토리에서 대용량 파일 제거 (BFG Repo-Cleaner 사용)
cd /home/billy/25-1kp/vla
git gc --aggressive --prune=now

# 또는 더 강력하게:
# java -jar bfg.jar --strip-blobs-bigger-than 100M .git
# git reflog expire --expire=now --all
# git gc --prune=now --aggressive
```

#### 1.2 Git Recovery Backup 삭제 (7GB 확보)
- **위치:** `/home/billy/25-1kp/vla/git_recovery_backup/`
- **용량:** 7.0GB
- **내용:** 
  - `best_robovlms_mobile_model_epoch_1.pt` (5.2GB)
  - Git 복구 완료 후 백업 파일
- **안전성:** Git 상태가 정상화되었으므로 안전하게 삭제 가능

**삭제 명령:**
```bash
rm -rf /home/billy/25-1kp/vla/git_recovery_backup/
```

#### 1.3 로그 아카이브 정리 (224MB 확보)
- **위치:** `/home/billy/25-1kp/vla/logs/archive/`
- **용량:** 224MB
- **안전성:** 분석 완료된 과거 로그

**삭제 명령:**
```bash
rm -rf /home/billy/25-1kp/vla/logs/archive/
```

#### 1.4 Python 캐시 파일 정리 (약 1-2MB, 관리 목적)
- **위치:** 전체 프로젝트의 `__pycache__` 디렉토리
- **용량:** 약 1.5MB (미미하지만 정리 필요)

**삭제 명령:**
```bash
find /home/billy/25-1kp/vla -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find /home/billy/25-1kp/vla -type f -name "*.pyc" -delete 2>/dev/null
```

#### 1.5 Hugging Face 캐시 정리 (약 50-80GB 확보 가능)
- **위치:** `/home/billy/.cache/huggingface/hub/`
- **용량:** 117GB
- **내용:** 다운로드된 사전학습 모델들 (필요시 재다운로드 가능)

**삭제 명령 (선택적):**
```bash
# 전체 삭제 (필요시 재다운로드)
# rm -rf /home/billy/.cache/huggingface/hub/*

# 또는 오래된 모델만 삭제 (30일 이상 미사용)
find /home/billy/.cache/huggingface/hub/ -type f -atime +30 -delete 2>/dev/null
```

#### 1.6 Poetry 가상환경 캐시 정리 (약 20-30GB 확보 가능)
- **위치:** `/home/billy/.cache/pypoetry/`
- **용량:** 49GB
- **내용:** Poetry 가상환경 (재생성 가능)

**삭제 명령 (선택적):**
```bash
# 사용하지 않는 가상환경 정리
poetry env list  # 현재 환경 확인
# poetry env remove <env-name>  # 필요 없는 환경 삭제
```

#### 1.7 다운로드 폴더 정리 (약 50-90GB 확보 가능)
- **위치:** `/home/billy/다운로드/`
- **용량:** 102GB (그 중 90GB가 `Giheyon` 서브디렉토리)
- **안전성:** 현재 프로젝트와 무관한 다운로드 파일

**삭제 명령 (수동 확인 후):**
```bash
# 수동으로 확인 후 삭제
ls -lh /home/billy/다운로드/
# 필요 없는 파일/폴더 삭제
```

---

### **우선순위 2: 검토 후 삭제 (신중)** - 약 **200-300GB** 추가 확보 가능

#### 2.1 오래된 실험 체크포인트 정리 (약 100-150GB 확보)

##### A. RoboVLMs_upstream 오래된 실험 (183GB)
- **위치:** `/home/billy/25-1kp/vla/RoboVLMs_upstream/runs/mobile_vla_lora_20251106/`
- **용량:** 183GB
- **날짜:** 2025-11-06 실험 (현재 11월 실험은 성능 불량으로 확인됨)
- **검토 필요:** LoRA 실패 케이스로 문서화되었는지 확인

**삭제 명령 (검토 후):**
```bash
# Best 체크포인트만 백업 후 삭제
mkdir -p /home/billy/25-1kp/vla/checkpoints/archived_experiments/
cp /home/billy/25-1kp/vla/RoboVLMs_upstream/runs/mobile_vla_lora_20251106/*/best*.ckpt \
   /home/billy/25-1kp/vla/checkpoints/archived_experiments/ 2>/dev/null

# 전체 디렉토리 삭제
rm -rf /home/billy/25-1kp/vla/RoboVLMs_upstream/runs/mobile_vla_lora_20251106/
```

##### B. 실험 중복 체크포인트 정리 (약 50-70GB)
각 실험마다 **4-5개의 에폭 체크포인트**(각 6.9GB)가 저장됨:
- `mobile_vla_no_chunk_abs_20251210`: 28GB (4개 체크포인트)
- `mobile_vla_no_chunk_20251209`: 28GB (4개 체크포인트)
- `mobile_vla_kosmos2_aug_abs_20251209`: 28GB (4개 체크포인트)

**정리 전략:**
- **Best 체크포인트 1개만 보존**
- 나머지 에폭 체크포인트 삭제

**삭제 명령 (예시 - mobile_vla_no_chunk_abs_20251210):**
```bash
cd /home/billy/25-1kp/vla/runs/vla_runs_temp/mobile_vla_no_chunk_abs_20251210

# Best 체크포인트 확인 (val_loss 가장 낮은 것)
# epoch_epoch=04-val_loss=val_loss=0.002.ckpt 가 best

# 다른 에폭 체크포인트 삭제 (last.ckpt, 기타 에폭)
find . -name "epoch_epoch=*.ckpt" ! -name "*val_loss=0.002.ckpt" -delete
find . -name "last.ckpt" -delete
```

#### 2.2 오래된 프로젝트 정리 (약 100-200GB 확보)
다음 프로젝트들이 현재 VLA 연구와 무관해 보임:

| 프로젝트 | 용량 | 마지막 수정일 추정 | 삭제 가능성 |
|---------|------|-----------------|-----------|
| `koalpaca` | 99GB | 오래됨 | **High** |
| `yong/RLN` | 39GB | 오래됨 | Medium |
| `WIR` | 39GB | 오래됨 | Medium |
| `llama` | 31GB | 오래됨 | Medium |
| `capstone_` | 24GB | 오래됨 | **High** |
| `rd/korpatbert` | 21GB | 오래됨 | Medium |

**삭제 명령 (수동 확인 후):**
```bash
# 각 프로젝트의 마지막 수정일 확인
ls -ltrhd /home/billy/koalpaca /home/billy/capstone_ /home/billy/llama

# 백업 후 삭제 (필요시)
# tar -czf ~/backup_koalpaca_20251217.tar.gz /home/billy/koalpaca
# rm -rf /home/billy/koalpaca
```

#### 2.3 Anaconda 환경 정리 (약 30-50GB 확보)
- **위치:** `/home/billy/anaconda3/`
- **용량:** 85GB (그 중 56GB가 `envs/`, 17GB가 `pkgs/`)
- **전략:** 사용하지 않는 가상환경 제거

**삭제 명령:**
```bash
# 가상환경 목록 확인
conda env list

# 사용하지 않는 환경 삭제
# conda env remove -n <env_name>

# 패키지 캐시 정리
conda clean --all -y
```

---

### **우선순위 3: 보존 필요** - 삭제 불가

#### 3.1 현재 활성 실험 (약 160GB)
- `runs/vla_runs_temp/` (26GB - frozen VLM 최신 실험)
- `RoboVLMs_upstream/runs/` 중 최근 3개월 실험
- `.vlms/` (25GB - VLM 모델 필수)

#### 3.2 핵심 데이터셋
- `ROS_action/` (13GB - 수집한 로봇 데이터셋)
- `result/` (5.6GB - 분석 결과)

#### 3.3 코드 및 문서
- 모든 소스 코드
- `docs/` 디렉토리

---

## 📋 실행 계획 요약

### Phase 1: 즉시 실행 (안전, 약 60-80GB 확보)
```bash
# 1. Git recovery backup 삭제
rm -rf /home/billy/25-1kp/vla/git_recovery_backup/

# 2. 로그 아카이브 삭제
rm -rf /home/billy/25-1kp/vla/logs/archive/

# 3. Python 캐시 정리
find /home/billy/25-1kp/vla -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find /home/billy/25-1kp/vla -type f -name "*.pyc" -delete 2>/dev/null

# 4. Git 최적화
cd /home/billy/25-1kp/vla
git gc --aggressive --prune=now
```

### Phase 2: 검토 후 실행 (약 150-250GB 추가 확보)
```bash
# 1. 오래된 LoRA 실험 삭제 (183GB)
# [검토 필요] 교수님 미팅 자료에 사용되었는지 확인 후 삭제

# 2. 체크포인트 중복 정리 (50-70GB)
# 각 실험의 best 모델만 남기고 삭제

# 3. Hugging Face 캐시 정리 (50-80GB)
# 재다운로드 가능한 모델 캐시 삭제
```

### Phase 3: 외부 프로젝트 정리 (약 100-200GB 추가 확보)
```bash
# 1. 오래된 프로젝트 삭제 (koalpaca, capstone_ 등)
# [수동 확인 필요] 각 프로젝트 마지막 사용일 확인

# 2. Anaconda 환경 정리 (30-50GB)
# [수동 확인 필요] 사용 중인 환경 확인 후 정리
```

---

## ⚠️ 주의사항

1. **백업 우선:** 중요 데이터는 삭제 전 반드시 백업
2. **Git 히스토리 정리:** Force push가 필요하므로 팀원과 협의 필요 (현재 개인 프로젝트로 보임)
3. **실험 체크포인트:** Best 모델은 반드시 보존
4. **캐시 파일:** Hugging Face 캐시는 재다운로드 가능하지만 시간이 소요됨
5. **디스크 사용률 99%:** 즉시 조치 필요! 시스템 불안정 위험

---

## 📊 예상 확보 용량

| Phase | 작업 내용 | 예상 확보 용량 | 안전성 |
|-------|---------|--------------|--------|
| Phase 1 | Git 최적화 + 백업/로그 삭제 | 60-80GB | ✅ 안전 |
| Phase 2 | 체크포인트 + 캐시 정리 | 150-250GB | ⚠️ 검토 필요 |
| Phase 3 | 외부 프로젝트 정리 | 100-200GB | ⚠️ 수동 확인 |
| **합계** | | **310-530GB** | |

**목표 사용률:** 99% → **70-75%** (약 450GB 여유 공간 확보)

---

## 🚀 다음 단계

1. ✅ **Phase 1 즉시 실행** (사용자 승인 후)
2. 🔍 **Phase 2 검토:** 
   - LoRA 실험 결과가 논문/미팅 자료에 포함되었는지 확인
   - Best 체크포인트 식별 및 보존
3. 🔍 **Phase 3 검토:**
   - 외부 프로젝트 마지막 사용일 확인
   - 중요 데이터 백업 여부 확인

---

**생성일:** 2025-12-17 11:17 KST  
**문서 버전:** 1.0
