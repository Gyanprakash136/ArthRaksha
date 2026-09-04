# Escalation Templates

These templates are used to create tickets for human review, preventing LLM calls for standard escalations.

## Template 1: Fraud/Risk Flag
**Subject**: [URGENT] Fraud Risk Flag on Event {event_id}
**Priority**: CRITICAL
**Body**:
The automated recovery system has flagged this event for suspected fraud.
- Customer ID: {customer_id}
- Merchant ID: {merchant_id}
- Amount: ₹{amount}
- Error Reason: {error_reason}
- Evidence: {evidence_list}

**Action Required**: Please review the transaction and customer history. Contact the risk team if necessary.

## Template 2: High Value Override
**Subject**: [REVIEW] High Value Action Override Requested
**Priority**: HIGH
**Body**:
A recovery action was proposed for a high-value transaction (₹{amount}), exceeding automated thresholds.
- Strategy Proposed: {strategy}
- Reason: {reason}
- EV: ₹{ev}

**Action Required**: Approve or override the proposed strategy.

## Template 3: Repeated Promise Broken
**Subject**: [ESCALATION] Customer Broke Payment Promise {broken_count} Times
**Priority**: MEDIUM
**Body**:
Customer {customer_name} has broken {broken_count} payment promises.
- Promise Dates: {promise_dates}
- Total Owed: ₹{total_owed}

**Action Required**: Manual outreach required. Consider freezing account services.
