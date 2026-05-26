#!/usr/bin/env bash
set -euo pipefail

test_db="${TEST_POSTGRES_DB:-azitrax_test}"
owner="${POSTGRES_USER:-azitrax}"

psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --set ON_ERROR_STOP=1 <<SQL
CREATE DATABASE "$test_db" OWNER "$owner";
SQL
