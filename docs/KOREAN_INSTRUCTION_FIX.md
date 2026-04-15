# Korean Instruction Fix - Quick Start Guide

## 변경 사항 요약

**문제**: 학습 시 한국어 instruction을 사용했으나, 추론/테스트 코드는 영어를 사용하여 성능 저하 발생

**해결**: 모든 추론 코드를 학습 데이터와 일치하도록 한국어 instruction 사용

## 수정된 파일

### 1. 새로 생성된 파일
- `Mobile_VLA/instruction_mapping.py` - 한국어 instruction 중앙 관리 모듈
- `scripts/inference_node_korean.py` - 한국어 기반 standalone 추론 노드  
- `scripts/test_korean_instruction.py` - 종합 검증 테스트

### 2. 수정된 파일
- `test_inference_stepbystep.py` - Line 72, 113
- `scripts/inference_abs_action.py` - Line 35
- `test_quick.py` - Line 33 (전체 재작성)
- `src/robovlms_mobile_vla_inference.py` - Line 49 (docstring)

## 사용법

### 추론 노드 실행 (Left scenario)
```bash
python3 scripts/inference_node_korean.py --scenario 1
```

### 추론 노드 실행 (Right scenario)
```bash
python3 scripts/inference_node_korean.py --scenario 2
```

### 종합 테스트 실행
```bash
python3 scripts/test_korean_instruction.py
```

## Instruction 매핑

| Scenario ID | Instruction (Korean) |
|-------------|---------------------|
| '1' (left)  | "가장 왼쪽 외곽으로 돌아 컵까지 가세요" |
| '2' (right) | "가장 오른쪽 외곽으로 돌아 컵까지 가세요" |

## 검증 결과 확인

### 1. 데이터로더 일치성
```python
from robovlms.data.mobile_vla_action_dataset import MobileVLAActionDataset
ds = MobileVLAActionDataset(data_dir='...', model_name='kosmos')
sample = ds[0]
# sample의 instruction이 한국어인지 확인
```

### 2. 추론 결과 확인
- Left (scenario '1'): `linear_y > 0` (양수 회전)
- Right (scenario '2'): `linear_y < 0` (음수 회전)

## 다음 단계

로봇 실물 테스트 시:
1. `Mobile_VLA/instruction_mapping.py`의 `get_instruction_for_robot_id()` 사용
2. 로봇 노드에서 시나리오 ID ('1', '2')로 instruction 자동 변환
3. Billy 서버 API로 요청 전송

## 참고 코드

```python
from Mobile_VLA.instruction_mapping import get_instruction_for_robot_id

# 로봇 시나리오 ID → 한국어 instruction
scenario_id = '1'  # From robot controller
instruction = get_instruction_for_robot_id(scenario_id)
# Returns: "가장 왼쪽 외곽으로 돌아 컵까지 가세요"
```
