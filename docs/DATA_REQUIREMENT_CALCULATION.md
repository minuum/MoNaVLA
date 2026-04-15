# Mobile-VLA 필요 데이터 규모 계산

## 📊 RoboVLMs vs Mobile-VLA 비교

### RoboVLMs (Pretrain - OXE)
```
Episodes:  ~970,000
Objects:   ~200개 (추정)
Tasks:     ~1,000개 (추정)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
에피소드당 비율 계산:
  970,000 / (200 objects × 1,000 tasks) = 4.85 episodes per (object, task) pair
```

**추정 근거**:
- Open-X는 60+ 데이터셋 집합
- 각 데이터셋별 수십 개 objects
- 총 추정: 200~300 objects
- Tasks: object당 3~10개 variations
- 총 추정: 1,000~3,000 task variations

---

## 🧮 비율 기반 계산

### 방법 1: Object당 비율
```python
RoboVLMs:
  Episodes per object = 970,000 / 200 = 4,850 episodes/object

Mobile-VLA:
  Objects = 2 (box, bottle)
  필요 episodes = 2 × 4,850 = 9,700 episodes
```

### 방법 2: Task당 비율
```python
RoboVLMs:
  Episodes per task = 970,000 / 1,000 = 970 episodes/task

Mobile-VLA:
  Tasks = 1 (obstacle avoidance)
  필요 episodes = 1 × 970 = 970 episodes
```

### 방법 3: (Object, Task) Pair당 비율
```python
RoboVLMs:
  Episodes per (object, task) = 970,000 / (200 × 1,000) 
                              = 970,000 / 200,000
                              = 4.85 episodes per pair

Mobile-VLA:
  Object-Task pairs = 2 objects × 1 task = 2 pairs
  필요 episodes = 2 × 4.85 = 9.7 episodes
```

---

## ⚠️ 문제점 분석

### 우리 상황의 특수성

**Mobile-VLA는 1개 태스크가 아닙니다!**

실제로는:
```
Objects: 2 (box, bottle)
Tasks: 4가지
  1. Left obstacle avoidance (왼쪽 회피)
  2. Right obstacle avoidance (오른쪽 회피)
  3. Box avoidance (박스 회피)
  4. Bottle avoidance (병 회피)

실제 combinations:
  - Box + Left = 1
  - Box + Right = 1
  - Bottle + Left = 1
  - Bottle + Right = 1
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Total: 4 (object, task) pairs
```

---

## 📈 정확한 필요 데이터 계산

### 시나리오 1: Conservative (보수적)
**기준**: RoboVLMs의 최소 비율 적용

```python
Episodes per (object, task) pair = 4.85

Mobile-VLA pairs:
  1. Box + Left:    4.85 episodes
  2. Box + Right:   4.85 episodes
  3. Bottle + Left: 4.85 episodes
  4. Bottle + Right: 4.85 episodes
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total: 4 × 4.85 = 19.4 episodes ≈ 20 episodes
```

**현재 보유**: 500 episodes ✅ **충분!**

---

### 시나리오 2: Task Variation 고려
**기준**: 난이도별 variations 포함

```
RoboVLMs task variations 예시:
  "Pick up cup"
    - Pick up red cup
    - Pick up blue cup
    - Pick up from table
    - Pick up from shelf
    → 1 task = 4~10 variations

Mobile-VLA task variations:
  "Obstacle avoidance"
    - Close distance (0.5m)
    - Medium distance (1.0m)
    - Far distance (1.5m)
    × 2 directions (left, right)
    × 2 objects (box, bottle)
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    Total variations: 3 × 2 × 2 = 12 variations

Episodes per variation = 4.85
Total needed: 12 × 4.85 = 58.2 episodes ≈ 60 episodes
```

**현재 보유**: 500 episodes ✅ **충분!**

---

### 시나리오 3: Robust Training 기준
**기준**: 일반화 성능을 위한 충분한 데이터

```
RoboVLMs에서 task당 평균 episodes:
  970,000 / 1,000 tasks = 970 episodes/task

Mobile-VLA:
  Tasks (세분화):
    - Box + Left (easy/medium/hard)
    - Box + Right (easy/medium/hard)
    - Bottle + Left (easy/medium/hard)
    - Bottle + Right (easy/medium/hard)
  
  Total detailed tasks: 4 base × 3 difficulties = 12 tasks
  
  Episodes per task = 970 / 12 ≈ 80 episodes/task
  Total needed: 12 × 80 = 960 episodes
```

**현재 보유**: 500 episodes ⚠️ **부족!**

---

### 시나리오 4: Real-world Deployment 기준
**기준**: Production-ready 모델

```
업계 경험치:
  - Simple task: 100~500 episodes
  - Medium task: 500~2,000 episodes
  - Complex task: 2,000~10,000 episodes

Mobile-VLA complexity:
  - Navigation: Medium complexity
  - VLM-based: Needs more data
  - 2-DOF: Simpler than 7-DOF
  
권장: 1,000~2,000 episodes per scenario

Scenarios:
  1. Left avoidance: 1,000 episodes
  2. Right avoidance: 1,000 episodes
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total: 2,000~3,000 episodes
```

