# ⚙️ Crypto Trading Pipeline

Data pipeline that collects, stores and serves market data for more than **50 cryptocurrencies**:
per-minute prices (CoinGecko) and 1-minute candle history (Binance), exposed through a REST API.

![Airflow](https://img.shields.io/badge/Airflow-3.4.0-017CEE?logo=apacheairflow&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![Vault](https://img.shields.io/badge/Vault-1.18-FFEC6E?logo=vault&logoColor=black)
![Tests](https://img.shields.io/badge/tests-pytest-0A9EDC?logo=pytest&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.67-3776AB?logo=Streamlit&logoColor=white)
![pandas](https://img.shields.io/badge/pandas-3.1-150458?logo=pandas&logoColor=white)

---

## 📌 Context

Analysing cryptocurrencies requires reliable data from several sources.
This project aggregates heterogeneous feeds (price, volume, market cap, candles) from several free public APIs, with:

- **automated and resilient collection** (retries, incremental resume);
- **hybrid storage**: PostgreSQL for recent data, Parquet for history;
- a **low-latency serving API**.

## 🎯 Goals and results

| Criterion | Goal | Result |
|-----------|------|--------|
| Collection frequency | CoinGecko every minute; Binance daily (incremental) | ✅ DAGs running in a local production-like setup |
| Retry logic | Automatic handling of API errors | ✅ Airflow retries + retries and rate limiting in the HTTP client |
| API latency | < 200 ms | ✅ **~14 ms (1 day) / ~50 ms (7 days)** median |
| Availability | > 99% | ⏳ 99.71% (measured over a 6-hour window) |

## 🏗️ Architecture

![](/img/architecture.jpg)

### Design choices

- **Hybrid storage**:
PostgreSQL for recent data queried by the API (`market_snapshots`, and `klines` over a rolling 7 days);
Parquet partitioned by interval/symbol/month for history.
- **One Airflow task per pair** using *dynamic task mapping* (`.expand()`): error isolation and controlled parallelism (`max_active_tis_per_dag`).
Each task only returns a **summary** (no large payloads in XCom).
- **Idempotent incremental ingestion**: 30-day backfill on the first run, then resume from the last known candle.
The in-progress candle is excluded and duplicates are removed (Parquet merge, `ON CONFLICT DO NOTHING` in the database).
- **CoinGecko -> Binance matching**: 34 of 51 cryptos have a USDT pair with `TRADING` status on Binance.
The other 17 are logged as *warnings* and are only tracked through CoinGecko.

## 🔐 Secrets management

- **No application password in the code or in `docker-compose.yml`.**
The connection to the `crypto` database is stored in **HashiCorp Vault** (`secret/connections/crypto_db`) and read by Airflow when tasks run
(Vault secrets backend, `BaseHook.get_connection("crypto_db")`).
- **Vault in server mode**: persistent storage (Docker volume `vault_data`), starts sealed, unsealed by `vault/start.sh`.
- **Least privilege**: Airflow authenticates through **AppRole** with a read-only policy. The root token is only used by the start script and for administration.
- **What stays in `.env`**: the secrets Airflow needs before Vault is readable (Fernet key, JWT secret, database password).

## 🛠️ Stack

| Layer | Technology |
|-------|------------|
| Orchestration | Apache Airflow 3.4.0 |
| Storage | PostgreSQL 16, Parquet |
| Processing | pandas, pyarrow |
| API | FastAPI |
| Containers | Docker Compose |
| Secrets | HashiCorp Vault (server mode, persistent storage, Airflow access through AppRole) |
| BI | Streamlit, Plotly |
| Quality | pytest |

## 📦 Project structure

```
project_crypto/
├── docker-compose.yml
│
├── requirements.txt
│
├── bi/                             # Streamlit app (BI)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── db.py                       # Vault access + PostgreSQL queries
│   └── app.py                      # dashboard
│
├── dags/
│   ├── coingecko_dag.py            # crypto_collect_minute (every minute)
│   └── binance_pipeline.py         # daily klines ingestion (every day)
│
├── src/                            # PYTHONPATH=/opt/airflow/src
│   ├── extract/
│   │   ├── binance.py              # get_binance_symbols, get_klines (pagination, retries)
│   │   └── coingecko.py            # fetch_coingecko_data
│   │
│   ├── transform/
│   │   ├── models.py               # cleaning / typing (safe_*), transform, process_coingecko_data
│   │   └── mappers.py              # get_mapper: CoinGecko <-> Binance reconciliation
│   │
│   ├── load/
│   │   ├── parquet_io.py           # Parquet read/write
│   │   └── postgres_db.py          # inserts, purge of old klines, mapping
│   │
│   └── pipelines/
│       └── ingestion.py            # ingest_pair, load_recent_klines_pipe
│
├── api/                            # FastAPI + bench.py
│      ├── vault_config.py
│      └── main, schema, queries,...
│
├── storage/
│   ├── schema.sql                  # market_snapshots, klines
│   └── bi.sql                      # bi schema, views, read-only role bi_ro
│
├── tests/                          # pytest tests
│
├── vault/
│   ├── config.hcl                  # Vault config (file storage, HTTP listener)
│   ├── airflow-read.hcl            # policy: read-only on connections/* and variables/*
│   ├── bi-read.hcl
│   ├── start.sh                    # entry point: unseals Vault, generates Airflow credentials, starts Docker
│   └── keys.json                   # unseal key + root token (NOT versioned)
│
├── data/                           # not versioned (Parquet)
│
└── logs/                           # not versioned
```

## 🚀 Quick start

### Requirements

- Docker and Docker Compose
- ~4 GB of RAM and 2 CPUs allocated to Docker (Airflow recommendation)

### Installation

```bash
git clone <repo-url>
cd <repo-url>

cp .env.example .env        # fill it in (see below)
```

Variables expected in `.env` (not versioned):

| Variable | Purpose |
|----------|---------|
| `POSTGRES_PASSWORD` | PostgreSQL password |
| `FERNET_KEY` | Airflow encryption key |
| `AIRFLOW__API_AUTH__JWT_SECRET` | Airflow JWT secret |
| `AIRFLOW_UID` | Linux UID of the user (`id -u`) |
| `AIRFLOW_PROJ_DIR` | `.` |
| `_AIRFLOW_WWW_USER_PASSWORD` | Airflow admin password |
| `_PIP_ADDITIONAL_REQUIREMENTS` | "pytest apache-airflow-providers-hashicorp" |

> Values containing spaces or special characters (`$ & ; ( ) ! #`) must be quoted, because `start.sh` reads this file with `source`.

### First-time Vault setup

Application secrets (the `crypto` database connection) live in Vault, not in `.env`.
Requires `jq`.

```bash
# 1. Start Vault alone (it starts empty and sealed)
docker compose up -d vault

# 2. Initialise: 1 unseal key, 1 required. Shown only once, saved to keys.json
docker compose exec -T vault vault operator init -key-shares=1 -key-threshold=1 -format=json > vault/keys.json
chmod 600 vault/keys.json          # file is already in .gitignore; also keep a copy somewhere safe

# 3. Unseal, create the secrets engine, the secret, the policy and the AppRole
set -a; source .env; set +a
export UNSEAL_KEY=$(jq -r '.unseal_keys_b64[0]' vault/keys.json)
export VAULT_TOKEN=$(jq -r '.root_token' vault/keys.json)

docker compose exec -T -e UNSEAL_KEY vault sh -c 'vault operator unseal "$UNSEAL_KEY"'
docker compose exec -T -e VAULT_TOKEN vault vault secrets enable -path=secret kv-v2
docker compose exec -T -e VAULT_TOKEN -e POSTGRES_PASSWORD vault sh -c 'vault kv put -mount=secret connections/crypto_db conn_type=postgres host=postgres port=5432 login=airflow password="$POSTGRES_PASSWORD" schema=crypto'
docker compose exec -T -e VAULT_TOKEN vault vault policy write airflow-read - < vault/airflow-read.hcl
docker compose exec -T -e VAULT_TOKEN vault vault auth enable approle
docker compose exec -T -e VAULT_TOKEN vault vault write auth/approle/role/airflow token_policies=airflow-read token_ttl=720h token_max_ttl=720h secret_id_ttl=0

unset UNSEAL_KEY VAULT_TOKEN
```

### Start

```bash
./vault/start.sh
```

The script:
1. reads `.env`;
2. starts Vault and **unseals** it if needed (Vault restarts sealed, for example after a PC reboot);
3. generates new AppRole credentials for Airflow (**read-only** access, the root token is only used here);
4. starts all the other services with `docker compose up -d`.

> Use `./vault/start.sh` instead of `docker compose up`. Without it Vault stays sealed and tasks fail.

```bash
# Check that services are healthy
docker compose ps
```

> 🔐 Neither `.env`, `vault/keys.json` nor `data/` are versioned (`.gitignore`).

### Access

| Service | URL |
|---------|-----|
| Airflow UI | http://localhost:8080 |
| FastAPI API | http://localhost:8000 |
| API Swagger UI (API docs) | http://localhost:8000/docs |
| Streamlit | http://localhost:8501 |
| Vault UI (administration) | http://127.0.0.1:8200 (root token in `vault/keys.json`) |


## 🔌 API

Interactive documentation (Swagger UI): http://localhost:8000/docs

| Route | Description |
|-------|-------------|
| `GET /` | Home page |
| `GET /health` | API status |
| `GET /price/{coin_id}` | Latest CoinGecko price collected for a crypto |
| `GET /klines/{coin_id}` | Binance 1-minute candles of a crypto over a period |

`coin_id` is the CoinGecko identifier (e.g. `bitcoin`): 1 to 64 characters among `a-z`, `0-9` and `-`.

### `GET /price/{coin_id}`

```bash
curl "http://localhost:8000/price/bitcoin"
```

```json
{
  "coin_id": "bitcoin",
  "current_price": "61446",
  "collected_at": "2026-11-20T13:29:01Z"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `coin_id` | string | CoinGecko identifier |
| `current_price` | string | Latest price in USD (a string, to keep decimal precision) |
| `collected_at` | datetime (UTC) | Collection timestamp |

### `GET /klines/{coin_id}`

Returns the 1-minute candles of a crypto over a period.

```bash
curl "http://localhost:8000/klines/bitcoin?start=2026-11-20T09:00:00Z&end=2026-11-20T09:03:00Z"
```

| Parameter | Description |
|-----------|-------------|
| `coin_id` | CoinGecko identifier (in the URL) |
| `start`, `end` | ISO 8601 bounds with timezone, in UTC (`end` excluded). `start` must be before `end`, and the period cannot exceed **7 days** |

```json
{
  "coin_id": "bitcoin",
  "symbol": "BTCUSDT",
  "count": 3,
  "candles": [
    {
      "open_time": "2026-11-20T09:00:00Z",
      "open": 61833.19,
      "high": 61854.05,
      "low": 61813.1,
      "close": 61846.68,
      "volume": 5.2798
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `coin_id` | string | CoinGecko identifier |
| `symbol` | string | Matching Binance pair (e.g. `BTCUSDT`) |
| `count` | integer | Number of candles returned |
| `candles[].open_time` | datetime (UTC) | Candle open time |
| `candles[].open`, `high`, `low`, `close` | number | OHLC prices |
| `candles[].volume` | number | Traded volume (in units of the crypto) |

### Error codes

| Code | Route | Cause |
|------|-------|-------|
| 404 | `/price` | Unknown crypto |
| 404 | `/klines` | No candle in the period: unknown crypto, crypto without a Binance pair, or period outside the history |
| 422 | `/klines` | `start` >= `end`, period > 7 days, invalid date, or malformed `coin_id` |


## 📈 BI dashboard (Streamlit)

App available at http://localhost:8501

**Content:**
1. Choice of the dashboard period
2. Biggest price moves (up and down)
3. Top 5 most expensive cryptos
4. Candlestick chart of a crypto (chosen by name)

**Data**
- `bi` schema: the only interface between the dashboard and the database.
- View `bi.v_klines_1m`: 1-minute candles of all Binance pairs (symbol, open time, open, high, low, close, volume), read from `public.klines`. Larger candles (5 min, 1 h, 1 day) are aggregated on the fly by the query (`date_bin`).
- View `bi.v_latest_prices`: latest known price of each CoinGecko crypto (name, symbol, price, collection date), read from `public.market_snapshots`. It feeds the top 5 and links to Binance (CoinGecko symbol + `USDT`).
- Only the columns the dashboard needs are exposed (no CoinGecko market cap or volume).

**Architecture and security:**
- Streamlit uses the `bi_ro` role, read-only on the PostgreSQL `bi` schema, with no rights on `public` tables.
- The `bi_ro` credentials are stored in Vault (`secret/bi/crypto_bi_ro`).

**Known limits:**
- Candles in the database only cover a rolling 7 days: a longer period is displayed but limited to that history.
- Only cryptos with a USDT pair on Binance appear.

**Screenshots**

![](img/screen1.png)
![](img/screen2.png)


## ⚡ Performance
Measured on `bitcoin`, locally (Docker, personal PC).
The `api/bench.py` script measures the three steps of a `/klines` request:
SQL query, Pydantic validation, JSON serialisation.

**Method**: 1-day and 7-day windows ending now,
21 runs per window, the first one (warm-up) is ignored.
The script prints the median and p95 of each step and of the total.

```bash
docker compose exec api python bench.py bitcoin    # another crypto: replace "bitcoin"
```

**Internal breakdown** (`docker compose exec api python bench.py bitcoin`):

| Period | Candles | SQL | Validation | JSON | **Total** | p95 |
|--------|--------:|----:|-----------:|-----:|----------:|----:|
| 1 day | 1,294 | 10.4 ms | 0.5 ms | 0.8 ms | **11.7 ms** | 12.2 ms |
| 7 days | 9,934 | 36.4 ms | 3.7 ms | 7.3 ms | **47.6 ms** | 49.4 ms |

**End-to-end measure** (HTTP with `curl`, 10 requests after a warm-up call, median):

| Period | Median |
|--------|-------:|
| 1 day | 14 ms |
| 7 days | 50 ms |

➡️ The **< 200 ms** goal is met with a wide margin, including on the maximum 7-day window in PostgreSQL.
The cost is dominated by the SQL query (~75%), followed by JSON serialisation.

## ✅ Tests

```bash
docker compose exec api pytest <test_file>
```
test_file:
- test_binance_transform.py
- test_mappers.py
- test_process_coingecko.py



## 📊 Monitoring and reliability

- Automatic **retries** on DAGs and API calls (backoff, rate limit).
- **Alerts** on task failure.
- Docker **healthchecks** on every service.
- Airflow **logs**; cryptos with no Binance equivalent are logged as *warnings*.

## ⚠️ Known limits

- **Vault configured for local use**: the unseal key and the root token (`vault/keys.json`) are stored on the same machine as the vault data (`vault_data` volume), and traffic is plain HTTP.
In production: unseal keys kept separately (or cloud KMS auto-unseal), keys split between several people, TLS, volume backups, highly available Raft storage.
- After a machine restart Vault is sealed: run `./vault/start.sh` again.
- Not every CoinGecko-to-Binance match is found.
- Backfill only covers the **1m** interval.
- Availability was measured on a local machine, not on production infrastructure.

## 🗺️ Roadmap

- Cloud storage for Parquet (S3 / Azure Blob).
- Support for other candle intervals.
- Visualisation dashboard (Grafana / Metabase).

## 📚 Resources

- [CoinGecko API](https://www.coingecko.com/en/api/documentation)
- [Binance API](https://binance-docs.github.io/apidocs/)
- [Apache Airflow](https://airflow.apache.org/docs/)


## 🙏 Acknowledgements

Thanks to Gaël Penessot for the initial problem statement and project framing.
[Website](https://gpenessot.github.io/#formations)

## 👤 Author

**François Dumont**
[GitHub](https://github.com/FrancoisDumont30)
[Portfolio](https://francoisdumont30.github.io/portfolio/)
[LinkedIn](https://www.linkedin.com/in/fran%C3%A7oisdumont)
