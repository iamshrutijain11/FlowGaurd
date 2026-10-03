# FlowGuard – Grievance Stage Reference

Stages are **frozen** — names must match the API contract exactly.

| Stage | Label | Meaning |
|---|---|---|
| `FILED` | Filed | Investor has submitted the complaint. |
| `ACKNOWLEDGED` | Acknowledged | Entity has sent an acknowledgement. |
| `AWAITING_RESPONSE` | Awaiting Response | Within the regulatory response window. |
| `RESPONSE_RECEIVED` | Response Received | Entity response recorded in FlowGuard. |
| `RESOLVED` | Resolved | Investor is satisfied; case closed. |
| `FURTHER_ACTION` | Further Action | Escalation / regulatory body referral required. |

## Allowed Transitions (state_machine.py)

```
FILED → ACKNOWLEDGED
ACKNOWLEDGED → AWAITING_RESPONSE
AWAITING_RESPONSE → RESPONSE_RECEIVED | FURTHER_ACTION | RESOLVED
RESPONSE_RECEIVED → RESOLVED | FURTHER_ACTION
FURTHER_ACTION → RESOLVED
RESOLVED → (terminal)
```

## Warnings (never change the stage)

| Warning | Meaning |
|---|---|
| `POTENTIAL_DELAY` | No response within monitoring window |
| `MISSING_INFORMATION` | Required fields or documents absent |
| `FOLLOW_UP_DUE` | Investor should send a follow-up |
| `DOCUMENT_REQUIRED` | Missing supporting document |
| `NO_RECENT_UPDATE` | No activity for an extended period |
