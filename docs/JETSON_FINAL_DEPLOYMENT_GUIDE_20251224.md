# Jetson 배포 - 최종 실행 가이드

**일시**: 2025-12-24 11:52 KST  
**Status**: ✅ Checkpoint 전송 중, 코드 푸시 완료

---

## ✅ 완료된 작업

### Billy 서버
1. ✅ SSH 키 복사 완료 (`soda@linnaeus`)
2. ✅ Checkpoint 전송 중 (6.4 GB, ~20분 소요)
3. ✅ 코드 푸시 완료 (`inference-integration` 브랜치)
   - `Mobile_VLA/action_buffer.py`
   - `scripts/transfer_to_jetson.sh`
   - Documentation

---

## 🚀 Jetson에서 실행할 명령어

### 1. Git 업데이트
```bash
# Jetson(soda@linnaeus)에서 실행
cd ~/vla

# 최신 코드 pull
git checkout inference-integration
git pull origin inference-integration

# Submodule 업데이트 (중요!)
git submodule update --init --recursive
```

**확인**:
```bash
# Mobile VLA Trainer 확인
ls RoboVLMs_upstream/robovlms/train/mobile_vla_trainer.py

# Inference Server 확인
ls Mobile_VLA/inference_server.py

# Action Buffer 확인
ls Mobile_VLA/action_buffer.py
```

---

### 2. Dependencies 설치
```bash
# requirements 확인
cat requirements-inference.txt

# 설치
pip install -r requirements-inference.txt

# 또는 setup script 사용
./setup_jetson.sh
```

**필수 패키지**:
- torch (Jetson pre-installed)
- transformers
- bitsandbytes (ARM64)
- accelerate
- fastapi
- uvicorn

---

### 3. Pretrained Model 다운로드

**Option A: Hugging Face에서 다운로드** (권장)
```bash
cd ~/vla
mkdir -p .vlms

# Hugging Face CLI 사용
pip install huggingface_hub
huggingface-cli download microsoft/kosmos-2-patch14-224 \
  --local-dir .vlms/kosmos-2-patch14-224
```

**Option B: Billy 서버에서 복사하기**
```bash
# Billy 서버에서 실행
cd /home/billy/25-1kp/vla
tar -czf kosmos2_pretrained.tar.gz .vlms/kosmos-2-patch14-224/
rsync -avP kosmos2_pretrained.tar.gz soda@linnaeus:/home/soda/

# Jetson에서 실행
cd ~/vla
tar -xzf ~/kosmos2_pretrained.tar.gz
```

---

### 4. Checkpoint 확인

**전송 완료 후 확인**:
```bash
ls -lh ~/vla/runs/mobile_vla_no_chunk_20251209/kosmos/mobile_vla_finetune/2025-12-17/mobile_vla_chunk5_20251217/epoch_epoch=06-val_loss=val_loss=0.067.ckpt
```

**Expected**: 6.4 GB

---

### 5. API Key 설정
```bash
cd ~/vla

# API Key 생성
python3 -c "import secrets; print(secrets.token_urlsafe(32))" > api_key.txt

# secrets.sh 생성
echo "export VLA_API_KEY=\"$(cat api_key.txt)\"" > secrets.sh
chmod 600 secrets.sh

# 적용
source secrets.sh
```

---

### 6. API Server 시작

**Foreground (테스트용)**:
```bash
cd ~/vla
source secrets.sh

python3 -m uvicorn Mobile_VLA.inference_server:app \
  --host 0.0.0.0 --port 8000
```

**Background (Production)**:
```bash
cd ~/vla
source secrets.sh
mkdir -p logs

nohup python3 -m uvicorn Mobile_VLA.inference_server:app \
  --host 0.0.0.0 --port 8000 > logs/api_server.log 2>&1 &

echo "Server PID: $!"
```

---

### 7. 테스트

**Health Check**:
```bash
curl http://localhost:8000/health
```

**Expected**:
```json
{
    "status": "healthy",
    "model_loaded": false,
    "device": "cuda",
    "gpu_memory": {
        "allocated_gb": 0.0,
        "device_name": "NVIDIA ..."
    }
}
```

**API Test**:
```bash
cd ~/vla
python3 scripts/test_api_inference_complete.py
```

**Expected**:
- ✅ 첫 요청: ~600ms (모델 로딩 포함)
- ✅ 이후 요청: ~500ms
- ✅ GPU Memory: ~1.8 GB

**Robot Simulation Test**:
```bash
python3 scripts/test_robot_driving_18steps.py
```

**Expected**:
- ✅ 18/18 성공
- ✅ Total: ~10-11초
- ✅ No memory leaks

---

## 🔍 문제 해결

### 1. Submodule 비어있음
```bash
git submodule update --init --recursive
```

### 2. BitsAndBytes 설치 실패
```bash
# ARM64 버전 빌드
pip install bitsandbytes==0.43.1 --no-binary bitsandbytes
```

### 3. Checkpoint not found
```bash
# Billy 서버에서 전송 상태 확인
tail -f logs/rsync_to_jetson_*.log

# Jetson에서 확인
find ~/vla/runs -name "*.ckpt" -type f
```

### 4. CUDA out of memory
```bash
# Swap 늘리기
sudo systemctl disable nvzramconfig
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

## 📊 예상 성능 (Jetson Orin)

| Metric | Expected |
|--------|----------|
| **GPU Memory** | 1.8-2.0 GB |
| **Inference** | 500-600 ms |
| **Rate** | 1.7-2.0 Hz |
| **18 calls** | 10-11 sec |

**Billy 서버 대비**:
- Latency: 495ms → 550ms (+10%)
- Memory: 1.80GB → 1.85GB (동일)

---

## 🎯 최종 체크리스트

### Jetson 준비
- [ ] Git pull & submodule init
- [ ] Dependencies 설치
- [ ] Pretrained model 다운로드
- [ ] Checkpoint 전송 완료
- [ ] API Key 생성

### 실행 & 테스트
- [ ] API Server 시작
- [ ] Health check 성공
- [ ] Single inference 테스트
- [ ] 18 consecutive 테스트

### ROS2 통합 (다음 단계)
- [ ] ROS2 node 작성
- [ ] Camera topic 연결
- [ ] cmd_vel publish
- [ ] 실제 주행 테스트

---

## 🚨 현재 전송 상태

**Billy 서버에서 확인**:
```bash
# 전송 로그 확인
tail -f logs/rsync_to_jetson_*.log

# 프로세스 확인
ps aux | grep rsync
```

**예상 완료 시간**: Billy 서버 시작 후 약 20분

---

**다음 단계**:
1. Checkpoint 전송 완료 대기 (~20분)
2. Jetson에서 위 명령어 순서대로 실행
3. API Server 테스트
4. ROS2 통합

**Status**: 🟡 Checkpoint 전송 중 → 🟢 Ready for Jetson setup
