#!/usr/bin/env bash
set -euo pipefail

INTERVAL_SECONDS="${1:-300}"

if ! [[ "$INTERVAL_SECONDS" =~ ^[0-9]+$ ]] || [ "$INTERVAL_SECONDS" -lt 30 ]; then
  echo "usage: $0 [interval_seconds>=30]"
  exit 1
fi

if command -v menemory >/dev/null 2>&1; then
  MEM_CMD="menemory"
elif [ -x "./menemory/menemory" ]; then
  MEM_CMD="./menemory/menemory"
else
  echo "menemory command not found"
  exit 1
fi

MEN_HOME="$("$MEM_CMD" where)"
SNAPSHOT_DIR="$MEN_HOME/sessions/autosave"
LOCK_DIR="$SNAPSHOT_DIR/.lock"
mkdir -p "$SNAPSHOT_DIR"

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "autosave loop already running: $LOCK_DIR"
  exit 1
fi

cleanup() {
  rmdir "$LOCK_DIR" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "menemory autosave started"
echo "workspace: $MEN_HOME"
echo "snapshot_dir: $SNAPSHOT_DIR"
echo "interval_seconds: $INTERVAL_SECONDS"
echo "set MENEMORY_AUTO_BACKUP_PUSH=1 to push Supabase backup each cycle"

while true; do
  TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
  ACTIVE_SRC="$MEN_HOME/sessions/active_session.json"
  BACKUP_SRC="$MEN_HOME/sessions/active_session.backup.json"

  if [ -f "$ACTIVE_SRC" ]; then
    cp "$ACTIVE_SRC" "$SNAPSHOT_DIR/${TIMESTAMP}_active_session.json"
  fi
  if [ -f "$BACKUP_SRC" ]; then
    cp "$BACKUP_SRC" "$SNAPSHOT_DIR/${TIMESTAMP}_active_session.backup.json"
  fi

  if [ "${MENEMORY_AUTO_BACKUP_PUSH:-0}" = "1" ]; then
    if ! "$MEM_CMD" backup push >/dev/null 2>&1; then
      echo "[$(date -Iseconds)] warning: menemory backup push failed"
    fi
  fi

  echo "[$(date -Iseconds)] autosaved menemory state"
  sleep "$INTERVAL_SECONDS"
done
