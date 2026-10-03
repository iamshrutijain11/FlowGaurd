# FlowGuard

Investor grievance tracking platform.

## Monorepo layout

```
flowguard/
├── backend/          ← FastAPI + SQLAlchemy (Person 2)
│   └── app/
│       ├── api/          routers
│       ├── models/       SQLAlchemy tables + enums
│       ├── schemas/      Pydantic request/response
│       ├── services/     persistence + placeholder AI hooks
│       ├── core/         config, security, errors
│       ├── db/           session, seed
│       ├── workflow/     rule engine + state machine (Person 3)
│       └── ai/           LLM extraction + prompts (Person 4)
├── shared/           ← contract docs used by all teams
│   ├── api-contract.md
│   ├── grievance-statuses.md
│   └── demo-data.json
└── docker-compose.yml
```

## Quick start (backend)

```bash
cd backend
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt
cp .env.example .env          # edit DATABASE_URL + JWT_SECRET
alembic upgrade head          # run migrations
pytest                        # 20/20 tests (SQLite, no Postgres needed)
uvicorn app.main:app --reload # http://localhost:8000/docs
```

## Docker (full stack)

```bash
# set JWT_SECRET in your shell first
docker-compose up --build
```

## Demo login

| Field | Value |
|---|---|
| Email | `demo@flowguard.app` |
| Password | `Demo@12345` |
| Grievance | `CMP-2026-DEMO-001` |

## Team handoffs

| Person | Folder | Entry point |
|---|---|---|
| 1 – Frontend | `frontend/` | Calls `http://localhost:8000/api/v1` |
| 2 – Backend | `backend/` | All routes live in `app/api/` |
| 3 – Workflow | `backend/app/workflow/` | `engine.py::run_all_checks`, `state_machine.py::validate_transition` |
| 4 – AI / LLM | `backend/app/ai/` | Replace bodies in `services/next_action_service.py` + `services/explanation_service.py` |
