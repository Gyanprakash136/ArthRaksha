You are designing ArthRaksha — a production-ready
AI Revenue Recovery SaaS dashboard for Razorpay
merchants. Integrate this into the Minimalist
Modern design system provided.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL RULE — NO MOCK DATA. EVER.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Every single number, name, amount, percentage,
chart value, table row, and status in this
design must be shown in ONE of two states:

STATE 1 — LOADING (skeleton):
  Animated shimmer placeholder
  Gray rounded rectangle
  Same dimensions as the real content
  No text, no numbers, nothing hardcoded

STATE 2 — POPULATED (API token):
  Shows the data field token it maps to
  Format: {{field_name}}
  Examples:
    {{total_at_risk}}
    {{recovery_rate}}
    {{customer_name}}
    {{error_code}}
    {{amount}}

Design BOTH states for every component.
Loading state = what user sees while
                API call is in flight
Populated state = what user sees when
                  API responds

API ENDPOINTS THAT FEED THIS DASHBOARD:
  GET /dashboard/metrics
    → total_at_risk, total_recovered,
      total_escalated, total_written_off,
      recovery_rate, cache_hit_rate,
      tokens_saved, top_failure_codes,
      agent_tier_breakdown, health_score,
      health_score_delta, trend_7_days

  GET /dashboard/cases
    → cases[] each containing:
      payment_id, customer_name, amount,
      error_code, agent_tier, outcome,
      attempts, age_hours, complexity_score,
      llm_reasoning, audit_log[], ltv,
      months_subscribed, bank_issuer

  GET /dashboard/insights
    → cache_evolution[], failure_breakdown[],
      recovery_path_performance[],
      cross_merchant_patterns[],
      agent_lessons[], tokens_saved,
      token_cost_saved, cache_hit_rate

  GET /dashboard/promises
    → promises[] each containing:
      promise_id, customer_name, amount,
      promised_date, status, reminder_sent

  GET /dashboard/conversations
    → conversations[] each containing:
      transcript_id, customer_name,
      amount, error_code, messages[],
      detected_intent, outcome,
      promise_created

NEVER put a real rupee amount, a real name,
a real percentage, or a real error code
as static content anywhere in this design.
Structure only. Tokens only. Skeletons only.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DESIGN SYSTEM TOKENS — USE EXACTLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

From existing system (do not change):
  background:        #FAFAFA
  foreground:        #0F172A
  muted:             #F1F5F9
  muted-foreground:  #64748B
  accent:            #0052FF
  accent-secondary:  #4D7CFF
  border:            #E2E8F0
  card:              #FFFFFF

Add these semantic tokens:
  success:           #27AE60
  success-light:     #F0FDF4
  warning:           #F2994A
  warning-light:     #FFF7ED
  danger:            #EB5757
  danger-light:      #FFF5F5

