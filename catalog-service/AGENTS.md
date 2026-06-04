# Catalog Service AGENTS.md

Instructions for future coding agents working in `catalog-service`.

## Catalog Service Direction

- The catalog service owns product discovery, product release state, promotions, sales metadata, inventory visibility, and cart inventory reservations.
- Use `user-service` as the access-management authority. Keep authorization permission-scope based and compatible with the existing Auth0-style `require_permissions(...)` pattern.
- End users should only see released products and active promotions.
- Admin users can view product and inventory state.
- Super admin users can manage products, release state, inventory settings, and promotions.
- Cart reservations should reduce available inventory while the item sits in a cart and should expire after the configured reservation TTL, currently one hour by default.

## Structure

- Application bootstrap lives in `main.py`.
- Auth token validation and permission enforcement lives in `auth.py`.
- Service configuration lives in `config.py`.
- ORM setup lives in `database.py`.
- SQLAlchemy models live in `models.py`.
- Route handlers live under `routers`.
- Service/business logic lives under `services`.
- Tests live under `tests`.
- Functional requirements live in `REQUIREMENTS.md`.

## Database And ORM

- Postgres is the intended catalog database.
- Use SQLAlchemy ORM models and repository/service helpers for database reads and writes.
- Do not put raw SQL in route handlers.
- Keep transaction boundaries explicit when moving from dummy data to persisted inventory behavior.
- Inventory reservation updates must be safe under concurrent cart additions.

## Authorization

- All application endpoints must require an Auth0 bearer token unless there is a deliberate, documented exception.
- Route authorization must use `require_permissions(...)` with a route-specific scope.
- Keep permission names aligned with user-service/Auth0 scope management.
- Current catalog scopes include:
  - `read:catalog_status`
  - `read:catalog_health`
  - `read:products`
  - `reserve:cart_inventory`
  - `read:inventory`
  - `manage:catalog`
  - `manage:inventory`
  - `manage:promotions`

## Updating Endpoints

- Add or update request and response schemas in `routers/schemas.py`.
- Add or update routes under `routers`.
- Add or update service-layer behavior under `services`.
- Add or update ORM models in `models.py` when persistence shape changes.
- Add or update tests for permission checks and the core business behavior.
- Update `REQUIREMENTS.md` when functional requirements or public API shape changes.

## Secrets

- Never delete, rewrite, inspect, print, or stage `catalog-service/.env`.
- The `.env` file is user-owned and ignored by Git.
- Do not hard-code database credentials, Auth0 secrets, or service tokens.
- Application code should read configuration through `config.py`.

## Validation Checklist

Run from `catalog-service`:

```bash
.venv/bin/python -m unittest discover -s tests
.venv/bin/python -m compileall *.py routers/*.py services/*.py tests/*.py
```

Run from the repo root:

```bash
git diff --check -- catalog-service
git status --short --ignored catalog-service/.env
```

Expected: `catalog-service/.env` is ignored, not staged.
