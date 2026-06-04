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
PERMISSION_CACHE_TTL_SECONDS=60
USER_DELETE_WORKFLOW_RETENTION_DAYS=30
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

Grant the user-service Auth0 client the Management API scopes needed by the implemented Auth0 helper calls:

```bash
python3 scripts/configure_auth0_management_grant.py
```

The script defaults to granting the Management API scopes to `AUTH0_CLIENT_ID`. Set `AUTH0_MANAGEMENT_GRANT_CLIENT_ID` only when the service runtime uses a different Auth0 machine-to-machine client.

Created user-service API scopes:

```text
read:service_status
read:health_liveness
read:health_readiness
read:health_dependencies
read:auth_config
read:profile
create:registration
complete:registration
read:own_profile
update:own_profile
change:own_password
read:own_mfa
enroll:own_mfa
challenge:own_mfa
delete:own_mfa
read:users
update:users
disable:users
delete:users
reset:passwords
reset:mfa
read:groups
create:groups
update:groups
delete:groups
create:permissions
read:permissions
update:permissions
delete:permissions
assign:permissions
unassign:permissions
```

## Endpoints

All application endpoints require an Auth0 bearer token and the listed scope.

Health/core:

```text
GET /                         read:service_status
GET /health/live              read:health_liveness
GET /health/ready             read:health_readiness
GET /health/dependencies      read:health_dependencies
GET /auth/config              read:auth_config
GET /me                       read:profile
```

The canonical OpenAPI-style service document lives at:

```text
user-service/openapi/user-service.openapi.yaml
```

Self-service:

```text
POST   /self-service/registration                    create:registration
POST   /self-service/registration/complete           complete:registration
GET    /self-service/profile                         read:own_profile
PATCH  /self-service/profile                         update:own_profile
POST   /self-service/password-change                 change:own_password
GET    /self-service/mfa/enrollments                 read:own_mfa
POST   /self-service/mfa/enroll                      enroll:own_mfa
POST   /self-service/mfa/challenge                   challenge:own_mfa
DELETE /self-service/mfa/enrollments/{enrollment_id} delete:own_mfa
```

Self-service Auth0 upstream calls:

```text
POST   /self-service/registration                    POST   https://{AUTH0_DOMAIN}/api/v2/users
POST   /self-service/registration/complete           PATCH  https://{AUTH0_DOMAIN}/api/v2/users/{user_id}
GET    /self-service/profile                         GET    https://{AUTH0_DOMAIN}/api/v2/users/{user_id}
PATCH  /self-service/profile                         PATCH  https://{AUTH0_DOMAIN}/api/v2/users/{user_id}
POST   /self-service/password-change                 POST   https://{AUTH0_DOMAIN}/api/v2/tickets/password-change
GET    /self-service/mfa/enrollments                 GET    https://{AUTH0_DOMAIN}/api/v2/users/{user_id}/authentication-methods
POST   /self-service/mfa/enroll                      POST   https://{AUTH0_DOMAIN}/mfa/associate
POST   /self-service/mfa/challenge                   POST   https://{AUTH0_DOMAIN}/mfa/challenge
DELETE /self-service/mfa/enrollments/{enrollment_id} DELETE https://{AUTH0_DOMAIN}/api/v2/users/{user_id}/authentication-methods/{enrollment_id}
```

### Self-Service MFA Usage

The self-service MFA endpoints use two different Auth0 APIs:

```text
POST /self-service/mfa/enroll      -> POST https://{AUTH0_DOMAIN}/mfa/associate
POST /self-service/mfa/challenge   -> POST https://{AUTH0_DOMAIN}/mfa/challenge
GET  /self-service/mfa/enrollments -> GET  https://{AUTH0_DOMAIN}/api/v2/users/{user_id}/authentication-methods
```

Every user-service MFA request still requires a user-service bearer token with the listed user-service scope. The `mfa_token` in the request body is the Auth0 MFA API token for the current MFA flow.

Supported MFA enrollment options:

```text
Authenticator app / TOTP  authenticator_type=otp
SMS code                  authenticator_type=oob, oob_channels=["sms"], phone_number=E.164 phone number
Voice code                authenticator_type=oob, oob_channels=["voice"], phone_number=E.164 phone number
Guardian push             authenticator_type=oob, oob_channels=["auth0"]
```

