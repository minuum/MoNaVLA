# Instruction Flow 분석: 한국어 vs 영어 Instruction

**작성일**: 2026-01-07  
**목적**: Instruction이 학습/추론 파이프라인에서 실제로 전달되는지 환각 없이 코드 분석

---

## 📋 요약

### 현재 상태
- **학습 데이터**: ✅ **한국어 instruction 사용** (확인됨)
- **추론 파이프라인**: ✅ **Instruction 실제로 모델에 전달** (확인됨)
- **구조적 문제**: ⚠️ **중복 정의 및 문서 불일치**

### 핵심 발견
1. **Instruction은 실제로 모델에 전달되고 있음** ✅
2. **학습 시 한국어, 추론 시도 한국어 사용 가능** ✅
3. **BUT**: Dataset loader에 중복 정의 존재 (line 48-57 vs 151-160)
4. **BUT**: 상충하는 문서들 존재 (한국어 유지 vs 영어 변경)

---

## 🔍 코드 흐름 분석 (환각 없이)

### 1. **학습 데이터 로더** 
**파일**: `RoboVLMs_upstream/robovlms/data/mobile_vla_action_dataset.py`

#### 문제: 중복 정의
```python
# Line 48-57: 첫 번째 정의 (사용 안 됨)
self.scenario_instructions = {
    "1box_vert_left": "박스 1개 장애물, 가장 왼쪽 외곽으로 돌아 컵까지 가세요",  # ❌ 사용 안 됨
    ...
}

# Line 151-160: 실제 사용되는 정의
self.scenario_instructions = {
    "1box_vert_left": "가장 왼쪽 외곽으로 돌아 컵까지 가세요",  # ✅ 실제 사용
    "1box_vert_right": "가장 오른쪽 외곽으로 돌아 컵까지 가세요",
    "1box_hori_left": "가장 왼쪽 외곽으로 돌아 컵까지 가세요",
    "1box_hori_right": "가장 오른쪽 외곽으로 돌아 컵까지 가세요",
    "2box_vert_left": "가장 왼쪽 외곽으로 돌아 컵까지 가세요",
    "2box_vert_right": "가장 오른쪽 외곽으로 돌아 컵까지 가세요",
    "2box_hori_left": "가장 왼쪽 외곽으로 돌아 컵까지 가세요",
    "2box_hori_right": "가장 오른쪽 외곽으로 돌아 컵까지 가세요",
}
```

#### Instruction이 데이터에 포함되는 방법
```python
# Line 258-260
scenario = self._extract_scenario(str(episode_name))
task_description = self.scenario_instructions.get(scenario, "컵까지 가세요")

# Line 266-272: batch_transform 호출
return self.batch_transform(
    task_description=task_description,  # ← 한국어 instruction 전달 ✅
    action=padded_actions,
    episode_mask=episode_mask,
    images=images,
    gripper_images=None,
)
```

**✅ 확인**: `task_description` (한국어)이 `batch_transform`을 통해 데이터셋에 포함됨

---

### 2. **추론 파이프라인**
**파일**: `Mobile_VLA/inference_pipeline.py`

#### Instruction 전달 흐름

```python
# Line 137-141: predict() 메서드 정의
def predict(self, image: Image.Image, instruction: str) -> dict:
    """
    Args:
        instruction: Language instruction  # ← 입력 파라미터 ✅
    """
```

#### 실제 모델에 전달되는 부분
```python
# Line 167-179: Instruction을 tokenize
from transformers import AutoProcessor
processor = AutoProcessor.from_pretrained(
    self.config['tokenizer']['pretrained_model_name_or_path'],
    trust_remote_code=True
)

encoded = processor.tokenizer(
    instruction,  # ← 한국어/영어 instruction 여기서 tokenize ✅
    return_tensors='pt',
    padding='max_length',
    max_length=self.config['tokenizer']['max_text_len'],
    truncation=True
).to(self.device)

# Line 182-186: 모델의 inference() 메서드에 전달
outputs = self.trainer.model.inference(
    vision_x=image_tensor,
    lang_x=encoded['input_ids'],  # ← Tokenized instruction ✅
    attention_mask=encoded['attention_mask']
)
```

**✅ 확인**: Instruction이 tokenize되어 `lang_x`로 모델에 실제로 전달됨

---

### 3. **Instruction Mapping 모듈**
**파일**: `Mobile_VLA/instruction_mapping.py`

#### 목적
- 로봇 시나리오 ID ('1', '2') → 한국어 instruction 변환
- Dataset loader와 동일한 instruction 사용 보장

