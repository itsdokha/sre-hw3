#!/usr/bin/env bash
# Кратковременно останавливает PostgreSQL, чтобы приложение отвечало 503 и писало ERROR-логи.
# Использование: ./scripts/simulate-db-outage.sh [BASE_URL] [SECONDS]
set -euo pipefail

BASE_URL="${1:-$(minikube service tasks-app --url)}"
DURATION="${2:-20}"

kubectl scale statefulset postgres --replicas=0
kubectl wait --for=delete pod/postgres-0 --timeout=60s || true
end=$((SECONDS + DURATION))
while ((SECONDS < end)); do
  curl -s -o /dev/null -w '%{http_code} ' "$BASE_URL/api/tasks"
  sleep 0.5
done
echo
kubectl scale statefulset postgres --replicas=1
kubectl rollout status statefulset postgres --timeout=120s
