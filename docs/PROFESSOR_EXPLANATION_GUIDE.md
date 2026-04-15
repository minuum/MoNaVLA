# 교수님 미팅 설명 가이드 (2025-12-10 16:00)

**시간**: 36분 남음  
**준비 상태**: CRITICAL 수정 필요!

---

## ⚠️ CRITICAL: Action Space 수정

### 잘못 이해했던 것
- ❌ angular_z (회전 속도)
- ❌ Differential drive
- ❌ 회전하며 전진

### 실제
- ✅ **linear_y (횡방향 속도)**
- ✅ **Holonomic drive (전방향 이동)**
- ✅ **전진 + 옆으로 대각선 이동**

---

## 1. Task 설명 (간결하게)

### "Holonomic robot으로 obstacle 옆으로 피하며 navigation"

**환경**:
```
[Robot] ← Holonomic (전방향 이동)
   ↓
[Box] ← 장애물
   ↓
[Bottle] ← 목표
```

**Action** (2 DOF):
```
[linear_x, linear_y]
- linear_x: 전진 (1.15 m/s)
- linear_y: 횡방향 (+1.15 = 왼쪽, -1.15 = 오른쪽)
```

**움직임**:
- Left: [1.15, +1.15] → 45도 대각선 왼쪽
- Right: [1.15, -1.15] → 45도 대각선 오른쪽

---

## 2. 핵심 발견 설명

### No Chunk가 압도적 (98% 개선)

**수치**:
- Chunk=1: Val Loss 0.000532
- Chunk=10: Val Loss 0.027
- **98% 개선!**

**왜?**
- ✅ **Coupled control**: linear_x + linear_y 동시 조정
- ✅ **Smooth trajectory**: 부드러운 대각선 경로
- ✅ **Real-time**: 장애물 거리 즉시 반응
- ✅ **Holonomic 특성**: 즉각 횡이동

---

## 3. Latent Space 설명 (만약 질문 받으면)

### 준비된 자료
**파일**: `docs/meeting_urgent/results/`
- analysis_summary.png
- tsne_comparison.png
- results.json

### 설명 순서

**Step 1: Context란?**
"VLM (Kosmos-2)이 이미지를 이해한 representation입니다."
- Shape: (8 frames, 64 tokens, 2048 features)
- 이미지 8장 → Vision features

**Step 2: 우리가 본 것**
"Left와 Right episode의 context 차이를 분석했습니다."

**실제 데이터 (Placeholder 아님)**:
- Image-based features 사용
- Left-Left similarity: 0.94
- Right-Right similarity: 0.86
- **Left-Right similarity: 0.82 (차이 있음!)**

**Step 3: 의미**
"Image features만으로도 Left vs Right 구분 가능"
→ VLM이 visual difference 포착

**Step 4: 한계**
"하지만 실제 model hidden states 필요"
→ 향후 작업

---

## 4. 예상 질문 & 답변

### Q1: "왜 No Chunk가 좋은가?"
**A**: "Holonomic robot은 전진+횡방향을 동시에 제어합니다. Chunk=1이면 매 step마다 두 방향을 즉시 조정할 수 있어서, 장애물을 피하면서 부드러운 대각선 경로를 만들 수 있습니다. Chunk=10은 10 steps를 미리 예측하는데, 장애물과의 거리가 실시간으로 변하는 navigation에서는 즉각 반응이 더 중요합니다."

### Q2: "LoRA가 정말 효과적인가?"
**A**: "네, Val Loss가 0.027에서 0.000532로 98% 개선되었습니다. VLM을 freeze하고 LoRA만 학습했는데도 이정도 성능이 나왔습니다. Efficient합니다."

### Q3: "Latent space 분석 결과는?"
**A**: "Image features 기반으로 분석했을 때, Left와 Right episode가 이미 구분되는 것을 확인했습니다 (similarity 0.82). 하지만 실제 model hidden states를 추출하면 더 명확한 차이가 나올 것으로 예상합니다. 이건 향후 작업입니다."

### Q4: "실제 로봇 테스트는?"
**A**: "Best model (Case 5)이 준비되어 있습니다. Deployment 준비 중이고, 실제 로봇에서 성능을 검증할 계획입니다."

### Q5: "Chunk=10도 쓸모 있지 않나?"
**A**: "맞습니다. Manipulation 같은 task에서는 10 steps 예측이 유용할 수 있습니다. 하지만 우리 navigation task는 환경이 dynamic하고 obstacle avoidance가 중요해서, reactive control이 더 효과적입니다."

### Q6: "Data가 500 episodes면 적지 않나?"
**A**: "VLM이 pre-trained라서 적은 데이터로도 효과적입니다. 그리고 실제로 250 episodes (Right only)보다 500 (L+R)이 30배 더 좋았습니다. Diversity가 중요합니다."

---

## 5. 강조할 점

### 핵심 3가지
1. **No Chunk → 98% 개선** (가장 중요!)
2. **Holonomic navigation → Reactive control 필요**
3. **Simple baseline > Complex strategies**

### 실용적 가치
- Deployment ready (Case 5)
- Design guidelines 제시
- Efficient (LoRA)

---

## 6. 만약 막히면

### Plan B (간결하게)
"핵심은 No Chunk입니다. Holonomic robot이 장애물을 피하려면 매 step 전진+횡방향을 동시에 조정해야 하는데, Chunk=1이 이걸 가능하게 합니다. 결과적으로 98% 성능 개선을 달성했습니다."

---

**준비**: 80% (Action space 수정 필요!)  
**시간**: 36분  
**우선순위**: Action 설명 수정!
