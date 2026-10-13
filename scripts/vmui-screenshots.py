"""Снимает скриншоты vmui для запросов из отчёта через headless Chrome.

Нужен работающий port-forward: kubectl -n logging port-forward svc/victoria-logs 9428:9428
Использование: python3 scripts/vmui-screenshots.py screenshots [a-raw b-errors ...]
"""
import os
import subprocess
import sys
import tempfile
import urllib.parse

out = sys.argv[1]
shots = [
  ("a-raw", "_time:15m | sort by (_time) desc | limit 100", "group",
   "_time,service.name,k8s.pod.name,level,_msg"),
  ("b-errors", "_time:1h level:ERROR | fields _time, k8s.pod.name, request_id, http.status_code, error.type, _msg | sort by (_time) desc", "json",
   "_time,k8s.pod.name,request_id,http.status_code,error.type,_msg"),
  ("c-stats", "_time:1h | stats by (service.name, level) count() logs | sort by (logs desc)", "json",
   "service.name,level,logs"),
  ("d-quantile", "_time:1h logger:tasks.access -user_agent:kube-probe* | stats by (http.route, http.method) count() requests, quantile(0.5, duration_ms) p50_ms, quantile(0.95, duration_ms) p95_ms, max(duration_ms) max_ms | sort by (p95_ms desc)", "json",
   "http.route,http.method,requests,p50_ms,p95_ms,max_ms", 1750),
]
only = sys.argv[2:]
profile = tempfile.mkdtemp(prefix="vmui-chrome-")
for name, q, view, fields, *size in shots:
    height = size[0] if size else 1100
    if only and name not in only: continue
    params = urllib.parse.urlencode({"query": q, "g0.range_input": "1h", "view": view, "displayFields": fields, "limit": "100"}, quote_via=urllib.parse.quote)
    url = f"http://localhost:9428/select/vmui/#/?{params}"
    subprocess.run(["google-chrome", "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
        f"--window-size=1600,{height}", "--virtual-time-budget=8000", f"--user-data-dir={profile}",
        f"--screenshot={out}/{name}.png", url], check=True, capture_output=True, timeout=60)
    print(name, "ok")
