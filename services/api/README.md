# TestPsico API

FastAPI service for TestPsico. See the repository root `README.md` for the
official commands (up / migrate / seed / reset / clean / test).

Layout:

```
services/api/
├── pyproject.toml        # dependencies + pytest config
├── alembic.ini           # Alembic config (URL injected from env)
├── alembic/              # env.py + one linear versions/ chain
├── app/
│   ├── main.py           # FastAPI app, envelope + request_id middleware
│   ├── core/             # config, auth, permissions, errors, audit, consent
│   ├── db/               # engine/session + declarative base
│   ├── models/           # 9 table families + seed_manifest (SQLAlchemy 2)
│   ├── schemas/          # pydantic request/response models
│   ├── api/              # deps + versioned routers
│   └── seed/             # idempotent synthetic seed (UUID5 + ON CONFLICT)
└── tests/                # pytest suite (scripts/schema/auth/audit/consent/seed/web)
```

Run the suite: `docker compose run --rm api pytest`
