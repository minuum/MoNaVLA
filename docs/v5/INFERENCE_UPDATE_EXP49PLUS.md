# Inference Integration 업데이트 — Exp49+

**작성일**: 2026-05-22  
**대상 브랜치**: `inference-integration` / `monavla-driving`  
**참조**: `docs/v5/CHECKPOINT_REGISTRY_EXP49PLUS.json`

---

## 현재 배포 구조 (exp49)

```
proxy_inference_server.py
  └── GoalNavInferenceModel
        ├── backbone: GroundingBackend (Kosmos-2 Pure HF)
        │     → vis_feat 1024-dim + bbox(cx,cy,area)
        ├── MLP: GoalNavMLP(d_in=1059)
        │     → bbox(8×4=32) + vis(1024) + goal(3) → 512 → 64 → 8
        └── weights: runs/v5_nav/mlp/exp49/exp49_mlp.pt
```

**액션 매핑 (8-class, 모든 exp 공통):**

| idx | 이름 | ACTION_2D [lx,ly] | ACTION_3D [lx,ly,az] |
|-----|------|-------------------|----------------------|
| 0 | STOP    | [0.0,  0.0]  | [0.0,  0.0,  0.0] |
| 1 | FORWARD | [1.15, 0.0]  | [1.15, 0.0,  0.0] |
| 2 | LEFT    | [0.0,  1.15] | [0.0,  1.15, 0.0] |
| 3 | RIGHT   | [0.0, -1.15] | [0.0, -1.15, 0.0] |
| 4 | FWD+L   | [0.8,  0.8]  | [0.8,  0.8,  0.0] |
| 5 | FWD+R   | [0.8, -0.8]  | [0.8, -0.8,  0.0] |
| 6 | ROT_L   | [0.0,  0.0]  | [0.0,  0.0,  0.8] |
| 7 | ROT_R   | [0.0,  0.0]  | [0.0,  0.0, -0.8] |

> ⚠️ inference_server.py(구버전)의 9-class 공간과 **혼용 금지**

---

## Backbone 주의사항 (변경 금지)

| Backbone | 용도 | 주의 |
|----------|------|------|
| Pure HF Kosmos-2 (`.vlms/kosmos-2-patch14-224`) | exp46/49/50/51/52 feature 추출 | ✅ text generation 정상 |
| Google-robot post-train (`kosmos_ph_google-robot-post-train.pt`) | Exp11/15/17/18 (구버전) | ⛔ `generate()` 금지 — "Tin Tin..." 무한반복 |

**exp49~52는 모두 Pure HF Kosmos-2 backbone** 사용. Google-robot 혼용 시 feature 완전히 달라짐.

---

## exp49 → 다음 모델 전환 시 변경점

### exp50/51 전환 (GoalNavInferenceModel — 호환)

```python
# proxy_inference_server.py 환경변수만 교체하면 됨
# VLA_WEIGHTS_PATH=/path/to/exp50_mlp.pt 또는 exp51_mlp.pt
# d_in=1059 동일 → 코드 변경 없음
# feature 파일: exp50=flipped_features, exp51=crop_features 사전 추출 필요
```

> val_acc: exp50(0.9202) < exp51(0.9335) < exp49(0.9639) — 실이점 없어 전환 불필요

### exp52 전환 (GoalNavInferenceModel — d_in 변경)

```python
# d_in: 1059 → 2083
# vis_feat: 1024-dim → lang_vis 2048-dim (Kosmos-2 joint forward 필요)

# GroundingBackend.run() 에서 lang_vis 추출 추가 필요:
# 현재: grounding["vis_feat"] → 1024-dim image token hidden
# 필요: grounding["lang_vis_feat"] → 2048-dim (language+vision joint hidden)

# feature 파일: docs/v5/bbox_nav_exp52/lang_vis_features.npz 사전 참고
# 추출 스크립트: scripts/extract_lang_vis_features_exp52.py
```