Authenticator app enrollment:

```json
{
  "mfa_token": "AUTH0_MFA_TOKEN",
  "authenticator_type": "otp"
}
```

SMS enrollment:

```json
{
  "mfa_token": "AUTH0_MFA_TOKEN",
  "authenticator_type": "oob",
  "oob_channels": ["sms"],
  "phone_number": "+14155550100"
}
```

Voice enrollment:

```json
{
  "mfa_token": "AUTH0_MFA_TOKEN",
  "authenticator_type": "oob",
  "oob_channels": ["voice"],
  "phone_number": "+14155550100"
}
```

Guardian push enrollment:

```json
{
  "mfa_token": "AUTH0_MFA_TOKEN",
  "authenticator_type": "oob",
  "oob_channels": ["auth0"]
}
```

Challenge an enrolled authenticator:

```json
{
  "mfa_token": "AUTH0_MFA_TOKEN",
  "challenge_type": "otp",
  "authenticator_id": "totp|AUTHENTICATOR_ID"
}
```

For SMS, voice, Guardian push, and email authenticators, use `challenge_type=oob` and pass the `authenticator_id` returned by Auth0. Email authenticators can be challenged when Auth0 lists them, but user-service does not enroll email MFA because Auth0 email enrollment is tenant/user-email driven rather than a phone or device enrollment payload.

Admin:

```text
GET    /admin/users                                 read:users
GET    /admin/users/{user_id}                       read:users
PATCH  /admin/users/{user_id}/attributes            update:users
POST   /admin/users/{user_id}/disable               disable:users
POST   /admin/users/{user_id}/delete-workflow       delete:users
POST   /admin/users/{user_id}/password-reset        reset:passwords
POST   /admin/users/{user_id}/mfa/reset             reset:mfa
GET    /admin/groups                                read:groups
POST   /admin/groups                                create:groups
GET    /admin/groups/{group_id}                     read:groups
PATCH  /admin/groups/{group_id}                     update:groups
DELETE /admin/groups/{group_id}                     delete:groups
GET    /admin/groups/{group_id}/users               read:groups
POST   /admin/permissions                           create:permissions
PATCH  /admin/permissions/{permission}              update:permissions
DELETE /admin/permissions/{permission}              delete:permissions
GET    /admin/users/{user_id}/permissions           read:permissions
POST   /admin/users/{user_id}/permissions           assign:permissions
DELETE /admin/users/{user_id}/permissions           unassign:permissions
GET    /admin/users/{user_id}/groups                read:groups
POST   /admin/users/{user_id}/groups                update:groups
DELETE /admin/users/{user_id}/groups/{group_id}     delete:groups
```

Permission admin Auth0 upstream calls:

```text
POST /admin/permissions                 GET   https://{AUTH0_DOMAIN}/api/v2/resource-servers?identifier={AUTH0_AUDIENCE}
POST /admin/permissions                 PATCH https://{AUTH0_DOMAIN}/api/v2/resource-servers/{resource_server_id}
PATCH /admin/permissions/{permission}   GET   https://{AUTH0_DOMAIN}/api/v2/resource-servers?identifier={AUTH0_AUDIENCE}
PATCH /admin/permissions/{permission}   PATCH https://{AUTH0_DOMAIN}/api/v2/resource-servers/{resource_server_id}
DELETE /admin/permissions/{permission}  GET   https://{AUTH0_DOMAIN}/api/v2/resource-servers?identifier={AUTH0_AUDIENCE}
DELETE /admin/permissions/{permission}  PATCH https://{AUTH0_DOMAIN}/api/v2/resource-servers/{resource_server_id}
GET  /admin/users/{user_id}/permissions GET   https://{AUTH0_DOMAIN}/api/v2/users/{user_id}/permissions
POST /admin/users/{user_id}/permissions POST  https://{AUTH0_DOMAIN}/api/v2/users/{user_id}/permissions
DELETE /admin/users/{user_id}/permissions DELETE https://{AUTH0_DOMAIN}/api/v2/users/{user_id}/permissions
```

