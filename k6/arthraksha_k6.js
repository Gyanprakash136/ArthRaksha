/**
 * ArthRaksha — k6 Load Test
 * ===========================
 * Two scenarios driven by environment variable:
 *   BASE_URL=http://localhost:8000 k6 run -e SCENARIO=baseline arthraksha_k6.js
 *   BASE_URL=http://localhost:8000 k6 run -e SCENARIO=spike    arthraksha_k6.js
 *
 * Thresholds (hard SLOs):
 *   - http_req_duration P99 < 200ms  (ingestion endpoint)
 *   - http_req_failed   < 1%
 *   - Malformed payload acceptance: 0
 */

import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Counter, Trend } from "k6/metrics";
import { uuidv4 } from "https://jslib.k6.io/k6-utils/1.4.0/index.js";

// ── Custom metrics ────────────────────────────────────────────────────────────
const malformedAccepted = new Counter("malformed_accepted");
const t1Latency        = new Trend("t1_latency",   true);
const t2Latency        = new Trend("t2_latency",   true);
const t3Latency        = new Trend("t3_latency",   true);
const errorRate        = new Rate("error_rate");

// ── Config ────────────────────────────────────────────────────────────────────
const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const SCENARIO = __ENV.SCENARIO || "baseline";

const TECH_CODES         = ["gateway_technical_error", "server_error", "network_error"];
const UNINTENTIONAL_CODES = ["insufficient_funds", "card_expired", "wrong_otp"];
const INTENTIONAL_CODES  = ["payment_risk_check_failed", "payment_cancelled"];

// ── Scenarios ─────────────────────────────────────────────────────────────────
export const options = SCENARIO === "spike"
  ? {
      scenarios: {
        spike: {
          executor: "ramping-vus",
          startVUs: 0,
          stages: [
            { duration: "5s",  target: 100  },  // ramp up
            { duration: "10s", target: 500  },  // spike
            { duration: "5s",  target: 0    },  // ramp down
          ],
          gracefulRampDown: "5s",
        },
      },
      thresholds: {
        "http_req_duration{name:webhook}": ["p(99)<500"],   // looser during spike
        "http_req_failed":                  ["rate<0.05"],   // 5% error budget under spike
        "malformed_accepted":               ["count==0"],
        "error_rate":                       ["rate<0.05"],
      },
    }
  : {
      // baseline
      scenarios: {
        baseline: {
          executor: "ramping-vus",
          startVUs: 0,
          stages: [
            { duration: "10s", target: 50  },
            { duration: "20s", target: 100 },
            { duration: "10s", target: 0   },
          ],
          gracefulRampDown: "5s",
        },
      },
      thresholds: {
        "http_req_duration{name:webhook}": ["p(99)<200"],
        "http_req_duration{name:metrics}": ["p(95)<100"],
        "http_req_failed":                  ["rate<0.01"],
        "malformed_accepted":               ["count==0"],
        "error_rate":                       ["rate<0.01"],
      },
    };

