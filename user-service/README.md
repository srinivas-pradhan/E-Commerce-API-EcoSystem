# User Service

Auth0-backed identity and user administration service for the e-commerce ecosystem.

Current responsibilities:

- Validate Auth0 bearer access tokens.
- Enforce route-level permissions from the token `permissions` claim.
- Provide self-service user registration, profile, and MFA routes.
- Provide admin user, password reset, MFA reset, and group-management routes.
- Use Auth0 Management API helpers for trusted server-side operations.
- Treat application "groups" as Auth0 Roles.

## Auth0 Configuration

`user-service` expects Auth0 settings from environment variables:

```env
AUTH0_DOMAIN=dev-lqyjuexwhe1bupvs.us.auth0.com
AUTH0_CLIENT_ID=hG5aklxMlkilsmsfF6HjuROKNsivDJLU
AUTH0_CLIENT_SECRET=...
AUTH0_AUDIENCE=https://user-service
AUTH0_CONNECTION=Username-Password-Authentication
```

`user-service/.env` is intentionally ignored by Git. Do not commit secrets.

Auth0 API requirements:

- API identifier should match `AUTH0_AUDIENCE`.
- Signing algorithm: `RS256`.
- Enable RBAC.
- Enable "Add Permissions in the Access Token".

The Auth0 machine-to-machine client used by the service must be authorized for the Auth0 Management API scopes needed by the implemented helpers, including:

```text
create:users
read:users
update:users
read:roles
create:roles
update:roles
delete:roles
read:authentication_methods
delete:authentication_methods
create:user_tickets
```

The scope bootstrap script also needs:

```text
read:resource_servers
update:resource_servers
```

## Bootstrap Auth0 API Scopes

Create or update the custom API scopes for `user-service`:

```bash
python3 scripts/create_auth0_scopes.py
```

The script reads Auth0 settings from exported environment variables first, then from `user-service/.env`.

Created user-service API scopes:

```text
read:service_status
read:auth_config
read:profile
create:registration
complete:registration
read:own_profile
update:own_profile
enroll:own_mfa
challenge:own_mfa
delete:own_mfa
read:users
update:users
reset:passwords
reset:mfa
read:groups
create:groups
update:groups
delete:groups
```

## Endpoints

All application endpoints require an Auth0 bearer token and the listed scope.

Core:

```text
GET /                         read:service_status
GET /auth/config              read:auth_config
GET /me                       read:profile
```

Self-service:

```text
POST   /self-service/registration                    create:registration
POST   /self-service/registration/complete           complete:registration
GET    /self-service/profile                         read:own_profile
PATCH  /self-service/profile                         update:own_profile
POST   /self-service/mfa/enroll                      enroll:own_mfa
POST   /self-service/mfa/challenge                   challenge:own_mfa
DELETE /self-service/mfa/enrollments/{enrollment_id} delete:own_mfa
```

Admin:

```text
GET    /admin/users                                 read:users
GET    /admin/users/{user_id}                       read:users
PATCH  /admin/users/{user_id}/attributes            update:users
POST   /admin/users/{user_id}/password-reset        reset:passwords
POST   /admin/users/{user_id}/mfa/reset             reset:mfa
GET    /admin/groups                                read:groups
POST   /admin/groups                                create:groups
POST   /admin/users/{user_id}/groups                update:groups
DELETE /admin/users/{user_id}/groups/{group_id}     delete:groups
```

## Local Development

Install dependencies:

```bash
cd user-service
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Run the service:

```bash
cd user-service
./start-user-service.sh
```

The user service currently runs on port `8080`.

## Validation

From `user-service`:

```bash
.venv/bin/python -m unittest discover -s tests
.venv/bin/python -m compileall *.py routers/*.py services/*.py services/auth0/*.py tests/*.py
```

From the repo root:

```bash
git diff --check
```

## Layout

```text
user-service/
  auth.py
  config.py
  main.py
  routers/
  services/auth0/
  tests/
```
