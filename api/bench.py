import statistics
import sys
import time
from datetime import datetime, timedelta, timezone

from pydantic import TypeAdapter

from queries import get_db_klines
from schema import KlineResponse

coin = sys.argv[1] if len(sys.argv) > 1 else "bitcoin"
adapter = TypeAdapter(KlineResponse)
RUNS = 21  # the first run is ignored (warm-up)


def stats(values):
    v = sorted(values)
    return f"{statistics.median(v):7.1f} ms | p95 {v[int(0.95 * (len(v) - 1))]:7.1f} ms"


for days in (1, 7):
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    t_sql, t_val, t_json = [], [], []
    rows = 0

    for i in range(RUNS):
        t0 = time.perf_counter()
        res = get_db_klines(coin, start, end)
        t1 = time.perf_counter()
        if res is None:
            print(f"{days} j : aucune donnée pour {coin}")
            break
        model = adapter.validate_python(res)
        t2 = time.perf_counter()
        adapter.dump_json(model)
        t3 = time.perf_counter()

        if i == 0:
            rows = res["count"]
            continue
        t_sql.append((t1 - t0) * 1000)
        t_val.append((t2 - t1) * 1000)
        t_json.append((t3 - t2) * 1000)

    if t_sql:
        total = [a + b + c for a, b, c in zip(t_sql, t_val, t_json)]
        print(f"\n=== {days} jour(s) : {rows} bougies ===")
        print(f"SQL           : {stats(t_sql)}")
        print(f"Validation    : {stats(t_val)}")
        print(f"JSON          : {stats(t_json)}")
        print(f"TOTAL         : {stats(total)}")