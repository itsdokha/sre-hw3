#!/usr/bin/env bash
# Генерирует разнообразный трафик к приложению, чтобы в логах были INFO/WARNING/ERROR.
# Использование: ./scripts/generate-load.sh [BASE_URL] [ROUNDS]
# По умолчанию BASE_URL берётся из `minikube service tasks-app --url`.
set -euo pipefail

BASE_URL="${1:-$(minikube service tasks-app --url)}"
ROUNDS="${2:-30}"
agents=("Mozilla/5.0 (X11; Linux x86_64) Firefox/131.0" "Mozilla/5.0 (Macintosh) Safari/605.1" "curl/8.5.0" "python-requests/2.32")

req() { curl -s -o /dev/null -w '%{http_code} ' -A "${agents[RANDOM % ${#agents[@]}]}" "$@"; }

for ((i = 1; i <= ROUNDS; i++)); do
  id=$(curl -s -X POST "$BASE_URL/api/tasks" -H 'Content-Type: application/json' \
    -d "{\"title\": \"Задача $i\"}" | sed -n 's/.*"id": *\([0-9]*\).*/\1/p')
  req "$BASE_URL/api/tasks"
  req "$BASE_URL/api/tasks/$id"
  req -X PUT "$BASE_URL/api/tasks/$id" -H 'Content-Type: application/json' \
    -d "{\"title\": \"Задача $i (готово)\", \"completed\": true}"
  (( i % 3 == 0 )) && req -X DELETE "$BASE_URL/api/tasks/$id"
  (( i % 4 == 0 )) && req "$BASE_URL/api/tasks/999999"                       # 404
  (( i % 5 == 0 )) && req -X POST "$BASE_URL/api/tasks" -H 'Content-Type: application/json' -d '{"title": ""}'  # 400
  (( i % 7 == 0 )) && req "$BASE_URL/does-not-exist"                         # 404
  echo
done
