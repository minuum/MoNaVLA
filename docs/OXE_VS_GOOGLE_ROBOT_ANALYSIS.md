# OXE vs Google Robot: Mobile VLA Task 적합성 분석

**작성일**: 2026-01-11  
**목적**: 우리 Mobile VLA task에 OXE와 Google Robot 중 무엇이 더 적합한지 판단

---

## 1. RoboVLMs Pretrained Checkpoints

### 제공되는 Checkpoints

| Checkpoint | 학습 데이터 | 특징 |
|------------|------------|------|
| **kosmos_ph_google-robot-post-train** | Google Robot data | ❓ (우리가 사용 중) |
| **kosmos_ph_calvin_abcd** | CALVIN ABCD split | 테이블탑 manipulation |
| **kosmos_ph_calvin_abc** | CALVIN ABC split | 테이블탑 manipulation |
| **kosmos_ph_oxe-pretrain** | OXE-magic-soup | 22 embodiments, 527 skills |

---

## 2. Google Robot Data 특성

### 데이터 정보

**Google Robot**는 명확한 공개 dataset이 아니라, Google DeepMind의 내부 robot data를 의미합니다.

**특징** (추정):
- 주로 **manipulation tasks** (pick, place, push 등)
- **Single embodiment** 또는 소수 로봇
- **Tabletop environment** 중심
- 고품질, 전문가 수준 데이터

**Task Examples**:
- Pick and place objects
- Open/close drawers
- Manipulate objects on table
- Precision grasping

---

## 3. Open X-Embodiment (OXE) Data 특성

### 3.1 데이터 규모

```
Trajectories: 1,000,000+
Robot Embodiments: 22 (single arms, bi-manual, quadrupeds)
Skills: 527
Tasks: 160,266
Institutions: 21
Labs: 34
```

**핵심**: **Massive diversity**

---

### 3.2 포함된 Task Types

**주요 Tasks** (Manipulation 중심):
- Picking
- Placing
- Sliding
- Wiping
- Grasping
- Object manipulation

**Navigation Data**:
- ⚠️ 일부 포함되어 있음
- 하지만 **manipulation이 주**

---

### 3.3 OXE-magic-soup

```
"magic-soup" = OXE dataset의 선별된 subset
- High-quality trajectories
- 다양한 embodiments
- Cross-embodiment generalization 최적화
```

**목적**: 
- Generalist policy 학습
- Positive transfer across robots
- 7-DoF end-effector control

---

## 4. 우리 Mobile VLA Task 분석

### 4.1 Task 특성

```python
Task: Navigate around obstacles (LEFT/RIGHT)
Robot: Mobile base (2-DoF)
  - linear_x: Forward speed
  - linear_y: Lateral movement (strafe)
  
Action Space: Continuous [linear_x, linear_y]
Environment: Open space with obstacles
Camera: Single RGB camera (static view)

Instruction Examples:
  - "Navigate around the obstacle on the LEFT side"
  - "Navigate around the obstacle on the RIGHT side"
```

**핵심**: **Mobile Navigation**, NOT Manipulation

---

### 4.2 데이터 예시

```
Episode: obstacle_right
  t=0-3: [1.15, 0.00] - 직진
  t=4: [0.00, -1.15]   - 오른쪽 회전
  t=5-18: [1.15, -1.15] - 직진+오른쪽
  
Instruction: "Navigate RIGHT"
```

**특징**:
- Sequential navigation decisions
- Spatial reasoning (left/right)
- Obstacle avoidance
- **NO grasping, NO manipulation**

---

## 5. Google Robot vs OXE 비교

### 5.1 Task Domain

| 측면 | Google Robot | OXE | 우리 Task |
|------|--------------|-----|----------|
| **주요 Domain** | Manipulation | Manipulation | **Navigation** |
| **Action Type** | 7-DoF (arm+gripper) | 7-DoF (arm+gripper) | **2-DoF (mobile)** |
| **Environment** | Tabletop | Tabletop | **Open space** |
| **Object Interaction** | ✅ Heavy | ✅ Heavy | ❌ No interaction |
| **Navigation** | ❌ Minimal | ⚠️ Some | ✅ **Primary** |

**결론**: 
- ❌ Google Robot: Task mismatch (manipulation vs navigation)
- ⚠️ OXE: 주로 manipulation, 일부 navigation

