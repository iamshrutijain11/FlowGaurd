FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# Install build deps for psycopg2 (still in requirements for Postgres compat)
# but we only need it if DATABASE_URL is postgres. For SQLite it's not used.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Persistent data dirs
RUN mkdir -p /app/uploads /app/data

EXPOSE 8000

# If DATABASE_URL starts with "sqlite", skip alembic and use AUTO_CREATE_TABLES.
# If PostgreSQL, run alembic migrations first.
CMD ["sh", "-c", "\
  if echo \"$DATABASE_URL\" | grep -q '^sqlite'; then \
    echo 'SQLite mode: skipping alembic, using AUTO_CREATE_TABLES'; \
  else \
    alembic upgrade head; \
  fi && \
  uvicorn app.main:app --host 0.0.0.0 --port 8000"]
