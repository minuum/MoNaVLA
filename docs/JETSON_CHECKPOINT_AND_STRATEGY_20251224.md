# Jetson 배포 가이드 - 체크포인트 & 브랜치 전략

**일시**: 2025-12-24 09:04 KST

---

## 1️⃣ 체크포인트 선택

### 추천: Chunk5 Best (Epoch 6)

**파일 정보**:
```
이름: epoch_epoch=06-val_loss=val_loss=0.067.ckpt
경로: runs/mobile_vla_no_chunk_20251209/kosmos/mobile_vla_finetune/2025-12-17/mobile_vla_chunk5_20251217/
크기: 6.4 GB
Val Loss: 0.067 (가장 낮음)
```

**선택 이유**:
1. ✅ **가장 낮은 validation loss** (0.067)
2. ✅ **완전히 테스트됨** (18회 연속 성공)
3. ✅ **성능 검증됨** (495ms, 1.8GB)
4. ✅ **안정적** (100% 신뢰성)

**전송 방법**:
```bash
# Billy 서버에서
cd /home/billy/25-1kp/vla

# 압축 (선택)
tar -czf chunk5_best.tar.gz \
  runs/mobile_vla_no_chunk_20251209/kosmos/mobile_vla_finetune/2025-12-17/mobile_vla_chunk5_20251217/epoch_epoch=06-val_loss=val_loss=0.067.ckpt \
  Mobile_VLA/configs/mobile_vla_chunk5_20251217.json

# Jetson으로 전송
scp chunk5_best.tar.gz jetson@jetson-ip:/home/jetson/

# Jetson에서
cd /home/jetson/vla
tar -xzf ~/chunk5_best.tar.gz
```

---

## 2️⃣ 브랜치 전략

### 추천: 같은 브랜치 사용 ⭐⭐⭐

**브랜치**: `inference-integration` (동일)

### 장점
1. ✅ **코드 동기화 쉬움**
   - Billy 서버: `git push`
   - Jetson: `git pull`
   - 자동 동기화

2. ✅ **패치 적용 자동**
   - Bug fix → 즉시 반영
   - 성능 개선 → 자동 업데이트

3. ✅ **관리 간편**
   - 단일 브랜치 관리
   - 코드 중복 없음

4. ✅ **테스트 일관성**
   - Billy에서 테스트 → Jetson에서 동일

### 단점 (무시 가능)
- Jetson 전용 설정 변경 시 conflict 가능
  → 해결: Environment variables 사용

---

### 대안: 다른 브랜치 (비추천)

**브랜치**: `jetson-deployment` (별도)

### 장점
- Jetson 전용 설정 자유

### 단점
1. ❌ **코드 중복**
2. ❌ **동기화 어려움** (manual merge)
3. ❌ **관리 복잡**
4. ❌ **버그 수정 2배 작업**

---

## 3️⃣ 추가로 신경써야 할 부분

### A. Pretrained Model (.vlms/)

**문제**: Kosmos-2 pretrained model 필요

**확인**:
```bash
ls -lh .vlms/kosmos-2-patch14-224/
```

**해결**:

#### Option 1: Hugging Face에서 다운로드 (Jetson에서)
```bash
# Jetson에서 실행
cd /home/jetson/vla
mkdir -p .vlms

# Hugging Face CLI 사용
pip install huggingface_hub
huggingface-cli download microsoft/kosmos-2-patch14-224 \
  --local-dir .vlms/kosmos-2-patch14-224
```

#### Option 2: Billy 서버에서 복사 (추천)
```bash
# Billy 서버에서
tar -czf kosmos2_pretrained.tar.gz .vlms/kosmos-2-patch14-224/

# Jetson으로 전송
scp kosmos2_pretrained.tar.gz jetson@jetson-ip:/home/jetson/

# Jetson에서
cd /home/jetson/vla
tar -xzf ~/kosmos2_pretrained.tar.gz
```

**크기**: ~1-2 GB

---

### B. Git Submodule (RoboVLMs_upstream)

**문제**: Submodule이 자동으로 clone 안됨

**해결**:
```bash
# Jetson에서
cd /home/jetson/vla
git submodule update --init --recursive
```

**확인**:
```bash
ls RoboVLMs_upstream/robovlms/
```

---

### C. API Key 설정

**문제**: secrets.sh가 .gitignore됨

**해결**:

#### Option 1: 새로 생성 (Jetson에서)
```bash
# Jetson에서
cd /home/jetson/vla
python3 -c "import secrets; print(secrets.token_urlsafe(32))" > api_key.txt
echo "export VLA_API_KEY=\"$(cat api_key.txt)\"" > secrets.sh
chmod 600 secrets.sh
```

#### Option 2: Billy와 동일한 키 사용
```bash
# Billy의 secrets.sh 복사
scp secrets.sh jetson@jetson-ip:/home/jetson/vla/
```

---

### D. Python Dependencies

**주의**: BitsAndBytes ARM64 버전

**확인**:
```bash
# Jetson에서
python3 -c "import bitsandbytes; print(bitsandbytes.__version__)"
```

**문제 시**:
```bash
# ARM64 빌드
pip install bitsandbytes==0.43.1 --no-binary bitsandbytes
```

---

### E. CUDA/cuDNN 버전

**Jetson 확인**:
```bash
nvcc --version
python3 -c "import torch; print(torch.__version__); print(torch.version.cuda)"
```

**필요 버전**:
- CUDA: 11.8+ (Jetson은 보통 11.4+)
- PyTorch: 2.0+

