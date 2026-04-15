# 교수님 의문점 해결 TODO (우선순위별)

**최근 미팅**: 2025-12-05 (목)  
**다음 미팅**: 2025-12-11 (수) 16:00  
**업데이트**: 2025-12-05 20:00

---

## 🆕 최신 미팅 결과 (2025-12-05)

### **새로운 핵심 질문: Frozen vs LoRA**
> VLM을 Freeze 하는 것 vs LoRA로 Fine-tuning 하는 것의 차이
> Context vector (의미 벡터)가 어떻게 다른가?
> Latent space는 어떻게 다른가?

**교수님 의견**: 방법 2 (Frozen)가 의미 있을 것 같다
- 데이터 효율적
- 안정적 학습
- 일반화 능력

**실험 계획**:
1. 방법 1: VLM LoRA + Action Head (데이터 1,000~3,000 필요)
2. 방법 2: VLM Frozen + Action Head (데이터 500~1,000 가능)
3. Context vector 유사도 비교 (Cosine, Euclidean, Correlation)
4. Latent space 매칭 분석

**상세**: `docs/PROFESSOR_MEETING_20251205.md`

---

## 🎯 교수님 핵심 의문점 (원본)

### **Q1: 7DOF→2DOF 변환 가능한가?**
> VLM에서 나오는 context는 clear, 하지만 velocity가 **어떻게** 변경될지 알려줘야 함
> RoboVLMs 7DOF와 Mobile 2DOF를 어떻게 매칭?

### **Q2: Mobile 연구 실현 가능한가?**
> Serbot-omniwheel 같은 연구 없음, 의미 있으려면 몇만 장 필요

### **Q3: 데이터 증강 (500→5,000)?**
> Simulation으로 증강, VLM 파인튜닝

### **Q4: 추론 시나리오**
> - 0.4초마다 2DOF velocity
> - Action chunk: 10개 미리 예측
> - 거리 측정
> - 제대로 된 x, y 값 검증

### **Q5: 데이터 수집 전략**
> - Left vs Right vs Left+Right
> - 250 + 250 같은 guide
> - 동일 trajectory

---

## ✅ 이미 완료된 것

1. **7DOF→2DOF 분석** ✅
   - 파일: `analyze_7dof_to_2dof.py`
   - 결과: 5가지 불가능 이유 정리
   - 결론: 직접 매칭 불가, Action head 교체만 가능

2. **데이터 균형** ✅
   - 250 left + 250 right = 500 episodes
   - Case 3 학습 진행 중

3. **문서화** ✅
   - 7DOF→2DOF: `docs/7dof_to_2dof_conversion/`
   - Mobile vs Manipulator: `docs/Mobile_vs_Manipulator_Research/`
   - 데이터 증강: `docs/Mobile-VLA/DATA_AUGMENTATION_STRATEGY.md`
   - 추론 시나리오: `docs/Inference_Scenario/INFERENCE_DESIGN.md`

---

## 🔥 우선순위별 실행 계획

### **Priority 0: Frozen vs LoRA 비교** 🔥🔥🔥🔥 (NEW!)
**미팅 결과 (2025-12-05)**: 수요일(12/11) 발표 필요

**현재 상태**:
- ✅ Case 3 (Frozen) 학습 완료
- ⬜ Case 4 (LoRA) 학습 준비 중
- ⬜ Context vector 비교 스크립트 작성 완료
- ⬜ 논문 사례 조사 필요

**즉시 실행**:
```bash
# 1. Frozen baseline 추출
python3 scripts/compare_frozen_vs_lora.py
→ Output: context_frozen_baseline.npy

# 2. 논문 사례 조사
- RT-2 (Frozen VLM)
- OpenVLA (Fine-tuning)
- RoboFlamingo (Frozen)
- PaLM-E (Fine-tuning)

# 3. 데이터 추가 수집 고려 (Case 4용)
→ 현재 500 → 목표 1,000 episodes
```

