#!/usr/bin/env python3
"""Create active Auth0 test users and roles for service integration testing.

Required environment variables, or values in user-service/.env:
  AUTH0_DOMAIN
  AUTH0_CLIENT_ID
  AUTH0_CLIENT_SECRET

Optional environment variables:
  AUTH0_CONNECTION
  AUTH0_AUDIENCE
  AUTH0_TEST_PASSWORD
  AUTH0_TEST_EMAIL_DOMAIN

The client must be allowed to call the Auth0 Management API with scopes:
  create:users read:users update:users create:roles read:roles update:roles
"""

from __future__ import annotations

import json
import os
import secrets
import string
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
USER_SERVICE_ENV = REPO_ROOT / "user-service" / ".env"

BASE_SCOPES = [
    "read:service_status",
    "read:health_liveness",
    "read:health_readiness",
    "read:health_dependencies",
    "read:auth_config",
    "read:profile",
    "read:catalog_status",
    "read:catalog_health",
]

END_USER_SCOPES = [
    *BASE_SCOPES,
    "read:own_profile",
    "update:own_profile",
    "change:own_password",
    "read:own_mfa",
    "read:products",
    "reserve:cart_inventory",
]

ADMIN_SCOPES = [
    *END_USER_SCOPES,
    "read:users",
    "read:groups",
    "read:permissions",
    "read:inventory",
]

SUPER_ADMIN_SCOPES = [
    *ADMIN_SCOPES,
    "update:users",
    "disable:users",
    "delete:users",
    "reset:passwords",
    "reset:mfa",
    "create:groups",
    "update:groups",
    "delete:groups",
    "create:permissions",
    "update:permissions",
    "delete:permissions",
    "assign:permissions",
    "unassign:permissions",
    "manage:catalog",
    "manage:inventory",
    "manage:promotions",
]

TEST_PERSONAS = [
    {
        "key": "end_user",
        "role_name": "ecommerce-test-end-user",
        "description": "Active test shopper for product browsing, cart reservation, and checkout flows.",
        "email_local_part": "test.end.user",
        "given_name": "Test",
        "family_name": "End User",
        "permissions": END_USER_SCOPES,
    },
    {
        "key": "admin",
        "role_name": "ecommerce-test-admin",
        "description": "Active test admin for read-only catalog inventory and user-admin inspection flows.",
        "email_local_part": "test.admin",
        "given_name": "Test",
        "family_name": "Admin",
        "permissions": ADMIN_SCOPES,
    },
    {
        "key": "super_admin",
        "role_name": "ecommerce-test-super-admin",
        "description": "Active test super admin for catalog, inventory, promotion, and user-management flows.",
        "email_local_part": "test.super.admin",
        "given_name": "Test",
        "family_name": "Super Admin",
        "permissions": SUPER_ADMIN_SCOPES,
    },
]


@dataclass(frozen=True)
class Auth0Config:
    domain: str
    client_id: str
    client_secret: str
    connection: str
    audience: str
    test_email_domain: str
    test_password: str
    generated_password: bool

    @property
    def issuer(self) -> str:
        return f"https://{self.domain}"

    @property
    def management_audience(self) -> str:
        return f"{self.issuer}/api/v2/"


def load_user_service_env() -> dict[str, str]:
    if not USER_SERVICE_ENV.exists():
        return {}

    values = {}
    for line in USER_SERVICE_ENV.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")

        if key:
            values[key] = value

    return values


def config_value(env_file: dict[str, str], key: str, fallback: str | None = None) -> str | None:
    return os.getenv(key) or env_file.get(key) or fallback


def generate_password() -> str:
    alphabet = string.ascii_letters + string.digits + "!#$%&*+-=?@^_"
    return "".join(secrets.choice(alphabet) for _ in range(24))


