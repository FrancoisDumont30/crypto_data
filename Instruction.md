# ⚙️ Crypto Trading Pipeline (initial brief)

> Robust pipeline to collect and serve real-time data for 50+ cryptocurrencies.

## 📊 Business problem

**Context**: analysing cryptos requires reliable, real-time, multi-source data.

**Challenge**: aggregate heterogeneous feeds (price, volume) from several APIs with high availability.

**Goal**: a stable pipeline collecting **50+ cryptos every minute**, with history and an API.

---

## 🗂️ Dataset

- **Main source**: [CoinGecko API](https://www.coingecko.com/en/api) (free)
- **History**: [Binance API](https://binance-docs.github.io/apidocs/) (free)
- **Volume**: 50 cryptos, minute-level data
- **Features**: price, volume, market cap

---

## 🎯 Success criteria

| Metric | Goal |
|--------|------|
| **Pipeline availability** | > 99% uptime |
| **Collection frequency** | Every minute |
| **Retry logic** | Automatic handling of API errors |
| **API serving latency** | < 200 ms |

---

## 🛠️ Stack

- **Orchestration**: Apache Airflow
- **Storage**: PostgreSQL + Parquet
- **Processing**: pandas
- **API**: FastAPI, Docker

---

## 💡 Key techniques

**Orchestration**:
- Airflow DAGs with retry logic and alerts
- Granular scheduling per collection frequency

**Storage**:
- PostgreSQL for recent structured data
- Parquet for long-term history

**Monitoring**:
- Centralised Airflow logs
- Alerts on collection failures

---

## 📚 Resources

- [CoinGecko API Docs](https://www.coingecko.com/en/api/documentation)
- [Binance API Docs](https://binance-docs.github.io/apidocs/)
- [Apache Airflow Docs](https://airflow.apache.org/docs/)
