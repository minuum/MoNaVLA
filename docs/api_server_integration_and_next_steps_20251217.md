# API 서버 통합 및 다음 단계 플랜
**날짜**: 2025-12-17 22:30  
**상태**: Jetson 기준 통합 완료 ✅

---

## ✅ 완료된 작업

### 1. API 서버 통합
- ✅ **Jetson의 올바른 Action Space 적용**: 2 DOF (linear_x, angular_z)
- ✅ **실제 모델 로딩 및 추론 로직 구현**
- ✅ **3개 최신 모델 지원**:
  - Chunk5 Epoch 6 (val_loss=0.067) - 기본 모델
  - Chunk10 Epoch 8 (val_loss=0.312)
  - No Chunk Epoch 4 (val_loss=0.001)
- ✅ **첫 번째 액션만 실행** (Reactive control, 교수님 합의사항)
- ✅ **중복 파일 제거**: Mobile_VLA/inference_api_server.py 삭제
- ✅ **모델 정보 조회 엔드포인트** 추가 (/model/info)
- ✅ **환경 변수로 모델 선택** 가능 (VLA_MODEL_NAME)

### 2. Git 커밋
```
5b7a52ae chore: Remove duplicate API server file
a04b70f9 feat: Complete API server with Jetson's correct Action Space
```

---

## 🎯 다음 단계 플랜

### Phase 1: API 서버 테스트 및 배포 (우선순위: 높음)

#### 1.1 로컬 테스트
```bash
# 1. API 서버 시작 (기본 모델: Chunk5 Epoch 6)
cd /home/billy/25-1kp/vla
python3 api_server.py

# 2. 다른 터미널에서 테스트
python3 scripts/test_inference_api.py

# 3. 다른 모델 테스트
VLA_MODEL_NAME=chunk10_epoch8 python3 api_server.py
VLA_MODEL_NAME=no_chunk_epoch4 python3 api_server.py
```

**예상 시간**: 30분  
**목표**: 3개 모델 모두 정상 동작 확인

---

#### 1.2 모델 성능 비교
```bash
# Chunk5, Chunk10, No Chunk 모델의 실제 추론 latency 측정
python3 scripts/test_models_real_inference.py
```

**비교 항목**:
- Inference latency (목표: \<100ms)
- Action 정확도
- Chunk size에 따른 차이

**예상 시간**: 1시간  
**목표**: 최적 모델 선정

---

#### 1.3 Jetson 연동 테스트
```bash
# Billy 서버에서 API 서버 시작
python3 api_server.py --host 0.0.0.0 --port 8000

# Jetson에서 ROS2 클라이언트 테스트
# (Tailscale로 연결)
ros2 run mobile_vla_package api_client_node
```

**예상 시간**: 1시간  
**목표**: Jetson-Billy 통신 성공

---

### Phase 2: 문서 정리 (우선순위: 중간)

#### 2.1 INFERENCE_API_GUIDE.md 업데이트
- [ ] linear_y → angular_z로 수정 (Line 83-86, 129)
- [ ] Chunk5/Chunk10 모델 정보 추가
- [ ] 환경 변수 사용법 추가

#### 2.2 통합 사용 가이드 작성 (선택사항)
**파일**: `docs/MOBILE_VLA_INFERENCE_COMPLETE_GUIDE.md`

구조:
```markdown
# Part 1: 시스템 개요
- Jetson-Billy 멀티 서버 구조
- Action Space 설명 (2 DOF)

# Part 2: API 서버 사용법
- 서버 시작
- 모델 선택
- Endpoint 사용법

# Part 3: 모델 정보
- Chunk5 vs Chunk10 vs No Chunk
- 성능 비교

# Part 4: Jetson 연동
- ROS2 클라이언트 설정
- 실시간 추론
```

**예상 시간**: 2시간

---

### Phase 3: 로봇 실제 테스트 (우선순위: 최고)

#### 3.1 시뮬레이션 테스트
```bash
# Gazebo 시뮬레이션에서 테스트
# 1. 장애물 회피
# 2. 목표물 도달
```

**예상 시간**: 2시간  
**목표**: 3개 모델 시뮬레이션 비교

---

#### 3.2 실제 로봇 테스트
**시나리오**:
1. **Scenario 1**: 왼쪽 음료수 병 도달
2. **Scenario 2**: 오른쪽 상자 도달
3. **Scenario 3**: 장애물 회피 후 목표 도달

