# AGENTS.md

Repository-wide instructions for future coding agents.

## General Workflow

- Read the relevant service files before editing.
- Check for a service-level `AGENTS.md` and follow it for service-specific rules.
- Keep changes scoped to the requested service or feature.
- Prefer the existing FastAPI patterns in each service.
- Use `rg` or `find` for local discovery.
- Use `apply_patch` for manual file edits.
- Run targeted validation before finishing, and include service docs/spec/collection checks when API behavior changes.
- Any functionality upgrade must include relevant tests or a clear note explaining why tests were not practical.
- Do not commit unless the user asks for a commit.
- Do not push unless the user asks for a push.

## Cross-Service Authentication

- Every service in this repo should accept traffic only from authenticated Auth0 callers unless there is a deliberate, documented exception.
- Use `user-service` as the access-management authority for Auth0 users, roles, groups, and permission scopes.
- Services should validate Auth0 bearer access tokens and enforce route-specific permissions from the token `permissions` claim using the same pattern as `user-service`.
- New service endpoints must define explicit permission scopes and document them in that service's README or API spec.
- Shared test personas should be created through top-level scripts under `scripts/` and reused across services instead of creating service-local test users.
- Baseline shared personas are end user, admin, and super admin. Add service-specific permissions to their Auth0 roles as new services require them.
- Keep Auth0 scope bootstrap and test-user bootstrap scripts idempotent so they can safely update an existing tenant.

## Secrets And Environment Files

- Treat every `**/.env` file as user-owned secret material.
- Never delete, rewrite, inspect, print, or stage `.env` files.
- Do not rely on `.env.example` as a source of truth when the user has provided a real ignored `.env`.
- Do not add code that directly references Google Drive credential paths.
- Application code should read configuration from environment variables through service config modules.
- `.env` files must remain ignored by Git.
- Postman environment exports, local credential files, `.DS_Store`, `.venv`, and `__pycache__` must remain ignored and unstaged.

## Git Hygiene

- Never stage ignored `.env`, `.venv`, Postman environment exports, `.DS_Store`, or `__pycache__` files.
- Before committing, inspect `git diff --cached --name-only`.
- Keep commit messages concise and feature-oriented.
