# 서버 상태 및 디스크 정리 보고서

**일시**: 2025-12-24 05:28 KST

---

## 🔍 현재 상태

### 1. API Server 상태

**상태**: ❌ 실행 중 아님

**확인 결과**:
```bash
ps aux | grep uvicorn | grep -v grep
# 결과: 없음
```

**inference_server.py**:
- ✅ 코드: BitsAndBytes INT8로 업데이트 완료
- ❌ 실행: 서버 미실행

**해야 할 일**:
```bash
cd /home/billy/25-1kp/vla
export VLA_API_KEY="your-secret-key"
uvicorn Mobile_VLA.inference_server:app --host 0.0.0.0 --port 8000
```

---

### 2. 디스크 사용량 (⚠️ 심각)

**전체 디스크**:
- 용량: 1.8 TB
- 사용: 1.5 TB
- 여유: 232 GB
- **사용률: 87%** ⚠️

**문제 발견**:

#### `.git_corrupted_20251217/` 
- **크기: 33 GB** 🚨
- 파일 수: 723개
- objects/: 4.0 GB
- index: 3.4 GB

#### `.git.bfg-report/`
- 크기: 124 KB (무시 가능)

---

## 🗑️ 정리 계획

### 우선순위 1: `.git_corrupted_20251217/` 삭제

**이유**:
1. 2025-12-17에 생성된 백업 (7일 경과)
2. 현재 Git 정상 작동 중
3. **33 GB 회수 가능**
4. 필요시 이미 GitHub에 백업됨

**안전성**:
- ✅ 현재 `.git/` 폴더 정상
- ✅ Git 작업 정상 (push 완료)
- ✅ 백업은 이미 GitHub에 존재

**삭제 명령어**:
```bash
# 확인
ls -lh .git_corrupted_20251217/

# 삭제
rm -rf .git_corrupted_20251217/
rm -rf .git.bfg-report/

# 확인
df -h /home
```

**예상 효과**:
- 디스크 여유: 232 GB → **265 GB** (+33 GB)
- 사용률: 87% → **85%**

---

### 우선순위 2: 추가 정리 항목

#### 1. Quantized Models (선택)
```bash
du -sh quantized_models/
# 예상: ~5-6 GB

# PyTorch Static INT8 모델 (사용 안함)
# BitsAndBytes는 checkpoint에서 직접 로딩하므로 불필요
```

**판단 기준**:
- 보관: 테스트/검증용
- 삭제: BitsAndBytes만 사용할 경우

#### 2. 로그 파일
```bash
find . -name "*.log" -size +100M
find . -name "*_log_*.txt" -size +10M
```

#### 3. 오래된 체크포인트
```bash
# 7일 이상 된 checkpoint 중 best가 아닌 것
find runs -name "*.ckpt" -mtime +7 -not -name "*best*" -ls
```

---

## 📊 자동 정리 대상 분석

### 현재 vla 디렉토리 구조

**대용량 디렉토리** (예상):
1. `runs/` - 학습 체크포인트 (~100-200 GB)
2. `ROS_action/mobile_vla_dataset/` - 데이터셋
3. `.git/` - Git 저장소 (~5 GB)
4. `.git_corrupted_20251217/` - **33 GB 삭제 대상** 🎯

---

## ✅ 즉시 실행 가능한 안전한 정리

### 1. Git Corrupted 백업 삭제 (추천 ⭐⭐⭐)

```bash
cd /home/billy/25-1kp/vla

# 1. 백업 디렉토리 삭제
rm -rf .git_corrupted_20251217/
rm -rf .git.bfg-report/

# 2. 결과 확인
df -h /home
du -sh . 

# 예상 절감: 33 GB
```

**안전도**: ✅ 매우 안전
- 현재 Git 정상 작동
- GitHub에 모든 코드 백업됨
- 7일 경과한 백업

---

### 2. API Server 시작 (추천 ⭐⭐⭐)

```bash
cd /home/billy/25-1kp/vla

# API Key 설정 (기존 것 사용 또는 새로 생성)
export VLA_API_KEY="your-secret-key"

# background로 실행
nohup uvicorn Mobile_VLA.inference_server:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 1 \
  > api_server.log 2>&1 &

# 확인
curl http://localhost:8000/health
```

**예상 메모리 사용**: ~2 GB (BitsAndBytes INT8)

---

## 🎯 추천 실행 순서

### 단계 1: 디스크 정리 (5분)
```bash
cd /home/billy/25-1kp/vla
rm -rf .git_corrupted_20251217/
rm -rf .git.bfg-report/
# +33 GB 확보
```

### 단계 2: API Server 시작 (2분)
```bash
export VLA_API_KEY="your-key"
nohup uvicorn Mobile_VLA.inference_server:app \
  --host 0.0.0.0 --port 8000 > api_server.log 2>&1 &
```

### 단계 3: 확인 (1분)
```bash
# 디스크
df -h /home

# API
ps aux | grep uvicorn
curl http://localhost:8000/health
```

---

## 📋 요약

| 항목 | 현재 상태 | 조치 필요 |
|------|-----------|-----------|
| **API Server** | ❌ 미실행 | ✅ 시작 필요 |
| **디스크 여유** | 232 GB (87%) | ⚠️ 정리 권장 |
| **Git Corrupted** | 33 GB | 🗑️ **삭제 강력 추천** |
| **BFG Report** | 124 KB | 🗑️ 삭제 가능 |

**즉시 실행 추천**:
1. ✅ `.git_corrupted_20251217/` 삭제 (+33 GB)
2. ✅ API Server 시작 (BitsAndBytes INT8)

---

**작성 일시**: 2025-12-24 05:28 KST
