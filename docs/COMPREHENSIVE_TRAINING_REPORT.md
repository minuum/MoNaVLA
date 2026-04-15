# Mobile-VLA 학습 전체 정리 및 이슈 분석 (1차 완료)

**작성일**: 2025-12-04 09:25
**목적**: 모든 학습 케이스, 발생 이슈, 데이터 특성 종합 정리

---

## 🎯 **학습 케이스 요약표** (개선)

| Case# | 날짜 | Model | VLM Backbone | VLM Freeze | LoRA | Action Head | 데이터 | Epochs | Best Val Loss | 상태 |
| :---: | :--- | :--- | :--- | :---: | :---: | :--- | :---: | :---: | :---: | :---: |
| **1** | 11-12 | Kosmos-2 | MS Kosmos-2 | ✅ | ✅ | MobileVLALSTM (2DOF) | ~100 | 20 | ? | ⚠️ 초기 |
| **2** | 11-20 | Kosmos-2 | MS Kosmos-2 | ✅ | ✅ | MobileVLALSTM (2DOF) | ~150 | 10 | **0.280** | ⚠️ 중간 |
| **3** | 12-03 | Kosmos-2 | MS Kosmos-2 | ✅ | ✅ | MobileVLALSTM (2DOF) | **250** | 10 | **0.013** | ✅ **Best** |
| **4** | 12-04 | RoboVLMs | RoboVLMs (OXE) | ✅ | ✅ | MobileVLALSTM (2DOF) | 250 | 10 | TBD | ⏳ 진행중 |

**범례**:
- **Model**: 실제 사용한 checkpoint 모델
- **VLM Backbone**: VLM의 기본 아키텍처
- **VLM Freeze**: Backbone 고정 여부 (✅=Frozen, ❌=Fine-tune)
- **LoRA**: LoRA adapter 활성화 여부

---

## ⚠️ **발생한 모든 이슈 정리**

### **Issue 1: VLM Pretrain 불일치** 🔴
**문제**:
- RoboVLMs는 Manipulator (7DOF)로 사전학습
- 우리 로봇은 Mobile Base (2DOF)
- → Transfer Learning 효과 제한적

**증거**:
```
RoboVLMs Pretrain:
- Robot: WidowX, Franka, UR5 (팔 로봇)
- Task: Pick, Place, Push
- Action: 7DOF pose

우리 로봇:
- Robot: Serbot-omniwheel (바퀴 로봇)
- Task: Navigate, Avoid
- Action: 2DOF velocity
```

**영향**:
- Case 3에서 Microsoft Kosmos-2 (일반 VLM) 사용
- **Robot 지식 활용 못 함**
- VLM은 실질적으로 ImageNet-level Feature Extractor

**해결 시도**:
- Case 4: RoboVLMs checkpoint로 초기화
- → Robot pretrain 효과 검증 중

---

### **Issue 2: Case 4 경로 문제** 🟡
**문제**:
```
FileNotFoundError: .vlms/RoboVLMs/checkpoints/kosmos_ph_oxe-pretrain.pt
```

**원인**:
- 심볼릭 링크의 상대 경로 문제
- RoboVLMs_upstream에서 실행 시 경로 불일치

**해결**:
```json
// Before
"model_load_path": ".vlms/RoboVLMs/checkpoints/kosmos_ph_oxe-pretrain.pt"

// After
"model_load_path": "/home/billy/.cache/huggingface/hub/models--robovlms--RoboVLMs/blobs/b66d3fb4..."
```

**상태**: ✅ 해결됨 (절대 경로 사용)

---

### **Issue 3: 데이터 부족** 🔴
**문제**:
- Mobile VLA 연구는 보통 ~50,000 episodes 사용
- 우리: **250 episodes** (0.5% 수준)

**비교**:
| 연구 | Episodes |
| :--- | :---: |
| MOSAIC | 50,000 |
| ViNT | 100,000 |
| NoMaD | 50,000+ |
| **우리** | **250** |

**영향**:
- VLM Fine-tuning 불가능 (필요: ~10,000)
- Frozen VLM + LoRA만 가능
- 일반화 성능 제한적

**해결책**:
- ✅ Frozen VLM 전략
- ⏸️ Simulation 증강 (계획 중, ~5,000 목표)

---

### **Issue 4: 태스크 단순성** 🟡
**문제**:
- **단일 시나리오**: "박스를 회피하고 병에 도달"
- **제한된 변수**: 박스 위치만 약간 변경
- **경로 고정**: 한 종류의 경로만 학습

