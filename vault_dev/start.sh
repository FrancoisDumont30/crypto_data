#!/usr/bin/env bash
set -euo pipefail

# Se placer à la racine du projet (un niveau au-dessus de vault_dev/)
cd "$(dirname "$0")/.."

# 1. Lire le .env
set -a
source .env
set +a

# 2. Démarrer Vault seul
docker compose up -d vault

# 3. Attendre que Vault réponde
echo "Attente de Vault..."
until docker compose exec -T vault vault status >/dev/null 2>&1; do
  sleep 2
done

# 4. Créer les secrets
docker compose exec -T \
  -e VAULT_TOKEN="${VAULT_DEV_TOKEN}" \
  -e POSTGRES_PASSWORD \
  vault sh < vault_dev/init.sh

# 5. Lancer tout le reste
docker compose up -d

echo "Pipeline démarré."