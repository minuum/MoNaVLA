#!/usr/bin/env bash
set -euo pipefail

if command -v menemory >/dev/null 2>&1; then
  MEM_CMD="menemory"
elif [ -x "./menemory/menemory" ]; then
  MEM_CMD="./menemory/menemory"
else
  echo "menemory command not found"
  exit 1
fi

exec "$MEM_CMD" recover --build-prompt "$@"
