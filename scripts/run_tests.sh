#!/usr/bin/env bash
# =============================================================================
# ArthRaksha Test Suite Runner
# =============================================================================
# Orchestrates pytest (unit + integration + chaos) → Locust → k6
# and collects all outputs into reports/
#
# Usage:
#   ./scripts/run_tests.sh [--skip-locust] [--skip-k6] [--real-hf] [--host URL]
#
# Prerequisites:
#   pip install pytest httpx pytest-asyncio pytest-timeout locust
#   npm install -g k6   (or: brew install k6 / snap install k6)
#   ArthRaksha server must be running at $HOST (default: http://localhost:8000)
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
HOST="${HOST:-http://localhost:8000}"
SKIP_LOCUST=false
SKIP_K6=false
USE_REAL_HF=0
REPORT_DIR="reports/$(date +%Y%m%d_%H%M%S)"

# ---------------------------------------------------------------------------
# Arg parsing
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-locust) SKIP_LOCUST=true ;;
    --skip-k6)     SKIP_K6=true ;;
    --real-hf)     USE_REAL_HF=1 ;;
    --host)        HOST="$2"; shift ;;
    *) echo "Unknown argument: $1"; exit 1 ;;
  esac
  shift
done

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
mkdir -p "$REPORT_DIR"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║          ArthRaksha Revenue Recovery — Test Suite           ║"
echo "╠══════════════════════════════════════════════════════════════╣"
printf "║  Host:    %-51s║\n" "$HOST"
printf "║  Reports: %-51s║\n" "$ROOT_DIR/$REPORT_DIR"
printf "║  Real HF: %-51s║\n" "$USE_REAL_HF"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
echo "── [0/4] Health check ──────────────────────────────────────────"
if ! curl -sf "$HOST/dashboard/metrics" > /dev/null; then
  echo "  ✗ Server not reachable at $HOST"
  echo "    Start ArthRaksha first:"
  echo "      cd $ROOT_DIR && source venv/bin/activate"
  echo "      python -m uvicorn arthraksha.api.main:app --host 0.0.0.0 --port 8000"
  exit 1
fi
echo "  ✓ Server is up at $HOST"
echo ""

# ---------------------------------------------------------------------------
# Phase 1 — pytest (unit + integration + chaos)
# ---------------------------------------------------------------------------
echo "── [1/4] pytest ────────────────────────────────────────────────"

cd "$ROOT_DIR"

echo "  → Unit tests (guardrails, idempotency, cache, risk router, audit)"
USE_REAL_HF=$USE_REAL_HF pytest pytest/unit/ \
  -v \
  --timeout=30 \
  --tb=short \
  --junitxml="$REPORT_DIR/junit_unit.xml" \
  2>&1 | tee "$REPORT_DIR/pytest_unit.log"

echo ""
echo "  → Integration tests (tier routing, LLM mocking, escalation)"
USE_REAL_HF=$USE_REAL_HF pytest pytest/integration/ \
  -v \
  --timeout=60 \
  --tb=short \
  --junitxml="$REPORT_DIR/junit_integration.xml" \
  2>&1 | tee "$REPORT_DIR/pytest_integration.log"

echo ""
echo "  → Chaos tests (burst, SQLite, overflow, stopping rules)"
USE_REAL_HF=$USE_REAL_HF pytest pytest/chaos/ \
  -v \
  --timeout=120 \
  --tb=short \
  --junitxml="$REPORT_DIR/junit_chaos.xml" \
  2>&1 | tee "$REPORT_DIR/pytest_chaos.log"

echo ""
echo "  ✓ pytest complete"
echo ""

# ---------------------------------------------------------------------------
# Phase 2 — Locust
# ---------------------------------------------------------------------------
echo "── [2/4] Locust load tests ─────────────────────────────────────"

if $SKIP_LOCUST; then
  echo "  ⊘ Skipped (--skip-locust)"
else
  if ! command -v locust &>/dev/null; then
    echo "  ⚠ locust not found — install with: pip install locust"
    echo "  ⊘ Skipping Locust"
  else
    cd "$ROOT_DIR/locust"

    echo "  → Baseline (60/30/10 distribution, 100 users, 30s)"
    locust -f locustfile.py \
      --host "$HOST" \
      --headless \
      -u 100 -r 20 \
      --run-time 30s \
      --csv "$ROOT_DIR/$REPORT_DIR/locust_baseline" \
      --html "$ROOT_DIR/$REPORT_DIR/locust_baseline.html" \
      2>&1 | tee "$ROOT_DIR/$REPORT_DIR/locust_baseline.log"

    echo ""
    echo "  → Spike (500 users, all T2, 20s)"
    locust -f locustfile.py \
      --host "$HOST" \
      --headless \
      -u 500 -r 100 \
      --run-time 20s \
      --csv "$ROOT_DIR/$REPORT_DIR/locust_spike" \
      --html "$ROOT_DIR/$REPORT_DIR/locust_spike.html" \
      --class-picker WorstCaseSpike \
      2>&1 | tee "$ROOT_DIR/$REPORT_DIR/locust_spike.log"

    echo ""
    echo "  → Validation bombardment (malformed only, 50 users, 15s)"
    locust -f locustfile.py \
      --host "$HOST" \
      --headless \
      -u 50 -r 25 \
      --run-time 15s \
      --csv "$ROOT_DIR/$REPORT_DIR/locust_validation" \
      --html "$ROOT_DIR/$REPORT_DIR/locust_validation.html" \
      --class-picker ValidationBombardment \
      2>&1 | tee "$ROOT_DIR/$REPORT_DIR/locust_validation.log"

    echo ""
    echo "  ✓ Locust complete"
  fi