---

### 5.2 Embodiment Match

| 측면 | Google Robot | OXE | 우리 Task |
|------|--------------|-----|----------|
| **Embodiment** | Robot arm | 22 embodiments (mostly arms) | **Mobile base** |
| **DoF** | 7-DoF | 7-DoF | **2-DoF** |
| **Action Space** | [x,y,z,roll,pitch,yaw,gripper] | [x,y,z,roll,pitch,yaw,gripper] | **[linear_x, linear_y]** |
| **Control** | End-effector | End-effector | **Base velocity** |

**결론**:
- ❌ Google Robot: Embodiment 완전히 다름
- ⚠️ OXE: 대부분 arm, 일부 mobile robots 포함

---

### 5.3 Instruction Grounding

| 측면 | Google Robot | OXE | 우리 Task |
|------|--------------|-----|----------|
| **Instruction Type** | "Pick the red cup" | "Slide the block left" | **"Navigate LEFT/RIGHT"** |
| **Spatial Reasoning** | Object-centric | Object-centric | **Directional** |
| **Grounding** | Object attributes | Object manipulation | **Spatial directions** |

**예시 비교**:
```
Google Robot: "Pick up the RED cup" (color grounding)
OXE: "Slide the block to the LEFT" (direction + object)
우리: "Navigate on the LEFT side" (direction only)
```

**유사성**:
- ⚠️ OXE에 "LEFT/RIGHT" spatial instruction 일부 포함
- ✅ Direction grounding 학습 가능

---

### 5.4 Data Diversity

| 측면 | Google Robot | OXE |
|------|--------------|-----|
| **Embodiments** | 1-few | **22** |
| **Environments** | Lab settings | **21 institutions** |
| **Tasks** | Focused | **527 skills** |
| **Generalization** | Single domain | **Cross-embodiment** |

**의미**:
- Google Robot: **Focused, high-quality**
- OXE: **Diverse, generalization**

---

## 6. 합리적 판단

### 6.1 Google Robot의 장점

✅ **Pros**:
1. High-quality, expert data
2. Instruction grounding 잘 학습됨 (우리가 확인함)
3. Text encoder가 robot task에 최적화
4. 안정적, 검증됨

❌ **Cons**:
1. **Manipulation task only** (navigation 없음)
2. **7-DoF embodiment** (2-DoF와 완전히 다름)
3. Task domain mismatch
4. Spatial reasoning은 object-centric

---

### 6.2 OXE의 장점

✅ **Pros**:
1. **22 embodiments** (일부 mobile robots 포함 가능성)
2. **Navigation data 일부 포함**
3. Diverse environments and tasks
4. **Cross-embodiment generalization** (2-DoF로 transfer 가능성)
5. "LEFT/RIGHT" 같은 directional instruction 포함

❌ **Cons**:
1. Manipulation이 주 (navigation은 부차적)
2. Data quality가 불균일할 수 있음
3. 527 skills 중 navigation은 소수

---

### 6.3 우리 Task와의 Alignment

| 요구사항 | Google Robot | OXE | 중요도 |
|---------|--------------|-----|--------|
| **Navigation task** | ❌ (0%) | ⚠️ (10-20%) | ⭐⭐⭐⭐⭐ |
| **2-DoF mobile base** | ❌ (7-DoF) | ⚠️ (22 embodiments) | ⭐⭐⭐⭐⭐ |
| **Spatial directions** | ⚠️ (object-centric) | ✅ (direction-aware) | ⭐⭐⭐⭐⭐ |
| **Instruction grounding** | ✅ (검증됨) | ✅ (다양함) | ⭐⭐⭐⭐⭐ |
| **Generalization** | ⚠️ (single domain) | ✅ (cross-embodiment) | ⭐⭐⭐⭐ |

---

## 7. 최종 판단

### 현실적 평가

```
우리 Task: Mobile navigation (2-DoF)

Google Robot:
  - Manipulation (7-DoF)
  - Task domain 불일치: 90%
  - Embodiment 불일치: 100%
  - 적합도: ⭐⭐ (20%)

OXE:
  - 주로 Manipulation (7-DoF)
  - 일부 Navigation 포함
  - 22 embodiments (일부 mobile 가능성)
  - Task domain 불일치: 80%
  - Embodiment 일부 일치: 10-20%
  - 적합도: ⭐⭐⭐ (30%)
```

