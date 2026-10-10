# HireTrack API

A REST API for tracking job applications — built with **FastAPI**, **PostgreSQL**
(via SQLAlchemy 2.0), and **JWT authentication**. Each user manages their own
pipeline of applications: wishlist → applied → interviewing → offered / rejected.

## Features

- User registration and login (OAuth2 password flow, bcrypt-hashed passwords)
- JWT bearer-token authentication; users can only access their own data
- Full CRUD for job applications
- List with filtering by status, text search (company / role), and pagination
- Per-status summary statistics endpoint
- Input validation with Pydantic v2
- Pytest suite (SQLite-backed, no external services needed to run tests)
- Docker + Docker Compose (API + PostgreSQL 16)
- GitHub Actions CI running the test suite on every push

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Interactive docs: http://localhost:8000/docs

With Docker Compose (uses PostgreSQL):

```bash
docker compose up --build
```

Set `SECRET_KEY` (and `DATABASE_URL` if not using compose) via environment
variables or a `.env` file — see `app/config.py` for all settings.

## API overview

| Method | Endpoint                        | Description                              |
| ------ | ------------------------------- | ---------------------------------------- |
| POST   | `/auth/register`                | Register a new user                      |
| POST   | `/auth/token`                   | Login, returns a JWT bearer token        |
| GET    | `/applications`                 | List (filters: `status`, `search`, paging)|
| POST   | `/applications`                 | Create an application                    |
| GET    | `/applications/{id}`            | Get one application                      |
| PATCH  | `/applications/{id}`            | Update fields / move pipeline status     |
| DELETE | `/applications/{id}`            | Delete an application                    |
| GET    | `/applications/stats/summary`   | Count of applications per status         |
| GET    | `/health`                       | Health check                             |

Example:

```bash
# register + login
curl -X POST localhost:8000/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"dev@example.com","password":"supersecret1"}'
TOKEN=$(curl -s -X POST localhost:8000/auth/token \
  -d 'username=dev@example.com&password=supersecret1' | python -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')

# track an application
curl -X POST localhost:8000/applications \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"company":"Acme Corp","role":"Python Backend Developer","location":"Bengaluru","status":"applied"}'
```

## Testing

```bash
pytest -q
```

## Architecture

```
app/
  main.py          # app factory, router wiring, lifespan (creates tables)
  config.py        # pydantic-settings, env-driven
  database.py      # engine, session factory, get_db dependency
  models.py        # User, JobApplication (SQLAlchemy 2.0 style)
  schemas.py       # Pydantic v2 request/response models
  security.py      # bcrypt hashing + JWT encode/decode
  routers/
    auth.py        # /auth/register, /auth/token, get_current_user
    applications.py# CRUD, filters, pagination, stats
tests/
  test_api.py      # 8 end-to-end tests via TestClient
```

## Design decisions

- **Auth**: stateless JWT (30-minute expiry) keeps the API horizontally
  scalable; passwords are bcrypt-hashed, never stored or logged.
- **Multi-tenancy**: every query is scoped by `owner_id`, enforced in a
  single `_get_owned` helper so a user can never read or mutate another
  user's rows (covered by tests).
- **Database**: SQLite for zero-config local dev and tests; PostgreSQL in
  Docker Compose / production via `DATABASE_URL` — no code changes needed.
- **Validation**: Pydantic v2 schemas reject bad input at the boundary
  (e.g. passwords < 8 chars, page sizes > 100).

## Built by

Saahil Khan Mehar — https://github.com/saahilkhan17
