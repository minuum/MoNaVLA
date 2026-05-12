# Plan: Exp52 — Language-Conditioned Visual Features (True VLA)
작성일: 2026-05-12

---

## 1. 목표

**현재 문제 (Exp49):**
- `model.vision_model(image_only)` → 1024-dim feature (언어 영향 없음)
- 언어는 episode 시작 시 goal_cx0(3-dim)으로만 관여, 이후 MLP에 언어 없음

**달성 목표:**
- `model(image + text)` joint forward → LM last hidden state의 image token 추출 → 2048-dim
- 이 feature는 Kosmos-2 LM의 self-attention을 거쳐 **언어가 이미지를 어떻게 보는지에 영향**
- 이것이 True VLA의 핵심 조건: 언어가 visual feature 추출 과정 자체에 참여

**검증 질문:**
- Exp49 대비 val acc가 오르는가?
- paraphrase robustness: 다른 표현으로도 같은 행동이 나오는가?
- Exp47(fingerprinting 74%)과 구조적으로 다른가?

---

## 2. 왜 이게 True VLA인가

```
Exp46/49 (언어 독립):
  vision_model(image) → 1024-dim
  언어는 goal_cx0으로만 참여

Exp47 (fingerprinting):
  text_embed(instruction) → 2048-dim (문장 패턴 암기)
  언어 이해 없음, paraphrase 74%

Exp52 (True VLA):
  full_kosmos2(image + text) → LM last hidden state
  image_embeds_position_mask로 64개 image token 추출
  → mean pool → 2048-dim (언어가 이미지 처리에 영향)

핵심: Kosmos-2 LM의 self-attention에서
  text token ←→ image token 이 서로 어텐드함
  → image token hidden state에 언어 의미가 녹아있음
  → "왼쪽 바구니"라고 하면 왼쪽 영역 image token이 강조됨
```

**실험 확인값 (방금 측정):**
```
inputs: pixel_values, input_ids(seq_len=76), image_embeds_position_mask
image token count: 64개 (positions 2~65)
LM last hidden: (1, 76, 2048)
image token hidden: (64, 2048) → mean → (2048,) ← 이게 Exp52의 vision feat
```

---

## 3. 아키텍처

```
[에피소드 시작]
  instruction → processor → input_ids
  frame_0 + instruction → Kosmos-2 joint → goal_cx0 (grounding, 3-dim)

[매 타임스텝 t]
  frame_t + instruction → Kosmos-2 joint forward
    → out.hidden_states[-1]        # (1, 76, 2048)
    → mask = image_embeds_position_mask[0].bool()
    → img_tokens = hidden[0][mask]  # (64, 2048)
    → vis_feat = img_tokens.mean(0) # (2048,)  ← language-conditioned!

  bbox_history(window=8) = [cx,cy,area,has_bbox] × 8 = 32-dim

[MLP 입력]
  [bbox_history(32) + lang_vis(2048) + goal(3)] = 2083-dim

[MLP 구조]
  2083 → 512 → 256 → 128 → 64 → 8 (action)
  (Exp49와 동일 구조, d_in만 1059→2083)
```

---

## 4. Exp47과의 차이 (왜 fingerprinting이 아닌가)

| 항목 | Exp47 (fingerprinting) | Exp52 (language-conditioned) |
|------|----------------------|------------------------------|
| 입력 | text만 encode → 2048-dim | image + text jointly → image token hidden |
| 언어 역할 | "경로 label" 역할 | 이미지를 어떻게 볼지 결정 |
| paraphrase 예측 | 표현 바뀌면 vector 달라짐 → 74% | 시각적 attention이 결정 → 이론상 강인 |
| MLP이 학습하는 것 | 고정 문장 패턴 | 언어에 의해 변조된 visual scene |

---

## 5. 데이터 파이프라인

### 5.1 에피소드별 instruction (path_type 기반)

```python
INSTRUCTIONS = {
    "center_straight": "Navigate straight ahead to the basket in the center",
    "center_left":     "Navigate to the basket on the left",
    "center_right":    "Navigate to the basket on the right",
    "left_straight":   "Turn left and navigate straight to the basket",
    "left_left":       "Turn left and go to the basket on the left side",
    "left_right":      "Turn left then right to reach the basket",
    "right_straight":  "Turn right and navigate straight to the basket",
    "right_left":      "Turn right then left to reach the basket",
    "right_right":     "Turn right and go to the basket on the right side",
}
```

기존 Exp49의 goal_cx0 grounding도 유지 (Exp49 bbox_dataset_full.json 재사용).

