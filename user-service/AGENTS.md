# User Service AGENTS.md

Instructions for future coding agents working in `user-service`.

## Auth0 User Service

- Auth0 config lives in `config.py`.
- Auth0 token validation and permission enforcement lives in `auth.py`.
- Auth0 API helper code lives under `services/auth0`.
- Admin audit logging lives in `services/audit.py`.
- User permission caching lives in `services/permission_cache.py`.
- Route handlers live under `routers`.
- Tests live under `tests`.
- Application groups are currently mapped to Auth0 Roles.
- All application endpoints must require an Auth0 bearer token.
- Route authorization must use `require_permissions(...)` with a route-specific scope.
- The canonical OpenAPI document is `openapi/user-service.openapi.yaml`.
- The Postman collection is `postman/user-service.postman_collection.json`.

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
- Update `openapi/user-service.openapi.yaml`, including operation ids, request/response schemas, and `x-required-permission`.
- Update `postman/user-service.postman_collection.json` so each request uses its exact scope-specific token variable.
- Update `tests/test_openapi_docs.py` when the canonical OpenAPI contract changes.
- Ensure every route uses `require_permissions(...)`.
- Run the scope bootstrap script after adding scopes when Auth0 should be updated.

## Admin Workflows

- Do not add a raw `DELETE /admin/users/{user_id}` endpoint.
- User removal must use the disable/delete workflow:
  - `POST /admin/users/{user_id}/disable` with `disable:users`.
  - `POST /admin/users/{user_id}/delete-workflow` with `delete:users`.
- Disable/delete workflow routes should block the Auth0 user and write workflow details under `app_metadata.user_service_workflow`.
- Permission read APIs may use the in-process cache. Keep `use_cache=false` available for callers that need a fresh Auth0 read.
- Permission assign/remove calls must invalidate that user's permission cache.
- Admin mutation routes should emit audit events with non-secret metadata.

## Auth0 Scope Script

- `../scripts/create_auth0_scopes.py` bootstraps custom API scopes.
- The script should remain idempotent.
- It may read `user-service/.env`, but must not print secret values.
- Existing Auth0 scopes should be preserved.
- When `AUTH0_GRANT_CLIENT_ID` is set, the script also ensures that client can request the user-service API scopes.

## Postman

- API requests should not use a generic `{{access_token}}`.
- Each API request must reference the token variable for its required scope, such as `{{access_token_read_users}}`.
- Token requests in the `Auth0 Tokens` folder should request one relevant scope at a time and store the matching scoped token.
- Postman environment exports are ignored by Git and must not be staged.

## Integration Tests

- Real Auth0 integration checks belong in skipped-by-default tests.
- Gate real tenant calls behind `RUN_AUTH0_INTEGRATION_TESTS=true`.
- Use optional env vars such as `AUTH0_TEST_USER_ID` for real-user checks.
- Never print tokens, secrets, or `.env` contents from tests.

## Validation Checklist

Run from `user-service`:

```bash
.venv/bin/python -m unittest discover -s tests
.venv/bin/python -m compileall *.py routers/*.py services/*.py services/auth0/*.py tests/*.py
```

Run from the repo root:

```bash
python3 -m json.tool user-service/postman/user-service.postman_collection.json
git diff --check
git status --short --ignored user-service/.env user-service/postman/user-service.postman_environment.json .DS_Store
```

Expected: `user-service/.env`, Postman environment exports, and `.DS_Store` are ignored, not staged.