---

## 4️⃣ Jetson 배포 체크리스트

### Phase 1: 준비 (Billy 서버)
- [ ] Checkpoint 압축
  ```bash
  tar -czf checkpoint.tar.gz \
    runs/.../epoch_epoch=06-val_loss=val_loss=0.067.ckpt \
    Mobile_VLA/configs/mobile_vla_chunk5_20251217.json
  ```

- [ ] Pretrained model 압축
  ```bash
  tar -czf kosmos2.tar.gz .vlms/kosmos-2-patch14-224/
  ```

- [ ] Jetson으로 전송
  ```bash
  scp checkpoint.tar.gz kosmos2.tar.gz jetson@jetson-ip:~/
  ```

---

### Phase 2: 설치 (Jetson)
- [ ] Clone repository
  ```bash
  git clone git@github.com-vla:minuum/vla.git
  cd vla
  git checkout inference-integration
  ```

- [ ] Submodule 초기화
  ```bash
  git submodule update --init --recursive
  ```

- [ ] 압축 해제
  ```bash
  tar -xzf ~/checkpoint.tar.gz
  tar -xzf ~/kosmos2.tar.gz
  ```

- [ ] Dependencies 설치
  ```bash
  ./setup_jetson.sh
  # 또는
  pip install -r requirements-inference.txt
  ```

- [ ] API Key 설정
  ```bash
  python3 -c "import secrets; print(secrets.token_urlsafe(32))" > api_key.txt
  echo "export VLA_API_KEY=\"$(cat api_key.txt)\"" > secrets.sh
  ```

---

### Phase 3: 테스트 (Jetson)
- [ ] 서버 시작
  ```bash
  source secrets.sh
  python3 -m uvicorn Mobile_VLA.inference_server:app --host 0.0.0.0 --port 8000
  ```

- [ ] Health check
  ```bash
  curl http://localhost:8000/health
  ```

- [ ] API 테스트
  ```bash
  python3 scripts/test_api_inference_complete.py
  ```

- [ ] 18회 연속 테스트
  ```bash
  python3 scripts/test_robot_driving_18steps.py
  ```

---

### Phase 4: ROS2 통합 (Jetson)
- [ ] ROS2 노드 작성
- [ ] Camera topic 연결
- [ ] cmd_vel publish
- [ ] 실제 주행 테스트

---

## 5️⃣ 파일 크기 요약

| 파일 | 크기 | 필수 |
|------|------|------|
| **Checkpoint** | 6.4 GB | ✅ 필수 |
| **Kosmos-2 Pretrained** | 1-2 GB | ✅ 필수 |
| **Code (Git)** | ~100 MB | ✅ 필수 |
| Config | ~10 KB | ✅ 포함 |

**Total**: ~8 GB

**Jetson 16GB 여유 확인**:
```bash
df -h /
```

---

## 6️⃣ 전송 스크립트 (자동화)

### Billy → Jetson 전송

```bash
#!/bin/bash
# sync_to_jetson.sh

JETSON_USER="jetson"
JETSON_IP="jetson-ip"
VLA_DIR="/home/billy/25-1kp/vla"

cd $VLA_DIR

# 1. Checkpoint 압축
echo "1. Compressing checkpoint..."
tar -czf /tmp/checkpoint.tar.gz \
  runs/mobile_vla_no_chunk_20251209/kosmos/mobile_vla_finetune/2025-12-17/mobile_vla_chunk5_20251217/epoch_epoch=06-val_loss=val_loss=0.067.ckpt \
  Mobile_VLA/configs/mobile_vla_chunk5_20251217.json

# 2. Pretrained model 압축
echo "2. Compressing Kosmos-2..."
tar -czf /tmp/kosmos2.tar.gz .vlms/kosmos-2-patch14-224/

# 3. Jetson으로 전송
echo "3. Transferring to Jetson..."
scp /tmp/checkpoint.tar.gz /tmp/kosmos2.tar.gz \
  $JETSON_USER@$JETSON_IP:/home/$JETSON_USER/

echo "4. Cleaning up..."
rm /tmp/checkpoint.tar.gz /tmp/kosmos2.tar.gz

echo "✅ Transfer complete!"
echo ""
echo "Next steps on Jetson:"
echo "1. cd ~/vla"
echo "2. tar -xzf ~/checkpoint.tar.gz"
echo "3. tar -xzf ~/kosmos2.tar.gz"
```

---

## 7️⃣ 최종 권장사항

### 브랜치 전략
✅ **같은 브랜치 사용** (`inference-integration`)

**이유**:
1. 코드 동기화 자동
2. 버그 수정 즉시 반영
3. 관리 간편
4. Jetson 전용 설정은 environment variables로

**Workflow**:
```
Billy (개발) → git push → GitHub
              ↓
Jetson (배포) → git pull → 자동 업데이트
```

### 필수 전송 파일
1. ✅ **Checkpoint** (6.4 GB) - 수동
2. ✅ **Kosmos-2** (1-2 GB) - 수동
3. ✅ **Code** (Git) - 자동
4. ✅ **API Key** - 수동 생성

### 선택 사항
- secrets.sh: Jetson에서 새로 생성 권장
- Dataset: inference에는 불필요

---

**요약**:
- **Checkpoint**: Chunk5 Best (6.4GB)
- **브랜치**: 같은 브랜치 (`inference-integration`)
- **주의사항**: Pretrained model, Submodule, API Key

**소요 시간**: 30분 - 1시간 (전송 + 설치)
