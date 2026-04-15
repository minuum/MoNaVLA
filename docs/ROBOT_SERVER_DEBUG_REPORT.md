# 🤖 로봇 서버 디버깅 리포트 및 수정 요청서

**작성일**: 2026-02-16  
**대상**: 로봇 서버 (`inference_server.py`)  
**상태**: ⚠️ 부분 개선되었으나, **INT8 양자화**로 인해 성능 저하 지속됨.

---

## 1. 현재 상태 분석 (Log Analysis)

원격 서버 로그(`vla-inference-gradio`) 분석 결과입니다.

| 항목 | 상태 | 분석 결과 |
| :--- | :--- | :--- |
| **입력 데이터** | ✅ **정상** | `tok_seq shape: [1, 8, ...]` 확인됨. 히스토리 버퍼(Window=8)는 정상 동작 중. |
| **모델 로딩** | ❌ **비정상** | `Model loaded with BitsAndBytes INT8` 로그 확인. <br>→ **직진 편향(`lx=0.98`)의 직접적인 원인.** |
| **설정 파일** | ⚠️ **경고** | `Config path ... not found` 발생. HuggingFace 기본 설정 사용 중. <br>→ 토크나이저 불일치 가능성 존재. |

---

## 2. 핵심 문제: 왜 아직도 직진만 하는가?

### 🔴 범인: `BitsAndBytes INT8`
로그에서 확인된 `lx=0.98, ly=-0.01` 출력 패턴은 전형적인 **Mode Collapse(모드 붕괴)** 현상입니다.
*   학습은 정밀한 **BF16 (BFloat16)**으로 이루어졌습니다.
*   이를 억지로 **INT8**로 구겨 넣으면, 모델은 가장 안전하고 빈도가 높은 행동(직진)만 선택하게 됩니다.
*   히스토리 버퍼가 있어도, 뇌(모델 가중치)가 손상되었기 때문에 제대로 된 판단을 못하는 것입니다.

---

## 3. 수정 요청 사항 (Action Items)

다음 코드를 `inference_server.py`의 `_load_model` 함수에 적용해 주십시오.

### ① INT8 비활성화 및 BF16 적용 (필수)
기존 `BitsAndBytesConfig` 코드를 주석 처리하고, 아래와 같이 변경해야 합니다.

```python
# ---------------------------------------------------------
# ❌ [삭제 또는 주석 처리] 기존 INT8 설정
# ---------------------------------------------------------
# bnb_config = BitsAndBytesConfig(
#     load_in_8bit=True,
#     ...
# )
# self.model = MobileVLATrainer(..., quantization_config=bnb_config)

# ---------------------------------------------------------
# ✅ [추가] BF16 / FP16 표준 로딩
# ---------------------------------------------------------
logger.info("🔧 Loading Model in Native Precision (BF16/FP16)...")

# 1. 모델 초기화 (No Quantization Config)
self.model = MobileVLATrainer(self.config)

# 2. 체크포인트 로드
checkpoint = torch.load(self.checkpoint_path, map_location='cpu')
state_dict = checkpoint.get('state_dict', checkpoint.get('model_state_dict', checkpoint))
self.model.load_state_dict(state_dict, strict=False)

# 3. GPU 이동 및 정밀도 변환
self.model.to(self.device)
self.model.eval()

# Ampere GPU(Orin, RTX 30/40)라면 BF16 권장
if torch.cuda.is_bf16_supported():
    self.model = self.model.bfloat16()
    logger.info("✅ Converted to BFloat16 (Recommended for V2)")
else:
    self.model = self.model.half()
    logger.info("✅ Converted to Float16")
```

### ② Config 경로 확인 (권장)
로그의 `⚠️ Config path ... not found` 경고를 없애기 위해, 로컬에 저장된 토크나이저 경로를 명시해주는 것이 좋습니다.
- 만약 로컬 경로가 없다면, 현재처럼 HuggingFace에서 받아오되 `Special Token`(`action_token`)이 잘 추가되었는지 확인이 필요합니다. (로그상 `Special tokens added`가 뜨므로 당장은 괜찮아 보임)

---

## 4. 예상 결과
위 수정(`INT8 제거`)이 적용되면:
1.  메모리 사용량은 약 **1.8GB (INT8)** → **3.5GB (BF16)** 정도로 증가합니다. (Jetson Orin에서 충분히 감당 가능)
2.  출력 액션(`lx`, `ly`)이 `0.98` 고정이 아니라, 상황에 따라 `0.0`(정지), `0.5`(서행), `ly=0.5`(좌회전) 등으로 **다양하게 변화**할 것입니다.
