#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-all}"
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOAD_DIR="$ROOT_DIR/load_test"
RESULTS_DIR="$LOAD_DIR/results"
TS="$(date +%Y%m%d_%H%M%S)"
RUN_DIR="$RESULTS_DIR/$TS"

BASE_URL="${BASE_URL:-http://localhost:8080}"
K6_DOCKER_IMAGE="${K6_DOCKER_IMAGE:-grafana/k6:latest}"
K6_DOCKER_NETWORK="${K6_DOCKER_NETWORK:-host}"
# Leave unset by default. Some servers use user namespaces where host UIDs are unmapped.
K6_DOCKER_USER="${K6_DOCKER_USER:-}"

mkdir -p "$RUN_DIR"
# Keep run output writable even when Docker k6 user mapping varies by host.
chmod 0777 "$RUN_DIR" 2>/dev/null || true

USE_DOCKER_K6=false
if command -v k6 >/dev/null 2>&1; then
  echo "Using local k6 binary."
elif command -v docker >/dev/null 2>&1; then
  USE_DOCKER_K6=true
  echo "Local k6 not found. Using Docker image: $K6_DOCKER_IMAGE"
  echo "Docker k6 network mode: $K6_DOCKER_NETWORK"
  echo "Current BASE_URL: $BASE_URL"
else
  echo "Neither k6 nor docker is available."
  exit 1
fi

run_k6() {
  local summary="$1"

  if [[ "$USE_DOCKER_K6" == "true" ]]; then
    local -a docker_user_args=()
    if [[ -n "$K6_DOCKER_USER" ]]; then
      docker_user_args+=(--user "$K6_DOCKER_USER")
    fi

    docker run --rm \
      "${docker_user_args[@]}" \
      --network "$K6_DOCKER_NETWORK" \
      -v "$ROOT_DIR:/work" \
      -w /work/load_test \
      -e TEST_TYPE \
      -e BASE_URL \
      -e SEARCH_QUERY \
      -e USER_PREFIX \
      -e PASS_PREFIX \
      -e UPLOADS_PER_ITER \
      -e WAIT_FOR_INDEX \
      -e POLL_INTERVAL_MS \
      -e MAX_POLL_SEC \
      -e THINK_TIME_SEC \
      -e BASELINE_VUS \
      -e BASELINE_DURATION \
      -e STRESS_VUS \
      -e STRESS_DURATION \
      -e SPIKE_BASELINE_VUS \
      -e SPIKE_VUS \
      -e SPIKE_BASELINE_DURATION \
      -e SPIKE_RAMP_UP_DURATION \
      -e SPIKE_HOLD_DURATION \
      -e SPIKE_RAMP_DOWN_DURATION \
      -e SPIKE_RECOVERY_DURATION \
      -e K6_DOCKER_NETWORK \
      "$K6_DOCKER_IMAGE" \
      run async_test.js --summary-export "/work/${summary#"$ROOT_DIR/"}"
  else
    k6 run "$LOAD_DIR/async_test.js" --summary-export "$summary"
  fi
}

run_k6_to_log() {
  local summary="$1"
  local out="$2"

  # Keep test suite running even when k6 exits non-zero due to thresholds.
  set +e
  run_k6 "$summary" | tee "$out"
  local status=${PIPESTATUS[0]}
  set -e

  if [[ "$status" -ne 0 ]]; then
    echo "k6 exited with status $status for $(basename "$out")."
  fi
}

run_baseline() {
  local repeats="${BASELINE_REPEATS:-3}"
  local vus="${BASELINE_VUS:-10}"
  local duration="${BASELINE_DURATION:-20m}"

  echo "Running baseline: repeats=$repeats, vus=$vus, duration=$duration"
  for i in $(seq 1 "$repeats"); do
    local summary="$RUN_DIR/baseline_run${i}.json"
    local out="$RUN_DIR/baseline_run${i}.log"

    TEST_TYPE=baseline \
    BASE_URL="$BASE_URL" \
    BASELINE_VUS="$vus" \
    BASELINE_DURATION="$duration" \
    WAIT_FOR_INDEX=true \
    run_k6_to_log "$summary" "$out"
  done
}

run_stress() {
  local vus_list="${STRESS_VUS_LIST:-10 15 20 30 50}"
  local duration="${STRESS_DURATION:-3m}"

  echo "Running stress: vus_list=[$vus_list], duration=$duration"
  for vus in $vus_list; do
    local summary="$RUN_DIR/stress_vus${vus}.json"
    local out="$RUN_DIR/stress_vus${vus}.log"

    TEST_TYPE=stress \
    BASE_URL="$BASE_URL" \
    STRESS_VUS="$vus" \
    STRESS_DURATION="$duration" \
    WAIT_FOR_INDEX=true \
    run_k6_to_log "$summary" "$out"
  done
}

run_spike() {
  local baseline_vus="${SPIKE_BASELINE_VUS:-10}"
  local spike_vus="${SPIKE_VUS:-40}"

  echo "Running spike: baseline_vus=$baseline_vus, spike_vus=$spike_vus"

  TEST_TYPE=spike \
  BASE_URL="$BASE_URL" \
  SPIKE_BASELINE_VUS="$baseline_vus" \
  SPIKE_VUS="$spike_vus" \
  WAIT_FOR_INDEX=true \
  run_k6_to_log "$RUN_DIR/spike.json" "$RUN_DIR/spike.log"
}

case "$MODE" in
  baseline)
    run_baseline
    ;;
  stress)
    run_stress
    ;;
  spike)
    run_spike
    ;;
  all)
    run_baseline
    run_stress
    run_spike
    ;;
  *)
    echo "Unknown mode: $MODE"
    echo "Usage: $0 [baseline|stress|spike|all]"
    exit 1
    ;;
esac

echo "Done. Results written to: $RUN_DIR"
