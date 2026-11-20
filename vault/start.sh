#!/usr/bin/env bash
set -euo pipefail

# Racine du projet (un niveau au-dessus de vault/)
cd "$(dirname "$0")/.."

KEYS=vault/keys.json
[ -f "$KEYS" ] || { echo "vault/keys.json introuvable"; exit 1; }

# 1. Lire le .env
set -a; source .env; set +a

# 2. Démarrer Vault seul
docker compose up -d vault

# 3. Attendre que Vault réponde (code 2 = scellé, c'est normal)
echo "Attente de Vault..."
until docker compose exec -T vault vault status >/dev/null 2>&1 || [ $? -eq 2 ]; do
  sleep 2
done

# 4. Déverrouiller si nécessaire
SEALED=$( (docker compose exec -T vault vault status -format=json || true) | jq -r '.sealed')
if [ "$SEALED" = "true" ]; then
  export UNSEAL_KEY=$(jq -r '.unseal_keys_b64[0]' "$KEYS")
  docker compose exec -T -e UNSEAL_KEY vault sh -c 'vault operator unseal "$UNSEAL_KEY" >/dev/null'
  unset UNSEAL_KEY
  echo "Vault déverrouillé."
fi

# 5. Générer les identifiants AppRole d'Airflow (le token root ne sert qu'ici)
export VAULT_TOKEN=$(jq -r '.root_token' "$KEYS")
VAULT_ROLE_ID=$(docker compose exec -T -e VAULT_TOKEN vault vault read -field=role_id auth/approle/role/airflow/role-id)
VAULT_SECRET_ID=$(docker compose exec -T -e VAULT_TOKEN vault vault write -f -field=secret_id auth/approle/role/airflow/secret-id)
export VAULT_ROLE_ID VAULT_SECRET_ID
unset VAULT_TOKEN

# 6. Lancer le reste
docker compose up -d

echo "Pipeline démarré."