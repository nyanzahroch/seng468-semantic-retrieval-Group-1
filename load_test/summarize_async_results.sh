#!/usr/bin/env bash
set -euo pipefail

RESULT_DIR="${1:-}"

if [[ -z "$RESULT_DIR" ]]; then
  RESULT_DIR="$(ls -dt load_test/results/* 2>/dev/null | head -n1 || true)"
fi

if [[ -z "$RESULT_DIR" || ! -d "$RESULT_DIR" ]]; then
  echo "Could not find a valid results directory."
  echo "Usage: $0 <results_dir>"
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required to summarize results. Install jq and rerun."
  exit 1
fi

OUT_CSV="$RESULT_DIR/summary_table.csv"

echo "scenario,vu_label,throughput_req_per_sec,avg_latency_sec,p95_sec,login_error_pct,search_error_pct,documents_error_pct,upload_error_pct,indexing_not_ready_pct,http_error_pct" > "$OUT_CSV"

for f in "$RESULT_DIR"/*.json; do
  [[ -f "$f" ]] || continue

  base="$(basename "$f" .json)"
  scenario="$base"
  vu_label=""

  if [[ "$base" =~ stress_vus([0-9]+)$ ]]; then
    scenario="stress"
    vu_label="${BASH_REMATCH[1]}"
  elif [[ "$base" =~ baseline_run([0-9]+)$ ]]; then
    scenario="baseline"
    vu_label="run${BASH_REMATCH[1]}"
  elif [[ "$base" == "spike" ]]; then
    scenario="spike"
    vu_label="profile"
  fi

  reqs="$(jq -r '.metrics.http_reqs.rate // 0' "$f")"
  avg_s="$(jq -r '((.metrics.http_req_duration.avg // 0) / 1000)' "$f")"
  p95_s="$(jq -r '((.metrics.http_req_duration["p(95)"] // 0) / 1000)' "$f")"
  http_err="$(jq -r '((.metrics.http_req_failed.value // 0) * 100)' "$f")"

  login_pass="$(jq -r '.root_group.checks["login success"].passes // 0' "$f")"
  login_fail="$(jq -r '.root_group.checks["login success"].fails // 0' "$f")"

  search_pass="$(jq -r '.root_group.checks["search success"].passes // 0' "$f")"
  search_fail="$(jq -r '.root_group.checks["search success"].fails // 0' "$f")"

  docs_pass="$(jq -r '.root_group.checks["documents success"].passes // 0' "$f")"
  docs_fail="$(jq -r '.root_group.checks["documents success"].fails // 0' "$f")"

  upload_pass="$(jq -r '.root_group.checks["upload accepted"].passes // 0' "$f")"
  upload_fail="$(jq -r '.root_group.checks["upload accepted"].fails // 0' "$f")"

  idx_value="$(jq -r 'if .metrics.indexing_ready_rate and .metrics.indexing_ready_rate.value != null then .metrics.indexing_ready_rate.value else 1 end' "$f")"

  login_err="$(awk -v p="$login_pass" -v f="$login_fail" 'BEGIN {t=p+f; if (t==0) print 0; else printf "%.4f", (f/t)*100}')"
  search_err="$(awk -v p="$search_pass" -v f="$search_fail" 'BEGIN {t=p+f; if (t==0) print 0; else printf "%.4f", (f/t)*100}')"
  docs_err="$(awk -v p="$docs_pass" -v f="$docs_fail" 'BEGIN {t=p+f; if (t==0) print 0; else printf "%.4f", (f/t)*100}')"
  upload_err="$(awk -v p="$upload_pass" -v f="$upload_fail" 'BEGIN {t=p+f; if (t==0) print 0; else printf "%.4f", (f/t)*100}')"
  idx_not_ready="$(awk -v v="$idx_value" 'BEGIN {printf "%.4f", (1-v)*100}')"

  printf "%s,%s,%.4f,%.4f,%.4f,%s,%s,%s,%s,%s,%.4f\n" \
    "$scenario" "$vu_label" "$reqs" "$avg_s" "$p95_s" \
    "$login_err" "$search_err" "$docs_err" "$upload_err" "$idx_not_ready" "$http_err" >> "$OUT_CSV"
done

echo "Wrote summary CSV: $OUT_CSV"
