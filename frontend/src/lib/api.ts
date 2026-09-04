/**
 * ArthRaksha API — backend connection map
 *
 * BASE: Set VITE_API_BASE_URL in .env (default: http://localhost:8000/api/v1)
 * AUTH: Bearer token via Authorization header
 *
 * Every {{field_name}} token in the UI maps to a field from one of these endpoints.
 * Replace BASE_URL with your deployed backend URL before shipping.
 */

export const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";
export const MERCHANT_ID = import.meta.env.VITE_MERCHANT_ID ?? "{{merchant_id}}";

// ── Auth helper ───────────────────────────────────────────────────────────────
export function authHeaders(): HeadersInit {
  const token = localStorage.getItem("arthraksha_token");
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

// ── Shared fetcher ────────────────────────────────────────────────────────────
export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: authHeaders(),
    ...options,
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  return res.json() as Promise<T>;
}

// ══════════════════════════════════════════════════════════════════════════════
// OVERVIEW PAGE  →  GET /overview
// Response shape covers all {{...}} tokens on the Overview page
// ══════════════════════════════════════════════════════════════════════════════
export const ENDPOINTS = {
  /**
   * GET /overview?merchant_id=&date_from=&date_to=
   * Tokens: health_score, health_trend, health_description,
   *         at_risk_amount, at_risk_count, recovered_amount, recovered_count,
   *         recovered_trend_pct, in_progress_amount, in_progress_count,
   *         written_off_amount, written_off_count,
   *         recovery_rate_by_tier[].tier, recovery_rate_by_tier[].rate,
   *         action_items[].customer_name, action_items[].amount,
   *         action_items[].reason, action_items[].severity,
   *         date_range
   */
  overview: `${BASE_URL}/overview`,

  /**
   * GET /cases?merchant_id=&page=&per_page=&status=&tier=&error_category=&q=
   * Tokens: case_id, customer_name, amount, error_category, tier_label,
   *         status, days_since, attempt_count, last_contact,
   *         filter_count, start, end, total_count,
   *         + full case detail on /cases/:case_id
   */
  cases:     `${BASE_URL}/cases`,
  caseById:  (id: string) => `${BASE_URL}/cases/${id}`,

  /**
   * GET /intelligence?merchant_id=&run_id=
   * Tokens: final_cache_hit_rate, tokens_saved, token_cost_saved,
   *         cache_evolution[].event_number, cache_evolution[].hit_rate,
   *         failure_breakdown[].category, failure_breakdown[].pct, failure_breakdown[].cases,
   *         recovery_path_performance[].path_name, recovery_path_performance[].count, recovery_path_performance[].success_rate,
   *         cross_merchant_patterns[].pattern_description, cross_merchant_patterns[].affected_count,
   *         agent_lessons[].title, agent_lessons[].description, lesson_count
   */
  intelligence: `${BASE_URL}/intelligence`,

  /**
   * GET /conversations?merchant_id=&page=&per_page=
   * Tokens: conversations[].customer_name, conversations[].timestamp,
   *         conversations[].amount, conversations[].detected_intent,
   *         conversations[].last_message_preview,
   *         messages[].text, messages[].from, messages[].timestamp,
   *         detected_intent, confidence, outcome
   */
  conversations:    `${BASE_URL}/conversations`,
  conversationById: (id: string) => `${BASE_URL}/conversations/${id}`,

  /**
   * GET /promises?merchant_id=
   * Tokens: promises[].customer_name, promises[].amount,
   *         promises[].promised_date, promises[].promise_status
   */
  promises: `${BASE_URL}/promises`,

  /**
   * GET  /settings?merchant_id=
   * POST /settings  (save)
   * Tokens: merchant_name, merchant_id, industry_vertical, contact_email,
   *         recovery_tier, monthly_recovery_target,
   *         webhook_url, webhook_secret, retry_attempts, timeout_ms, webhook_status,
   *         hinglish_enabled, auto_escalation, cross_merchant_enabled, batch_scheduling,
   *         aggressiveness_level, max_attempts, cooldown_days, contact_window,
   *         notify_batch_complete, notify_high_value, notify_anomalies, notify_weekly_digest,
   *         notification_emails, api_key_1, api_key_2
   */
  settings:       `${BASE_URL}/settings`,

  /**
   * POST /batch/run  { merchant_id, date_from, date_to }
   * Kicks off a recovery batch. Streams progress via SSE:
   * GET  /batch/:run_id/events  (text/event-stream)
   */
  batchRun:        `${BASE_URL}/batch/run`,
  batchEvents:     (runId: string) => `${BASE_URL}/batch/${runId}/events`,

  /**
   * POST /webhooks/test  { merchant_id }
   * Fires a test payload to the configured webhook URL.
   */
  webhookTest:     `${BASE_URL}/webhooks/test`,

  /**
   * POST /api-keys/generate  { merchant_id }
   * PUT  /api-keys/:key_id/rotate
   * DELETE /api-keys/:key_id
   */
  apiKeyGenerate:  `${BASE_URL}/api-keys/generate`,
  apiKeyRotate:    (id: string) => `${BASE_URL}/api-keys/${id}/rotate`,
  apiKeyRevoke:    (id: string) => `${BASE_URL}/api-keys/${id}`,
} as const;

