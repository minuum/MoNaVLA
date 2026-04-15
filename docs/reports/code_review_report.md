# 코드 점검 보고서: VLM 및 Mobile VLA 파이프라인

**날짜**: 2025-12-07 02:55  
**목적**: 코드 문제점 및 최신화 상태 점검

---

## 🔬 점검 항목 및 결과

### 1. 데이터셋 로더 (MobileVLAH5Dataset)

**상태**: ⚠️ 일부 문제 발견

| 항목 | 상태 | 비고 |
|:---|:---:|:---|
| 에피소드 로드 | ✅ | 정상 작동 |
| 이미지 로드 | ✅ | 정상 작동 |
| 액션 로드 | ✅ | 정상 작동 |
| **언어 토크나이징** | ⚠️ | **collater에서만 처리, __getitem__에서는 더미 반환** |

**문제 코드** (mobile_vla_h5_dataset.py:196-198):
```python
# 언어 토크나이징 (더미 - collate_fn에서 실제 처리)
input_ids = torch.zeros(256, dtype=torch.long)  # ← 항상 0!
attention_mask = torch.ones(256, dtype=torch.long)
```

**영향**: 
- `__getitem__`을 직접 호출하면 토큰이 모두 0
- 학습 시에는 `collater`에서 `text_fn`이 호출되어 정상 작동

---

### 2. Action Head (MobileVLALSTMDecoder)

**상태**: ✅ 정상

| 항목 | 상태 | 비고 |
|:---|:---:|:---|
| LSTM 구조 | ✅ | LSTMDecoder 기반 |
| 입력 처리 | ✅ | (B, seq_len, latent, hidden) → (B, seq_len, hidden*latent) |
| 출력 형태 | ✅ | (B, seq_len, fwd_pred_next_n, action_dim=2) |
| Loss 계산 | ✅ | Huber Loss 사용 |

---

### 3. Loss 파이프라인

**상태**: ✅ 정상

| 플로우 | 키 이름 |
|:---|:---|
| policy_head.loss() | `{"loss_velocity": ...}` |
| _update_loss(suffix="act") | `{"loss_velocity_act": ...}` |
| base_trainer._get_loss() | `loss_velocity_act` 사용 |

---

### 4. 언어 지시문 처리

**상태**: ⚠️ 문제 발견

#### 학습 시 플로우:
```
1. main.py: GRDataModule(tokenizer=model.model.tokenizer, tokenizer_config=variant["tokenizer"])
2. gr_datamodule.py: dataset_config.update(self.kwargs)  # kwargs에 tokenizer 포함
3. MobileVLAH5Dataset.__init__: self.text_fn = get_text_function(...)  # 조건부 초기화
4. MobileVLAH5Dataset.collater: text_fn(stacked_language) 호출
```

#### 문제점:
- `text_fn`이 `None`이면 더미 토큰(0) 사용
- 학습 시에는 tokenizer가 전달되어 정상 작동
- 추론 시에는 tokenizer 전달 여부에 따라 문제 발생 가능

---

### 5. VLM Forward 경로

**상태**: ✅ 정상 (코드 구조상)

```
training_step()
    → model.forward(rgb, language, ...)
        → forward_continuous()
            → merge_multi_modal_input(input_embeds, vision_x, ...)  # 언어+이미지 결합
            → self.model(inputs_embeds=multimodal_embeds)
            → output_hs에서 action_token 위치 추출
            → act_head(action_hs)
```

---

## 🚨 발견된 문제점

### 문제 1: __getitem__ 직접 호출 시 토큰 0

**원인**: `__getitem__`에서 토크나이징을 하지 않고 더미 반환
**영향**: 테스트/디버깅 시 혼란 초래
**해결**: 주석으로 명확히 설명 또는 __getitem__에서도 토크나이징 처리

### 문제 2: Context 차이가 Action으로 이어지지 않음

**확인된 사실**:
- Context cosine similarity: 0.74 (차이 있음)
- Action 차이: 0.001 (거의 없음)

**추정 원인**:
1. Action Head가 context 차이를 action으로 변환하지 못함
2. MSE Loss가 평균 예측 유도
3. 언어 조건화가 action_token 위치에 충분히 반영 안 됨

---

## 📝 기타 점검 결과

### 버전/최신화

| 항목 | 상태 |
|:---|:---:|
| PyTorch Lightning | ✅ |
| H5PY 데이터 로드 | ✅ |
| LoRA 설정 | ✅ |
| Kosmos-2 통합 | ✅ |

### 경고 사항 없음

| 항목 | 상태 |
|:---|:---:|
| 메모리 누수 | ❌ 발견 안 됨 |
| 타입 오류 | ❌ 발견 안 됨 |
| 경로 오류 | ❌ 발견 안 됨 |

---

## 🎯 권장 조치

### 즉시 조치 필요

1. **테스트 코드 수정**: `__getitem__` 직접 테스트 시 collater 사용
2. **디버그 로그 추가**: text_fn 초기화 여부 확인 로그

### 향후 개선

1. **언어 조건화 강화**: Action Head에 언어 임베딩 직접 전달
2. **별도 분류기**: Left/Right 분류 → 적절한 action 선택
3. **Loss 개선**: Contrastive loss 등 조건부 학습 유도

---

## 📊 요약

| 영역 | 상태 | 주요 발견 |
|:---|:---:|:---|
| 데이터 로딩 | ✅ | 정상 |
| 토크나이징 | ⚠️ | collater에서만 처리 |
| Action Head | ✅ | 구조 정상 |
| Loss 계산 | ✅ | 정상 |
| VLM Forward | ✅ | 구조 정상 |
| **Action 구분** | ❌ | Context 차이 → Action 차이 X |

**핵심 결론**: 
> 코드 구조는 대체로 정상이나, **Action Head가 context의 미세한 차이를  
> action 출력으로 변환하지 못하는 것**이 핵심 문제
