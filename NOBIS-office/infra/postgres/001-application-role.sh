#!/usr/bin/env bash
set -euo pipefail
: "${NOBIS_DB_USER:?NOBIS_DB_USER is required}"
: "${NOBIS_DB_PASSWORD:?NOBIS_DB_PASSWORD is required}"
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --set=ON_ERROR_STOP=1 --set=app_user="$NOBIS_DB_USER" --set=app_password="$NOBIS_DB_PASSWORD" --set=app_db="$POSTGRES_DB" <<'SQL'
SELECT format('CREATE ROLE %I LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD %L', :'app_user', :'app_password') \gexec
SELECT format('ALTER DATABASE %I OWNER TO %I', :'app_db', :'app_user') \gexec
SQL