**솔직한 결론**:
> **둘 다 완벽하게 적합하지 않음**

---

### 상대 비교: OXE가 약간 더 나음

**이유**:

1. **Diversity Helps**
   ```
   Google Robot: Manipulation only
   OXE: Manipulation + Some navigation + 22 embodiments
   
   → OXE가 transfer learning에 유리
   ```

2. **Spatial Instruction**
   ```
   OXE의 "Slide LEFT/RIGHT" instructions
   → 우리 "Navigate LEFT/RIGHT"와 유사
   → Spatial grounding 학습 가능
   ```

3. **Cross-embodiment**
   ```
   OXE: 7-DoF → 2-DoF transfer 가능성
   Google Robot: 7-DoF only
   ```

4. **Generalization**
   ```
   OXE: 다양한 환경, 다양한 tasks
   → Generalist policy
   → Novel task (navigation)에 더 robust
   ```

---

## 8. 권장 전략

### Option A: OXE Pretrained ⭐ (권장)

```json
{
  "pretrained_vlm_path": "kosmos_ph_oxe-pretrain.pt",
  "train_setup": {
    "freeze_backbone": false,
    "lora_enable": true,
    "lora_r": 16,
    "lora_alpha": 32
  }
}
```

**기대 효과**:
- ✅ Diverse data로 학습된 VLM
- ✅ Cross-embodiment generalization
- ✅ Spatial instruction grounding
- ⚠️ Navigation은 여전히 소수

---

### Option B: Google Robot (현재)

```json
{
  "pretrained_vlm_path": "kosmos_ph_google-robot.pt",
  "train_setup": {
    "freeze_backbone": false,
    "lora_enable": true
  }
}
```

**기대 효과**:
- ✅ High-quality instruction grounding
- ✅ 안정적 학습
- ❌ Task/Embodiment mismatch

---

### Option C: From Scratch (Kosmos-2)

```json
{
  "model_load_path": null,
  "train_setup": {
    "freeze_backbone": false,
    "lora_enable": true
  }
}
```

**기대 효과**:
- ✅ Task-specific 학습
- ❌ Robot domain knowledge 없음
- ❌ 더 많은 data 필요

---

## 9. 실험 제안

### Phase 1: OXE vs Google Robot 비교

```bash
# OXE Pretrained
python train.py \
  --config mobile_vla_oxe.json \
  --pretrained kosmos_ph_oxe-pretrain.pt \
  --epochs 10

# Google Robot (현재)
python train.py \
  --config mobile_vla_pretrained.json \
  --pretrained kosmos_ph_google-robot.pt \
  --epochs 10
```

**비교 지표**:
1. Val Loss
2. Instruction Grounding (LEFT vs RIGHT)
3. Generalization to new obstacles

---

### Phase 2: LoRA Fine-tuning

```
둘 다 LoRA fine-tuning 적용:
  - freeze_backbone: false
  - lora_enable: true
  
비교:
  - OXE + LoRA
  - Google Robot + LoRA
```

---

## 10. 최종 답변

### "OXE vs Google Robot, 무엇이 더 적합한가?"

**상대 평가**: **OXE가 약간 더 나음** ⭐⭐⭐ vs ⭐⭐

**이유**:
1. ✅ Diversity (22 embodiments)
2. ✅ Navigation data 일부 포함
3. ✅ Cross-embodiment generalization
4. ✅ Spatial instruction ("LEFT/RIGHT")

**하지만**:
- ⚠️ 둘 다 완벽하게 적합하지 않음
- ⚠️ OXE도 manipulation이 주

---

### 실용적 권장사항

**1순위**: **OXE Pretrained + LoRA** ⭐⭐⭐⭐
- 더 diverse
- Transfer 가능성 높음

**2순위**: **Google Robot + LoRA** (현재) ⭐⭐⭐
- 이미 테스트됨
- Stable baseline

**3순위**: **Kosmos-2 Scratch + LoRA** ⭐⭐
- Task-specific
- More data needed

---

**결론**: 
> **OXE Pretrained로 실험해볼 가치 있음**  
> **하지만 Google Robot도 LoRA 추가하면 충분히 좋을 것**

둘 다 시도해보고 비교하는 것이 가장 확실한 방법입니다! 🎯
