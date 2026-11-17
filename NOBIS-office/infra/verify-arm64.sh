#!/bin/sh
# Run on the target Debian 13 ARM64 host with Docker/Compose installed.
set -eu
cd "$(dirname "$0")/.."
ENV_FILE="${1:-.env.production}"
[ -f "$ENV_FILE" ] || { echo "Generate environment first: python3 infra/init-env.py" >&2; exit 1; }
command -v docker >/dev/null || { echo "Docker is required" >&2; exit 1; }
case "$(docker info --format '{{.Architecture}}')" in
  arm64|aarch64) ;;
  *) echo "An ARM64 Docker engine is required" >&2; exit 2 ;;
esac
docker compose --env-file "$ENV_FILE" -f compose.yaml config --quiet
docker compose --env-file "$ENV_FILE" -f compose.yaml up --build -d --wait --wait-timeout 120
docker compose --env-file "$ENV_FILE" -f compose.yaml exec -T backend python -c 'import platform, urllib.request; assert platform.machine() in ("aarch64", "arm64"); print(urllib.request.urlopen("http://localhost:8000/health").read().decode())'
docker compose --env-file "$ENV_FILE" -f compose.yaml exec -T frontend wget -qO- http://127.0.0.1/health
docker compose --env-file "$ENV_FILE" -f compose.yaml exec -T backend python -m app.cli migrate
docker compose --env-file "$ENV_FILE" -f compose.yaml exec -T postgres sh -c 'export PGPASSWORD="$NOBIS_DB_PASSWORD"; psql -h 127.0.0.1 -U "$NOBIS_DB_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -c "SELECT version();"'
docker compose --env-file "$ENV_FILE" -f compose.yaml ps
printf '\nARM64 startup checks passed. Continue with two-browser movement/chat tests.\n'
