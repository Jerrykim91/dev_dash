#!/bin/sh
set -eu

NOBIS_PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$NOBIS_PROJECT_DIR"
if [ -x "$NOBIS_PROJECT_DIR/.tools/node/bin/node" ]; then
  export PATH="$NOBIS_PROJECT_DIR/.tools/node/bin:$PATH"
fi
if ! command -v npm >/dev/null 2>&1; then
  echo "Node.js와 npm이 필요합니다. 프로젝트 .tools/node 또는 PATH를 확인하세요." >&2
  exit 1
fi
exec "$NOBIS_PROJECT_DIR/.venv/bin/python" "$NOBIS_PROJECT_DIR/infra/dev/start-local.py"
