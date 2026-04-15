# Poetry 환경에서 VLA 추론 실행 가이드

## Poetry 환경 정보
- **환경 경로**: `/home/billy/.cache/pypoetry/virtualenvs/robovlms-ASlHafON-py3.10`
- **Python**: 3.10.12
- **프로젝트**: RoboVLMs_upstream

## 빠른 실행 명령어

### 1. 환경 변수 설정
```bash
export PATH="/home/billy/.local/bin:$PATH"
export POETRY_PYTHON=/home/billy/.cache/pypoetry/virtualenvs/robovlms-ASlHafON-py3.10/bin/python
export VLA_CHECKPOINT_PATH="/home/billy/25-1kp/vla/RoboVLMs_upstream/runs/mobile_vla_kosmos2_right_only_20251207/kosmos/mobile_vla_finetune/2025-12-07/mobile_vla_kosmos2_right_only_20251207/last.ckpt"
```

### 2. Poetry로 실행
```bash
cd /home/billy/25-1kp/vla/RoboVLMs_upstream
poetry run python ../test_inference_stepbystep.py
```

### 3. 직접 Python 실행
```bash
cd /home/billy/25-1kp/vla
$POETRY_PYTHON test_inference_stepbystep.py
```

### 4. 기존 inference_abs_action.py 사용
```bash
cd /home/billy/25-1kp/vla
$POETRY_PYTHON scripts/inference_abs_action.py \
    --checkpoint "$VLA_CHECKPOINT_PATH" \
    --image test_images/sample.jpg \
    --text "Navigate to the left bottle"
```

## API 서버 실행

```bash
cd /home/billy/25-1kp/vla
$POETRY_PYTHON api_server.py
```

## 주의사항

1. **항상 Poetry 환경 사용**: RoboVLMs 관련 코드는 반드시 Poetry Python 사용
2. **의존성 충돌**: 시스템 Python과 Poetry Python을 섞어 쓰지 말 것
3. **체크포인트 경로**: 환경 변수로 관리

## 트러블슈팅

### 패키지가 없다는 에러
```bash
cd RoboVLMs_upstream
poetry install  # pyproject.toml 기반 설치
```

### torch wheel경고
- pyproject.toml의 wheel 경로 무시 (시스템 torch 사용 중)
- 문제 없으면 그대로 진행

## 작성일
2025-12-09
