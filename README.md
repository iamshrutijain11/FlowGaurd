# FlowGuard

AI-powered investor grievance tracking and escalation assistant (SANGYAN Investor Resilience Hackathon, Track B).

FlowGuard shows an investor where their grievance stands, what has happened so far, whether a potential delay was detected, what information may be missing, and what legitimate next step is available. It is not a stock advisory tool: no buy/sell recommendations, no price predictions, no invented regulatory deadlines.

The product keeps four kinds of information separate:
1. Recorded facts
2. FlowGuard warnings (deterministic rules, shown as "potential delay", never as a violation)
3. AI-generated explanations (based only on recorded case data)
4. Verified official guidance

## Monorepo layout

```
flowguard/
├── frontend/         Next.js + React + TypeScript + Tailwind (Person 1)
├── backend/          FastAPI + SQLAlchemy (Person 2)
│   └── app/
│       ├── api/            routers
│       ├── models/         tables + enums
│       ├── schemas/        request/response models
│       ├── services/       persistence + integration
│       ├── core/           config, security, errors
│       ├── db/             session, seed
│       ├── workflow/       rule engine + state machine (Person 3)
│       ├── ai/             explanation, evidence helper, document extraction, verified guidance (Person 4)
│       └── notifications/  in-app notifications (Person 4)
├── shared/           contract docs (api-contract.md, grievance-statuses.md, demo-data.json)
├── docker-compose.yml
└── docker-compose.person4.yml
```

## Quick start (Windows, Command Prompt)

### Backend

```
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` and set:

| Variable | Value |
|---|---|
| `DATABASE_URL` | `sqlite:///./flowguard.db` (local) or a Postgres URL |
| `JWT_SECRET` | any long random string |
| `LLM_API_KEY` | your Gemini API key (optional: without it, explanations use a built-in fallback template) |
| `ALLOWED_ORIGINS` | `http://localhost:3000` |
| `AUTO_CREATE_TABLES` / `SEED_DEMO_DATA` | `true` for local demo |

Run:

```
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs  Health check: http://localhost:8000/health

Tests: `pytest`

### Frontend

```
cd frontend
npm install
echo NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1> .env.local
npm run dev
```

Open http://localhost:3000/login

## Demo login

| Field | Value |
|---|---|
| Email | `demo@flowguard.app` |
| Password | `Demo@12345` |
| Grievance | `CMP-2026-DEMO-001` |

Demo path: dashboard, open the grievance, pipeline (Awaiting Response), potential-delay warning, plain-language explanation, next action and evidence checklist, timeline, notification, English/Hindi switch.

## How it fits together

- The **workflow engine** (`backend/app/workflow/`) decides stages and potential-delay warnings from configurable demo rules. The AI never decides deadlines.
- The **AI layer** (`backend/app/ai/`) explains the case in simple language using only the recorded grievance, events, documents, workflow result and verified guidance. If the LLM is unavailable, a deterministic fallback response is returned.
- **Document extraction** returns suggested values with confidence; they are not saved as confirmed fields until the user validates them.
- Time windows in the demo are labelled "demo configuration" and are not official regulatory deadlines.

## Docker

```
docker-compose up --build
```

Set JWT_SECRET and LLM_API_KEY in your environment first, and make sure backend/.env exists. docker-compose.person4.yml is an alternative full-stack compose file (backend + PostgreSQL) that reads backend/.env.

## Team

| Person | Area |
|---|---|
| 1 | Frontend (`frontend/`) |
| 2 | Backend, database, auth, APIs (`backend/app/api`, `models`, `schemas`, `core`, `db`) |
| 3 | Workflow engine and delay detection (`backend/app/workflow/`) |
| 4 | AI explanations, guidance, notifications, integration (`backend/app/ai/`, `backend/app/notifications/`) |