```python
# Line 9-18: 학습 데이터와 동일한 한국어 instruction
SCENARIO_INSTRUCTIONS_KO = {
    "1box_vert_left": "가장 왼쪽 외곽으로 돌아 컵까지 가세요",
    "1box_vert_right": "가장 오른쪽 외곽으로 돌아 컵까지 가세요",
    "1box_hori_left": "가장 왼쪽 외곽으로 돌아 컵까지 가세요",
    "1box_hori_right": "가장 오른쪽 외곽으로 돌아 컵까지 가세요",
    ...
}

# Line 66-80: 로봇 ID → Instruction 변환 함수
def get_instruction_for_robot_id(robot_scenario_id: str) -> str:
    """
    Args:
        robot_scenario_id: '1' (left) or '2' (right)
    Returns:
        학습 시 사용된 한국어 instruction
    """
    return get_instruction_for_scenario(robot_scenario_id)
```

**✅ 확인**: Dataset loader의 instruction과 정확히 일치

---

### 4. **테스트 스크립트들**
**파일**: `scripts/inference_node_korean.py`, `scripts/test_korean_instruction.py`

#### `inference_node_korean.py` 흐름

```python
# Line 41: Instruction 가져오기
instruction = get_instruction_for_robot_id(scenario_id)  # ← "가장 왼쪽..." 

# Line 68: Pipeline의 predict() 호출
result = pipeline.predict(image, instruction)  # ← 한국어 instruction 전달 ✅
```

**✅ 확인**: 한국어 instruction이 pipeline을 통해 모델에 전달됨

---

## 📊 문제점 정리

### 1. **중복 정의 (Dataset Loader)**
**파일**: `mobile_vla_action_dataset.py`

| 위치 | 내용 | 사용 여부 |
|------|------|-----------|
| Line 48-57 | 첫 번째 정의 (상세 설명 포함) | ❌ 사용 안 됨 (Line 151에서 재정의) |
| Line 151-160 | 두 번째 정의 (간결한 버전) | ✅ **실제 사용** |

**문제**: 
- 첫 번째 정의가 `super().__init__()` 전에 있어야 해서 정의했지만
- 실제로는 Line 151의 두 번째 정의가 사용됨
- **혼란 야기**

### 2. **상충하는 문서**

| 문서 | 주장 | 작성일 |
|------|------|--------|
| `KOREAN_INSTRUCTION_FIX.md` | 한국어 instruction 유지 | 최근 |
| `INSTRUCTION_CHANGE_20260107.md` | 영어 instruction으로 변경 제안 | 2026-01-07 |

**문제**:
- 두 문서가 정반대 방향 제시
- 어떤 것이 최종 결정인지 불명확

---

## 🎯 해결 방안

### 옵션 1: 한국어 Instruction 유지 (현재 상태 정리)

#### 장점
- ✅ 재학습 불필요
- ✅ 현재 모델 바로 사용 가능
- ✅ 빠른 배포 가능

#### 단점
- ❌ Kosmos-2는 영어 중심 pre-training
- ❌ 한국어 semantic understanding 약할 가능성
- ❌ VLA 논문 표준과 불일치

#### 필요한 작업
1. **Dataset loader 정리**
   ```python
   # Line 48-57 삭제
   # Line 151-160만 유지하고, Line 62 이전으로 이동
   ```

2. **문서 정리**
   - `KOREAN_INSTRUCTION_FIX.md` 유지
   - `INSTRUCTION_CHANGE_20260107.md` archived 폴더로 이동

3. **검증**
   ```bash
   python3 scripts/test_korean_instruction.py
   ```

---

### 옵션 2: 영어 Instruction으로 변경 및 재학습

#### 장점
- ✅ Kosmos-2 VLM과 호환성 우수
- ✅ VLA 논문 표준 준수 (OpenVLA, RT-2)
- ✅ Instruction grounding 성능 향상 기대

#### 단점
- ❌ 재학습 필요 (30-60분)
- ❌ 검증 시간 필요
- ❌ 기존 체크포인트 무효화

#### 필요한 작업

##### 1. Dataset Loader 수정
```python
# RoboVLMs_upstream/robovlms/data/mobile_vla_action_dataset.py
# Line 48-57 삭제
# Line 151-160을 영어로 변경

self.scenario_instructions = {
    "1box_vert_left": "Navigate around the obstacle on the left side and reach the cup",
    "1box_vert_right": "Navigate around the obstacle on the right side and reach the cup",
    "1box_hori_left": "Navigate around the obstacle on the left side and reach the cup",
    "1box_hori_right": "Navigate around the obstacle on the right side and reach the cup",
    "2box_vert_left": "Navigate around the obstacle on the left side and reach the cup",
    "2box_vert_right": "Navigate around the obstacle on the right side and reach the cup",
    "2box_hori_left": "Navigate around the obstacle on the left side and reach the cup",
    "2box_hori_right": "Navigate around the obstacle on the right side and reach the cup",
}
```

