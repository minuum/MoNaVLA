#!/usr/bin/env bash
# Free 에피소드 H5를 minum 서버로 rsync 전송
#
# 사용법:
#   bash scripts/sync/push_free_episodes_to_minum.sh            # 전체 (FL+FC+FR)
#   bash scripts/sync/push_free_episodes_to_minum.sh --dry-run  # 목록만 확인
#   bash scripts/sync/push_free_episodes_to_minum.sh fc         # FC만
#   bash scripts/sync/push_free_episodes_to_minum.sh fl fr      # FL+FR만

set -euo pipefail

MINUM_HOST="${MINUM_HOST:-minum}"
MINUM_PATH="${MINUM_PATH:-/home/minum/26CS/MoNaVLA}"
LOCAL_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOCAL_DATASET="${LOCAL_ROOT}/ROS_action/mobile_vla_dataset_v5"

DRY_RUN=false
TARGETS=()

for arg in "$@"; do
  case "$arg" in
    --dry-run|-n) DRY_RUN=true ;;
    fc|FC) TARGETS+=("free_center") ;;
    fl|FL) TARGETS+=("free_left") ;;
    fr|FR) TARGETS+=("free_right") ;;
  esac
done

# 전송 파일 수집
FILES=()
for f in "${LOCAL_DATASET}"/episode_*free_*.h5; do
  [[ -f "$f" ]] || continue
  if [[ ${#TARGETS[@]} -eq 0 ]]; then
    FILES+=("$f")
  else
    for t in "${TARGETS[@]}"; do
      [[ "$f" == *"${t}"* ]] && FILES+=("$f") && break
    done
  fi
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  soda → minum: Free 에피소드 전송"
echo "  목적지: ${MINUM_HOST}:${MINUM_PATH}/ROS_action/mobile_vla_dataset_v5/"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [[ ${#FILES[@]} -eq 0 ]]; then
  echo "전송할 free 에피소드가 없습니다."
  exit 1
fi

echo "전송 파일 (${#FILES[@]}개):"
for f in "${FILES[@]}"; do
  size=$(du -sh "$f" | cut -f1)
  tag=$(basename "$f" | sed 's/episode_[0-9_]*_//' | sed 's/__core.*$//')
  echo "  ${size}  ${tag}"
done
echo ""
TOTAL=$(du -ch "${FILES[@]}" | tail -1 | cut -f1)
echo "총 크기: ${TOTAL}"
echo ""

if $DRY_RUN; then
  echo "[DRY RUN] 실제 전송하지 않음."
  exit 0
fi

rsync -avz --progress \
  "${FILES[@]}" \
  "${MINUM_HOST}:${MINUM_PATH}/ROS_action/mobile_vla_dataset_v5/"

echo ""
echo "✅ 전송 완료"
echo ""
echo "minum 확인:"
ssh "${MINUM_HOST}" "ls ${MINUM_PATH}/ROS_action/mobile_vla_dataset_v5/ | grep free_ | sort"