**데이터 특성**:
```
250 episodes 모두:
- 동일한 환경 (실험실)
- 동일한 목표물 (beverage bottle)
- 동일한 장애물 (box, 크기/색상 동일)
- 다른 점: 박스 위치만 (좌/우, 거리 약간)
```

**파일명 예시**:
```
episode_20251203_042905_1box_hori_left_core_medium.h5
                         ^^^^  ^^^^  ^^^^      ^^^^^^
                         박스수  방향  위치    거리
```

**영향**:
- VLA의 장점 (다양한 태스크) 활용 못 함
- Rule-based로도 가능한 수준
- 다른 환경/목표에 적용 불가능

**교수님 지적**:
> "한 경로에 대해서만 조금씩 다른 이미지로 학습"

**현실적 평가**:
- ✅ Case 3 Loss 0.013은 이 단순한 태스크에 대해서만 성공
- ❌ 새로운 목표물/환경에는 적용 불가
- ⚠️ Overfitting보다는 "Task Memorization"

---

### **Issue 5: 샘플링 단순성** 🟡
**문제**:
- 순차 샘플링: 같은 episode의 연속 프레임만
- 에피소드 간 다양성 부족

**수정**:
```python
# Before (순차)
for ep in episodes:
    for frame in range(0, len(ep)-18):
        sample = ep[frame:frame+18]

# After (랜덤)
ep = random.choice(episodes)
start = random.randint(0, len(ep)-18)
sample = ep[start:start+18]
```

**결정**:
- ⏸️ 재학습 안 함 (태스크 단순해서 효과 미미 예상)

---

### **Issue 6: Action Dimension 불일치** 🟢
**문제**:
- H5 파일: 3D actions (linear_x, linear_y, angular_z)
- 학습: 2D만 사용 (linear_x, linear_y)

**검증**:
```python
# H5 파일
f['actions'].shape = (N, 3)  # 3차원

# 사용
action = f['actions'][t][:2]  # 앞 2개만
```

**영향**:
- angular_z (회전) 무시
- 직진만 학습, 회전 제어 못 함

**해결책**:
- ⏸️ 3DOF 확장 가능 (향후)

---

## 📊 **데이터셋 특성 상세 분석**

### **1. 데이터 구조**
```
ROS_action/mobile_vla_dataset/
├── episode_20251119_*.h5 (November)  # ~100 episodes
└── episode_20251203_*.h5 (December)  # ~150 episodes
```

### **2. Episode 명명 규칙**
```
episode_YYYYMMDD_HHMMSS_[config].h5
        ^^^^^^^^  ^^^^^^  ^^^^^^^^
        날짜       시간     시나리오

예시:
episode_20251203_042905_1box_hori_left_core_medium.h5
- 날짜: 2025-12-03
- 시간: 04:29:05
- 시나리오:
  - 1box: 박스 1개
  - hori: 수평(horizontal) 배치
  - left: 왼쪽 위치
  - core: 중심 경로
  - medium: 중간 거리
```

### **3. 시나리오 변형**
| 변수 | 값 | 설명 |
| :--- | :--- | :--- |
| 박스 개수 | 1box | 항상 1개 |
| 방향 | hori | 항상 수평 |
| 위치 | left, right | 좌/우 |
| 경로 | core | 항상 중앙 경로 |
| 거리 | medium | 항상 중간 거리 |

**결론**: **거의 동일한 시나리오, 박스 위치만 약간 변경**

### **4. H5 파일 구조**
```python
episode.h5:
├── images: (N, 480, 640, 3)  # RGB 이미지
├── actions: (N, 3)             # [linear_x, linear_y, angular_z]
└── language_instruction: str   # "Navigate around obstacles..."
```

### **5. Episode 통계**
```
Total episodes: 250
평균 프레임 수: ~18-25
총 데이터 포인트: ~4,500-6,000
유효 window: ~4,000 (18프레임씩 필요)
```

---

## 🔬 **학습 결과 재해석**

### **Case 1 → Case 2 → Case 3 진행**
```
데이터 증가의 효과:
100 eps → 150 eps → 250 eps
  ?    →  0.280  →  0.013

결론: 데이터만 늘려도 같은 시나리오 반복 학습으로 Loss 감소
```

### **하지만 이것의 의미는?**
```
✅ 같은 시나리오 (박스 회피 → 병 도달)를 잘 학습함
❌ 새로운 시나리오 (다른 목표물, 다른 환경)는 못 함
⚠️ "Task-specific Overfitting"
```