def load_config() -> Auth0Config:
    env_file = load_user_service_env()
    domain = config_value(env_file, "AUTH0_DOMAIN")
    client_id = config_value(env_file, "AUTH0_CLIENT_ID")
    client_secret = config_value(env_file, "AUTH0_CLIENT_SECRET")
    connection = config_value(env_file, "AUTH0_CONNECTION", "Username-Password-Authentication")
    audience = config_value(env_file, "AUTH0_AUDIENCE", client_id)
    test_email_domain = config_value(env_file, "AUTH0_TEST_EMAIL_DOMAIN", "example.com")
    configured_password = config_value(env_file, "AUTH0_TEST_PASSWORD")
    test_password = configured_password or generate_password()

    missing = [
        key
        for key, value in {
            "AUTH0_DOMAIN": domain,
            "AUTH0_CLIENT_ID": client_id,
            "AUTH0_CLIENT_SECRET": client_secret,
            "AUTH0_CONNECTION": connection,
            "AUTH0_AUDIENCE": audience,
            "AUTH0_TEST_EMAIL_DOMAIN": test_email_domain,
        }.items()
        if not value
    ]

    if missing:
        print(f"Missing required Auth0 setting(s): {', '.join(missing)}", file=sys.stderr)
        print(f"Set them in the environment or in {USER_SERVICE_ENV}.", file=sys.stderr)
        sys.exit(2)

    return Auth0Config(
        domain=str(domain),
        client_id=str(client_id),
        client_secret=str(client_secret),
        connection=str(connection),
        audience=str(audience),
        test_email_domain=str(test_email_domain),
        test_password=test_password,
        generated_password=configured_password is None,
    )


