from functools import lru_cache
import os
import hvac


@lru_cache(maxsize=1)
def get_crypto_db_url() -> str:
    client = hvac.Client(
        url=os.environ["VAULT_ADDR"],
        token=os.environ["VAULT_TOKEN"],
    )
    secret = client.secrets.kv.v2.read_secret_version(
        path="api/crypto_db",
        mount_point="secret",
    )
    return secret["data"]["data"]["crypto_db_url"]