### **일반화 능력 의문**
```
Question: Loss 0.013이 정말 일반화인가?
Answer: 아마도 아님. 단일 태스크 Memorization으로 추정

증거:
1. Train Loss ≈ Val Loss (둘 다 같은 시나리오)
2. 태스크 단순 (Rule-based 가능 수준)
3. 데이터 편향 (한 경로만)
```

---

## 🎯 **Case 3 vs Case 4 비교 (진행 중)**

### **유일한 차이**
| 항목 | Case 3 | Case 4 |
| :--- | :--- | :--- |
| VLM Init | Microsoft Kosmos-2 | RoboVLMs (OXE) |
| VLM Pretrain | 일반 이미지 (COCO) | Robot (Manipulator) |
| 나머지 | **완전 동일** | **완전 동일** |

### **예상 시나리오**
```
시나리오 A: Case 4 < Case 3
→ Robot pretrain도 Mobile에 도움 안 됨
→ 일반 VLM이 오히려 나음

시나리오 B: Case 4 ≈ Case 3
→ Pretrain 차이 없음
→ 둘 다 Feature Extractor 역할만

시나리오 C: Case 4 > Case 3
→ Robot pretrain이 약간 도움됨
→ (가능성 낮음, Manipulator ≠ Mobile)
```

---

## 📝 **모든 이슈 체크리스트**

| # | 이슈 | 심각도 | 상태 | 해결 |
| :---: | :--- | :---: | :---: | :--- |
| 1 | VLM Pretrain 불일치 | 🔴 | 진행중 | Case 4로 검증 |
| 2 | Case 4 경로 문제 | 🟡 | ✅ | 절대 경로 사용 |
| 3 | 데이터 부족 | 🔴 | 지속 | Frozen VLM 전략 |
| 4 | 태스크 단순성 | 🟡 | 지속 | 인정 필요 |
| 5 | 샘플링 단순성 | 🟡 | 보류 | 효과 미미 예상 |
| 6 | Action Dim 불일치 | 🟢 | 인지됨 | 향후 3DOF 확장 |

---

## 🎓 **교수님께 보고할 핵심 사항**

### **1. 데이터 특성 (중요!)** ⚠️
```
- 250 episodes 모두 거의 동일한 시나리오
- "박스 회피 → 병 도달" 한 가지 태스크만
- 박스 위치만 좌/우, 거리 약간 변경
- 한 경로(core)만 학습
```

### **2. Loss 0.013의 의미**
```
✅ 이 특정 태스크에서는 잘 작동
❌ 일반화는 아님 (Task Memorization)
⚠️ 새 환경/목표에 적용 불가
```

### **3. VLM Pretrain 효과** (Case 4 대기)
```
Microsoft Kosmos-2 vs RoboVLMs
→ Robot pretrain이 Mobile에 도움되는지 검증 중
→ 예상: 차이 없거나 미미할 것
```

### **4. 현실적 평가**
```
우리 성과:
✅ Frozen VLM 전략 작동 확인
✅ 250 episodes로 특정 태스크 학습 가능
✅ LoRA 효과적

한계:
❌ 일반화 불가 (단일 시나리오)
❌ Robot VLM 효과 미확인
❌ VLA 장점 활용 못 함 (다양성 부족)
```

---

## 📂 **체크포인트 및 로그 정리**

### **Case 3 (Best)**
```
Checkpoint:
RoboVLMs_upstream/runs/mobile_vla_lora_20251203/.../
└── epoch_epoch=09-val_loss=val_loss=0.013.ckpt

Log:
lora_training_log_20251203_225632.txt
```

### **Case 4 (진행중)**
```
Checkpoint: TBD
Log: lora_training_robovlms_20251204_073828.txt

Issue Log:
- 07:38 FileNotFoundError (경로 문제)
- 09:25 재시작 (절대 경로 사용)
```

---

## 🔧 **재현 가능성**

### **재현 절차 (Case 3)**
```bash
1. 데이터: ROS_action/mobile_vla_dataset (250 eps)
2. Config: Mobile_VLA/configs/mobile_vla_20251203_lora.json
3. 실행: cd RoboVLMs_upstream && poetry run python main.py [config]
4. 예상 시간: ~25분
5. 예상 결과: Val Loss ~0.013
```

### **재현 고려사항**
- 동일한 데이터 필요 (250 episodes, 같은 시나리오)
- Poetry 환경 필요
- GPU 필요 (V100 이상 권장)

---

*모든 이슈와 데이터 특성을 투명하게 정리했습니다.*