def request_json(
    method: str,
    url: str,
    *,
    token: str | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any] | list[dict[str, Any]]:
    data = None
    headers = {"Content-Type": "application/json"}

    if token is not None:
        headers["Authorization"] = f"Bearer {token}"

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    for attempt in range(5):
        request = urllib.request.Request(url, data=data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read().decode("utf-8")
                break
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8")
            if error.code == 429 and attempt < 4:
                retry_after = error.headers.get("Retry-After")
                delay = int(retry_after) if retry_after and retry_after.isdigit() else 5 * (attempt + 1)
                print(f"Auth0 rate limit reached. Retrying in {delay} second(s).", file=sys.stderr)
                time.sleep(delay)
                continue

            print(f"Auth0 request failed: {method} {url}", file=sys.stderr)
            print(f"Status: {error.code}", file=sys.stderr)
            print(body, file=sys.stderr)
            sys.exit(1)

    if not body:
        return {}

    return json.loads(body)


def get_management_token(config: Auth0Config) -> str:
    response = request_json(
        "POST",
        f"{config.issuer}/oauth/token",
        payload={
            "grant_type": "client_credentials",
            "client_id": config.client_id,
            "client_secret": config.client_secret,
            "audience": config.management_audience,
        },
    )

    if not isinstance(response, dict) or "access_token" not in response:
        print("Auth0 did not return an access token.", file=sys.stderr)
        sys.exit(1)

    return response["access_token"]


def path_segment(value: str) -> str:
    return urllib.parse.quote(value, safe="")


def find_role(config: Auth0Config, token: str, role_name: str) -> dict[str, Any] | None:
    query = urllib.parse.urlencode({"name_filter": role_name, "per_page": 50})
    response = request_json("GET", f"{config.management_audience}roles?{query}", token=token)
    roles = response.get("roles", []) if isinstance(response, dict) else response

    if not isinstance(roles, list):
        print("Unexpected Auth0 roles response.", file=sys.stderr)
        sys.exit(1)

    for role in roles:
        if role.get("name") == role_name:
            return role

    return None


def ensure_role(config: Auth0Config, token: str, persona: dict[str, Any]) -> dict[str, Any]:
    role = find_role(config, token, persona["role_name"])
    if role is not None:
        return role

    response = request_json(
        "POST",
        f"{config.management_audience}roles",
        token=token,
        payload={
            "name": persona["role_name"],
            "description": persona["description"],
        },
    )
    if not isinstance(response, dict):
        print("Unexpected Auth0 create role response.", file=sys.stderr)
        sys.exit(1)
    return response


def list_role_permissions(config: Auth0Config, token: str, role_id: str) -> set[str]:
    response = request_json(
        "GET",
        f"{config.management_audience}roles/{path_segment(role_id)}/permissions",
        token=token,
    )
    permissions = response.get("permissions", []) if isinstance(response, dict) else response

    if not isinstance(permissions, list):
        print("Unexpected Auth0 role permissions response.", file=sys.stderr)
        sys.exit(1)

    return {
        permission["permission_name"]
        for permission in permissions
        if permission.get("resource_server_identifier") == config.audience
    }


def assign_role_permissions(
    config: Auth0Config,
    token: str,
    role_id: str,
    permissions: list[str],
) -> list[str]:
    existing = list_role_permissions(config, token, role_id)
    missing = [permission for permission in permissions if permission not in existing]
    if not missing:
        return []

    request_json(
        "POST",
        f"{config.management_audience}roles/{path_segment(role_id)}/permissions",
        token=token,
        payload={
            "permissions": [
                {
                    "permission_name": permission,
                    "resource_server_identifier": config.audience,
                }
                for permission in missing
            ]
        },
    )
    return missing


def find_user_by_email(config: Auth0Config, token: str, email: str) -> dict[str, Any] | None:
    query = urllib.parse.urlencode({"q": f'email:"{email}"', "search_engine": "v3"})
    response = request_json("GET", f"{config.management_audience}users?{query}", token=token)

    if not isinstance(response, list):
        print("Unexpected Auth0 users response.", file=sys.stderr)
        sys.exit(1)

    for user in response:
        if user.get("email") == email:
            return user

    return None


def ensure_user(config: Auth0Config, token: str, persona: dict[str, Any]) -> dict[str, Any]:
    email = f"{persona['email_local_part']}@{config.test_email_domain}"
    user = find_user_by_email(config, token, email)
    app_metadata = {
        "registration_completed": True,
        "test_persona": persona["key"],
        "managed_by": "scripts/create_auth0_test_users.py",
    }

    if user is not None:
        user_id = user["user_id"]
        response = request_json(
            "PATCH",
            f"{config.management_audience}users/{path_segment(user_id)}",
            token=token,
            payload={
                "blocked": False,
                "email_verified": True,
                "app_metadata": app_metadata,
            },
        )
        if not isinstance(response, dict):
            print("Unexpected Auth0 update user response.", file=sys.stderr)
            sys.exit(1)
        return response

    response = request_json(
        "POST",
        f"{config.management_audience}users",
        token=token,
        payload={
            "connection": config.connection,
            "email": email,
            "password": config.test_password,
            "email_verified": True,
            "verify_email": False,
            "blocked": False,
            "given_name": persona["given_name"],
            "family_name": persona["family_name"],
            "name": f"{persona['given_name']} {persona['family_name']}",
            "app_metadata": app_metadata,
        },
    )
    if not isinstance(response, dict):
        print("Unexpected Auth0 create user response.", file=sys.stderr)
        sys.exit(1)
    return response


def list_user_roles(config: Auth0Config, token: str, user_id: str) -> set[str]:
    response = request_json(
        "GET",
        f"{config.management_audience}users/{path_segment(user_id)}/roles",
        token=token,
    )
    roles = response.get("roles", []) if isinstance(response, dict) else response

    if not isinstance(roles, list):
        print("Unexpected Auth0 user roles response.", file=sys.stderr)
        sys.exit(1)

    return {role["id"] for role in roles}


def assign_user_role(config: Auth0Config, token: str, user_id: str, role_id: str) -> bool:
    existing = list_user_roles(config, token, user_id)
    if role_id in existing:
        return False

    request_json(
        "POST",
        f"{config.management_audience}users/{path_segment(user_id)}/roles",
        token=token,
        payload={"roles": [role_id]},
    )
    return True


def main() -> int:
    config = load_config()
    token = get_management_token(config)
    ensured_users = []

    for persona in TEST_PERSONAS:
        role = ensure_role(config, token, persona)
        added_permissions = assign_role_permissions(config, token, role["id"], persona["permissions"])
        user = ensure_user(config, token, persona)
        assigned_role = assign_user_role(config, token, user["user_id"], role["id"])
        ensured_users.append(
            {
                "persona": persona["key"],
                "email": user["email"],
                "role": persona["role_name"],
                "permissions_added_to_role": len(added_permissions),
                "role_assigned": assigned_role,
            }
        )

    print("Ensured active Auth0 test personas:")
    for user in ensured_users:
        role_status = "assigned" if user["role_assigned"] else "already assigned"
        print(
            f"  - {user['persona']}: {user['email']} "
            f"({user['role']}, {role_status}, {user['permissions_added_to_role']} permission(s) added)"
        )

    if config.generated_password:
        print("Generated a password for new users. Set AUTH0_TEST_PASSWORD to reuse a known password.")
    else:
        print("Used AUTH0_TEST_PASSWORD for any newly created users.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
