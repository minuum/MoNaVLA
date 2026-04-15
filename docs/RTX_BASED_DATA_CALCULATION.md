# RT-X (Open X-Embodiment) 기반 Mobile-VLA 데이터 요구사항

## 📊 RT-X Dataset 정확한 스펙

### Official Statistics (공식 통계)
```
Dataset: Open X-Embodiment (RT-X)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Trajectories:  1,000,000+ (1M+)
Robots:        22 embodiments
Institutions:  21 institutions (34 labs)
Skills:        527 distinct skills
Tasks:         160,266 tasks
Datasets:      60 pooled datasets
```

**Source**: https://robotics-transformer-x.github.io/

---

## 🧮 공통 비율 계산

### 비율 1: Trajectories per Skill
```python
Total Trajectories: 1,000,000
Total Skills:       527

Ratio = 1,000,000 / 527 = 1,898 trajectories/skill
```

### 비율 2: Trajectories per Task
```python
Total Trajectories: 1,000,000
Total Tasks:        160,266

Ratio = 1,000,000 / 160,266 = 6.24 trajectories/task
```

### 비율 3: Tasks per Skill
```python
Total Tasks:  160,266
Total Skills: 527

Ratio = 160,266 / 527 = 304 tasks/skill
```

**해석**: 
- 1개 Skill = 평균 304개 Tasks (variations)
- 1개 Task = 평균 6.24개 Trajectories
- 1개 Skill = 평균 1,898개 Trajectories

---

## 🎯 Mobile-VLA 매핑

### 우리 상황 정의

#### Skills (고수준 태스크)
```
Mobile-VLA Skills:
  1. Obstacle Avoidance (장애물 회피)

Total Skills: 1
```

#### Tasks (세부 variations)
```
Mobile-VLA Tasks:
  1. Avoid box on left
  2. Avoid box on right
  3. Avoid bottle on left
  4. Avoid bottle on right
  ×
  Difficulty levels:
    - Easy (far distance: 1.5m)
    - Medium (medium distance: 1.0m)
    - Hard (close distance: 0.5m)

Total Tasks: 4 base × 3 difficulties = 12 tasks
```

#### Trajectories (Episodes)
```
Current: 500 episodes
Target: ???
```

---

## 📏 Method 1: Skill-based Calculation

### RT-X 비율 적용
```
RT-X: 1,898 trajectories/skill

Mobile-VLA:
  Skills: 1
  Required = 1 × 1,898 = 1,898 trajectories
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
권장: ~1,900 episodes

현재: 500 episodes
부족: 1,400 episodes (74% 부족)
```

**평가**: ⚠️ 약 1/4 수준, 추가 수집 필요

---

## 📏 Method 2: Task-based Calculation

### RT-X 비율 적용
```
RT-X: 6.24 trajectories/task

Mobile-VLA:
  Tasks: 12 (4 base × 3 difficulties)
  Required = 12 × 6.24 = 74.9 trajectories
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
최소: ~75 episodes

현재: 500 episodes
초과: 425 episodes ✅
```

**평가**: ✅ 충분! 약 6.7배 초과

---

## 📏 Method 3: Comprehensive (Skill + Task hierarchy)

### 계층적 계산
```
RT-X 구조:
  1 Skill → 304 Tasks → 1,898 Trajectories
  
  Per Task = 1,898 / 304 = 6.24 trajectories

Mobile-VLA 구조:
  1 Skill → 12 Tasks → ??? Trajectories

Option A: Skill 기준
  Required = 1,898 trajectories

Option B: Task 기준  
  Required = 12 × 6.24 = 75 trajectories

Option C: 절충 (RT-X의 Task/Skill 비율 고려)
  RT-X Task/Skill ratio: 304
  Mobile-VLA Task/Skill ratio: 12
  
  비율 조정 = 12 / 304 = 0.0395 (약 4%)
  Required = 1,898 × 0.0395 = 75 trajectories
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
결론: 75~1,900 사이

중간값: (75 + 1,900) / 2 = 987.5 ≈ 1,000 trajectories
```

**평가**: 현재 500은 중간값의 50%

---

## 🎯 공통 기준 도출

### 다양한 관점에서의 권장치

| 계산 방법 | 필요 Episodes | 현재 보유 | 비율 | 평가 |
|:---|---:|---:|:---:|:---:|
| **Skill 기준** | 1,900 | 500 | 26% | ⚠️ 부족 |
| **Task 기준** | 75 | 500 | 667% | ✅ 충분 |
| **절충 (중간값)** | 1,000 | 500 | 50% | ⚠️ 보통 |
| **보수적 (상한)** | 1,900 | 500 | 26% | ⚠️ 부족 |
| **낙관적 (하한)** | 75 | 500 | 667% | ✅ 충분 |

---

## 💡 왜 이렇게 범위가 넓은가?

### 분석: Task Complexity 차이

#### RT-X Tasks (복잡도 높음)
```
예시: "Pick and Place" Skill
  Tasks:
    - Pick red cup from table
    - Pick blue cup from table
    - Pick red cup from shelf
    - Pick blue cup from shelf
    - Pick red cup from drawer
    - ...
    (수백 가지 variations)

→ 각 variation이 "다른 Task"로 카운트
→ 1 Skill = 304 Tasks (매우 세분화)
→ Task당 적은 데이터 필요 (6.24 trajectories)
```