**타임라인**:
- Day 1 (목, 12/5): ✅ 계획 수립, ⬜ Baseline 추출
- Day 2 (금, 12/6): ⬜ 논문 조사, ⬜ 시각화
- Day 3-4 (토-일): ⬜ 데이터 수집 (선택)
- Day 5-6 (월-화): ⬜ Case 4 학습, ⬜ 비교 분석
- Day 7 (수, 12/11): ⬜ 미팅 발표

**예상 결과**:
- Context similarity: > 0.8 (유사할 것)
- Latent difference: > 0.3 (다를 것)
- Performance: 비슷할 것

---

### **Priority 1: Context Vector 검증** 🔥🔥🔥
**질문**: VLM context가 정말 clear한가?

**현재 상태** (2025-12-04 업데이트):
- ✅ **Non-GPU 준비 완료**
  - ✅ Dataset 분석 완료 (500 episodes, 완벽한 균형)
  - ✅ Checkpoint 구조 분석 완료
  - ✅ Sampling 전략 수립 완료
  - ✅ 비교 메트릭 스크립트 작성 완료
  - ✅ 문서화 완료
- ⏳ **GPU 작업 대기**
  - Kosmos-2 context vector 추출
  - RoboVLMs context vector 추출
  - 통계 비교 및 시각화

**완료된 작업**:
```bash
# 1. Dataset Statistics
docs/RoboVLMs_validation/analyze_dataset_stats.py
→ Output: dataset_statistics.json
→ 500 episodes (250 left + 250 right, 18 frames each)

# 2. Checkpoint Structure Analysis  
docs/RoboVLMs_validation/verify_checkpoint_structure.py
→ Output: checkpoint_structure_analysis.json
→ Kosmos-2: 3.69B params, Action Head: 12.7M params

# 3. Comparison Metrics (준비됨)
docs/RoboVLMs_validation/compare_vectors_metrics.py
→ Cosine similarity, Wasserstein distance 등

# 4. 문서화
docs/RoboVLMs_validation/CHECKPOINT_STRUCTURE.md
docs/RoboVLMs_validation/SAMPLING_PLAN.md
docs/RoboVLMs_validation/NON_GPU_TASKS_COMPLETE.md
```

**주요 발견**:
1. **Dataset**: 
   - 완벽한 균형 (250 left + 250 right)
   - 일관된 길이 (18 frames)
   - 총 9,000 frames, 12.5 GB
   
2. **Checkpoint**:
   - Kosmos-2: PyTorch Lightning 형식, 6.83 GB
   - RoboVLMs: 중첩 dictionary 형식, 6.80 GB
   - Action Head: 동일한 LSTM decoder (2048D → 2D)
   
3. **Sampling Plan**:
   - 100 episodes (50 left + 50 right)
   - Episode당 5 frames (0%, 25%, 50%, 75%, 100%)
   - 총 500 context vectors 추출 예정

**GPU 작업 준비 완료**:
```bash
# 다음 GPU 세션에서 실행
# 1. Context vector 추출 (Kosmos-2)
python3 docs/RoboVLMs_validation/sampling_test.py \
  --model kosmos2 \
  --output context_vectors_kosmos2.npy

# 2. Context vector 추출 (RoboVLMs)  
python3 docs/RoboVLMs_validation/sampling_test.py \
  --model robovlms \
  --output context_vectors_robovlms.npy

# 3. 비교 분석
python3 docs/RoboVLMs_validation/compare_vectors_metrics.py \
  --kosmos context_vectors_kosmos2.npy \
  --robovlms context_vectors_robovlms.npy
```

**예상 결과**:
- Context vector shape: (500, 2048)
- Kosmos-2: mean≈0, std≈1 (일반 vision-language pretrain)
- RoboVLMs: mean≈0, std≈1 (robot manipulation pretrain)
- 차이점: Feature activation 패턴, 특정 dimension의 중요도

**이슈**:
⚠️ RoboVLMs pretrained checkpoint 미다운로드
- 경로: `checkpoints/RoboVLMs/checkpoints/kosmos_ph_oxe-pretrain.pt`
- 현재: Lock 파일만 존재
- 해결: HuggingFace에서 재다운로드 필요


