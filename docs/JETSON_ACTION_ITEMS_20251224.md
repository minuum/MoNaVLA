# Jetson 배포 - 액션 아이템 요약

**작성일시**: 2025-12-24 12:35 KST  
**우선순위**: 🔴🔴🔴 긴급  
**브랜치**: `inference-integration`

---

## 🚨 즉시 해결 필요

### **블로커 #1: Jetson 오프라인**

**현재 상태**:
```
❌ Jetson (linnaeus) 오프라인
   - Tailscale: offline (23분 전)
   - rsync 전송 실패
   - 체크포인트 전송 불가 (6.4 GB)
```

**해결 방법**:
1. **Jetson 전원 켜기**
2. **Tailscale 연결**:
   ```bash
   # Jetson에서
   sudo tailscale up
   ```
3. **Billy 서버에서 확인**:
   ```bash
   tailscale status | grep linnaeus
   # "active" 상태 확인
   ```
4. **체크포인트 재전송**:
   ```bash
   bash scripts/sync/push_checkpoint_to_jetson.sh \
     runs/mobile_vla_no_chunk_20251209/kosmos/mobile_vla_finetune/2025-12-17/mobile_vla_chunk5_20251217/epoch_epoch=06-val_loss=val_loss=0.067.ckpt
   ```

---

## ✅ Jetson 온라인 후 실행할 명령어

### **Step 1: Git 동기화** (1분)
```bash
cd ~/vla
git checkout inference-integration
git pull origin inference-integration
git submodule update --init --recursive
```

### **Step 2: Dependencies 설치** (5분)
```bash
pip install -r requirements-inference.txt
# 또는
./setup_jetson.sh
```

### **Step 3: Pretrained Model 다운로드** (10분)
```bash
cd ~/vla
huggingface-cli download microsoft/kosmos-2-patch14-224 \
  --local-dir .vlms/kosmos-2-patch14-224
```

### **Step 4: 체크포인트 확인** (전송 완료 후)
```bash
ls -lh ~/vla/ROS_action/last.ckpt
# Expected: 6.4 GB (6,863,842,304 bytes)
```

### **Step 5: API Server 테스트** (2분)
```bash
# Terminal 1: API Server 시작
cd ~/vla
python3 -m uvicorn Mobile_VLA.inference_server:app --host 0.0.0.0 --port 8000

# Terminal 2: Health Check
curl http://localhost:8000/health

# Terminal 3: 추론 테스트
python3 scripts/test_api_inference_complete.py
```

**예상 결과**:
- ✅ 첫 추론: ~600ms (모델 로딩 포함)
- ✅ 이후 추론: ~500ms
- ✅ GPU Memory: ~1.8 GB

---

## 📋 체크리스트

### **Phase 1: 모델 준비** (필수 - 오늘)
- [ ] Jetson 전원 켜기
- [ ] Tailscale 연결 확인
- [ ] 체크포인트 전송 (6.4 GB, ~20분)
- [ ] Git pull & submodule update
- [ ] Dependencies 설치
- [ ] Pretrained model 다운로드 (2.4 GB, ~10분)

### **Phase 2: 추론 테스트** (중요 - 오늘)
- [ ] API Server 시작
- [ ] Health check 성공
- [ ] 단일 추론 테스트 (~500ms)
- [ ] 18회 연속 테스트 (test_robot_driving_18steps.py)

### **Phase 3: ROS2 통합** (선택 - 내일)
- [ ] Camera service 확인
- [ ] VLA Inference Node 실행
- [ ] cmd_vel publish 검증

### **Phase 4: 실제 주행** (최종 - 내일)
- [ ] 정지 상태 추론 테스트
- [ ] 직진/회피 테스트
- [ ] 실제 시나리오 주행

---

## 📊 진행률

| Phase | 상태 | 완료율 | 예상 시간 |
|-------|------|--------|----------|
| 코드 작성 | ✅ 완료 | 100% | - |
| **Phase 1: 모델 준비** | ⚠️ **블로킹** | 0% | ~45분 |
| Phase 2: 추론 테스트 | ⏸️ 대기 | 0% | ~30분 |
| Phase 3: ROS2 통합 | ⏸️ 대기 | 0% | ~1시간 |
| Phase 4: 실제 주행 | ⏸️ 대기 | 0% | ~2시간 |

**총 예상 시간**: ~4시간 (Jetson 온라인 후)

---

## 🔗 참고 자료

### **핵심 문서**
1. **전체 브리핑**: [JETSON_DEPLOYMENT_BRIEFING_20251224.md](https://github.com/minuum/vla/blob/inference-integration/docs/JETSON_DEPLOYMENT_BRIEFING_20251224.md)
2. **배포 가이드**: [JETSON_FINAL_DEPLOYMENT_GUIDE_20251224.md](https://github.com/minuum/vla/blob/inference-integration/docs/JETSON_FINAL_DEPLOYMENT_GUIDE_20251224.md)
3. **주간 진행 보고**: [WEEKLY_PROGRESS_20251222-24.md](https://github.com/minuum/vla/blob/inference-integration/docs/WEEKLY_PROGRESS_20251222-24.md)

### **핵심 코드**
1. **API Server**: [Mobile_VLA/inference_server.py](https://github.com/minuum/vla/blob/inference-integration/Mobile_VLA/inference_server.py)
2. **ROS2 Node**: [vla_inference_node.py](https://github.com/minuum/vla/blob/inference-integration/ROS_action/src/mobile_vla_package/mobile_vla_package/vla_inference_node.py)
3. **전송 스크립트**: [push_checkpoint_to_jetson.sh](https://github.com/minuum/vla/blob/inference-integration/scripts/sync/push_checkpoint_to_jetson.sh)
4. **테스트 스크립트**: [test_api_inference_complete.py](https://github.com/minuum/vla/blob/inference-integration/scripts/test_api_inference_complete.py)

---

## 🎯 성공 기준

### **Today's Goal (오늘)**
- ✅ Jetson 온라인
- ✅ 체크포인트 전송 완료
- ✅ 모델 로딩 성공
- ✅ 단일 추론 < 1초

### **Tomorrow's Goal (내일)**
- ✅ 18회 연속 추론 100% 성공
- ✅ ROS2 통합 성공
- ✅ 실제 로봇 주행 테스트

---

**작성일**: 2025-12-24 12:35 KST  
**Status**: 🔴 **Jetson 오프라인 - 즉시 해결 필요**  
**Next**: Jetson 전원 켜기 → Tailscale 연결 → 체크포인트 전송
