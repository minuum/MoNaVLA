# VLM 분석: 의심 포인트 및 검증 결과

**날짜**: 2025-12-07 02:45  
**목적**: VLM 출력이 왜 Left/Right를 구분하지 못하는지 분석

---

## 🔬 검증한 의심 포인트

### 의심 1: VLM이 Left/Right 이미지를 다르게 인코딩하는가?

**검증 결과**:
```
Context shape: (1, 8, 64, 2048)
Left context mean:  -0.010103
Right context mean: -0.010192
Difference:          0.000090 (매우 작음)
Cosine similarity:   0.749954 (0.75 = 25% 다름)
Max element diff:    1.892700
Mean element diff:   0.073868
```

**결론**: 
- Context vector에 **차이가 있음** (cosine 0.75 ≠ 1.0)
- 하지만 **평균값 차이는 매우 작음** (0.00009)
- **VLM은 이미지 차이를 어느 정도 인식하고 있음**

---

### 의심 2: 언어 지시문이 Context에 반영되는가?

**코드 분석 결과**:

#### encode_images() 함수 (base_backbone.py:179)
```python
def encode_images(self, images, image_sizes=None):
    # input: images: list of b,c,h,w or b,t,c,h,w
    # output: image_features: b, t, n, d
    ...
    image_features = self.model_encode_images(images)
    ...
```

**결론**: 
- `encode_images()`는 **이미지만 입력받음**
- **언어 지시문은 입력으로 받지 않음**

#### forward_continuous() 함수 (base_backbone.py:1001)
```python
def forward_continuous(
    self,
    vision_x: torch.Tensor,
    lang_x: torch.Tensor,  # ← 언어 입력
    attention_mask: torch.Tensor = None,
    ...
):
    ...
    input_embeds = self.word_embedding(lang_x)  # ← 언어 임베딩
    
    # 멀티모달 결합
    (multimodal_embeds, ...) = self.merge_multi_modal_input(
        input_embeds,  # 언어 임베딩
        vision_x,      # 이미지
        ...
    )
    
    # VLM forward
    output = self.model(
        inputs_embeds=multimodal_embeds,  # ← 언어+이미지 결합
        ...
    )
```

**결론**:
- `forward_continuous()`에서 **언어와 이미지가 결합됨**
- `multimodal_embeds`에 언어 정보가 포함됨
- **하지만** action head는 `output_hs`의 **특정 위치(action token)**만 사용

---

### 의심 3: Action Head가 언어 정보를 활용하는가?

**코드 분석 (base_backbone.py:1416-1426)**:
```python
# action_token_mask가 True인 위치의 hidden state만 사용
masked_hs = output_hs[action_token_mask]
action_hs = masked_hs.reshape(bs, seq_len, self.latent_num, -1)
```

**문제점**:
- Action head는 **action_token 위치의 hidden state만** 사용
- 이 hidden state가 **언어 정보를 충분히 반영하지 않을 수 있음**

---

### 의심 4: Context 차이가 Action 차이로 이어지는가?

**검증 결과**:
```
5개 샘플 평균:
  Context cosine similarity: 0.7353 (차이 있음)
  Action linear_y 차이:      0.0012 (차이 없음!)
```

**결론**:
- **Context에는 차이가 있지만**
- **Action 출력에는 차이가 거의 없음**
- → **Action head가 context 차이를 action으로 변환하지 못함**

---

## 🚨 핵심 발견

### 문제의 원인 추정

```
Image → VLM → Context (차이 있음) → Action Head → Action (차이 없음!)
                                       ↑
                                    문제 지점
```

**가능한 원인**:

1. **Action Head 학습 부족**
   - LSTM이 context 차이를 action 차이로 매핑하는 법을 학습하지 못함
   - 학습 데이터에서 Left/Right가 같은 비율로 있어서 평균으로 수렴

2. **Language Conditioning 약화**
   - VLM의 multimodal embedding에서 언어 정보가 action token 위치에 충분히 전달되지 않음
   - Action token은 주로 이미지 정보에 의존

3. **MSE Loss의 특성**
   - MSE Loss는 평균 예측을 선호
   - Left (+0.32)와 Right (-0.38)의 평균(≈-0.03)이 손실을 최소화

---

## 📊 데이터로 확인된 사실들

| 항목 | 값 | 해석 |
|:---|:---:|:---|
| Context cosine similarity | 0.74 | 이미지 차이 인식됨 |
| Context mean difference | 0.00009 | 평균은 거의 동일 |
| Action mean difference | 0.0012 | Action 출력 거의 동일 |
| Case 1 (Left only) output | +0.374 | Left 패턴 학습 |
| Case 4 (Right only) output | -0.466 | Right 패턴 학습 |
| Case 3 (Left+Right) output | -0.137 | 평균 수렴 |

---

## 🎯 결론

### 근본 원인

> **VLM은 이미지 차이를 인식하지만,  
> Action Head가 이 차이를 action 출력으로 변환하지 못함**

### 왜 Case 1, 4는 작동하고 Case 3은 안 되는가?

| Case | 데이터 | Action Head가 해야 할 일 |
|:---:|:---|:---|
| Case 1 | Left만 | 단순: 항상 +0.32 출력 학습 |
| Case 4 | Right만 | 단순: 항상 -0.38 출력 학습 |
| Case 3 | 둘 다 | 복잡: 언어/이미지 보고 +/-0.3 결정 |

- Case 1, 4: **단순 패턴 매핑** (항상 같은 출력)
- Case 3: **조건부 출력** 필요 (입력에 따라 다른 출력)
- MSE Loss → **평균 예측이 손실 최소화** → 평균 수렴

---

## 🔧 해결 방안

### Option 1: 언어 조건화 강화
- Action Head에 언어 임베딩 직접 전달
- Cross-attention으로 언어-action 연결

### Option 2: 분류기 추가
- Left/Right 분류기 학습
- 분류 결과에 따라 action 조정

### Option 3: 별도 모델
- Left 모델, Right 모델 분리
- 실행 시 언어 지시에 따라 모델 선택

### Option 4: Loss 함수 개선
- MSE 대신 조건부 손실 (contrastive loss 등)
- Left/Right 샘플을 명시적으로 구분

---

## 📝 교수님께 보고할 핵심 메시지

> **발견**:
> - VLM은 이미지 차이를 인식함 (context similarity 0.74)
> - 하지만 Action Head가 이 차이를 action으로 변환하지 못함
> - 결과: Left+Right 학습 시 평균으로 수렴
> 
> **원인**:
> - Action Head가 조건부 출력(언어/이미지에 따라 다른 action)을 학습하지 못함
> - MSE Loss가 평균 예측을 유도
> 
> **해결 방안**:
> - 언어 조건화 강화 또는 별도 분류기 추가 필요
