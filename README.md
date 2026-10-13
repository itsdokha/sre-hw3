# ДЗ 3: логи приложения в Victoria Logs

Приложение «Список задач» из ДЗ 1–2 пишет структурированные JSON-логи в stdout. Vector (DaemonSet) читает их с ноды minikube и отправляет в Victoria Logs (single-node).

Путь логов:

1. Поды `tasks-app`, `tasks-migrate` и `postgres` пишут в stdout, kubelet сохраняет это в `/var/log/pods` на ноде.
2. Vector (DaemonSet в namespace `logging`) читает эти файлы.
3. Vector отправляет записи в Victoria Logs (порт 9428) через Elasticsearch bulk API.
4. Логи смотрятся в vmui.

## Структура

| Путь | Что внутри |
| --- | --- |
| `app/logs.py` | JSON-форматтер логов (stdlib `logging`), конфиг логов gunicorn |
| `app/__init__.py` | access-лог на каждый запрос и доменные события в JSON |
| `gunicorn.conf.py`, `Dockerfile` | образ `tasks-app:1.1`, логи gunicorn тоже в JSON |
| `k8s/app/` | манифесты приложения (из ДЗ 2; образ 1.1, переменные `SERVICE_*`) |
| `k8s/logging/victoria-logs.yaml` | Victoria Logs: Deployment + Service + PVC |
| `k8s/logging/vector.yaml` | конфиг шиппера Vector |
| `k8s/logging/vector-daemonset.yaml` | ServiceAccount, RBAC и DaemonSet Vector |
| `k8s/logging/kustomization.yaml` | собирает namespace `logging` и ConfigMap из `vector.yaml` |
| `scripts/generate-load.sh` | разнообразный трафик к API (200/201/204/400/404) |
| `scripts/simulate-db-outage.sh` | кратковременно останавливает PostgreSQL, чтобы получить 503 и ERROR-логи |
| `queries.logsql` | LogsQL-запросы из отчёта |
| `scripts/vmui-screenshots.py` | скриншоты vmui для запросов из отчёта (headless Chrome) |
| `screenshots/` | скриншоты для отчёта |

## Запуск

```bash
minikube start --driver=docker
eval $(minikube docker-env)
docker build -t tasks-app:1.1 .

# секрет из ДЗ 2, если его ещё нет в кластере
kubectl create secret generic postgres-secret --from-literal=POSTGRES_PASSWORD='my-local-password'

kubectl apply -f k8s/app/
kubectl apply -k k8s/logging
kubectl get pods -A
```

Job неизменяем: при обновлении образа перезапустить миграцию через `kubectl delete job tasks-migrate && kubectl apply -f k8s/app/migrate-job.yaml`.

## Проверка

```bash
kubectl logs deploy/tasks-app --tail=3          # JSON-строки
kubectl -n logging port-forward svc/victoria-logs 9428:9428
```

- vmui: <http://localhost:9428/select/vmui/> (в v1.52 путь `/vmui/` не работает)
- из терминала: `curl -s localhost:9428/select/logsql/query -d 'query=_time:5m | limit 5'`

Наполнить логи данными:

```bash
URL=$(minikube service tasks-app --url)
./scripts/generate-load.sh "$URL" 30
./scripts/simulate-db-outage.sh "$URL" 20
./scripts/generate-load.sh "$URL" 20
```

## Очистка

```bash
kubectl delete -k k8s/logging      # Victoria Logs вместе с PVC и Vector
```
