"""Load check: signs in a few demo users, then hammers a realistic read mix from many threads and reports latency percentiles.
Usage: python loadtest.py [base_url] [workers] [seconds]   (demo/staging only; never run against real customer data)"""
import json
import sys
import threading
import time
import urllib.request
from statistics import quantiles

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
WORKERS = int(sys.argv[2]) if len(sys.argv) > 2 else 30
SECONDS = int(sys.argv[3]) if len(sys.argv) > 3 else 20
USERS = [("priya.rao@aadi.demo.test", ["/api/dashboard", "/api/insights", "/api/employees", "/api/planned-actual", "/api/performance", "/api/projects"]),
         ("sameer.joshi@aadi.demo.test", ["/api/invoices", "/api/expenses", "/api/finance/contribution", "/api/costing/profitability", "/api/planned-actual"]),
         ("meera.nair@aadi.demo.test", ["/api/dashboard", "/api/timesheets", "/api/tasks", "/api/performance"])]


def call(path, token=None, body=None):
    req = urllib.request.Request(BASE + path, data=None if body is None else json.dumps(body).encode(), method="POST" if body is not None else "GET",
                                 headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + token} if token else {})})
    t = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
            return r.status, time.perf_counter() - t, data
    except urllib.error.HTTPError as e:
        return e.code, time.perf_counter() - t, b""
    except Exception:
        return 0, time.perf_counter() - t, b""


tokens = []
for email, paths in USERS:
    s, _, d = call("/api/auth/login", body={"email": email, "password": "Tracker@Demo26"})
    assert s == 200, (email, s)
    tokens.append((json.loads(d)["token"], paths))
lat, bad, lock = [], {}, threading.Lock()
stop = time.time() + SECONDS


def worker(i):
    n = 0
    while time.time() < stop:
        tok, paths = tokens[(i + n) % len(tokens)]
        p = paths[(i * 7 + n) % len(paths)]
        s, dt, _ = call(p, tok)
        with lock:
            lat.append(dt)
            if s != 200:
                bad[(p, s)] = bad.get((p, s), 0) + 1
        n += 1


ts = [threading.Thread(target=worker, args=(i,)) for i in range(WORKERS)]
t0 = time.time()
[t.start() for t in ts]
[t.join() for t in ts]
el = time.time() - t0
q = quantiles(lat, n=100)
print(f"{len(lat)} requests, {WORKERS} workers, {el:.0f}s: {len(lat) / el:.0f} req/s | p50 {q[49] * 1000:.0f} ms, p95 {q[94] * 1000:.0f} ms, p99 {q[98] * 1000:.0f} ms, max {max(lat) * 1000:.0f} ms")
print("errors:", bad or "none")
sys.exit(1 if bad or q[94] > 2.0 else 0)
