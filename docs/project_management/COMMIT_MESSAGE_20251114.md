# 커밋 메시지: Mobile VLA LoRA 파인튜닝 구조 완성

## 주요 변경사항

### 1. Config 수정 (RoboVLMs 기본값 적용)
- `window_size`: 4 → 8 (RoboVLMs 기본값)
- `action_dim`: 7 → 2 (2D navigation)
- `act_head` 내부 설정 유지

### 2. 데이터셋 구조 수정 (DiskCalvinDataset 구조 준수)
- `__getitem__`: 18프레임 로드 (window_size + fwd_pred_next_n)
- 액션을 시퀀스 형태로 반환: `(18, 2)`
- `collater`: unfold 방식으로 chunk 생성
- 반환 키: DiskCalvinDataset과 동일 (`'actions'`, `'lang'`, etc.)

### 3. 액션 처리 개선
- 7D 패딩 제거, 2D 액션 그대로 사용
- 정규화: `torch.clamp(actions_tensor, -1.0, 1.0)`

### 4. text_fn 초기화 추가
- `tokenizer`, `tokenizer_config`에서 `text_fn` 생성
- kosmos tokenizer 지원

### 5. 문서화
- `PROJECT_CENTRAL_KNOWLEDGE_BASE.md`: 중앙 지식 베이스 생성
- `ROBOVLMS_STRUCTURE_ANALYSIS_20251114.md`: RoboVLMs 구조 분석
- `CORE_PATTERN_ANALYSIS_20251114.md`: Core 패턴 분석
- `TRAJECTORY_ANALYSIS_20251114.md`: Trajectory 분석
- `CODE_REVIEW_MOBILE_VLA_20251114.md`: 코드 리뷰

## 핵심 발견사항

1. **18프레임 수집 의도 확인**
   - RoboVLMs 기본 설정: window_size=8, fwd_pred_next_n=10
   - 18프레임 = 8 + 10 (정확히 일치)
   - 데이터 수집 시점부터 RoboVLMs 구조 고려

2. **데이터셋 구조 호환성**
   - DiskCalvinDataset 구조 완전 준수
   - unfold 방식으로 chunk 생성 (generate_chunck_data 대신)

3. **Core 패턴 분석**
   - 5개 고유 패턴 발견
   - 주요 패턴 일관성: 88.8%
   - 파인튜닝에 문제 없음

## 영향 범위

- Config: `Mobile_VLA/configs/mobile_vla_20251114_lora.json`
- 데이터셋: `RoboVLMs_upstream/robovlms/data/mobile_vla_h5_dataset.py`
- 문서: 여러 분석 및 가이드 문서 추가

## 테스트 상태

- Config 검증 완료
- 데이터셋 구조 검증 완료
- 코드 리뷰 완료
- 실제 학습 실행은 다음 단계

