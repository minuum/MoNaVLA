#!/usr/bin/env bash

set -euo pipefail

ROBOT_HOST="${ROBOT_HOST:-}"
ROBOT_PATH="${ROBOT_PATH:-}"

if [[ -z "${ROBOT_HOST}" || -z "${ROBOT_PATH}" ]]; then
  echo "Usage:"
  echo "  ROBOT_HOST=user@host ROBOT_PATH=/remote/repo bash scripts/sync/push_v5_top3_candidates_to_robot_server.sh"
  exit 1
fi

cd /home/billy/25-1kp/MoNaVLA

FILES=(
  "docs/v5/robot_server_top3_candidates_20260423.json"
  "docs/v5/robot_server_top3_candidates_20260423.md"
  "configs/mobile_vla_v5_exp25_step3_balanced_objective.json"
  "configs/mobile_vla_v5_exp26_step3_objective_direct224.json"
  "configs/mobile_vla_v5_exp27_step3_objective_letterbox224.json"
  "runs/v5_nav/kosmos/mobile_vla_v5_exp25/2026-04-22/v5-exp25-step3-balanced-objective/epoch_epoch=epoch=02-val_loss=val_loss=10.117.ckpt"
  "runs/v5_nav/kosmos/mobile_vla_v5_exp26/2026-04-22/v5-exp26-step3-objective-direct224/epoch_epoch=epoch=14-val_loss=val_loss=7.036.ckpt"
  "runs/v5_nav/kosmos/mobile_vla_v5_exp27/2026-04-23/v5-exp27-step3-objective-letterbox224/epoch_epoch=epoch=08-val_loss=val_loss=7.932.ckpt"
)

echo "Pushing V5 top-3 robot-server candidates to ${ROBOT_HOST}:${ROBOT_PATH}"

for file in "${FILES[@]}"; do
  if [[ ! -f "${file}" ]]; then
    echo "Missing file: ${file}"
    exit 1
  fi
done

rsync -av --progress --relative "${FILES[@]}" "${ROBOT_HOST}:${ROBOT_PATH}/"

echo ""
echo "Done."
echo "Recommended default on robot server:"
echo "  export VLA_CHECKPOINT_PATH=\"runs/v5_nav/kosmos/mobile_vla_v5_exp25/2026-04-22/v5-exp25-step3-balanced-objective/epoch_epoch=epoch=02-val_loss=val_loss=10.117.ckpt\""
echo "  export VLA_CONFIG_PATH=\"configs/mobile_vla_v5_exp25_step3_balanced_objective.json\""