#### Mobile-VLA Tasks (복잡도 낮음)
```
Skill: "Obstacle Avoidance"
  Tasks:
    - Avoid box left
    - Avoid box right
    - Avoid bottle left
    - Avoid bottle right
    (4 base variations × 3 difficulties = 12 total)

→ 상대적으로 단순
→ 1 Skill = 12 Tasks (거친 분류)
→ Task당 더 많은 데이터 필요
```

---

## 🎯 최종 권장사항

### Conservative Estimate (보수적 추정)
```
기준: RT-X Skill-based ratio
필요: ~1,900 episodes

이유:
  - Mobile-VLA task가 RT-X보다 단순하지만
  - Navigation은 variation이 많음 (환경, 조명, 각도 등)
  - Robust training 필요

권장: 1,500~2,000 episodes
현재: 500 episodes (25~33%)
추가 필요: 1,000~1,500 episodes
```

### Moderate Estimate (중간 추정)
```
기준: 절충안 (Skill과 Task 비율 고려)
필요: ~1,000 episodes

이유:
  - Task 수가 적으므로 Skill 비율보다 낮춤
  - 하지만 Task당 비율보다는 높임
  - Real-world deployment 고려

권장: 800~1,200 episodes
현재: 500 episodes (42~62%)
추가 필요: 300~700 episodes
```

### Optimistic Estimate (낙관적 추정)
```
기준: RT-X Task-based ratio
필요: ~75 episodes

이유:
  - Task 수 기준으로만 계산
  - 최소 viable 수준

권장: 200~500 episodes
현재: 500 episodes (100%)
추가 필요: 0 episodes ✅
```

---

## 📊 비율 종합 분석

### RT-X 기준 환산

```
RT-X Structure:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1,000,000 trajectories
÷ 527 skills
÷ 304 tasks/skill
= 6.24 trajectories/task

Mobile-VLA Mapping:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Option 1: 우리도 "1 skill" 기준
  → 1,898 trajectories

Option 2: 우리 "12 tasks" 기준
  → 12 × 6.24 = 75 trajectories

Option 3: Task complexity 보정
  RT-X: 1 skill → 304 tasks (매우 세분화)
  우리: 1 skill → 12 tasks (거친 분류)
  
  Complexity ratio = 304 / 12 = 25.3
  
  우리 1 task ≈ RT-X 25.3 tasks
  Required = 12 × (6.24 × 25.3) = 1,894 trajectories
```

---

## ✅ 최종 결론 및 권장

### 공통 기준 (Consensus)

**최소 (Minimum Viable)**:
```
Episodes: 200~300
근거: Task 기준 × 안전 계수 3~4
현재 대비: ✅ 초과 달성
```

**권장 (Recommended)**:
```
Episodes: 800~1,200
근거: Skill-Task 절충 + real-world variations
현재 대비: ⚠️ 500은 하한선
추가 필요: 300~700 episodes
```

**이상적 (Ideal)**:
```
Episodes: 1,500~2,000
근거: Skill 기준 + robustness margin
현재 대비: ❌ 2~4배 부족
추가 필요: 1,000~1,500 episodes
```

### 단계별 목표

```
Phase 1: 500 episodes (현재) ✅
  → Research quality
  → 논문 작성 가능
  
Phase 2: 1,000 episodes (목표)
  → +500 수집
  → Production quality
  → 실제 배포 고려 가능
  
Phase 3: 2,000 episodes (이상)
  → +1,500 수집 (simulation 활용)
  → Robust deployment
  → Real-world variations 커버
```

---

## 📋 구체적 실행 계획

### 즉시 실행 (현재 500 활용)
```
✅ Case 3 (500 episodes) 학습 완료
✅ 성능 평가 및 분석
✅ 논문 작성 시작
```

### 단기 목표 (1,000 total)
```
추가 수집: +500 episodes
  - Easy difficulty: 125 (left) + 125 (right)
  - Hard difficulty: 125 (left) + 125 (right)

소요 시간: 1주일
예상 효과: 
  - Robustness 2배 향상
  - Generalization 개선
```

### 중기 목표 (2,000 total)
```
Simulation: +1,000 episodes
  - Gazebo/PyBullet 환경
  - Lighting variations: 5
  - Object size variations: 4
  - Position variations: 5
  → 100 combinations × 10 = 1,000

소요 시간: 2~3주
예상 효과:
  - Production-ready
  - Real-world deployment 가능
```

---

## 🎯 요약

### RT-X 비율 기반 결론

| 기준 | 필요 Episodes | 현재 상태 | 권장 |
|:---|---:|:---:|:---|
| **Task 기준** | 75 | ✅ 충분 | 최소 viable |
| **절충안** | 1,000 | ⚠️ 50% | **권장 목표** |
| **Skill 기준** | 1,900 | ❌ 26% | 이상적 |

**공통 권장**: **1,000 episodes** (현재의 2배)
- RT-X Task-Skill 구조 고려
- Mobile-VLA complexity 반영
- Real-world deployment 대비

**현재 평가**: 500 episodes = Research Quality ✅, Production 준비 중 ⚠️

---

**상세 근거**: RT-X (Open X-Embodiment) 공식 데이터 기반
**참조**: https://robotics-transformer-x.github.io/