---

### **Priority 2: Velocity 출력 검증** 🔥🔥
**질문**: 제대로 된 x, y 값을 뿌려주는가?

**현재 상태**:
- ✅ `verify_velocity_output.py` 작성됨
- ⚠️ H5 파일 이슈 있음 (일부 손상)

**해결**:
```bash
# 정상 H5 파일 찾기
ls -lh ROS_action/mobile_vla_dataset/*.h5 | head -5

# Velocity 검증 (정상 파일로)
python3 verify_velocity_output.py \
  --checkpoint "...epoch_09-val_loss=0.013.ckpt" \
  --samples 10
```

**검증 항목**:
- Predicted vs Ground Truth
- RMSE < 0.12
- 출력 범위 [-1, 1]
- 합리성

---

### **Priority 3: Case 3 결과 분석** 🔥
**질문**: Left+Right 균형 데이터의 효과?

**현재 상태**:
- ⏳ Epoch 2 완료 (Val Loss 0.359)
- ⏳ 학습 진행 중 (~90% 완료)

**완료 후 분석**:
```bash
# 모니터링
./monitor_case3.sh

# 완료 후 비교
Case 1 (left only 250): Loss 0.013
Case 3 (left+right 500): Loss ???

→ 균형 데이터 효과 확인
```

---

## ⏳ 단기 (오늘 안)

### **Priority 4: Latency 측정** (수정 필요)
**질문**: 0.4초 간격 추론 가능한가?

**현재 상태**:
- ⚠️ `test_inference_latency.py` LSTM shape 오류
- 수정 필요

**해결**:
1. LSTM hidden state 수정
2. 재실행
3. Total < 200ms 확인

---

### **Priority 5: 거리 측정 구현**
**질문**: 초기 거리를 어떻게 잴까?

**방법**:
```python
# Option 1: YOLO + Depth
depth = get_depth_from_stereo()
distance = calculate_distance(bbox, depth)

# Option 2: Fixed assumption
initial_distance = 1.0  # 1m로 가정

# Option 3: Manual input
distance = input("거리 입력 (m): ")
```

**구현**:
- ROS 노드에 추가
- 추론 시작 시 측정

---

## ⏸️ 장기 (1주+)

### **Priority 6: Simulation 증강**
- Gazebo/PyBullet 환경 구축
- 5,000 episodes 생성
- 예상: 2주

### **Priority 7: VLM 파인튜닝**
- 5,000+ episodes 확보 후
- Top layers만 파인튜닝
- 예상: 3일

---

## 📊 즉시 실행 순서

### **1단계: 다운로드 확인** (지금)
```bash
ls -lh checkpoints/RoboVLMs/*.pt
```

### **2단계: Context Vector 비교** (다운 완료 후)
```bash
python3 compare_context_vectors.py
```

### **3단계: Velocity 검증** (지금)
```bash
# 정상 H5 찾기
find ROS_action/mobile_vla_dataset -name "*.h5" -size +25M | head -5

# 검증 실행
python3 verify_velocity_output.py --samples 5
```

### **4단계: Case 3 완료 대기** (~10분)
```bash
./monitor_case3.sh
```

---

## 💡 해결 가능 여부

| 의문점 | 해결 가능 | 시간 | 방법 |
| :--- | :---: | :---: | :--- |
| **Context clear?** | ✅ | 즉시 | `compare_context_vectors.py` |
| **x,y 값 검증?** | ✅ | 즉시 | `verify_velocity_output.py` |
| **7DOF→2DOF?** | ✅ | 완료 | 분석 완료 (매칭 불가) |
| **Left+Right 효과?** | ✅ | 10분 | Case 3 완료 대기 |
| **0.4초 추론?** | ✅ | 1시간 | Latency 스크립트 수정 |
| **거리 측정?** | ✅ | 2시간 | ROS 노드 구현 |
| **Sim 증강?** | ⏸️ | 2주+ | 장기 과제 |

---

*지금 바로: Context vector 비교 & Velocity 검증 실행!*
