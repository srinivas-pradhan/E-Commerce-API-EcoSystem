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
