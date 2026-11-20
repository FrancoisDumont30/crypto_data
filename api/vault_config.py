from functools import lru_cache
from urllib.parse import quote
import os
import hvac


@lru_cache(maxsize=1)
def get_crypto_db_url() -> str:
    client = hvac.Client(url=os.environ["VAULT_ADDR"])
    client.auth.approle.login(
        role_id=os.environ["VAULT_ROLE_ID"],
        secret_id=os.environ["VAULT_SECRET_ID"],
    )
    secret = client.secrets.kv.v2.read_secret_version(
        path="connections/crypto_db",
        mount_point="secret",
    )
    c = secret["data"]["data"]
    user = quote(c["login"], safe="")
    password = quote(c["password"], safe="")
    return f"postgresql://{user}:{password}@{c['host']}:{c['port']}/{c['schema']}"