`POST /admin/permissions` adds a scope to the Auth0 API identified by `AUTH0_AUDIENCE`. `PATCH /admin/permissions/{permission}` updates an existing scope description. `DELETE /admin/permissions/{permission}` removes a scope from the Auth0 API. `POST /admin/users/{user_id}/permissions` assigns one or more of those API permissions directly to a user. `DELETE /admin/users/{user_id}/permissions` removes direct user permissions. `GET /admin/users/{user_id}/permissions` is intended for trusted machine-to-machine callers that need to authorize object-level access for a user, optionally with local caching.

Permission reads are cached in-process for `PERMISSION_CACHE_TTL_SECONDS`, defaulting to `60`. Use `use_cache=false` on `GET /admin/users/{user_id}/permissions` when a caller needs a fresh Auth0 read after an external permission change. Assign/remove calls invalidate that user's cached permission pages.

User disable/delete workflow Auth0 upstream calls:

```text
POST /admin/users/{user_id}/disable         PATCH https://{AUTH0_DOMAIN}/api/v2/users/{user_id}
POST /admin/users/{user_id}/delete-workflow PATCH https://{AUTH0_DOMAIN}/api/v2/users/{user_id}
```

`POST /admin/users/{user_id}/disable` blocks the user and records workflow metadata in `app_metadata.user_service_workflow`. `POST /admin/users/{user_id}/delete-workflow` blocks the user, records delete-request metadata, and stores a `delete_after` timestamp based on `USER_DELETE_WORKFLOW_RETENTION_DAYS`, defaulting to `30`. This service intentionally does not expose a raw user delete endpoint.

Group admin Auth0 upstream calls:

```text
GET    /admin/groups                                GET    https://{AUTH0_DOMAIN}/api/v2/roles
POST   /admin/groups                                POST   https://{AUTH0_DOMAIN}/api/v2/roles
GET    /admin/groups/{group_id}                     GET    https://{AUTH0_DOMAIN}/api/v2/roles/{group_id}
PATCH  /admin/groups/{group_id}                     PATCH  https://{AUTH0_DOMAIN}/api/v2/roles/{group_id}
DELETE /admin/groups/{group_id}                     DELETE https://{AUTH0_DOMAIN}/api/v2/roles/{group_id}
GET    /admin/groups/{group_id}/users               GET    https://{AUTH0_DOMAIN}/api/v2/roles/{group_id}/users
GET    /admin/users/{user_id}/groups                GET    https://{AUTH0_DOMAIN}/api/v2/users/{user_id}/roles
POST   /admin/users/{user_id}/groups                POST   https://{AUTH0_DOMAIN}/api/v2/users/{user_id}/roles
DELETE /admin/users/{user_id}/groups/{group_id}     DELETE https://{AUTH0_DOMAIN}/api/v2/users/{user_id}/roles
```

Application groups are represented as Auth0 Roles.

Admin list endpoints support pagination:

```text
page=0
per_page=25
```

`GET /admin/users` also supports Auth0 Lucene search fragments:

```text
query=email:"user@example.com"
start_query=created_at:[2026-01-01 TO *]
end_query=created_at:[* TO 2026-02-01]
```

When multiple query fragments are supplied, the service combines them with `AND` and sends the composed query to Auth0 with `search_engine=v3`.

`GET /admin/groups` maps groups to Auth0 Roles and supports:

```text
page=0
per_page=25
query=admin
start_query=north
end_query=america
```

Auth0 Roles support `name_filter`, so group query fragments are folded into a single role name filter while pagination is preserved.

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
change:own_password
read:own_mfa
enroll:own_mfa
challenge:own_mfa
delete:own_mfa
read:users
update:users
disable:users
delete:users
reset:passwords
reset:mfa
read:groups
create:groups
update:groups
delete:groups
create:permissions
read:permissions
update:permissions
delete:permissions
assign:permissions
unassign:permissions
```

Optional Auth0 integration checks can be run manually when real tenant credentials are available:

```bash
cd user-service
RUN_AUTH0_INTEGRATION_TESTS=true .venv/bin/python -m unittest tests.test_auth0_integration
```

Set `AUTH0_TEST_USER_ID=auth0|...` to include the optional real-user permission read check. These tests are skipped by default in CI and do not read credential files directly.

## Layout

```text
user-service/
  auth.py
  config.py
  main.py
  postman/
  routers/
    health.py
  services/auth0/
  tests/
```
