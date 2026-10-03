# FlowGuard backend (Person 2)

FastAPI + SQLAlchemy 2 + PostgreSQL + JWT. Contract: `../shared/api-contract.md`.

## Run locally
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # set DATABASE_URL / JWT_SECRET
alembic upgrade head            # create tables
python -m app.db.seed           # or SEED_DEMO_DATA=true to seed on startup
uvicorn app.main:app --reload   # http://localhost:8000/docs
pytest                          # uses in-memory SQLite
```
Quick Postgres: `docker run -d -p 5432:5432 -e POSTGRES_USER=flowguard -e POSTGRES_PASSWORD=flowguard -e POSTGRES_DB=flowguard postgres:16`

Docker: `docker build -t flowguard-backend .` (runs migrations, then uvicorn; Person 4 wires it into docker-compose).

## Layout
`app/api` routers · `app/models` tables + enums · `app/schemas` request/response · `app/services` persistence + placeholders · `app/core` config/security/errors · `app/db` session + seed · `alembic/` migrations
