#!/bin/bash
# exp04 학습 완료 후 자동 실행:
# 1. exp04 best ckpt로 텍스트 이해 테스트
# 2. 결과 출력

set -e
ROOT="/home/billy/25-1kp/MoNaVLA"
PYTHON="/home/billy/anaconda3/envs/openvla/bin/python"
LOG="/tmp/v5_exp04_post.log"

echo "======================================"
echo "exp04 학습 완료. 후속 작업 시작..."
echo "======================================"

# best ckpt 찾기
EXP04_DIR="$ROOT/runs/v5_nav/kosmos/mobile_vla_v5_exp04/2026-04-11/v5-exp04-google-robot"
BEST_CKPT=$(ls "$EXP04_DIR"/epoch_*.ckpt 2>/dev/null | sort -t= -k4 -n | head -1)

if [ -z "$BEST_CKPT" ]; then
    echo "❌ exp04 체크포인트를 찾을 수 없습니다"
    exit 1
fi

echo "✅ Best ckpt: $(basename $BEST_CKPT)"

# test_v5_text_understanding.py에 exp04 추가해서 실행
# 기존 CHECKPOINTS에 동적으로 추가하기 위해 env var로 전달
EXP04_CKPT_REL="${BEST_CKPT#$ROOT/}"

echo ""
echo "📋 텍스트 이해 테스트 실행 중..."
cd "$ROOT"
$PYTHON scripts/test_v5_text_understanding.py \
    --skip-raw \
    --extra-ckpt "$EXP04_CKPT_REL" \
    --extra-config "configs/mobile_vla_v5_exp04_google_robot.json" \
    --extra-name "exp04_google_robot_best" \
    2>&1 | tee "$LOG"

echo ""
echo "✅ 완료. 결과: $LOG"
