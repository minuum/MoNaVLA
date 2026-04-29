# MoNaVLA V5 학습 전략 설계

> 작성일: 2026-04-22  
> 기반 데이터: `docs/v5/bbox_truth_mini.json` (72 frames, 100% 검수 완료)

---

## 1. 배경 및 목적

### 1.1 현재 문제 분석
V5 실험(Exp26: Direct resize / Exp27: Letterbox)에서 navigation 실패가 관찰됨.  
실패 원인을 **두 가지 가설**로 분리하여 검증해야 함:

| 실패 유형 | 설명 | 판별 방법 |
|-----------|------|-----------|
| **Perception 실패** | 모델이 목표 객체를 BBox로 localize 못함 | GT bbox vs 모델 예측 IoU 측정 |
| **Policy 실패** | Localize는 했지만 잘못된 action을 출력 | visible=True + wrong action 분석 |

### 1.2 검수 데이터 요약

| 항목 | 값 |
|------|-----|
| 총 검수 프레임 | 72개 |
| target_visible=True | 54개 (75%) |
| target_visible=partial | 16개 (22%) |
| target_visible=False | 0개 |
| bbox 입력 완료 | 72/72 (100%) |
| 논리 이상 항목 | **0건** ✅ |

---

## 2. 평가 우선 (Train 전 단계)

### 2.1 Grounding 성능 평가 (즉시 실행 가능)

검수 완료된 72개 GT bbox로 **Exp26 / Exp27 모델의 grounding 정확도를 정량 비교**:

```bash
python3 scripts/eval/eval_grounding_v5.py \
    --gt_json docs/v5/bbox_truth_mini.json \
    --exp_id exp26 exp27 \
    --iou_threshold 0.3 0.5
```

**측정 지표:**
- `IoU@0.3` / `IoU@0.5` : BBox overlap 기준 grounding 성공률
- `Center distance (norm)` : 예측 중심점 vs GT 중심점 거리
- `Position accuracy` : coarse_position (left/center/right) 일치율
- `goal_near accuracy` : 근접 여부 판단 정확도

### 2.2 Policy vs Perception 분리 분석

```
target_visible=True 54개에 대해:
  ├─ grounding_success=True (IoU≥0.3): Policy 실패 분석
  └─ grounding_success=False: Perception 실패로 분류
```

---

## 3. 학습 전략

### 3.1 Phase 1: Grounding-Conditioned Fine-tuning

**목표**: 목표 객체 위치를 명시적으로 학습하도록 보조 supervision 추가

**방법**:
- `bbox_xyxy_norm` GT를 학습 시그널로 활용
- **Auxiliary BBox regression loss** 추가:
  ```
  L_total = L_action + λ_bbox * L_bbox
  ```
  - `λ_bbox` = 0.1 (초기값, ablation으로 조정)
  - `L_bbox` = smooth L1 loss on normalized bbox coordinates

**데이터 구성**:
```
training split (72 GT frames):
  - visible=True (54개): full supervision (action + bbox)
  - visible=partial (16개): action supervision만, bbox loss 하향 가중 (0.5x)
  - visible=False (2개): action supervision만
```

**구현 위치**: `models/backbone/base_backbone.py` → `_format_loss()` 수정

---

### 3.2 Phase 2: Resize Strategy 비교 실험

**Exp28 (Direct, Grounding Loss)**:
```yaml
image_size: 224
resize_mode: "direct"
aux_bbox_loss: true
lambda_bbox: 0.1
```

**Exp29 (Letterbox, Grounding Loss)**:
```yaml
image_size: 224
resize_mode: "letterbox"
aux_bbox_loss: true
lambda_bbox: 0.1
```

**비교 기준**:
- Primary: navigation PM (Perfect Match) / DM (Directional Match)
- Secondary: grounding IoU@0.3 on 72-frame eval set

---

### 3.3 Phase 3: Position-Aware Navigation Loss

target_visible & coarse_position 정보를 action prediction에 연결:

```
입력: image + text instruction + [coarse_position_token]
출력: action logits + bbox_regression

coarse_position_token:
  center → CENTER
  left   → LEFT_OBJ
  right  → RIGHT_OBJ
  (not_visible → NO_OBJ)
```

**근거**: 검수 데이터에서 `coarse_position`이 일관성 있게 레이블됨:
- center: 38개 / left: 18개 / right: 16개

---

## 4. 실험 로드맵

```
Week 1 (현재)
  ├─ [완료] 72프레임 GT 검수 (bbox_truth_mini.json)
  ├─ [진행] eval_grounding_v5.py 구현
  └─ [예정] Exp26/27 grounding 벤치마크 실행

Week 2
  ├─ Auxiliary bbox loss 구현 (models/backbone)
  ├─ Exp28 (Direct + grounding) 학습
  └─ Exp29 (Letterbox + grounding) 학습

Week 3
  ├─ Exp28/29 closed-loop evaluation
  ├─ Position-aware token 실험 (Exp30)
  └─ 최종 비교 리포트 작성
```

---

## 5. 파일 구조 및 참조

```
docs/v5/
├─ bbox_truth_mini.json          # ← GT 검수 데이터 (72 frames, 100% done)
├─ training_strategy_v5.md       # ← 본 문서
└─ bbox_nav_step1/
   └─ bbox_dataset.json          # 원본 seed 데이터

scripts/
├─ label/
│   ├─ bbox_labeler.py           # YOLO-assisted 검수 서버
│   └─ README.md                 # 검수 가이드
└─ eval/
   └─ eval_grounding_v5.py       # [구현 예정] grounding 평가 스크립트

configs/v5/
├─ exp28_direct_grounding.yaml   # [예정]
└─ exp29_letterbox_grounding.yaml# [예정]
```

---

## 6. 주요 체크포인트

| 체크 항목 | 완료 조건 |
|-----------|-----------|
| GT 검수 완료 | ✅ 72/72 done, 이상 0건 |
| Grounding 벤치마크 | IoU@0.3 결과 확보 |
| Aux loss 구현 | training loss에 bbox regression 포함 |
| Exp28/29 학습 | 각 50 epoch 이상, val loss 수렴 확인 |
| Policy 분리 분석 | perception fail vs policy fail 비율 확정 |

---

## 7. 기술 참고

- **Resize 영향**: Letterbox는 aspect ratio를 보존하지만 padding으로 인한 bbox 좌표 변환 필요 (`bbox_xyxy_norm` 재계산 로직 구현 필수)
- **LoRA fine-tuning 시 bbox head**: frozen backbone 위에 trainable adapter + bbox regression head 추가
- **GT 데이터 한계**: 72개는 통계적으로 소규모. 핵심 subset이므로 **eval 전용**으로 사용하고 train은 전체 150 에피소드 활용 권장
