import os
from contextlib import closing

import hvac
import pandas as pd
import psycopg2
import streamlit as st


@st.cache_resource
def _get_credentials() -> dict:
    """Lit les identifiants bi_ro dans Vault (une seule fois par processus)."""
    client = hvac.Client(url=os.environ["VAULT_ADDR"])
    client.auth.approle.login(
        role_id=os.environ["VAULT_ROLE_ID"],
        secret_id=os.environ["VAULT_SECRET_ID"],
    )
    secret = client.secrets.kv.v2.read_secret_version(
        path="bi/crypto_bi_ro",
        mount_point="secret",
        raise_on_deleted_version=True,
    )
    return secret["data"]["data"]


def query_df(sql: str, params: tuple | None = None) -> pd.DataFrame:
    c = _get_credentials()
    with closing(
        psycopg2.connect(
            host=c["host"],
            port=c["port"],
            dbname=c["dbname"],
            user=c["user"],
            password=c["password"],
        )
    ) as conn:
        with conn, conn.cursor() as cur:
            cur.execute(sql, params)
            columns = [d[0] for d in cur.description]
            return pd.DataFrame(cur.fetchall(), columns=columns)