### 5.2 feature 추출 (사전 캐싱)

```python
# 입력: bbox_dataset_full.json (150 ep, 2626 frames)
# 출력: lang_vis_features_exp52.npz (ep_path → np.ndarray (N_frames, 2048))

proc = AutoProcessor.from_pretrained('.vlms/kosmos-2-patch14-224')
model = AutoModelForVision2Seq.from_pretrained(
    '.vlms/kosmos-2-patch14-224', torch_dtype=torch.float16
).cuda().eval()

for ep in episodes:
    instr = INSTRUCTIONS[ep['path_type']]
    imgs = load_episode_images(ep)
    feats = []
    for img in imgs:
        inputs = proc(text=instr, images=img, return_tensors='pt').to('cuda')
        with torch.no_grad():
            out = model(**inputs, output_hidden_states=True)
        hs = out.hidden_states[-1]                            # (1, 76, 2048)
        mask = inputs['image_embeds_position_mask'][0].bool() # (76,)
        feat = hs[0][mask].mean(0).float().cpu().numpy()     # (2048,)
        feats.append(feat)
    cache[ep_path] = np.stack(feats)  # (N_frames, 2048)
```

**예상 추출 시간:** 2626 frames × ~0.5s = ~22분

### 5.3 MLP 학습 (Exp49와 동일 구조)

- 입력: 2083-dim (32 + 2048 + 3)
- Exp49 bbox_dataset_full.json, goal 3-dim 재사용
- 학습: 300 epochs, AdamW, CosineAnnealingLR

---

## 6. 평가

### 6.1 baseline 비교

| 실험 | 입력 | val acc | paraphrase |
|------|------|---------|-----------|
| Exp46 | bbox+vis(1024) | 93.2% | — |
| Exp47 | +text_embed(2048) | 98.7% | 74.1% ❌ |
| Exp49 | +goal_cx0(3) | 96.4% | 100% ✅ |
| **Exp52** | **lang_vis(2048)+goal(3)** | **?** | **?** |

### 6.2 paraphrase 테스트

Exp49와 동일한 방식: 9 path_type × 5 표현 = 45개 테스트
- 단, 다른 표현으로 feature를 **새로 추출** (캐시 없이 on-the-fly)
- 같은 action이 나오면 → 진짜 language generalization
- 같은 action이 나오지 않으면 → 여전히 visual feature fingerprinting

---

## 7. 구현 단계

- [x] Step 1: `scripts/extract_lang_vis_features_exp52.py` — feature 추출 스크립트
- [x] Step 1b: `scripts/train_v5_exp52_true_vla.py` — MLP 학습 스크립트
- [ ] Step 2: feature 추출 실행 (150 ep × all frames, ~22분)
- [ ] Step 3: `scripts/train_v5_exp52_true_vla.py` — MLP 학습
- [ ] Step 4: val acc 평가
- [ ] Step 5: paraphrase robustness 테스트
- [ ] Step 6: 결과 문서화 (`docs/v5/bbox_nav_exp52/`)

---

## 8. 리스크

| 리스크 | 가능성 | 대응 |
|--------|--------|------|
| visual feature가 여전히 언어와 무관 | 중간 | 실험 전에 두 instruction의 feature cosine sim 비교로 확인 |
| paraphrase 여전히 낮음 | 중간 | goal_cx0 path가 백업으로 작동하므로 baseline 이하는 안 됨 |
| val acc Exp49보다 낮음 | 낮음 | 2048-dim이 더 많은 정보 — 낮을 이유 없음 |
| OOM (joint forward 부담) | 낮음 | float16, batch=1, 캐싱 방식이라 inference만 함 |

---

## 9. 선행 검증 (구현 전)

두 instruction으로 같은 이미지를 넣었을 때 feature 차이 확인:

```python
feat_left  = extract(img, "Navigate to the basket on the left")
feat_right = extract(img, "Navigate to the basket on the right")
feat_para  = extract(img, "Go to the container on the left side")  # paraphrase

cos_sim_lr = cosine(feat_left, feat_right)  # 기대: 낮음 (다른 지시)
cos_sim_pp = cosine(feat_left, feat_para)   # 기대: 높음 (같은 의미)
```

- cos_sim_lr << cos_sim_pp → 언어가 visual feature에 차별적으로 영향 → Exp52 진행 가치 있음
- cos_sim_lr ≈ cos_sim_pp → 언어 영향 없음 → 접근 수정 필요

**승인 후 구현 시작.**
