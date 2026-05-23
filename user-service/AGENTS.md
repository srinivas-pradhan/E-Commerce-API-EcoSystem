# User Service AGENTS.md

Instructions for future coding agents working in `user-service`.

## Auth0 User Service

- Auth0 config lives in `config.py`.
- Auth0 token validation and permission enforcement lives in `auth.py`.
- Auth0 API helper code lives under `services/auth0`.
- Route handlers live under `routers`.
- Tests live under `tests`.
- Application groups are currently mapped to Auth0 Roles.
- All application endpoints must require an Auth0 bearer token.
- Route authorization must use `require_permissions(...)` with a route-specific scope.

## Secrets

- Never delete, rewrite, inspect, print, or stage `user-service/.env`.
- The `.env` file is user-owned and ignored by Git.
- Do not move secrets into source code, README examples with real secret values, or test fixtures.

## Updating Endpoints

When adding or changing protected endpoints:

- Add or update the route in `routers`.
- Add or update Auth0 helper code in `services/auth0` when the route calls Auth0.
- Add or update request schemas in `routers/schemas.py`.
- Add or update tests for the functionality, especially Auth0 helper behavior and route authorization.
- Add or update custom API scopes in `../scripts/create_auth0_scopes.py`.
- Update `README.md` endpoint tables and scope lists.
- Ensure every route uses `require_permissions(...)`.

## Auth0 Scope Script

- `../scripts/create_auth0_scopes.py` bootstraps custom API scopes.
- The script should remain idempotent.
- It may read `user-service/.env`, but must not print secret values.
- Existing Auth0 scopes should be preserved.

## Validation Checklist

Run from `user-service`:

```bash
.venv/bin/python -m unittest discover -s tests
.venv/bin/python -m compileall *.py routers/*.py services/*.py services/auth0/*.py tests/*.py
```

Run from the repo root:

```bash
git diff --check
git status --short --ignored user-service/.env
```

Expected: `user-service/.env` is ignored, not staged.