**GoalNavInferenceModel 수정 포인트:**
```python
# __init__ 에서 d_in 체크
# _build_feature() 에서 vis_feat → lang_vis_feat 로 교체
# GroundingBackend.run() 에 lang_vis 추출 분기 추가
```

### exp54 전환 (별도 파이프라인 필요)

exp54는 **GoalNavInferenceModel 미호환** — 새 클래스 필요.

```python
class Exp54InferenceModel:
    """
    Stage1_v2(FrozenCLIPV2) + Stage2_v2(ActionMLP) 파이프라인
    
    구조:
      image → FrozenCLIPV2(vision_model + image_proj + proj_head)
             → proj_feat 256-dim
      [bbox_history(32) + proj_feat(256)] → ActionMLP(d_in=288) → 8-class
    
    로드:
      stage1_v2: runs/v5_nav/mlp/exp54/stage1_v2/stage1_v2_projs.pt
      stage2_v2: runs/v5_nav/mlp/exp54/stage2_v2/stage2_v2_mlp.pt
      backbone:  .vlms/kosmos-2-patch14-224 (Pure HF, vision_model만 사용)
    """
    def __init__(self, stage1_path, stage2_path, vlm_path, device):
        # FrozenCLIPV2 로드 (vision_model frozen)
        # ActionMLP 로드
        ...
    
    def predict(self, image_base64, instruction):
        # 1. image → FrozenCLIPV2.encode_batch() → proj_feat(256)
        # 2. bbox history → bbox_feat(32)
        # 3. concat → ActionMLP → pred_class
        ...
```

**참조 스크립트:**
- 학습: `scripts/train_exp54_stage2_v2_action.py`
- 평가: `scripts/eval_exp54_stage2_v2.py`
- closed-loop: `scripts/eval_exp54_stage2_v2_closedloop.py`

### exp53 전환 (CLIP LoRA — 미구현)

- weights: `runs/v5_nav/mlp/exp53/exp53_clip_lora.pt`
- 아키텍처: CLIP LoRA fine-tuned visual encoder
- inference 파이프라인 미작성 (val_acc 0.9468로 exp49 차순위)
- 구현 참조: `scripts/train_clip_lora_exp53.py`

---

## 체크포인트 → soda 서버 동기화

현재 체크포인트는 **minum에만 있음**. soda로 가져오려면:

```bash
# exp49 (운영 중 — 이미 있어야 함)
rsync -avz minum:/home/minum/26CS/MoNaVLA/runs/v5_nav/mlp/exp49/ \
  /home/soda/MoNaVLA/runs/v5_nav/mlp/exp49/

# exp54 stage1_v2 + stage2_v2 (stage1 586MB 제외)
rsync -avz \
  minum:/home/minum/26CS/MoNaVLA/runs/v5_nav/mlp/exp54/stage1_v2/ \
  minum:/home/minum/26CS/MoNaVLA/runs/v5_nav/mlp/exp54/stage2_v2/ \
  /home/soda/MoNaVLA/runs/v5_nav/mlp/exp54/

# feature 파일 (exp46 vis + exp52 lang_vis)
rsync -avz \
  minum:/home/minum/26CS/MoNaVLA/docs/v5/bbox_nav_exp46/ \
  minum:/home/minum/26CS/MoNaVLA/docs/v5/bbox_nav_exp52/ \
  /home/soda/MoNaVLA/docs/v5/
```

---

## 다음 액션 (우선순위 순)

1. **exp49 사용 유지** — 현재 CL 미평가. 교체 전 free 에피소드 포함 CL 재평가 권장
2. **exp55 학습** (`train_exp55_free_episodes.py`) — free 에피소드 추가 학습 (FL/FC/FR 21개)
3. **exp53 inference 구현** — val_acc 2위(0.9468). CLIP LoRA 파이프라인 작성 후 CL 평가
4. **exp54 inference 구현** — FrozenCLIPV2+ActionMLP. val_acc(0.9259)은 낮지만 구조 참신
5. **stage2_v2 재학습** — RIGHT 정확도 70%로 약함. free 에피소드 포함 시 개선 가능성
