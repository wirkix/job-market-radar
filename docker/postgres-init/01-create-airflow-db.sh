#!/usr/bin/env bash
# Runs once, on first container start, because it's mounted into
# /docker-entrypoint-initdb.d/. Creates the second database Airflow's
# metadata lives in, alongside the main $POSTGRES_DB warehouse database
# that docker-entrypoint already creates for us.
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres <<-EOSQL
    CREATE DATABASE "${AIRFLOW_DB}";
    GRANT ALL PRIVILEGES ON DATABASE "${AIRFLOW_DB}" TO "$POSTGRES_USER";
EOSQL
