# Smart Timetable Generator (PS1)

A multi-tenant SaaS scheduling engine that creates **provably conflict-free** timetables via OR-Tools CP-SAT, with independent re-verification.

## Quick Start (Phase 1 — Local Dev)

```bash
# 1. Start Postgres + Redis
docker compose up -d

# 2. API service
cd services/api
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# 3. Solver (for tests)
cd services/solver
pip install -e ".[dev]"
pytest tests/ -v

# 4. Frontend
cd apps/web
npm install
npm run dev
```

## Architecture

See [AGENTS.md](AGENTS.md) for the build companion and [docs/PROJECT_SPEC.md](docs/PROJECT_SPEC.md) for the full spec.

## Current Phase

**Phase 1**: Master data CRUD + single-cohort CP-SAT solver (H1–H9) + one read view.