**비교 항목**:
- Success rate
- Trajectory smoothness
- Reaction time (Chunk=1,5,10 비교)

**예상 시간**: 4시간 (시나리오당 1시간)  
**목표**: Best model 확정

---

### Phase 4: 교수님 미팅 준비 (우선순위: 최고)

#### 4.1 실험 결과 정리
**파일**: `docs/FINAL_ROBOT_TEST_REPORT_20251217.md`

내용:
- 3개 모델 성능 비교표
- 실제 로봇 테스트 결과
- 성공률, latency, trajectory 분석
- 결론 및 권장 모델

**예상 시간**: 2시간

---

#### 4.2 데모 영상 준비
- [ ] Chunk5 Epoch 6 모델 성공 시나리오
- [ ] 장애물 회피 demonstration
- [ ] 3개 모델 비교 영상

**예상 시간**: 2시간

---

## 📊 일정 계획

### D-Day까지 우선순위

| Phase | 작업 | 예상 시간 | 우선순위 |
|-------|------|----------|---------|
| 1.1 | 로컬 테스트 | 30분 | 🔴 즉시 |
| 1.3 | Jetson 연동 | 1시간 | 🔴 즉시 |
| 3.2 | 실제 로봇 테스트 | 4시간 | 🔴 최고 |
| 4.1 | 실험 결과 정리 | 2시간 | 🔴 최고 |
| 4.2 | 데모 영상 | 2시간 | 🟡 높음 |
| 1.2 | 성능 비교 | 1시간 | 🟡 높음 |
| 2.1 | 문서 업데이트 | 1시간 | 🟢 중간 |

**총 소요 시간**: 11.5시간

---

## 🔧 환경 변수 설정

### Billy 서버 (API 서버)
```bash
# .bashrc 또는 .zshrc에 추가
export VLA_API_KEY="your_secret_api_key_here"
export VLA_MODEL_NAME="chunk5_epoch6"  # 또는 chunk10_epoch8, no_chunk_epoch4
```

### Jetson (ROS2 클라이언트)
```bash
# Tailscale IP 확인
tailscale ip

# 환경 변수 설정
export BILLY_API_URL="http://BILLY_TAILSCALE_IP:8000"
export API_KEY="your_secret_api_key_here"
```

---

## 📝 API 서버 주요 엔드포인트

### 1. Health Check (인증 불필요)
```bash
curl http://localhost:8000/health
```

### 2. 모델 정보 조회 (API Key 필요)
```bash
curl -H "X-API-Key: YOUR_API_KEY" \
     http://localhost:8000/model/info
```

### 3. 추론 (API Key 필요)
```bash
curl -X POST http://localhost:8000/predict \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "image": "base64_encoded_image",
    "instruction": "Navigate to the left bottle"
  }'
```

**Response**:
```json
{
  "action": [1.234, -0.567],  // [linear_x, angular_z]
  "latency_ms": 87.5,
  "model_name": "chunk5_epoch6",
  "chunk_size": 5
}
```

---

## 🎓 교수님 합의사항 준수 확인

- [x] ✅ **Action Chunking**: Chunk=1,5,10 모델 지원, 첫 번째 액션만 실행
- [x] ✅ **Output DOF**: 2 DOF (linear_x, angular_z)
- [x] ✅ **Data**: L+R 500 episodes
- [x] ✅ **Strategy**: Baseline (Simple), Language instruction
- [x] ✅ **Model**: Kosmos-2 (Frozen) + Fine-tuning
- [ ] ⏳ **추론 주기**: Jetson 클라이언트에서 100-200ms 설정 필요
- [ ] ⏳ **실제 로봇 테스트**: 진행 예정

---

## 🚀 즉시 시작 가능한 작업

### 1. API 서버 테스트 (지금 바로)
```bash
cd /home/billy/25-1kp/vla
python3 api_server.py
```

### 2. 테스트 스크립트 실행 (별도 터미널)
```bash
cd /home/billy/25-1kp/vla
python3 scripts/test_inference_api.py
```

### 3. 모델 성능 비교 (옵션)
```bash
python3 scripts/test_models_real_inference.py
```

---

**다음 우선 작업**: API 서버 테스트 및 Jetson 연동 확인! 🚀
