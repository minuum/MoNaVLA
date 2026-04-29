#!/usr/bin/env bash

set -euo pipefail

cd /home/billy/25-1kp/MoNaVLA

CONFIGS=(
  "configs/mobile_vla_v5_exp29_step3_grounding_turnboost_bboxcoarse_5ep.json"
  "configs/mobile_vla_v5_exp30_step3_grounding_turnboost_coarseonly_5ep.json"
)

for cfg in "${CONFIGS[@]}"; do
  echo "============================================================"
  echo "[start] $(date '+%F %T') $cfg"
  python3 robovlm_nav/train.py "$cfg"
  echo "[done]  $(date '+%F %T') $cfg"
done

echo "============================================================"
echo "[all-done] $(date '+%F %T')"
