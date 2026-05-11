# Plan: Exp49 — Language-Grounded Goal Navigation (진짜 VLA)
작성일: 2026-05-11

## 1. 목표

**현재 문제:**
- Exp47: instruction = path_type별 고정 텍스트 임베딩 (2048-dim fingerprint)
- paraphrase 교체 시 PM 99.2% → 74.1% 급락 → 의미 이해 아님

**달성 목표:**
- 언어 → Kosmos-2 grounding → 기하학적 목표 위치 (cx, cy)
- 다른 표현이라도 같은 물체를 grounding하면 동일한 cx,cy → 동일한 행동
- paraphrase-robust navigation 실증 → 진짜 VLA 클레임 가능

## 2. 핵심 아이디어

```
[Exp47 — fingerprint 기반]
언어 문장 → Kosmos-2 text encoder → 2048-dim 벡터 (외운 것)
           → paraphrase 시 벡터 바뀜 → 행동 바뀜 (FAIL)

[Exp49 — grounding 기반]
"왼쪽 바구니로 가" → Kosmos-2 grounding → cx=0.35, cy=0.60
"왼편 컨테이너로 이동" → Kosmos-2 grounding → cx=0.35, cy=0.60  (같음!)
           → MLP 입력 동일 → 행동 동일 (PASS)
```

언어 변화를 기하학(위치)으로 흡수 → fingerprint 문제 해결.

## 3. 리서치 요약

### 3.1 기존 데이터 재사용 가능 여부

| 항목 | 현황 | Exp49 사용 |
|------|------|-----------|
| bbox_dataset_full.json | 150ep, 프레임별 cx/cy/area/gt_class | ✅ 그대로 |
| vision_features.npz | 150ep, 프레임별 Kosmos-2 1024-dim | ✅ 그대로 |
| instruction_embeddings.json (Exp47) | 2048-dim text embedding | ❌ 제거 |

→ **새 grounding 실행 불필요.** bbox_dataset_full.json의 frame 0 cx/cy가 "언어로 지정된 목표 위치" 역할.

### 3.2 frame 0 cx 분포 (언어-기하학 구분력 확인)

| path_type | mean_cx | std |
|-----------|---------|-----|
| left_*    | 0.35~0.39 | 0.15~0.20 |
| center_*  | 0.50      | 0.00~0.01 |
| right_*   | 0.52~0.60 | 0.05~0.14 |

**단, center_left vs center_right는 cx 동일 (0.50).** → vision_feat와 bbox_history로 구분 가능 (Exp46이 93.2% 달성한 근거).

### 3.3 모델 비교

| 모델 | d_in | 입력 구성 | val acc | CL |
|------|------|----------|---------|-----|
| Exp46 | 1056 | bbox(32) + vision(1024) | 93.2% | 100% |
| Exp47 | 3104 | bbox(32) + vision(1024) + text_emb(2048) | 98.7% | 100% |
| **Exp49** | **1059** | **bbox(32) + vision(1024) + goal(3)** | 목표 ≥93% | 목표 100% |

goal = (cx0, cy0, area0) — 에피소드 시작 프레임의 grounded 바구니 위치.

## 4. 아키텍처

```
입력:
  bbox_history   (8 × 4 = 32-dim)   ← 현재까지의 BBox 궤적
  vision_feat    (1024-dim)          ← 현재 프레임 Kosmos-2 visual feature
  goal_pos       (3-dim)             ← (cx0, cy0, area0) 에피소드 시작 grounded 위치
  ──────────────────────────────────
  합계           1059-dim

MLP (Exp46/47과 동일 깊이):
  Linear(1059→512) ReLU Dropout(0.25)
  Linear(512→256)  ReLU Dropout(0.2)
  Linear(256→128)  ReLU Dropout(0.1)
  Linear(128→64)   ReLU
  Linear(64→8)     → 8-class action
```

## 5. 학습 계획

- 각 에피소드의 frame 0에서 (cx0, cy0, area0) 추출 → 에피소드 전체에서 goal 고정
- 80/20 stratified split, seed=42 (Exp47과 동일)
- AdamW (lr=1e-3, weight_decay=1e-4), CosineAnnealingLR, epochs=300, batch=128
- class_weights: 역빈도 (Exp46/47 동일)

## 6. 검증 계획

### 6.1 PM 평가
- 목표: ≥ 93.2% (Exp46 baseline)

### 6.2 Paraphrase-Grounding 일관성 테스트 (핵심)

동일 이미지 + 다른 언어 → Kosmos-2 grounding → cx0 비교:

| 표현 | 예상 cx0 |
|------|---------|
| "The gray basket is at" (원본) | 0.35 |
| "The container on the left" | ~0.35 |
| "The gray box nearby" | ~0.35 |

→ 같은 물체, 다른 표현 → 같은 cx0 → Exp49는 같은 행동 → **paraphrase generalization PASS**

### 6.3 Closed-loop 평가
- 목표: ≥ 100% (Exp47 유지)

## 7. 실배포 추론 파이프라인

```
사용자: "왼쪽 바구니로 가"
  → 언어에서 target entity 추출: "gray basket"
  → 첫 프레임 grounding: cx0=0.35, cy0=0.60
  → goal = (0.35, 0.60, 0.05)
  → 매 스텝: MLP(bbox_hist, vision, goal) → action
```

## 8. 연구 기여 포인트

1. **언어 → 기하학 변환**: fingerprinting 대신 grounding으로 언어 변화 흡수
2. **Paraphrase-robust VLA**: 표현이 달라도 같은 목표 → 동일 행동
3. **해석 가능성**: cx0=0.35 → "왼쪽에 있음" → 왼쪽으로 이동 (블랙박스 아님)
4. **경량성**: d_in 3104 → 1059 (Exp47 대비 34%)

## 9. 리스크

| 리스크 | 가능성 | 대응 |
|--------|--------|------|
| center_left/right 혼동 | 중간 | vision_feat가 이미 구분 (Exp46 93.2%) |
| grounding 실패 (has_bbox=False) | 낮음 | fallback: (0.5, 0.5, 0.0) |
| Exp46 대비 PM 하락 | 낮음 | goal(3)은 추가 신호, 제거 신호 아님 |

## 10. 구현 단계

- [x] Step 1: `scripts/train_v5_exp49_goal_nav.py` 작성 및 학습 → val acc 96.4%
- [x] Step 2: PM 평가 → 96.4%, Bootstrap CI [94.7%, 97.9%], 5-seed 95.1%±0.7%
- [x] Step 3: paraphrase-grounding 일관성 테스트 → 34/34 (100%) action 일치
- [x] Step 4: closed-loop 평가 → SR 100%, FPE 0.081
- [x] Step 5: 이미지 로버스트니스 테스트 → 조명/색상 89~100%, crop/blur 취약
- [ ] Step 6: 결과 문서화 (commit)

## 11. 실험 맥락

```
Exp46 (93.2%, 100% CL) — bbox + vision
Exp47 (98.7%, 100% CL) — + text fingerprint [paraphrase FAIL 74.1%]
Exp49 (96.4%, 100% CL) — + grounded goal [paraphrase PASS 100%] ✅
```

---
**완료 (2026-05-11)**
