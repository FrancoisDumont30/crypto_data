#!/bin/sh
set -eu

echo "Vault init : écriture des secrets..."

vault kv put -mount=secret connections/crypto_db \
  conn_type=postgres \
  host=postgres \
  port=5432 \
  login=airflow \
  password="${POSTGRES_PASSWORD}" \
  schema=crypto

vault kv get -mount=secret connections/crypto_db

echo "Vault init : terminé."