Fonts (from existing system):
  Display:    Calistoga (headlines, big numbers)
  UI/Body:    Inter (all UI text, labels, body)
  Monospace:  JetBrains Mono (badges, IDs,
              technical labels, section labels)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LAYOUT SHELL — APPLIES TO ALL PAGES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SIDEBAR (256px fixed left):
  Background: foreground (#0F172A)
  This is the inverted section from the
  design system applied as permanent sidebar.
  Dot pattern texture at 2% opacity (white dots).

  TOP SECTION:
    Logo mark:
      Shield icon in accent gradient background
      32px container, rounded-lg
    Brand:
      "ArthRaksha" Calistoga 18px white
      "Revenue Recovery" JetBrains Mono
      10px muted-foreground uppercase

  NAV ITEMS (vertical, gap-1):
    Height: 40px each
    Padding: 0 12px
    Border-radius: rounded-lg

    Active state:
      Background: accent gradient
      shadow-accent
      Text + icon: white

    Hover state:
      Background: rgba(255,255,255,0.06)
      Text + icon: white

    Default state:
      Text + icon: rgba(255,255,255,0.5)

    Items (icon 18px + label Inter 14px 500):
      LayoutDashboard  "Overview"
      FileText         "Cases"
      Brain            "Intelligence"
      MessageCircle    "Hinglish Recovery"
      Settings         "Settings"

  BOTTOM SECTION:
    Divider: rgba(255,255,255,0.08) 1px
    Merchant avatar:
      Circle 32px accent gradient background
      Initials Calistoga 14px white
    Merchant name: Inter 14px white 500
    Plan badge:
      Accent gradient pill
      JetBrains Mono 10px white uppercase
      "PRO"

TOP HEADER (64px fixed top):
  Background: card (#FFFFFF)
  Border-bottom: 1px solid border
  shadow-sm
  Padding: 0 32px

  Left:
    Page title: Calistoga 22px foreground
    (changes per page — use {{page_title}})

  Center:
    Date range selector:
      Outline button pattern from design system
      Calendar icon left
      "{{date_range}}" Inter 14px
      Chevron right

  Right (gap-3):
    Notification bell:
      Ghost button 40px circle
      Bell icon muted-foreground
      Red dot badge top-right: 8px circle
      Badge shows {{notification_count}}
      JetBrains Mono 9px white

    Run Batch button:
      Primary gradient button
      Play icon left
      "Run Batch" Inter 14px 500
      Pulsing dot indicator (design system)
      when batch is running

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PAGE 1 — OVERVIEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SECTION 1 — REVENUE HEALTH HERO (full width):
  Use INVERTED SECTION pattern from design system
  Background: foreground (#0F172A)
  Dot pattern: white dots 2% opacity
  Radial glow: accent 6% opacity top-right corner
  Border-radius: rounded-2xl
  Padding: 40px
  Border: 1px solid rgba(255,255,255,0.08)

  TWO COLUMN LAYOUT (60% / 40%):

  LEFT COLUMN:
    Section label badge (design system pattern):
      Pill: accent/20 border, accent/10 bg
      Dot: accent (pulsing animation)
      Text: JetBrains Mono 11px uppercase
            "REVENUE HEALTH SCORE"

    LOADING STATE:
      Skeleton: 80px tall, 160px wide
                rounded-lg shimmer

    POPULATED STATE:
      Score: "{{health_score}}" Calistoga
              96px white line-height 1
      "/100" Calistoga 36px
             rgba(255,255,255,0.4)
             same baseline

    Trend (design system badge pattern):
      LOADING: skeleton 80px × 24px
      POPULATED:
        Success variant pill
        Pulsing green dot
        "{{health_score_delta}} vs yesterday"
        Inter 13px

    Description:
      LOADING: two skeleton lines
               full width + 60% width
      POPULATED:
        Inter 15px rgba(255,255,255,0.65)
        "Your recovery is {{health_status}}.
         {{action_count}} cases need attention."

    Button row (gap-3):
      Primary gradient: "View Cases →"
      Ghost white: "Run New Batch"

  RIGHT COLUMN:
    Circular gauge:
      LOADING STATE:
        Circle skeleton 140px diameter shimmer

      POPULATED STATE:
        SVG circle gauge:
          Track: rgba(255,255,255,0.1) stroke
          Fill: accent gradient stroke
                dasharray calculated from
                {{health_score}} / 100
          Center:
            "{{health_score}}" Calistoga
             48px white
            "Health Score" Inter 11px
             JetBrains Mono muted-foreground

SECTION 2 — METRIC CARDS (4 equal, gap-4):

  ALL CARDS USE:
    Standard card pattern from design system
    shadow-md default
    shadow-lg + gradient overlay on hover
    Border-radius: rounded-xl
    Padding: 24px
    Top border: 3px solid (semantic color)

  CARD STRUCTURE (all 4 follow this):
    Row 1:
      Left: icon 20px (semantic color)
      Right: section label badge variant
             JetBrains Mono 10px uppercase

    Row 2 (main metric):
      LOADING: skeleton 120px × 36px shimmer
      POPULATED: Calistoga 32px (semantic color)
                 "{{metric_value}}"

    Row 3:
      LOADING: skeleton 80px × 16px shimmer
      POPULATED: Inter 13px muted-foreground
                 "{{metric_sub}}"

    Row 4 (optional trend):
      LOADING: skeleton 100px × 20px shimmer
      POPULATED: pill badge semantic color
                 "{{metric_trend}}"

  CARD 1 — AT RISK:
    Top border: border color (neutral)
    Icon: TrendingDown muted-foreground
    Label: "TOTAL AT RISK"
    Value token: {{total_at_risk}}
    Sub token: "{{total_cases}} cases active"
    No trend badge

  CARD 2 — RECOVERED:
    Top border: success
    Icon: CheckCircle success
    Label: "RECOVERED"
    Value token: {{total_recovered}}
                 USE gradient-text class
                 from design system
    Sub token: "{{recovered_cases}} cases
                · {{recovery_rate}}"
    Trend badge: success variant
                 "{{recovery_trend}}"
                 pulsing dot

  CARD 3 — IN PROGRESS:
    Top border: warning
    Icon: Clock warning
    Label: "IN PROGRESS"
    Value token: {{total_escalated}}
                 warning color
    Sub token: "{{escalated_cases}} cases
                · {{escalation_rate}}"

  CARD 4 — WRITTEN OFF:
    Top border: danger
    Icon: XCircle danger
    Label: "WRITTEN OFF"
    Value token: {{total_written_off}}
                 danger color
    Sub token: "{{written_off_cases}} cases
                · {{written_off_rate}}"

SECTION 3 — CHARTS ROW (60% / 40% gap-4):

  LEFT CARD — Recovery Trend:
    Header row:
      "Recovery Performance" Inter 16px 600
      Badge: JetBrains Mono "{{date_range}}"
             accent variant

    LOADING STATE:
      Rectangle skeleton full width
      200px tall shimmer

    POPULATED STATE:
      Area chart (two smooth curves):
        Curve 1: accent gradient fill
                 label: "Recovered"
                 data: {{trend_recovered[]}}
        Curve 2: danger 40% opacity fill
                 label: "Lost"
                 data: {{trend_lost[]}}
        X axis: {{trend_labels[]}}
                Inter 11px muted-foreground
        Grid: border color dashed 1px

  RIGHT CARD — Agent Tiers:
    Header: "Agent Performance" Inter 16px 600

    Three tier rows (gap-5):
    Each row:
      Top row: label Inter 14px +
               right: "{{tier_success_rate}}"
               success color Inter 14px 500

      Progress bar:
        Track: muted 6px tall rounded-full
        Fill: semantic color rounded-full
              width: {{tier_case_percentage}}

      Sub: "{{tier_cases}} cases
            · {{tier_amount}}"
           Inter 12px muted-foreground

    LOADING STATE for each row:
      Label skeleton 80px × 14px
      Bar skeleton full width × 6px
      Sub skeleton 120px × 12px

    POPULATED STATE:
      T1: accent gradient fill
          label: "T1 — Auto Retry"
      T2: warning fill
          label: "T2 — LLM Agent"
      T3: danger fill
          label: "T3 — Escalated"

SECTION 4 — ACTION REQUIRED (full width):
  Card with warning/20 border
  Card background with warning/3 tint

  Header row:
    Left:
      AlertTriangle icon warning 18px
      "Action Required" Inter 16px 600
    Right:
      Warning badge pill:
        "{{action_count}} items"
        JetBrains Mono

  LOADING STATE:
    Three skeleton rows:
      Each: full width × 56px shimmer
      gap-1 between

  POPULATED STATE:
    Renders {{action_items[]}} dynamically
    Each item row (divider between):
      Left (gap-2):
        Semantic color dot (pulsing if urgent)
        Type label JetBrains Mono 11px
                   uppercase muted-foreground
      Mid:
        "{{action_customer}} · {{action_amount}}"
        Inter 14px 500 foreground
        "{{action_description}}"
        Inter 12px muted-foreground
      Right (gap-2):
        Primary action: outline button
                        semantic color variant
                        "{{action_primary_label}}"
        Secondary: ghost button
                   "{{action_secondary_label}}"

    EMPTY STATE (zero action items):
      CheckCircle icon success 32px centered
      "No actions needed" Inter 15px 600
      "All cases are processing normally"
      Inter 13px muted-foreground

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PAGE 2 — CASES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Two panel layout.
Left panel: 55% width
Right panel: 45% width (hidden until row click)
When right panel opens: left shrinks to 55%
smooth transition 300ms ease-out

LEFT PANEL:

  TOP BAR (gap-3):
    Search input (design system pattern):
      height: 44px
      rounded-xl
      border: 1px solid border
      focus: ring-2 ring-accent
      Magnifier icon: muted-foreground left
      Placeholder: "Search by customer,
                    payment ID, error..."
      muted-foreground/50

    Export button:
      Outline button pattern
      Download icon
      "Export CSV"

  FILTER PILLS (horizontal scroll, gap-2):
    Use outline button pattern
    Active: accent gradient bg, white text
    Inactive: muted bg, border, foreground text
    JetBrains Mono 11px uppercase

    Pills (count from API):
      "ALL {{total_count}}"
      "ACTION NEEDED {{action_count}}"
      "RECOVERED {{recovered_count}}"
      "ESCALATED {{escalated_count}}"
      "WRITTEN OFF {{written_off_count}}"

  TABLE:
    Container: card rounded-xl border shadow-sm
    overflow hidden

    HEADER ROW:
      Background: muted
      Height: 40px
      Padding: 0 16px
      JetBrains Mono 10px uppercase
      letter-spacing: 0.1em
      muted-foreground
      Columns: CUSTOMER | AMOUNT | ERROR |
               TIER | STATUS | AGE | —

    LOADING STATE (5 skeleton rows):
      Each row height: 56px
      Cells: skeleton shimmer rectangles
             matching column widths
      Alternating opacity for depth

    POPULATED STATE:
      Renders {{cases[]}} from API
      Each row (height 56px):
        Hover: accent/3 bg
        Selected: accent/8 bg +
                  2px accent left border
        Padding: 0 16px

        CUSTOMER cell:
          Avatar circle 32px:
            accent gradient bg
            Initials: Calistoga 13px white
            Generated from {{customer_name}}
          Right of avatar (gap-2):
            "{{customer_name}}" Inter 14px 500
            "{{payment_id}}" JetBrains Mono
             10px muted-foreground

        AMOUNT cell:
          "{{amount}}" Inter 14px 500
          foreground

        ERROR cell:
          Pill badge (semantic by error type):
            Text: "{{error_code}}"
            JetBrains Mono 10px
            Color determined by error category:
              TECHNICAL:    muted bg/text
              UNINTENTIONAL:accent/10 bg
                            accent text
              AMBIGUOUS:    warning/10 bg
                            warning text
              INTENTIONAL:  danger/10 bg
                            danger text

        TIER cell:
          Badge pill:
            T1: success-light bg
                success text
                "T1 · AUTO"
            T2: accent/10 bg
                accent text
                "T2 · LLM"
            T3: danger-light bg
                danger text
                "T3 · HUMAN"
          JetBrains Mono 10px

        STATUS cell:
          Dot + label Inter 13px:
            recovered:   success dot
            escalated:   warning dot (pulsing)
            written_off: danger dot
            pending:     muted dot (pulsing)
          "{{outcome}}"

        AGE cell:
          "{{age_hours}}h ago"
          Inter 12px muted-foreground

        ACTION cell (visible on row hover):
          Ghost buttons Inter 12px accent:
            "Send Link" "View"

    FOOTER:
      Pagination Inter 14px
      "Showing {{start}}-{{end}}
       of {{total_count}} cases"
      ← prev  {{pages}}  next →

  EMPTY STATE (zero cases):
    Centered in table area:
    FileSearch icon 48px muted-foreground
    "No cases found" Calistoga 20px
    "Try adjusting your filters"
    Inter 14px muted-foreground
    [Clear Filters] outline button

RIGHT PANEL (slides in on row click):
  Background: card
  Border-left: 1px solid border
  shadow-xl
  Padding: 24px
  Overflow-y: scroll

  HEADER:
    Row: "Case Detail" Inter 16px 600 +
         X button ghost right
    "{{payment_id}}" JetBrains Mono 12px
                     muted-foreground
    Status badge: "{{outcome}}"
                  semantic color variant

  LOADING STATE:
    Stack of skeleton blocks:
      60px, 80px, 120px, 200px heights
      Full width shimmer

  POPULATED STATE:

    CUSTOMER BLOCK (card inside card):
      muted background rounded-lg p-16
      Avatar 40px accent gradient + initials
      "{{customer_name}}" Inter 15px 600
      "{{months_subscribed}} months
       · {{bank_issuer}}" Inter 13px
       muted-foreground
      LTV row:
        "{{ltv}}" Inter 14px 500 success
        "lifetime value" Inter 12px
         muted-foreground

    PAYMENT BLOCK:
      "{{amount}}" Calistoga 28px foreground
      "{{error_code}}" badge semantic color
      "{{payment_method}}" Inter 13px
       muted-foreground
      "Failed {{timestamp}}" Inter 12px
       muted-foreground

    AGENT DECISION BLOCK:
      muted background rounded-lg p-16
      Header: Brain icon accent 16px +
              "Agent Decision" Inter 14px 600
      Rows (label: value pattern):
        Tier: "{{agent_tier}}" badge
        Score: "{{complexity_score}}"
               Inter 14px muted-foreground
        Cache: "{{cache_hit}}"
               success if hit,
               muted if miss
        Tokens: "{{tokens_used}} tokens"
        Reasoning (if T2/T3):
          Italic Inter 13px muted-foreground
          quote marks design system style
          "{{llm_reasoning}}"

    TIMELINE BLOCK:
      "Audit Trail" Inter 14px 600
      Vertical timeline (design system
      arrow connector pattern):
        Each entry from {{audit_log[]}}:
          Dot: accent 6px circle
          Vertical line: border color
          Timestamp: JetBrains Mono 10px
                     muted-foreground
          Action: Inter 13px foreground
                  "{{action_taken}}"
          Reason: Inter 12px
                  muted-foreground
                  "{{action_reason}}"

        Final entry (if recovered):
          Dot: success larger 8px
          "{{amount}} recovered"
          Inter 13px success 500

      LOADING: 4 skeleton timeline entries

    ACTION BUTTONS (sticky bottom):
      Border-top: 1px solid border
      Padding-top: 16px
      gap-2:
        Primary gradient: "Send Payment Link"
        Outline danger: "Write Off"
        Outline warning: "Escalate"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PAGE 3 — INTELLIGENCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SECTION 1 — CACHE LEARNING (full width):
  INVERTED SECTION from design system:
    Background: foreground (#0F172A)
    Dot pattern texture 2% opacity
    Radial glow accent top-right
    Border-radius: rounded-2xl
    Padding: 40px

  Header row:
    Left:
      Section label badge:
        JetBrains Mono: "AGENT LEARNING"
        Pulsing accent dot
      Title: Calistoga 28px white
             "Intelligence Grew During Run"
      Sub: Inter 15px rgba(255,255,255,0.6)
           "Cache hit rate improved as agent
            learned from each event processed"
    Right (gap-3):
      Three metric pills (muted/10 bg):
        "{{final_cache_hit_rate}} hit rate"
        "{{tokens_saved}} tokens saved"
        "₹{{token_cost_saved}} saved"
        Each: JetBrains Mono 11px white
              accent left border 2px

  CHART AREA:
    LOADING: full width 200px skeleton shimmer

    POPULATED:
      Line chart smooth curve:
        X axis: "{{cache_evolution[].event_number}}"
                Inter 11px rgba(255,255,255,0.4)
        Y axis: 0% to 100%
                Inter 11px rgba(255,255,255,0.4)
        Line: accent gradient stroke 2px
        Fill: accent gradient 15% opacity
        Grid: rgba(255,255,255,0.06) dashed
        Tooltip on hover:
          Card background
          "Event {{n}}: {{hit_rate}} hit rate"

SECTION 2 — TWO COLUMNS (50/50 gap-4):

  LEFT — Failure Pattern:
    Card standard pattern
    Header:
      "Why Revenue Is At Risk" Inter 16px 600
      Section label: "FAILURE ANALYSIS"
                     muted variant

    LOADING: stack of 3 skeleton bars

    POPULATED:
      Renders {{failure_breakdown[]}} from API
      Each category row:
        Label Inter 14px foreground
        Right: "{{percentage}}"
               Inter 14px 500 semantic color
        Bar:
          Track: muted full width 8px rounded
          Fill: semantic color
                width: {{percentage}}
          Margin-bottom: 16px
        Sub: "{{case_count}} cases"
             Inter 12px muted-foreground

    EMPTY STATE:
      No data yet. Run a batch first.

  RIGHT — Recovery Path Performance:
    Card standard pattern
    Header: "What's Working" Inter 16px 600

    LOADING: table skeleton 4 rows

    POPULATED:
      Table (no outer border):
        Header: JetBrains Mono 10px uppercase
                muted-foreground
                PATH | USED | SUCCESS RATE
        Rows from {{recovery_path_performance[]}}:
          Path: Inter 13px foreground
                "{{path_name}}"
          Used: Inter 13px muted-foreground
                "{{path_count}} cases"
          Rate: Progress mini-bar 40px wide
                + "{{success_rate}}"
                Inter 13px success 500

SECTION 3 — PLATFORM ALERT:
  LOADING: skeleton card full width 80px

  POPULATED (only shows if pattern detected):
    {{cross_merchant_patterns[]}} → if empty
    this section is hidden entirely

    Card:
      Border: 1px solid warning/40
      Background: warning/5
      Padding: 24px
      Row layout:
        Left: AlertTriangle warning 24px
        Mid:
          "Cross-Merchant Pattern Detected"
          Inter 15px 600 foreground
          "{{pattern_description}}"
          Inter 13px muted-foreground
        Right:
          Outline warning button
          "View {{affected_count}} Cases"

SECTION 4 — AGENT LESSONS:
  Header row:
    "What ArthRaksha Learned" Calistoga 24px
    Section label: "LESSONS · {{lesson_count}}"
                   JetBrains Mono accent

  LOADING: 3 skeleton cards in a row

  POPULATED:
    Grid: 3 columns gap-4
    Renders {{agent_lessons[]}} from API

    Each lesson card (standard card pattern):
      Icon container:
        Gradient background (design system)
        32px rounded-lg
        Semantic icon based on lesson type
      Title: Inter 14px 600 foreground
             "{{lesson_title}}"
      Body: Inter 13px muted-foreground
            line-height 1.6
            "{{lesson_description}}"

    EMPTY STATE:
      "Lessons appear after batch runs"
      Inter 14px muted-foreground centered

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PAGE 4 — HINGLISH RECOVERY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

HEADER:
  Section label badge:
    "DIFFERENTIATOR FEATURE"
    Accent gradient background white text
    Pulsing dot
  Title: Calistoga 28px foreground
         "Hinglish Recovery Conversations"
  Sub: Inter 15px muted-foreground
       "AI agent communicates naturally in
        Hindi and English for better recovery"

TWO COLUMN LAYOUT (35% / 65%):

  LEFT — Conversation List:
    LOADING: 5 skeleton conversation cards

    POPULATED:
      Renders {{conversations[]}} from API
      Each card (standard card pattern):
        Padding: 16px
        Cursor: pointer
        Selected: accent/8 bg
                  accent left border 2px

        Row 1:
          Avatar 32px accent gradient
          initials from {{customer_name}}
          Right:
            "{{customer_name}}" Inter 14px 500
            "{{timestamp}}" Inter 11px
             muted-foreground right-aligned

        Row 2:
          "{{amount}}" Inter 13px foreground
          Intent badge right:
            will_pay:  success variant "Will Pay"
            promised:  accent variant "Promised"
            churned:   danger variant "Churned"
            unclear:   muted variant "Unclear"

        Row 3:
          Last message preview:
          "{{last_message_preview}}"
          Inter 12px muted-foreground
          single line truncated

      EMPTY STATE:
        MessageCircle 48px muted-foreground
        "No conversations yet"
        "Run a batch to generate
         Hinglish recovery conversations"

  RIGHT — Chat Window:
    EMPTY STATE (no conversation selected):
      Centered in panel:
      MessageCircle 48px muted-foreground
      "Select a conversation"
      Inter 14px muted-foreground

    LOADING STATE (conversation loading):
      Alternating skeleton chat bubbles:
        Left bubble: skeleton 240px × 48px
        Right bubble: skeleton 180px × 36px
        3 pairs