fi

echo ""

# ---------------------------------------------------------------------------
# Phase 3 — k6
# ---------------------------------------------------------------------------
echo "── [3/4] k6 load tests ─────────────────────────────────────────"

if $SKIP_K6; then
  echo "  ⊘ Skipped (--skip-k6)"
else
  if ! command -v k6 &>/dev/null; then
    echo "  ⚠ k6 not found — install: brew install k6"
    echo "  ⊘ Skipping k6"
  else
    cd "$ROOT_DIR/k6"

    echo "  → Baseline scenario"
    BASE_URL="$HOST" k6 run \
      -e SCENARIO=baseline \
      --out json="$ROOT_DIR/$REPORT_DIR/k6_baseline.json" \
      arthraksha_k6.js \
      2>&1 | tee "$ROOT_DIR/$REPORT_DIR/k6_baseline.log"

    echo ""
    echo "  → Spike scenario (T2 heavy)"
    BASE_URL="$HOST" k6 run \
      -e SCENARIO=spike \
      --out json="$ROOT_DIR/$REPORT_DIR/k6_spike.json" \
      arthraksha_k6.js \
      2>&1 | tee "$ROOT_DIR/$REPORT_DIR/k6_spike.log"

    echo ""
    echo "  ✓ k6 complete"
  fi
fi

echo ""

# ---------------------------------------------------------------------------
# Phase 4 — Summary report
# ---------------------------------------------------------------------------
echo "── [4/4] Generating summary ────────────────────────────────────"

SUMMARY="$ROOT_DIR/$REPORT_DIR/SUMMARY.md"

# Parse junit XML for pass/fail counts if xmllint available
unit_pass="-"  unit_fail="-"
integ_pass="-" integ_fail="-"
chaos_pass="-" chaos_fail="-"

if command -v python3 &>/dev/null; then
  _junit_stats() {
    python3 -c "
import xml.etree.ElementTree as ET, sys
try:
    t = ET.parse(sys.argv[1]).getroot()
    ts = t if t.tag == 'testsuite' else t.find('testsuite')
    print(ts.get('tests','?'), ts.get('failures','0'), ts.get('errors','0'))
except: print('? 0 0')
" "$1" 2>/dev/null || echo "? 0 0"
  }
  read -r u_t u_f u_e < <(_junit_stats "$ROOT_DIR/$REPORT_DIR/junit_unit.xml" 2>/dev/null || echo "? 0 0")
  read -r i_t i_f i_e < <(_junit_stats "$ROOT_DIR/$REPORT_DIR/junit_integration.xml" 2>/dev/null || echo "? 0 0")
  read -r c_t c_f c_e < <(_junit_stats "$ROOT_DIR/$REPORT_DIR/junit_chaos.xml" 2>/dev/null || echo "? 0 0")
  unit_pass=$u_t  unit_fail=$((u_f + u_e))
  integ_pass=$i_t integ_fail=$((i_f + i_e))
  chaos_pass=$c_t chaos_fail=$((c_f + c_e))
fi

cat > "$SUMMARY" <<EOF
# ArthRaksha Test Suite — Run Summary
**Date:** $(date)
**Host:** $HOST
**Real HF API:** $USE_REAL_HF

## Results At a Glance

| Phase | Tool | Tests | Failures |
|-------|------|-------|---------|
| Unit | pytest | $unit_pass | $unit_fail |
| Integration | pytest | $integ_pass | $integ_fail |
| Chaos | pytest | $chaos_pass | $chaos_fail |
| Load (Realistic) | Locust | 60/30/10 VU mix, 100 VUs, 30s | — |
| Load (Spike) | Locust | 500 VUs all-T2, 20s | — |
| Load (Validation) | Locust | Malformed bombardment, 50 VUs | — |
| Load (k6 Baseline) | k6 | Threshold-driven baseline | — |
| Load (k6 Spike) | k6 | Threshold-driven spike | — |

## Key SLO Thresholds

| Metric | Target |
|--------|--------|
| Webhook ingestion P99 | < 200 ms (baseline) |
| Server errors (5xx) | 0 |
| Malformed payload acceptance | 0 |
| Overall error rate | < 1% |
| 1000-event burst completion | < 60 s |
| Fraud detection (written_off) | 100% |

## Output Files

\`\`\`
$(ls "$ROOT_DIR/$REPORT_DIR/" 2>/dev/null || echo "No files yet")
\`\`\`
EOF

echo "  ✓ Summary written to: $REPORT_DIR/SUMMARY.md"
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    All tests complete                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "  Reports: $ROOT_DIR/$REPORT_DIR/"
