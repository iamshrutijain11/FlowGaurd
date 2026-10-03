# FlowGuard API contract (Person 2 -> everyone)

Base: `/api/v1` · Swagger: `/docs` · Auth: `Authorization: Bearer <jwt>` (except register/login/health)

Envelope - success `{ "success": true, "data": ..., "message": "..." }`, failure
`{ "success": false, "error": { "code": "GRIEVANCE_NOT_FOUND", "message": "...", "details?": [...] } }`

## Endpoints
| Method | Path | Notes |
|---|---|---|
| GET | `/health` | `{"status":"ok"}` (no envelope) |
| POST | `/auth/register` | `{name\|full_name, email, password(8-72), preferred_language: en\|hi}` -> user |
| POST | `/auth/login` | `{email,password}` -> `{access_token, token_type, expires_in}` |
| GET | `/auth/me` | user |
| GET | `/dashboard/summary` | `{active,on_track,potentially_delayed,resolved}` |
| POST | `/grievances` | `{complaint_id, entity_name, issue_type, issue_description?, submission_date, acknowledgement_date?, current_stage?}` |
| GET | `/grievances?stage=` | list (own only) |
| GET / PATCH | `/grievances/{id}` | PATCH: `entity_name, issue_type, issue_description, current_stage` |
| GET / POST | `/grievances/{id}/events` | POST only `NOTE_ADDED` / `FOLLOW_UP_SENT` (source forced to USER) |
| GET / POST | `/grievances/{id}/documents` | POST multipart: `file` (pdf/png/jpg, <=10MB), `document_type` |
| GET | `/documents/{id}` , `/documents/{id}/download` | download needs the Bearer header |
| GET | `/grievances/{id}/next-action` | `{type,title,description,required_documents[],official_source,is_placeholder}` |
| GET | `/grievances/{id}/explanation` | `{current_situation,timeline_summary,warning_explanation,missing_information[],next_step_summary,generated_at,is_placeholder}` |
| GET | `/notifications?unread_only=` | list |
| PATCH | `/notifications/{id}/read` | |

No DELETE for grievances/events (history is immutable).

## Enums (frozen)
- Stage: `FILED ACKNOWLEDGED AWAITING_RESPONSE RESPONSE_RECEIVED RESOLVED FURTHER_ACTION`
- Warning: `POTENTIAL_DELAY MISSING_INFORMATION FOLLOW_UP_DUE DOCUMENT_REQUIRED NO_RECENT_UPDATE`
- Event type: all stages + all warnings + `REMINDER DOCUMENT_UPLOADED EXTRACTION_COMPLETED DETAILS_UPDATED NOTE_ADDED FOLLOW_UP_SENT`
- Event source: `USER SYSTEM AI ADMIN`
- Document type: `ACKNOWLEDGEMENT RESPONSE SCREENSHOT SUPPORTING_EVIDENCE OTHER`
- Extraction status: `PENDING PROCESSING COMPLETED FAILED`
- Notification type: `STATUS_CHANGED POTENTIAL_DELAY FOLLOW_UP_DUE DOCUMENT_REQUIRED GRIEVANCE_RESOLVED`
- Next-action type: `NO_ACTION FOLLOW_UP REVIEW_DOCUMENTS FURTHER_ACTION_AVAILABLE`

## Warnings (stored separately from stage)
A warning is a SYSTEM event whose type is a warning type. Its `metadata` carries
`severity, rule_id, reason, based_on_event`. A grievance returns `warning` (or `null`) = latest warning
raised since it entered its current stage; changing stage clears it; RESOLVED never shows one.
```json
"warning": { "type":"POTENTIAL_DELAY","severity":"WARNING","rule":"DEMO_AWAITING_RESPONSE_WINDOW",
  "reason":"...","triggered_at":"...","event_id":"uuid","based_on_event":"uuid|null" }
```

## Python services for Person 3 / Person 4 (import, don't re-implement)
- `services.grievance_service`: `get_grievance`, `get_active_grievances(db)`, `update_grievance_stage(db, g, stage, source=SYSTEM, commit=True)`
- `services.event_service`: `create_event`, `list_events`, `create_warning_event(db, g, WarningType, rule_id=, reason=, based_on_event_id=, severity=)` (idempotent per type+rule+stage), `get_active_warning`
- `services.notification_service.create_notification(db, user_id=, grievance_id=, notification_type=, title=, message=)`
- `services.document_service.update_extraction_result(db, doc_id, status=, data=)`
- Replace the placeholder bodies (keep signatures + response shapes): `services.next_action_service.get_next_action`, `services.explanation_service.get_explanation`
- Stage validation: if `app/workflow/state_machine.py` exposes `validate_transition(from_stage: str, to_stage: str) -> bool`, PATCH uses it automatically.

## Demo data
`demo@flowguard.app` / `Demo@12345` · `CMP-2026-DEMO-001` · Demo Brokerage Pvt Ltd · AWAITING_RESPONSE ·
Filed 20 Sep 10:00Z, Acknowledged 20 Sep 12:00Z, Awaiting Response 21 Sep 09:00Z · no response event · no warning seeded.
