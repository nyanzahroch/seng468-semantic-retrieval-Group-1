#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080}"
COUNT="${1:-60}"
USER_PREFIX="${USER_PREFIX:-user}"
PASS_PREFIX="${PASS_PREFIX:-pass}"

for i in $(seq 1 "$COUNT"); do
  username="${USER_PREFIX}${i}"
  password="${PASS_PREFIX}${i}"

  code=$(curl -sS -o /tmp/signup_resp.json -w "%{http_code}" \
    -X POST "$BASE_URL/auth/signup" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"${username}\",\"password\":\"${password}\"}")

  if [[ "$code" == "200" || "$code" == "409" ]]; then
    echo "[$i/$COUNT] $username -> ok ($code)"
  else
    echo "[$i/$COUNT] $username -> failed ($code)"
    cat /tmp/signup_resp.json || true
    exit 1
  fi
done

rm -f /tmp/signup_resp.json
echo "User setup complete."
