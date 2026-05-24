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
The start script exports values from `user-service/.env` into the FastAPI process before startup. Restart the service after changing Auth0 settings such as `AUTH0_AUDIENCE`.

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

## Postman

Import the collection at:

```text
user-service/postman/user-service.postman_collection.json
```

Set these collection variables before running requests:

```text
base_url=http://localhost:8080
auth0_domain=dev-lqyjuexwhe1bupvs.us.auth0.com
auth0_audience=https://user-service
postman_client_id=<Auth0 client id for Postman>
postman_client_secret=<Auth0 client secret for Postman>
user_id=<Auth0 user id for admin routes>
group_id=<Auth0 role id for group routes>
enrollment_id=<Auth0 authentication method id for MFA delete>
mfa_token=<Auth0 MFA API token for MFA enroll/challenge>
```

The collection includes an `Auth0 Tokens` folder with one token request per API scope. Run the full collection from `Auth0 Tokens / Get token - read:service_status` and Postman will generate each scoped token, store it in the environment, then continue into the API requests.

Each token request calls:

```text
POST https://{{auth0_domain}}/oauth/token
```

It uses the client credentials grant and caches the token in a scope-specific environment variable such as:

```text
access_token_read_users
access_token_update_own_profile
```

API requests do not fetch tokens asynchronously. Each API request references the exact scoped token variable in its own Authorization config. For example:

```text
GET /                         Authorization: Bearer {{access_token_read_service_status}}
GET /admin/users              Authorization: Bearer {{access_token_read_users}}
PATCH /self-service/profile   Authorization: Bearer {{access_token_update_own_profile}}
```

For targeted manual testing, you can also run only the token request for the API you want. For example, run `Auth0 Tokens / Get token - read:users` before `GET /admin/users`, or run `Auth0 Tokens / Get token - update:own_profile` before `PATCH /self-service/profile`. The API request then uses the matching environment variable directly.

You should not need to copy tokens by hand.

If every request returns `401`, open the Postman Console and confirm the Auth0 token request succeeds. The service response body distinguishes the common causes:

```text
{"detail":"Missing bearer token"}        # Postman did not send Authorization
{"detail":"Could not validate credentials"} # Token was sent but rejected
```

If the token was sent but rejected, confirm the running service loaded the same audience Postman used:

```text
AUTH0_AUDIENCE=https://user-service
```

Then restart `./start-user-service.sh`.

If you export Postman environment or credential files, keep them under `user-service/postman/`.
Postman environment and credential exports are ignored by Git.

The Auth0 client used for Postman tokens must be allowed to request the user-service API scopes needed by the requests you run. For full collection coverage, grant/request:

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

## Layout

```text
user-service/
  auth.py
  config.py
  main.py
  postman/
  routers/
  services/auth0/
  tests/
```