// ══════════════════════════════════════════════════════════════════════════════
// Typed response shapes (expand as backend schema firms up)
// ══════════════════════════════════════════════════════════════════════════════

export interface OverviewResponse {
  health_score: number;            // 0–100
  health_trend: string;            // e.g. "+3.2%"
  health_description: string;
  date_range: string;              // e.g. "Aug 1–28, 2026"
  at_risk_amount: string;
  at_risk_count: number;
  recovered_amount: string;
  recovered_count: number;
  recovered_trend_pct: string;
  in_progress_amount: string;
  in_progress_count: number;
  written_off_amount: string;
  written_off_count: number;
  recovery_rate_by_tier: Array<{ tier: string; rate: number }>;
  action_items: Array<{
    customer_name: string;
    amount: string;
    reason: string;
    severity: "high" | "medium" | "low";
  }>;
}

export interface CaseListResponse {
  data: Array<{
    case_id: string;
    customer_name: string;
    amount: string;
    error_category: "technical" | "unintentional" | "ambiguous" | "intentional";
    tier_label: "T1·AUTO" | "T2·LLM" | "T3·HUMAN";
    status: "escalated" | "pending" | "recovered" | "written_off";
    days_since: number;
    attempt_count: number;
    last_contact: string;
  }>;
  start: number;
  end: number;
  total_count: number;
  filter_count: number;
}

export interface IntelligenceResponse {
  final_cache_hit_rate: string;
  tokens_saved: string;
  token_cost_saved: string;
  cache_evolution: Array<{ event_number: number; hit_rate: number }>;
  failure_breakdown: Array<{ category: string; pct: number; cases: number }>;
  recovery_path_performance: Array<{ path_name: string; count: number; success_rate: string }>;
  cross_merchant_patterns: Array<{ pattern_description: string; affected_count: number }>;
  agent_lessons: Array<{ title: string; description: string }>;
  lesson_count: number;
}

export interface ConversationsResponse {
  data: Array<{
    id: string;
    customer_name: string;
    timestamp: string;
    amount: string;
    detected_intent: "will_pay" | "promised" | "churned" | "unclear";
    confidence: string;
    last_message_preview: string;
  }>;
  total_count: number;
}

export interface ConversationDetailResponse {
  customer_name: string;
  messages: Array<{ from: "customer" | "bot"; text: string; timestamp: string }>;
  detected_intent: string;
  confidence: string;
  outcome: string;
}

export interface SettingsResponse {
  merchant_name: string;
  merchant_id: string;
  industry_vertical: string;
  contact_email: string;
  recovery_tier: string;
  monthly_recovery_target: string;
  webhook_url: string;
  webhook_secret: string;
  retry_attempts: number;
  timeout_ms: number;
  webhook_status: string;
  hinglish_enabled: boolean;
  auto_escalation: boolean;
  cross_merchant_enabled: boolean;
  batch_scheduling: boolean;
  aggressiveness_level: string;
  max_attempts: number;
  cooldown_days: number;
  contact_window: string;
  notify_batch_complete: boolean;
  notify_high_value: boolean;
  notify_anomalies: boolean;
  notify_weekly_digest: boolean;
  notification_emails: string;
  api_key_1: string;
  api_key_2: string;
}