##### 2. Instruction Mapping 수정
```python
# Mobile_VLA/instruction_mapping.py
SCENARIO_INSTRUCTIONS_EN = {
    "1box_vert_left": "Navigate around the obstacle on the left side and reach the cup",
    "1box_vert_right": "Navigate around the obstacle on the right side and reach the cup",
    ...
}
```

##### 3. 재학습
```bash
bash scripts/train_active/train_english_chunk5.sh
```

##### 4. 검증
```bash
# Ablation test (핵심)
python3 scripts/test_english_inference.py --checkpoint <CKPT> --scenario ablation

# Left/Right test
python3 scripts/test_english_inference.py --checkpoint <CKPT> --scenario left
python3 scripts/test_english_inference.py --checkpoint <CKPT> --scenario right
```

---

## 📌 추천 (Billy의 의견)

### **단기 (즉시)**: 옵션 1 - 한국어 유지 + 코드 정리
**이유**:
1. 빠른 검증 및 배포 가능
2. 현재 모델이 작동하는지 먼저 확인 필요
3. Instruction 무시 문제인지, 언어 문제인지 분리 필요

**작업**:
```bash
# 1. Dataset loader 중복 제거
# 2. 한국어 instruction으로 ablation test
python3 scripts/test_korean_instruction.py

# 3. 결과에 따라 다음 단계 결정
```

### **중기 (검증 후)**: 옵션 2 - 영어로 변경
**조건**: 위 테스트에서 instruction이 무시되는 것으로 판명되면

**이유**:
1. VLA 논문 표준 준수
2. Kosmos-2 VLM 호환성
3. 향후 확장성 (multilingual transfer learning)

---

## 🔧 즉시 해야 할 작업

### 1. **중복 정의 제거**
**파일**: `RoboVLMs_upstream/robovlms/data/mobile_vla_action_dataset.py`
- Line 48-57 삭제
- Line 151-160을 Line 60 근처로 이동 (한 번만 정의)

### 2. **Ablation Test 실행**
현재 한국어 instruction이 실제로 작동하는지 확인:

```bash
python3 scripts/test_korean_instruction.py
```

**기대 결과**:
- LEFT instruction → `linear_y > 0` (양수)
- RIGHT instruction → `linear_y < 0` (음수)

**만약 실패하면**:
- Instruction이 무시되는 것 → 옵션 2 (영어로 변경) 진행

**만약 성공하면**:
- 한국어 instruction 사용 가능 확인
- 로봇 배포 진행

---

## 📁 관련 파일

### 코드
- `RoboVLMs_upstream/robovlms/data/mobile_vla_action_dataset.py` - Dataset loader ⚠️ 중복 정의
- `Mobile_VLA/inference_pipeline.py` - 추론 파이프라인 ✅ Instruction 전달 확인
- `Mobile_VLA/instruction_mapping.py` - Instruction 매핑 ✅ 일관성 확인

### 테스트 스크립트
- `scripts/test_korean_instruction.py` - 종합 검증 테스트
- `scripts/inference_node_korean.py` - Standalone 추론 노드
- `scripts/validate_left_right_data.py` - 데이터 검증

### 문서
- `docs/KOREAN_INSTRUCTION_FIX.md` - 한국어 유지 방안
- `docs/INSTRUCTION_CHANGE_20260107.md` - 영어 변경 제안
- `docs/INSTRUCTION_FLOW_ANALYSIS.md` - **이 문서** (흐름 분석)

---

## ✅ 검증 체크리스트

### 코드 검증 (환각 없이)
- [x] Dataset loader에서 instruction이 `batch_transform`에 전달됨
- [x] `batch_transform`이 instruction을 포함시킴
- [x] Inference pipeline이 instruction을 tokenize함
- [x] Tokenized instruction이 `lang_x`로 모델에 전달됨
- [x] `instruction_mapping` 모듈이 dataset loader와 일치함

### 구조 문제
- [ ] Dataset loader 중복 정의 제거
- [ ] 상충 문서 정리
- [ ] Ablation test 실행
- [ ] 최종 방향 결정 (한국어 vs 영어)

---

**Status**: 분석 완료, 즉시 조치 필요  
**Next Action**: `mobile_vla_action_dataset.py` 중복 제거 → Ablation test
