# Korean → English Instruction 변경 및 재학습 계획 (2026.01.07)

## 문제 발견

### 1. 데이터 검증 결과
**파일**: `scripts/validate_left_right_data.py` 실행 결과
```
LEFT files:  Mean linear_y = +0.3194 (좌회전) ✓
RIGHT files: Mean linear_y = -0.3833 (우회전) ✓
```
→ **데이터는 정상**

### 2. 모델 추론 테스트
**한국어 Instruction**: "가장 왼쪽 외곽으로 돌아 컵까지 가세요" (LEFT)  
**모델 출력**: `linear_y = -0.8793` (우회전)  
**문제**: LEFT instruction인데 우회전 출력 → **Instruction 무시**

### 3. 원인 분석
- Kosmos-2 VLM이 **영어 중심**으로 pre-training됨
- 한국어 tokenization은 되지만 **semantic understanding 실패**
- Frozen VLM이라 한국어 학습 불가능

### 4. 논문 조사 결과
**주요 VLA 모델**: OpenVLA, RT-2, RoboFlamingo, Octo, π0
- **모두 영어 instruction 사용**
- 한국어 학습 사례 없음
- Multilingual은 zero-shot transfer로만 지원 (성능 저하)

---

## 해결 방안

### Dataset Loader 수정
**파일**: `RoboVLMs_upstream/robovlms/data/mobile_vla_action_dataset.py`

**Before** (Korean):
```python
"1box_hori_left": "가장 왼쪽 외곽으로 돌아 컵까지 가세요"
"1box_hori_right": "가장 오른쪽 외곽으로 돌아 컵까지 가세요"
```

**After** (English):
```python
"1box_hori_left": "Navigate around the obstacle on the left side and reach the cup"
"1box_hori_right": "Navigate around the obstacle on the right side and reach the cup"
```

**근거**:
- VLA 논문 표준 (OpenVLA, RT-2)
- Kosmos-2 VLM 호환성
- Instruction grounding 개선 기대

---

## 재학습 계획

### 학습 설정
- **Script**: `scripts/train_active/train_english_chunk5.sh`
- **Config**: `Mobile_VLA/configs/mobile_vla_chunk5_20251217.json` (재사용)
- **Chunk size**: 5
- **Epochs**: 10
- **Expected time**: 30-60분

### 실행 명령
```bash
cd /home/billy/25-1kp/vla
bash scripts/train_active/train_english_chunk5.sh

# 모니터링
tail -f logs/train_mobile_vla_english_chunk5_*.log
```

---

## 검증 계획

### 1. Ablation Test (핵심)
**목적**: 모델이 instruction을 실제로 사용하는지 검증

```bash
python3 scripts/test_english_inference.py \
    --checkpoint <BEST_CKPT> \
    --scenario ablation
```

**기대 결과**:
```
LEFT instruction  → linear_y = +0.XXX (좌회전)
RIGHT instruction → linear_y = -0.XXX (우회전)
```

### 2. Scenario Test
```bash
# Left
python3 scripts/test_english_inference.py --checkpoint <CKPT> --scenario left

# Right  
python3 scripts/test_english_inference.py --checkpoint <CKPT> --scenario right
```

---

## 성공 기준

✓ **Ablation Test 통과**: LEFT/RIGHT instruction에 반대 부호 출력  
✓ **방향성 일치**: Left → +양수, Right → -음수  
✓ **Gain Correction**: 여전히 작동 (1.0 초과 값 가능)

---

## 다음 단계 (학습 성공 시)

1. **API Server 업데이트**
   - 영어 instruction 사용
   
2. **로봇 노드 업데이트**
   ```python
   INSTRUCTIONS = {
       '1': "Navigate around the obstacle on the left side and reach the cup",
       '2': "Navigate around the obstacle on the right side and reach the cup"
   }
   ```

3. **실물 테스트**
   - Jetson 배포
   - Left/Right 주행 검증

4. **논문 작성**
   - Method: 영어 instruction 사용 명시
   - "Following standard VLA practice (OpenVLA, RT-2)"

---

## 참고 문서

- `docs/MULTILINGUAL_VLA_SURVEY.md` - 논문 조사 결과
- `docs/KOREAN_INSTRUCTION_DIAGNOSIS.md` - 문제 진단
- `docs/ENGLISH_TRAINING_GUIDE.md` - 재학습 가이드
- `scripts/validate_left_right_data.py` - 데이터 검증 스크립트

---

## 변경 파일 목록

### Modified
- `RoboVLMs_upstream/robovlms/data/mobile_vla_action_dataset.py`
  - Lines 47-57, 150-160, 260: Korean → English

### Created
- `scripts/train_active/train_english_chunk5.sh` - 재학습 스크립트
- `scripts/test_english_inference.py` - 추론 테스트 + Ablation
- `scripts/validate_left_right_data.py` - 데이터 검증
- `docs/MULTILINGUAL_VLA_SURVEY.md` - VLA 논문 multilingual 조사
- `docs/KOREAN_INSTRUCTION_DIAGNOSIS.md` - 문제 진단 및 해결책
- `docs/ENGLISH_TRAINING_GUIDE.md` - 재학습 전체 가이드
- `docs/INSTRUCTION_CHANGE_20260107.md` - 이 문서

---

**Status**: 재학습 준비 완료 → 학습 시작 대기  
**Date**: 2026-01-07  
**Next Action**: `bash scripts/train_active/train_english_chunk5.sh`