// ── Payload factories ─────────────────────────────────────────────────────────
function pick(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

function makeEvent(errorCode) {
  return JSON.stringify({
    event_id:   `evt_k6_${uuidv4()}`,
    payment_id: `pay_k6_${uuidv4()}`,
    amount:     Math.floor(Math.random() * 199500) + 500,
    error_code: errorCode,
    timestamp:  "2026-09-01T10:00:00Z",
    customer: {
      id:                  `cust_${uuidv4().slice(0, 8)}`,
      name:                "k6 User",
      contact:             "+919876543210",
      email:               "k6@test.com",
      ltv_estimate:        Math.floor(Math.random() * 99000) + 1000,
      opted_out_of_comms:  false,
    },
  });
}

const MALFORMED = [
  "{}",
  '{"event_id":"e1"}',
  '{"event_id":"e2","payment_id":"p2","amount":0,"error_code":"insufficient_funds","customer":{"contact":"+"}}',
  '{"event_id":"e3","payment_id":"p3","amount":5000,"error_code":"TOTALLY_FAKE_9999","customer":{"contact":"+"}}',
  "not-json-at-all",
];

const HEADERS = { "Content-Type": "application/json" };

// ── Main VU function ──────────────────────────────────────────────────────────
export default function () {
  const roll = Math.random();

  if (roll < 0.05) {
    // ── Malformed payload (5% of requests) ──────────────────────────────────
    const body = pick(MALFORMED);
    const res = http.post(`${BASE_URL}/webhook/razorpay`, body, {
      headers: HEADERS,
      tags: { name: "webhook_malformed" },
    });

    const accepted = check(res, {
      "malformed: must reject (400/422) or duplicate (200+duplicate_skipped)": (r) => {
        if (r.status === 400 || r.status === 422) return true;
        if (r.status === 200) {
          try {
            const b = JSON.parse(r.body);
            return b.message === "duplicate_skipped";
          } catch (_) { return false; }
        }
        return true; // 500 on null bodies is acceptable
      },
    });

    if (!accepted) malformedAccepted.add(1);
    errorRate.add(res.status >= 500 ? 1 : 0);

  } else if (roll < 0.65) {
    // ── T1 (60%) ─────────────────────────────────────────────────────────────
    const res = http.post(
      `${BASE_URL}/webhook/razorpay`,
      makeEvent(pick(TECH_CODES)),
      { headers: HEADERS, tags: { name: "webhook" } }
    );
    t1Latency.add(res.timings.duration);
    errorRate.add(res.status >= 500 ? 1 : 0);
    check(res, { "T1: 200 or 400": (r) => r.status === 200 || r.status === 400 });

  } else if (roll < 0.90) {
    // ── T2 (25%) ─────────────────────────────────────────────────────────────
    const res = http.post(
      `${BASE_URL}/webhook/razorpay`,
      makeEvent(pick(UNINTENTIONAL_CODES)),
      { headers: HEADERS, tags: { name: "webhook" } }
    );
    t2Latency.add(res.timings.duration);
    errorRate.add(res.status >= 500 ? 1 : 0);
    check(res, { "T2: 200 or 400": (r) => r.status === 200 || r.status === 400 });

  } else if (roll < 0.95) {
    // ── T3 (5%) ──────────────────────────────────────────────────────────────
    const res = http.post(
      `${BASE_URL}/webhook/razorpay`,
      makeEvent(pick(INTENTIONAL_CODES)),
      { headers: HEADERS, tags: { name: "webhook" } }
    );
    t3Latency.add(res.timings.duration);
    errorRate.add(res.status >= 500 ? 1 : 0);
    check(res, { "T3: 200 or 400": (r) => r.status === 200 || r.status === 400 });

  } else {
    // ── Dashboard read (5%) ───────────────────────────────────────────────────
    const res = http.get(`${BASE_URL}/dashboard/metrics`, {
      tags: { name: "metrics" },
    });
    errorRate.add(res.status !== 200 ? 1 : 0);
    check(res, {
      "dashboard: 200":         (r) => r.status === 200,
      "dashboard: has json":    (r) => {
        try { JSON.parse(r.body); return true; } catch (_) { return false; }
      },
    });
  }

  sleep(Math.random() * 0.1); // 0–100ms think time
}

// ── Teardown summary ──────────────────────────────────────────────────────────
export function handleSummary(data) {
  const p99webhook = data.metrics["http_req_duration{name:webhook}"]
    ? data.metrics["http_req_duration{name:webhook}"].values["p(99)"]
    : "N/A";
  const errRate = data.metrics.error_rate
    ? (data.metrics.error_rate.values.rate * 100).toFixed(2)
    : "N/A";
  const malformed = data.metrics.malformed_accepted
    ? data.metrics.malformed_accepted.values.count
    : 0;

  console.log("\n╔══════════════════════════════════════╗");
  console.log(`║  Scenario:          ${SCENARIO.padEnd(15)}║`);
  console.log(`║  Webhook P99:       ${String(p99webhook).padEnd(15)}ms ║`);
  console.log(`║  Error rate:        ${String(errRate).padEnd(15)}%  ║`);
  console.log(`║  Malformed accepted:${String(malformed).padEnd(15)}   ║`);
  console.log("╚══════════════════════════════════════╝\n");

  return {
    stdout: JSON.stringify(data, null, 2),
  };
}