**현재 보유**: 500 episodes ⚠️ **부족!**

---

## 🎯 최종 권장사항

### Tier 1: Minimum Viable (최소 실행)
```
Episodes: ~100
구성: 
  - Left: 50
  - Right: 50
목적: Proof of concept
현재 상태: ✅ 충분 (500개 보유)
```

### Tier 2: Research Quality (연구 품질)
```
Episodes: ~500~1,000
구성:
  - Left: 250~500
  - Right: 250~500
목적: 논문 발표 가능 수준
현재 상태: ✅ 하한선 충족 (500개), ⚠️ 상한 미달
```

### Tier 3: Production Ready (실용화)
```
Episodes: ~2,000~3,000
구성:
  - Left easy: 300
  - Left medium: 400
  - Left hard: 300
  - Right easy: 300
  - Right medium: 400
  - Right hard: 300
목적: 실제 배포 가능
현재 상태: ❌ 부족 (500개 → 2,000개 필요)
```

### Tier 4: Robust Generalization (강건한 일반화)
```
Episodes: ~5,000~10,000
구성:
  - 다양한 환경
  - 다양한 조명
  - 다양한 장애물 크기/색상
  - 다양한 시작 위치
목적: Real-world robust deployment
현재 상태: ❌ 크게 부족
```

---

## 📋 구체적 Data Collection 계획

### Phase 1: 현재 상태 (✅ 완료)
```
Episodes: 500 (250L + 250R)
Objects: Box, Bottle
Difficulty: Medium
Status: ✅ Case 3 학습 완료
```

### Phase 2: Difficulty Expansion (난이도 확장)
```
목표: 1,500 episodes (total)

추가 수집:
  - Left easy: 250
  - Left hard: 250
  - Right easy: 250
  - Right hard: 250
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total 추가: +1,000 episodes
Total 합계: 1,500 episodes

예상 소요:
  - 수집 시간: 1 episode/min
  - Total: 1,000분 ≈ 17시간
  - 실제 (준비 포함): 3~4일
```

### Phase 3: Simulation Augmentation (시뮬레이션 증강)
```
목표: 5,000 episodes (total)

Simulation:
  - Gazebo/PyBullet 환경 구축
  - 자동 수집: 3,500 episodes
  - Variations:
    * 조명 변화: 10 conditions
    * 박스 크기: 5 sizes
    * 박스 색상: 5 colors
    * 시작 위치: 7 positions
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total: 10 × 5 × 5 × 7 = 1,750 combinations
Per combination: 2 episodes
Total 생성: 3,500 episodes

예상 소요:
  - 환경 구축: 1주
  - 데이터 생성: 2~3일 (자동)
```

### Phase 4: Domain Randomization (도메인 랜덤화)
```
목표: 10,000 episodes

추가 variations:
  - 카메라 노이즈
  - 동적 장애물
  - 다양한 배경
  - 로봇 자세 변화

Total: 10,000 episodes
```

---

## 💡 현실적 전략

### 단기 (1주 이내)
```
✅ 현재 500 episodes 활용
✅ Case 3 모델 검증
✅ 성능 평가 및 논문 작성
```

### 중기 (1달 이내)
```
⬜ +500 episodes 추가 수집 (난이도 다양화)
⬜ Total 1,000 episodes로 재학습
⬜ 성능 개선 확인
```

### 장기 (2~3달)
```
⬜ Simulation 환경 구축
⬜ +4,000 simulated episodes
⬜ Total 5,000 episodes로 robust training
⬜ Real-world deployment
```

---

## 📊 비용-효과 분석

| 목표 | Episodes | 수집 비용 | 성능 | ROI |
|:---|---:|---:|:---:|:---:|
| **Tier 1 (Minimum)** | 100 | 낮음 | 낮음 | ⭐ |
| **Tier 2 (Research)** | 500-1K | 중간 | 중간 | ⭐⭐⭐ |
| **Tier 3 (Production)** | 2K-3K | 높음 | 높음 | ⭐⭐⭐⭐ |
| **Tier 4 (Robust)** | 5K-10K | 매우 높음 | 매우 높음 | ⭐⭐⭐⭐⭐ |

**현재 위치**: Tier 2 (Research Quality) ✅

**권장 다음 단계**: Tier 3 목표 (2,000 episodes)

---

## ✅ 결론

### 비율 기반 계산 결과
```
RoboVLMs 기준:
  최소: ~20 episodes (object-task pair 기준)
  중간: ~60 episodes (variation 고려)
  권장: ~1,000 episodes (task당 평균)
  이상: ~2,000-3,000 episodes (robust training)

현재 보유: 500 episodes
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
평가: ✅ 연구용으로는 충분
     ⚠️ 실용화는 2~4배 더 필요
```

### 최종 권장
1. **현재 (500)**: 논문 작성 및 검증 가능 ✅
2. **목표 (1,000)**: +500 수집으로 robustness 향상
3. **이상 (2,000)**: Simulation으로 달성, production-ready
4. **궁극 (5,000+)**: Domain randomization, real-world deployment

**즉각 액션**: 현재 500으로 학습 완료 후 성능 평가 → 필요시 추가 수집 결정
